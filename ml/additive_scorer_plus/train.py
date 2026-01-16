"""
FoodScore+ Training Script (v2 - Lightweight)

Trains the lightweight additive risk scorer with:
- Character n-gram text features
- Categorical embeddings
- ~50K parameters
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from pathlib import Path
from typing import Tuple, Dict, List
import argparse
import logging
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.additive_scorer_plus.model import AdditiveRiskScorerPlus
from ml.additive_scorer_plus.dataset import load_additive_data_plus, split_data_plus
from ml.training_utils import (
    setup_device, compute_gradient_stats, GradientStats,
    TrainingTracker, log_batch, log_epoch_summary, log_final_metrics, log_training_start,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Category mappings
TYPE_TO_IDX = {"dye": 0, "sweetener": 1, "preservative": 2, "emulsifier": 3, "flavor": 4, "other": 5}
FDA_TO_IDX = {"approved": 0, "banned": 1}
EU_TO_IDX = {"approved": 0, "restricted": 1, "banned": 2}


class AdditivePlusDataset(Dataset):
    """Simple dataset for FoodScore+."""

    def __init__(self, df):
        self.names = df['name'].tolist()
        self.types = [TYPE_TO_IDX.get(t.lower(), 5) for t in df['type']]
        self.fda = [FDA_TO_IDX.get(s.lower(), 0) for s in df['fda_status']]
        self.eu = [EU_TO_IDX.get(s.lower(), 0) for s in df['eu_status']]
        self.is_art = df['is_artificial'].fillna(False).astype(float).tolist()
        self.is_pet = df['is_petroleum_based'].fillna(False).astype(float).tolist()
        self.labels = df['risk_score'].values.astype(np.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            'name': self.names[idx],
            'type_idx': self.types[idx],
            'fda_idx': self.fda[idx],
            'eu_idx': self.eu[idx],
            'is_artificial': self.is_art[idx],
            'is_petroleum': self.is_pet[idx],
            'label': self.labels[idx],
        }


def collate_fn(batch):
    """Custom collate function."""
    return {
        'names': [b['name'] for b in batch],
        'type_idx': torch.tensor([b['type_idx'] for b in batch], dtype=torch.long),
        'fda_idx': torch.tensor([b['fda_idx'] for b in batch], dtype=torch.long),
        'eu_idx': torch.tensor([b['eu_idx'] for b in batch], dtype=torch.long),
        'binary': torch.tensor([[b['is_artificial'], b['is_petroleum']] for b in batch], dtype=torch.float32),
        'labels': torch.tensor([b['label'] for b in batch], dtype=torch.float32),
    }


class WeightedMSELoss(nn.Module):
    """
    MSE Loss with sample weighting based on risk category.

    High-risk samples (>=70) get higher weight to force model
    to learn these cases instead of always predicting moderate.
    """

    def __init__(self, low_weight: float = 1.0, mid_weight: float = 1.5, high_weight: float = 4.0):
        super().__init__()
        self.low_weight = low_weight
        self.mid_weight = mid_weight
        self.high_weight = high_weight

    def forward(self, predictions: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # Compute per-sample weights based on target risk score
        weights = torch.ones_like(targets)

        # Low risk (<30)
        low_mask = targets < 30
        weights[low_mask] = self.low_weight

        # Moderate risk (30-70)
        mid_mask = (targets >= 30) & (targets < 70)
        weights[mid_mask] = self.mid_weight

        # High risk (>=70)
        high_mask = targets >= 70
        weights[high_mask] = self.high_weight

        # Weighted MSE
        squared_errors = (predictions - targets) ** 2
        weighted_loss = (weights * squared_errors).mean()

        return weighted_loss


def compute_metrics(predictions: np.ndarray, labels: np.ndarray) -> Dict:
    """Compute comprehensive regression metrics."""
    mse = mean_squared_error(labels, predictions)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(labels, predictions)
    r2 = r2_score(labels, predictions)

    pearson_r, _ = stats.pearsonr(predictions, labels)
    spearman_r, _ = stats.spearmanr(predictions, labels)

    errors = np.abs(predictions - labels)

    # Category accuracy
    def to_cat(s): return 0 if s < 30 else (1 if s < 70 else 2)
    pred_cats = np.array([to_cat(p) for p in predictions])
    true_cats = np.array([to_cat(l) for l in labels])
    category_accuracy = (pred_cats == true_cats).mean()

    per_category = {}
    for i, name in enumerate(["low", "moderate", "high"]):
        mask = true_cats == i
        if mask.sum() > 0:
            per_category[name] = {
                "count": int(mask.sum()),
                "accuracy": float((pred_cats[mask] == i).mean()),
                "mean_error": float(np.mean(errors[mask])),
            }

    return {
        "mse": float(mse), "rmse": float(rmse), "mae": float(mae), "r2": float(r2),
        "pearson_r": float(pearson_r), "spearman_r": float(spearman_r),
        "category_accuracy": float(category_accuracy),
        "per_category": per_category,
    }


def train_epoch(
    model: AdditiveRiskScorerPlus,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
    log_interval: int = 5,
) -> Tuple[float, Dict, GradientStats]:
    """Train one epoch."""
    model.train()
    total_loss = 0
    total = 0
    all_preds, all_labels = [], []
    all_grad_stats = []

    num_batches = len(dataloader)
    lr = optimizer.param_groups[0]["lr"]

    for batch_idx, batch in enumerate(dataloader):
        names = batch['names']
        type_idx = batch['type_idx'].to(device)
        fda_idx = batch['fda_idx'].to(device)
        eu_idx = batch['eu_idx'].to(device)
        binary = batch['binary'].to(device)
        labels = batch['labels'].to(device)

        pred = model(names, type_idx, fda_idx, eu_idx, binary)
        loss = loss_fn(pred, labels)

        optimizer.zero_grad()
        loss.backward()

        grad_stats = compute_gradient_stats(model)
        all_grad_stats.append(grad_stats)

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        batch_loss = loss.item()
        total_loss += batch_loss * len(labels)
        total += len(labels)

        all_preds.extend(pred.detach().cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

        if batch_idx % log_interval == 0 or batch_idx == num_batches - 1:
            mae = np.mean(np.abs(np.array(all_preds[-len(labels):]) - labels.cpu().numpy()))
            log_batch(epoch, batch_idx, num_batches, batch_loss,
                     {"mae": mae, "running_loss": total_loss / total},
                     grad_stats, lr)

    avg_grad = GradientStats(
        total_norm=np.mean([g.total_norm for g in all_grad_stats]),
        max_norm=np.max([g.max_norm for g in all_grad_stats]),
        min_norm=np.min([g.min_norm for g in all_grad_stats]),
        mean_norm=np.mean([g.mean_norm for g in all_grad_stats]),
    )

    train_metrics = compute_metrics(np.array(all_preds), np.array(all_labels))
    return total_loss / total, train_metrics, avg_grad


def evaluate(
    model: AdditiveRiskScorerPlus,
    dataloader: DataLoader,
    loss_fn: nn.Module,
    device: str,
) -> Tuple[float, Dict]:
    """Evaluate model."""
    model.eval()
    total_loss = 0
    total = 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for batch in dataloader:
            names = batch['names']
            type_idx = batch['type_idx'].to(device)
            fda_idx = batch['fda_idx'].to(device)
            eu_idx = batch['eu_idx'].to(device)
            binary = batch['binary'].to(device)
            labels = batch['labels'].to(device)

            pred = model(names, type_idx, fda_idx, eu_idx, binary)
            loss = loss_fn(pred, labels)

            total_loss += loss.item() * len(labels)
            total += len(labels)

            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    metrics = compute_metrics(np.array(all_preds), np.array(all_labels))
    metrics["loss"] = total_loss / total
    return total_loss / total, metrics


def main(
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 1e-3,
    device: str = None,
    output_path: str = None,
):
    """Main training function."""
    output_path = output_path or str(Path(__file__).parent.parent / "weights" / "additive_scorer_plus.pt")
    log_interval = 5

    device, gpu_info = setup_device(device or "cuda")

    # Load data
    logger.info("Loading additive data...")
    df = load_additive_data_plus()
    train_df, val_df, test_df = split_data_plus(df)

    # Create datasets
    train_ds = AdditivePlusDataset(train_df)
    val_ds = AdditivePlusDataset(val_df)
    test_ds = AdditivePlusDataset(test_df)

    # Create weighted sampler to oversample high-risk additives
    # This helps balance training - high-risk (>=70) sampled 3x more often
    train_labels = train_df['risk_score'].values
    sample_weights = np.ones(len(train_labels))
    sample_weights[train_labels < 30] = 1.0      # Low risk
    sample_weights[(train_labels >= 30) & (train_labels < 70)] = 1.5  # Moderate
    sample_weights[train_labels >= 70] = 3.0    # High risk - oversample 3x

    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(train_labels) * 2,  # 2 epochs worth of samples per epoch
        replacement=True
    )

    logger.info(f"Sample weights: low={np.sum(train_labels < 30)} (1x), "
                f"mid={np.sum((train_labels >= 30) & (train_labels < 70))} (1.5x), "
                f"high={np.sum(train_labels >= 70)} (3x oversample)")

    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)

    # Model
    logger.info("Creating FoodScore+ model (lightweight)...")
    model = AdditiveRiskScorerPlus(
        ngram_vocab_size=1000,
        ngram_embedding_dim=64,
        text_output_dim=128,
        cat_embedding_dim=16,
        hidden_dims=(128, 64),
        dropout=0.3,
    ).to(device)

    # Fit text encoder on training names
    model.fit_text_encoder(train_df['name'].tolist())
    logger.info(f"Built n-gram vocabulary: {len(model.text_encoder.ngram_to_idx)} n-grams")

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    # Log config
    train_config = {
        "model": "FoodScore+ Lightweight",
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "ngram_vocab": 1000,
        "hidden_dims": [128, 64],
        "dropout": 0.3,
        "loss_weights": {"low": 1.0, "mid": 1.5, "high": 4.0},
        "oversampling": {"low": 1.0, "mid": 1.5, "high": 3.0},
    }
    log_training_start("FoodScore+ (Lightweight)", train_config, gpu_info, model,
                       len(train_df), len(val_df), len(test_df))

    logger.info(f"Parameters: {total_params:,} total ({trainable_params:,} trainable)")

    # Tracker
    tracker = TrainingTracker("additive_scorer_plus", Path(output_path).parent)
    tracker.config = train_config
    tracker.gpu_info = gpu_info

    # Loss with sample weighting - high-risk samples weighted 4x more
    # This fixes the 0% high-risk accuracy by forcing model to learn high scores
    loss_fn = WeightedMSELoss(low_weight=1.0, mid_weight=1.5, high_weight=4.0)
    logger.info("Using weighted MSE loss: low=1.0, mid=1.5, high=4.0")

    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=10, verbose=True)

    # Training
    logger.info(f"\n{'='*70}\nSTARTING FOODSCORE+ TRAINING (LIGHTWEIGHT)\n{'='*70}\n")
    best_val_loss = float("inf")
    patience_counter = 0
    patience = 15

    for epoch in range(epochs):
        epoch_start = time.time()
        lr = optimizer.param_groups[0]["lr"]

        train_loss, train_metrics, grad_stats = train_epoch(
            model, train_loader, optimizer, loss_fn, device, epoch, log_interval
        )
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device)

        epoch_duration = time.time() - epoch_start
        is_best = val_loss < best_val_loss

        # Log
        log_epoch_summary(
            epoch, epochs, train_loss, val_loss,
            {k: train_metrics[k] for k in ['mae', 'rmse', 'r2', 'pearson_r', 'category_accuracy']},
            {k: val_metrics[k] for k in ['mae', 'rmse', 'r2', 'pearson_r', 'category_accuracy']},
            grad_stats, lr, epoch_duration, is_best
        )

        tracker.log_epoch(epoch, train_loss, val_loss, train_metrics, val_metrics,
                         grad_stats, lr, epoch_duration, is_best)

        scheduler.step(val_loss)

        if is_best:
            best_val_loss = val_loss
            model.save(output_path)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"\nEarly stopping at epoch {epoch + 1}")
                break

    # Final evaluation
    logger.info(f"\n{'='*70}\nFINAL TEST EVALUATION\n{'='*70}")
    model = AdditiveRiskScorerPlus.load(output_path, device=device)
    test_loss, test_metrics = evaluate(model, test_loader, loss_fn, device)
    log_final_metrics("TEST", test_metrics)

    history_path = tracker.save(test_metrics)

    logger.info(f"\n{'='*70}\nFOODSCORE+ TRAINING COMPLETE\n{'='*70}")
    logger.info(f"Model: {output_path}")
    logger.info(f"History: {history_path}")

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train FoodScore+ (Lightweight)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--device", type=str)
    parser.add_argument("--output", type=str)
    args = parser.parse_args()

    main(args.epochs, args.batch_size, args.learning_rate, args.device, args.output)
