"""
Training Script for NOVA Food Classifier

Trains a custom CNN to classify food products into NOVA 1-4
based on ingredient lists.

NO SYNTHETIC DATA - Uses only real OpenFoodFacts data.

Usage:
    python -m ml.nova_classifier.train
    python -m ml.nova_classifier.train --epochs 30 --batch-size 128
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from pathlib import Path
from typing import Tuple, Dict
import argparse
import logging
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import NOVA_CLASSIFIER_CONFIG
from ml.nova_classifier.model import NovaClassifier, TemperatureScaledNovaClassifier
from ml.nova_classifier.tokenizer import IngredientTokenizer
from ml.nova_classifier.dataset import (
    NovaDataset, load_openfoodfacts_data, load_processed_data, split_data, compute_class_weights,
)
from ml.training_utils import (
    setup_device, log_gpu_info, get_memory_stats,
    compute_gradient_stats, GradientStats,
    TrainingTracker, log_batch, log_epoch_summary, log_final_metrics, log_training_start,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

NOVA_NAMES = ["NOVA 1", "NOVA 2", "NOVA 3", "NOVA 4"]


def compute_metrics(predictions: np.ndarray, labels: np.ndarray, probabilities: np.ndarray = None) -> Dict:
    """Compute comprehensive classification metrics (10+)."""
    accuracy = (predictions == labels).mean()

    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=[0, 1, 2, 3], zero_division=0
    )
    macro_f1 = f1.mean()
    weighted_f1 = np.average(f1, weights=support)
    macro_precision = precision.mean()
    macro_recall = recall.mean()

    cm = confusion_matrix(labels, predictions, labels=[0, 1, 2, 3])

    # Per-class
    per_class = {}
    for i, name in enumerate(NOVA_NAMES):
        per_class[name] = {
            "precision": float(precision[i]), "recall": float(recall[i]),
            "f1": float(f1[i]), "support": int(support[i]),
        }

    metrics = {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1), "weighted_f1": float(weighted_f1),
        "macro_precision": float(macro_precision), "macro_recall": float(macro_recall),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }

    # Confidence metrics
    if probabilities is not None:
        max_probs = probabilities.max(axis=1)
        metrics["mean_confidence"] = float(max_probs.mean())
        metrics["confidence_when_correct"] = float(max_probs[predictions == labels].mean()) if (predictions == labels).any() else 0
        metrics["confidence_when_wrong"] = float(max_probs[predictions != labels].mean()) if (predictions != labels).any() else 0
        metrics["confidence_std"] = float(max_probs.std())

        # Expected Calibration Error (ECE)
        n_bins = 10
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for i in range(n_bins):
            in_bin = (max_probs > bin_boundaries[i]) & (max_probs <= bin_boundaries[i+1])
            if in_bin.sum() > 0:
                avg_conf = max_probs[in_bin].mean()
                avg_acc = (predictions[in_bin] == labels[in_bin]).mean()
                ece += in_bin.sum() * abs(avg_conf - avg_acc)
        metrics["ece"] = float(ece / len(predictions))

    return metrics


def train_epoch(
    model: NovaClassifier,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
    log_interval: int = 50,
) -> Tuple[float, Dict, GradientStats]:
    """Train one epoch with comprehensive logging."""
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    all_preds, all_labels, all_probs = [], [], []
    all_grad_stats = []

    num_batches = len(dataloader)
    lr = optimizer.param_groups[0]["lr"]

    for batch_idx, batch in enumerate(dataloader):
        input_ids = batch["input_ids"].to(device)
        labels = batch["labels"].to(device)

        logits = model(input_ids)
        loss = loss_fn(logits, labels)

        optimizer.zero_grad()
        loss.backward()

        grad_stats = compute_gradient_stats(model)
        all_grad_stats.append(grad_stats)

        if grad_stats.has_nan or grad_stats.has_inf:
            logger.warning(f"⚠️ Gradient issue at batch {batch_idx}")

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        batch_loss = loss.item()
        total_loss += batch_loss * len(labels)
        probs = torch.softmax(logits, dim=1)
        predictions = torch.argmax(logits, dim=1)
        batch_correct = (predictions == labels).sum().item()
        correct += batch_correct
        total += len(labels)

        all_preds.extend(predictions.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        all_probs.extend(probs.detach().cpu().numpy())

        if batch_idx % log_interval == 0 or batch_idx == num_batches - 1:
            log_batch(epoch, batch_idx, num_batches, batch_loss,
                     {"acc": correct/total, "batch_acc": batch_correct/len(labels)},
                     grad_stats, lr)

    avg_grad = GradientStats(
        total_norm=np.mean([g.total_norm for g in all_grad_stats]),
        max_norm=np.max([g.max_norm for g in all_grad_stats]),
        min_norm=np.min([g.min_norm for g in all_grad_stats]),
        mean_norm=np.mean([g.mean_norm for g in all_grad_stats]),
    )

    train_metrics = compute_metrics(np.array(all_preds), np.array(all_labels), np.array(all_probs))
    return total_loss / total, train_metrics, avg_grad


def evaluate(model: NovaClassifier, dataloader: DataLoader, loss_fn: nn.Module, device: str) -> Tuple[float, Dict]:
    """Evaluate with comprehensive metrics."""
    model.eval()
    total_loss = 0
    total = 0
    all_preds, all_labels, all_probs = [], [], []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            logits = model(input_ids)
            loss = loss_fn(logits, labels)
            probs = torch.softmax(logits, dim=1)

            total_loss += loss.item() * len(labels)
            total += len(labels)

            all_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    metrics = compute_metrics(np.array(all_preds), np.array(all_labels), np.array(all_probs))
    metrics["loss"] = total_loss / total
    return total_loss / total, metrics


def main(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
    output_path: str = None,
    use_processed: bool = True,
    sample_size: int = None,
):
    """Main training function."""
    config = NOVA_CLASSIFIER_CONFIG
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)
    log_interval = config.log_interval

    device, gpu_info = setup_device(device or config.device)

    # Load data
    logger.info("Loading training data...")
    processed_path = Path(__file__).parent.parent.parent / "data" / "processed" / "foodscore" / "nova_training_full.parquet"
    raw_path = config.training_data

    if use_processed and processed_path.exists():
        ingredients, labels = load_processed_data(processed_path, sample_size=sample_size)
    elif raw_path.exists():
        ingredients, labels = load_openfoodfacts_data(raw_path, sample_size=sample_size)
    else:
        raise FileNotFoundError(f"No data found at {processed_path} or {raw_path}")

    logger.info(f"Loaded {len(ingredients):,} products")

    # Split
    (train_ing, train_lab), (val_ing, val_lab), (test_ing, test_lab) = split_data(ingredients, labels)

    # Tokenizer
    tokenizer = IngredientTokenizer(vocab_size=config.vocab_size, max_length=config.max_length)
    tokenizer.fit(train_ing)
    tokenizer.save(str(config.tokenizer_path))

    # Datasets
    train_dataset = NovaDataset(train_ing, train_lab, tokenizer)
    val_dataset = NovaDataset(val_ing, val_lab, tokenizer)
    test_dataset = NovaDataset(test_ing, test_lab, tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Model
    model = NovaClassifier(
        vocab_size=tokenizer.actual_vocab_size,
        embedding_dim=config.embedding_dim,
        conv_filters=config.conv_filters,
        conv_kernel_size=config.conv_kernel_size,
        hidden_dims=tuple(config.hidden_dims),
        num_classes=config.num_classes,
        dropout=config.dropout,
    ).to(device)

    # Log config
    train_config = {
        "epochs": epochs, "batch_size": batch_size, "learning_rate": learning_rate,
        "vocab_size": tokenizer.actual_vocab_size, "max_length": config.max_length,
        "embedding_dim": config.embedding_dim, "conv_filters": config.conv_filters,
        "hidden_dims": list(config.hidden_dims), "dropout": config.dropout,
    }
    log_training_start("NOVA Classifier", train_config, gpu_info, model,
                       len(train_lab), len(val_lab), len(test_lab))

    # Class distribution
    for name, labs in [("Train", train_lab), ("Val", val_lab), ("Test", test_lab)]:
        counts = np.bincount(labs, minlength=4)
        logger.info(f"{name} dist: " + " | ".join([f"N{i+1}:{c:,}" for i, c in enumerate(counts)]))

    # Tracker
    tracker = TrainingTracker("nova_classifier", Path(output_path).parent)
    tracker.config = train_config
    tracker.gpu_info = gpu_info

    # Class weights, loss, optimizer
    class_weights = compute_class_weights(train_lab).to(device)
    logger.info(f"Class weights: {class_weights.cpu().numpy()}")
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = Adam(model.parameters(), lr=learning_rate)
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=3, verbose=True)

    # Training
    logger.info(f"\n{'='*70}\nSTARTING TRAINING\n{'='*70}\n")
    best_val_f1 = 0
    patience_counter = 0

    for epoch in range(epochs):
        epoch_start = time.time()
        lr = optimizer.param_groups[0]["lr"]

        train_loss, train_metrics, grad_stats = train_epoch(
            model, train_loader, optimizer, loss_fn, device, epoch, log_interval
        )
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device)

        epoch_duration = time.time() - epoch_start
        is_best = val_metrics['macro_f1'] > best_val_f1

        # Log (5-10 metrics)
        log_epoch_summary(
            epoch, epochs, train_loss, val_loss,
            {k: train_metrics[k] for k in ['accuracy', 'macro_f1', 'weighted_f1', 'macro_precision', 'macro_recall']},
            {k: val_metrics[k] for k in ['accuracy', 'macro_f1', 'weighted_f1', 'mean_confidence', 'ece']},
            grad_stats, lr, epoch_duration, is_best
        )

        tracker.log_epoch(epoch, train_loss, val_loss, train_metrics, val_metrics,
                         grad_stats, lr, epoch_duration, is_best)

        scheduler.step(val_loss)

        if is_best:
            best_val_f1 = val_metrics['macro_f1']
            model.save(output_path)
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"\nEarly stopping at epoch {epoch+1}")
                break

    # Final eval (10+ metrics)
    logger.info(f"\n{'='*70}\nFINAL TEST EVALUATION\n{'='*70}")
    model = NovaClassifier.load(output_path, device=device)
    test_loss, test_metrics = evaluate(model, test_loader, loss_fn, device)
    log_final_metrics("TEST", test_metrics, NOVA_NAMES)

    # Calibration
    logger.info("Calibrating with temperature scaling...")
    calibrated = TemperatureScaledNovaClassifier(model)
    calibrated.calibrate(val_loader, device=device)
    torch.save({"temperature": calibrated.temperature.item()},
               str(config.output_model).replace(".pt", "_temperature.pt"))

    history_path = tracker.save(test_metrics)

    logger.info(f"\n{'='*70}\nTRAINING COMPLETE\n{'='*70}")
    logger.info(f"Model: {output_path}")
    logger.info(f"History: {history_path}")

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train NOVA Classifier")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--device", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--use-raw", action="store_true")
    parser.add_argument("--sample-size", type=int)
    args = parser.parse_args()

    main(args.epochs, args.batch_size, args.learning_rate, args.device, args.output,
         not args.use_raw, args.sample_size)
