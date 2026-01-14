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
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
)
from pathlib import Path
from typing import Tuple, Dict
import argparse
import logging
import json
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import ADDITIVE_SCORER_CONFIG
from ml.additive_scorer.model import AdditiveRiskScorer, AdditiveFeatureEncoder
from ml.additive_scorer.dataset import (
    AdditiveDataset,
    load_additive_csv,
    prepare_features,
    split_data,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def compute_metrics(predictions: np.ndarray, labels: np.ndarray) -> Dict:
    """
    Compute comprehensive regression metrics.

    Args:
        predictions: Model predictions
        labels: True labels

    Returns:
        Dict with all metrics
    """
    # Basic regression metrics
    mse = mean_squared_error(labels, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(labels, predictions)
    r2 = r2_score(labels, predictions)

    # Correlation metrics
    pearson_r, pearson_p = stats.pearsonr(predictions, labels)
    spearman_r, spearman_p = stats.spearmanr(predictions, labels)

    # Error distribution
    errors = predictions - labels
    max_error = np.max(np.abs(errors))
    std_error = np.std(errors)

    # Category accuracy (low < 30, moderate 30-70, high > 70)
    def to_category(score):
        if score < 30:
            return 0  # low
        elif score < 70:
            return 1  # moderate
        else:
            return 2  # high

    pred_cats = np.array([to_category(p) for p in predictions])
    true_cats = np.array([to_category(l) for l in labels])
    category_accuracy = (pred_cats == true_cats).mean()

    # Per-category accuracy
    category_names = ["low", "moderate", "high"]
    per_category = {}
    for i, name in enumerate(category_names):
        mask = true_cats == i
        if mask.sum() > 0:
            per_category[name] = {
                "count": int(mask.sum()),
                "accuracy": float((pred_cats[mask] == i).mean()),
                "mean_error": float(np.mean(np.abs(errors[mask]))),
            }

    return {
        "mse": float(mse),
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
        "pearson_r": float(pearson_r),
        "pearson_p": float(pearson_p),
        "spearman_r": float(spearman_r),
        "spearman_p": float(spearman_p),
        "max_error": float(max_error),
        "std_error": float(std_error),
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
) -> Tuple[float, float, Dict]:
    """
    Train for one epoch with detailed logging.

    Returns:
        avg_loss, avg_mae, gradient_info
    """
    model.train()
    total_loss = 0
    total_mae = 0
    total = 0

    all_predictions = []
    all_labels = []
    gradient_norms = []

    num_batches = len(dataloader)

    for batch_idx, batch in enumerate(dataloader):
        features = batch["features"].to(device)
        labels = batch["labels"].to(device)

        # Forward pass
        predictions = model(features).squeeze(-1)
        loss = loss_fn(predictions, labels)

        # Backward pass
        optimizer.zero_grad()
        loss.backward()

        # Compute gradient norm before clipping
        total_norm = 0
        for p in model.parameters():
            if p.grad is not None:
                param_norm = p.grad.data.norm(2)
                total_norm += param_norm.item() ** 2
        total_norm = total_norm ** 0.5
        gradient_norms.append(total_norm)

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        # Track metrics
        batch_loss = loss.item()
        batch_mae = torch.abs(predictions - labels).mean().item()
        total_loss += batch_loss * len(labels)
        total_mae += torch.abs(predictions - labels).sum().item()
        total += len(labels)

        all_predictions.extend(predictions.detach().cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

        # Log every batch
        if batch_idx % 10 == 0 or batch_idx == num_batches - 1:
            logger.info(
                f"Epoch {epoch+1} | Batch {batch_idx+1}/{num_batches} | "
                f"Loss: {batch_loss:.4f} | MAE: {batch_mae:.2f} | "
                f"Grad Norm: {total_norm:.4f}"
            )

    gradient_info = {
        "mean_grad_norm": float(np.mean(gradient_norms)),
        "max_grad_norm": float(np.max(gradient_norms)),
        "min_grad_norm": float(np.min(gradient_norms)),
    }

    return total_loss / total, total_mae / total, gradient_info


def evaluate(
    model: AdditiveRiskScorer,
    dataloader: DataLoader,
    loss_fn: nn.Module,
    device: str,
    split_name: str = "Val",
) -> Tuple[float, Dict]:
    """
    Evaluate model with comprehensive metrics.

    Returns:
        avg_loss, metrics_dict
    """
    model.eval()
    total_loss = 0
    total = 0

    all_predictions = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            features = batch["features"].to(device)
            labels = batch["labels"].to(device)

            predictions = model(features).squeeze(-1)
            loss = loss_fn(predictions, labels)

            total_loss += loss.item() * len(labels)
            total += len(labels)

            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    predictions = np.array(all_predictions)
    labels = np.array(all_labels)

    metrics = compute_metrics(predictions, labels)
    metrics["loss"] = total_loss / total

    return total_loss / total, metrics


def log_validation_results(metrics: Dict, split_name: str, epoch: int):
    """Log comprehensive validation results."""
    logger.info(f"\n{'='*60}")
    logger.info(f"{split_name} Results - Epoch {epoch+1}")
    logger.info(f"{'='*60}")
    logger.info(f"  Loss (MSE): {metrics['mse']:.4f}")
    logger.info(f"  RMSE: {metrics['rmse']:.4f}")
    logger.info(f"  MAE: {metrics['mae']:.2f}")
    logger.info(f"  R²: {metrics['r2']:.4f}")
    logger.info(f"  Pearson r: {metrics['pearson_r']:.4f} (p={metrics['pearson_p']:.2e})")
    logger.info(f"  Spearman r: {metrics['spearman_r']:.4f} (p={metrics['spearman_p']:.2e})")
    logger.info(f"  Max Error: {metrics['max_error']:.2f}")
    logger.info(f"  Category Accuracy: {metrics['category_accuracy']:.1%}")

    if "per_category" in metrics:
        logger.info(f"  Per-Category Breakdown:")
        for cat, info in metrics["per_category"].items():
            logger.info(f"    {cat}: n={info['count']}, acc={info['accuracy']:.1%}, mae={info['mean_error']:.2f}")
    logger.info(f"{'='*60}\n")


def main(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
    output_path: str = None,
):
    """Main training function."""
    config = ADDITIVE_SCORER_CONFIG

    # Override with arguments
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)

    # Device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(f"{'='*60}")
    logger.info("ADDITIVE RISK SCORER TRAINING")
    logger.info(f"{'='*60}")
    logger.info(f"Device: {device}")
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Batch Size: {batch_size}")
    logger.info(f"Learning Rate: {learning_rate}")
    logger.info(f"Output Path: {output_path}")

    # Load REAL data only - NO SYNTHETIC
    logger.info("\nLoading training data from additive_risks.csv...")
    csv_path = Path(__file__).parent.parent.parent / "data" / "raw" / "foodscore" / "additive_risks.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Required data file not found: {csv_path}")

    df = load_additive_csv(csv_path)
    logger.info(f"Loaded {len(df)} additives from real data")

    # Extract features
    features, labels, feature_info = prepare_features(df)
    logger.info(f"Feature dimension: {feature_info['n_features']}")
    logger.info(f"Label range: {labels.min():.1f} - {labels.max():.1f}")

    # Split data
    logger.info("\nSplitting data into train/val/test...")
    (train_features, train_labels), (val_features, val_labels), (test_features, test_labels) = split_data(
        features, labels, train_ratio=0.7, val_ratio=0.15
    )

    logger.info(f"Train: {len(train_labels)} samples")
    logger.info(f"Val: {len(val_labels)} samples")
    logger.info(f"Test: {len(test_labels)} samples")

    # Create datasets
    train_dataset = AdditiveDataset(train_features, train_labels)
    val_dataset = AdditiveDataset(val_features, val_labels)
    test_dataset = AdditiveDataset(test_features, test_labels)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # Initialize model
    logger.info("\nInitializing model...")
    model = AdditiveRiskScorer(
        input_features=feature_info["n_features"],
        hidden_dims=tuple(config.hidden_dims),
        dropout=config.dropout,
    )
    model.to(device)

    logger.info(f"Model Architecture:")
    logger.info(f"  Input: {feature_info['n_features']} features")
    logger.info(f"  Hidden: {config.hidden_dims}")
    logger.info(f"  Dropout: {config.dropout}")
    logger.info(f"  Output: 1 (risk score 0-100)")

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"  Total Parameters: {total_params:,}")
    logger.info(f"  Trainable Parameters: {trainable_params:,}")

    # Loss and optimizer
    loss_fn = nn.MSELoss()
    optimizer = Adam(model.parameters(), lr=learning_rate)
    scheduler = ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=20, verbose=True
    )

    # Training history
    history = {
        "train_loss": [],
        "val_loss": [],
        "val_metrics": [],
        "gradients": [],
        "learning_rates": [],
    }

    # Training loop
    logger.info(f"\n{'='*60}")
    logger.info("STARTING TRAINING")
    logger.info(f"{'='*60}\n")

    best_val_loss = float("inf")
    patience_counter = 0
    early_stopping_patience = config.early_stopping_patience

    for epoch in range(epochs):
        current_lr = optimizer.param_groups[0]["lr"]
        logger.info(f"\nEpoch {epoch+1}/{epochs} | LR: {current_lr:.2e}")
        logger.info("-" * 40)

        # Train
        train_loss, train_mae, grad_info = train_epoch(
            model, train_loader, optimizer, loss_fn, device, epoch
        )

        # Validate
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device, "Validation")

        # Log results
        logger.info(f"\nEpoch {epoch+1} Summary:")
        logger.info(f"  Train Loss: {train_loss:.4f} | Train MAE: {train_mae:.2f}")
        logger.info(f"  Val Loss: {val_loss:.4f} | Val MAE: {val_metrics['mae']:.2f}")
        logger.info(f"  Val R²: {val_metrics['r2']:.4f} | Val Pearson: {val_metrics['pearson_r']:.4f}")
        logger.info(f"  Gradient Norm (mean/max): {grad_info['mean_grad_norm']:.4f}/{grad_info['max_grad_norm']:.4f}")

        # Full validation suite every 10 epochs
        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            log_validation_results(val_metrics, "Validation", epoch)

        # Record history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_metrics"].append(val_metrics)
        history["gradients"].append(grad_info)
        history["learning_rates"].append(current_lr)

        # Scheduler step
        scheduler.step(val_loss)

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save(output_path)
            logger.info(f"  *** New best model saved (val_loss={val_loss:.4f})")
            patience_counter = 0
        else:
            patience_counter += 1
            logger.info(f"  No improvement ({patience_counter}/{early_stopping_patience})")

        # Early stopping
        if patience_counter >= early_stopping_patience:
            logger.info(f"\nEarly stopping triggered after {epoch+1} epochs")
            break

    # Load best model for final evaluation
    logger.info("\nLoading best model for final evaluation...")
    model = AdditiveRiskScorer.load(output_path, device=device)

    # Final test evaluation
    logger.info(f"\n{'='*60}")
    logger.info("FINAL TEST SET EVALUATION")
    logger.info(f"{'='*60}")

    test_loss, test_metrics = evaluate(model, test_loader, loss_fn, device, "Test")
    log_validation_results(test_metrics, "TEST", epochs - 1)

    # Additional test analysis
    logger.info("\nDetailed Test Analysis:")
    logger.info(f"  Samples in test set: {len(test_labels)}")
    logger.info(f"  MSE: {test_metrics['mse']:.4f}")
    logger.info(f"  RMSE: {test_metrics['rmse']:.4f}")
    logger.info(f"  MAE: {test_metrics['mae']:.2f}")
    logger.info(f"  R² Score: {test_metrics['r2']:.4f}")
    logger.info(f"  Pearson Correlation: {test_metrics['pearson_r']:.4f}")
    logger.info(f"  Spearman Correlation: {test_metrics['spearman_r']:.4f}")
    logger.info(f"  Category Accuracy: {test_metrics['category_accuracy']:.1%}")

    # Save encoder
    encoder = AdditiveFeatureEncoder()
    encoder_path = str(config.output_model).replace(".pt", "_encoder.json")
    encoder.save(encoder_path)

    # Save training history
    history_path = str(config.output_model).replace(".pt", "_history.json")
    with open(history_path, "w") as f:
        json.dump({
            "config": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "hidden_dims": list(config.hidden_dims),
            },
            "final_test_metrics": test_metrics,
            "best_val_loss": best_val_loss,
            "trained_at": datetime.now().isoformat(),
        }, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("TRAINING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Model saved to: {output_path}")
    logger.info(f"Encoder saved to: {encoder_path}")
    logger.info(f"History saved to: {history_path}")

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Additive Risk Scorer")
    parser.add_argument("--epochs", type=int, default=200, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--learning-rate", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--device", type=str, help="Device (cuda/cpu)")
    parser.add_argument("--output", type=str, help="Output model path")

    args = parser.parse_args()

    main(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        device=args.device,
        output_path=args.output,
    )
