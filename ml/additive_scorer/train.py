"""
Training Script for Additive Risk Scorer

Trains an MLP to predict additive risk scores (0-100) based on
regulatory status, type, and chemical properties.

NO SYNTHETIC DATA - Uses only real additive_risks.csv data.

Usage:
    python -m ml.additive_scorer.train
    python -m ml.additive_scorer.train --epochs 200 --batch-size 16
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from pathlib import Path
from typing import Tuple, Dict
import argparse
import logging
import time
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import ADDITIVE_SCORER_CONFIG
from ml.additive_scorer.model import AdditiveRiskScorer, AdditiveFeatureEncoder
from ml.additive_scorer.dataset import (
    AdditiveDataset, load_additive_csv, prepare_features, split_data,
)
from ml.training_utils import (
    setup_device, get_gpu_info, log_gpu_info, get_memory_stats,
    compute_gradient_stats, GradientStats,
    TrainingTracker, log_batch, log_epoch_summary, log_final_metrics, log_training_start,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def compute_metrics(predictions: np.ndarray, labels: np.ndarray) -> Dict:
    """Compute comprehensive regression metrics (10+)."""
    mse = mean_squared_error(labels, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(labels, predictions)
    r2 = r2_score(labels, predictions)

    # Correlations
    pearson_r, pearson_p = stats.pearsonr(predictions, labels)
    spearman_r, spearman_p = stats.spearmanr(predictions, labels)

    # Error distribution
    errors = predictions - labels
    max_error = np.max(np.abs(errors))
    std_error = np.std(errors)
    median_error = np.median(np.abs(errors))

    # Category accuracy (low < 30, moderate 30-70, high > 70)
    def to_cat(s): return 0 if s < 30 else (1 if s < 70 else 2)
    pred_cats = np.array([to_cat(p) for p in predictions])
    true_cats = np.array([to_cat(l) for l in labels])
    category_accuracy = (pred_cats == true_cats).mean()

    # Per-category
    per_category = {}
    for i, name in enumerate(["low", "moderate", "high"]):
        mask = true_cats == i
        if mask.sum() > 0:
            per_category[name] = {
                "count": int(mask.sum()),
                "accuracy": float((pred_cats[mask] == i).mean()),
                "mean_error": float(np.mean(np.abs(errors[mask]))),
            }

    return {
        "mse": float(mse), "rmse": float(rmse), "mae": float(mae), "r2": float(r2),
        "pearson_r": float(pearson_r), "pearson_p": float(pearson_p),
        "spearman_r": float(spearman_r), "spearman_p": float(spearman_p),
        "max_error": float(max_error), "std_error": float(std_error),
        "median_error": float(median_error),
        "category_accuracy": float(category_accuracy),
        "per_category": per_category,
    }


def train_epoch(
    model: AdditiveRiskScorer,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
    log_interval: int = 5,
) -> Tuple[float, Dict, GradientStats]:
    """Train one epoch with comprehensive logging."""
    model.train()
    total_loss = 0
    total_mae = 0
    total = 0
    all_preds, all_labels = [], []
    all_grad_stats = []

    num_batches = len(dataloader)
    lr = optimizer.param_groups[0]["lr"]

    for batch_idx, batch in enumerate(dataloader):
        features = batch["features"].to(device)
        labels = batch["labels"].to(device)

        # Forward
        predictions = model(features).squeeze(-1)
        loss = loss_fn(predictions, labels)

        # Backward
        optimizer.zero_grad()
        loss.backward()

        # Gradient stats
        grad_stats = compute_gradient_stats(model)
        all_grad_stats.append(grad_stats)

        if grad_stats.has_nan or grad_stats.has_inf:
            logger.warning(f"⚠️ Gradient issue at batch {batch_idx}: NaN={grad_stats.has_nan}, Inf={grad_stats.has_inf}")

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        # Track
        batch_loss = loss.item()
        batch_mae = torch.abs(predictions - labels).mean().item()
        total_loss += batch_loss * len(labels)
        total_mae += torch.abs(predictions - labels).sum().item()
        total += len(labels)

        all_preds.extend(predictions.detach().cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

        # Log batch
        if batch_idx % log_interval == 0 or batch_idx == num_batches - 1:
            log_batch(epoch, batch_idx, num_batches, batch_loss,
                     {"mae": batch_mae, "running_loss": total_loss/total},
                     grad_stats, lr)

    # Aggregate gradient stats
    avg_grad = GradientStats(
        total_norm=np.mean([g.total_norm for g in all_grad_stats]),
        max_norm=np.max([g.max_norm for g in all_grad_stats]),
        min_norm=np.min([g.min_norm for g in all_grad_stats]),
        mean_norm=np.mean([g.mean_norm for g in all_grad_stats]),
    )

    # Train metrics
    train_metrics = compute_metrics(np.array(all_preds), np.array(all_labels))

    return total_loss / total, train_metrics, avg_grad


def evaluate(model: AdditiveRiskScorer, dataloader: DataLoader, loss_fn: nn.Module, device: str) -> Tuple[float, Dict]:
    """Evaluate with comprehensive metrics."""
    model.eval()
    total_loss = 0
    total = 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in dataloader:
            features = batch["features"].to(device)
            labels = batch["labels"].to(device)
            predictions = model(features).squeeze(-1)
            loss = loss_fn(predictions, labels)

            total_loss += loss.item() * len(labels)
            total += len(labels)
            all_preds.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    metrics = compute_metrics(np.array(all_preds), np.array(all_labels))
    metrics["loss"] = total_loss / total
    return total_loss / total, metrics


def main(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
    output_path: str = None,
):
    """Main training function."""
    config = ADDITIVE_SCORER_CONFIG
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)
    log_interval = config.log_interval

    # Setup device (GPU)
    device, gpu_info = setup_device(device or config.device)

    # Load data - prefer parquet (125 additives) over CSV (42)
    df = load_additive_csv()  # Now auto-loads parquet if available
    features, labels, feature_info = prepare_features(df)

    # Split
    (train_f, train_l), (val_f, val_l), (test_f, test_l) = split_data(features, labels, 0.7, 0.15)

    # Datasets
    train_dataset = AdditiveDataset(train_f, train_l)
    val_dataset = AdditiveDataset(val_f, val_l)
    test_dataset = AdditiveDataset(test_f, test_l)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # Model
    model = AdditiveRiskScorer(
        input_features=feature_info["n_features"],
        hidden_dims=tuple(config.hidden_dims),
        dropout=config.dropout,
    ).to(device)

    # Log config
    train_config = {
        "epochs": epochs, "batch_size": batch_size, "learning_rate": learning_rate,
        "hidden_dims": list(config.hidden_dims), "dropout": config.dropout,
        "early_stopping": config.early_stopping_patience,
    }
    log_training_start("Additive Risk Scorer", train_config, gpu_info, model,
                       len(train_l), len(val_l), len(test_l))

    # Tracker
    tracker = TrainingTracker("additive_scorer", Path(output_path).parent)
    tracker.config = train_config
    tracker.gpu_info = gpu_info

    # Loss, optimizer, scheduler
    loss_fn = nn.MSELoss()
    optimizer = Adam(model.parameters(), lr=learning_rate)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=20, verbose=True)

    # Training
    logger.info(f"\n{'='*70}\nSTARTING TRAINING\n{'='*70}\n")
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        epoch_start = time.time()
        lr = optimizer.param_groups[0]["lr"]

        # Train
        train_loss, train_metrics, grad_stats = train_epoch(
            model, train_loader, optimizer, loss_fn, device, epoch, log_interval
        )

        # Validate
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device)

        epoch_duration = time.time() - epoch_start
        is_best = val_loss < best_val_loss

        # Log epoch (5-10 metrics)
        log_epoch_summary(
            epoch, epochs, train_loss, val_loss,
            {k: train_metrics[k] for k in ['mae', 'rmse', 'r2', 'pearson_r', 'category_accuracy']},
            {k: val_metrics[k] for k in ['mae', 'rmse', 'r2', 'pearson_r', 'category_accuracy']},
            grad_stats, lr, epoch_duration, is_best
        )

        # Track
        tracker.log_epoch(epoch, train_loss, val_loss, train_metrics, val_metrics,
                         grad_stats, lr, epoch_duration, is_best)

        scheduler.step(val_loss)

        # Save best
        if is_best:
            best_val_loss = val_loss
            model.save(output_path)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"\nEarly stopping at epoch {epoch+1}")
                break

    # Final evaluation (10+ metrics)
    logger.info(f"\n{'='*70}\nFINAL TEST EVALUATION\n{'='*70}")
    model = AdditiveRiskScorer.load(output_path, device=device)
    test_loss, test_metrics = evaluate(model, test_loader, loss_fn, device)
    log_final_metrics("TEST", test_metrics)

    # Save
    encoder = AdditiveFeatureEncoder()
    encoder.save(str(config.output_model).replace(".pt", "_encoder.json"))
    history_path = tracker.save(test_metrics)

    logger.info(f"\n{'='*70}\nTRAINING COMPLETE\n{'='*70}")
    logger.info(f"Model: {output_path}")
    logger.info(f"History: {history_path}")

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Additive Risk Scorer")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--device", type=str, help="cuda/cpu")
    parser.add_argument("--output", type=str)
    args = parser.parse_args()

    main(args.epochs, args.batch_size, args.learning_rate, args.device, args.output)
