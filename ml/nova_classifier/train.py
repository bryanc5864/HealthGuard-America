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
from scipy import stats
from sklearn.metrics import (
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)
from pathlib import Path
from typing import Tuple, Dict, List
import argparse
import logging
import json
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import NOVA_CLASSIFIER_CONFIG
from ml.nova_classifier.model import NovaClassifier, TemperatureScaledNovaClassifier
from ml.nova_classifier.tokenizer import IngredientTokenizer
from ml.nova_classifier.dataset import (
    NovaDataset,
    load_openfoodfacts_data,
    load_processed_data,
    split_data,
    compute_class_weights,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

NOVA_NAMES = ["NOVA 1", "NOVA 2", "NOVA 3", "NOVA 4"]


def compute_metrics(
    predictions: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray = None,
) -> Dict:
    """
    Compute comprehensive classification metrics.

    Args:
        predictions: Predicted classes (0-3)
        labels: True classes (0-3)
        probabilities: Class probabilities [n_samples, 4]

    Returns:
        Dict with all metrics
    """
    # Basic accuracy
    accuracy = (predictions == labels).mean()

    # Precision, recall, F1 per class
    precision, recall, f1, support = precision_recall_fscore_support(
        labels, predictions, labels=[0, 1, 2, 3], zero_division=0
    )

    # Macro and weighted averages
    macro_f1 = f1.mean()
    weighted_f1 = np.average(f1, weights=support)

    # Confusion matrix
    cm = confusion_matrix(labels, predictions, labels=[0, 1, 2, 3])

    # Per-class metrics
    per_class = {}
    for i, name in enumerate(NOVA_NAMES):
        per_class[name] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }

    metrics = {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }

    # Confidence metrics if probabilities provided
    if probabilities is not None:
        max_probs = probabilities.max(axis=1)
        metrics["mean_confidence"] = float(max_probs.mean())
        metrics["confidence_when_correct"] = float(max_probs[predictions == labels].mean())
        metrics["confidence_when_wrong"] = float(max_probs[predictions != labels].mean()) if (predictions != labels).any() else 0.0

    return metrics


def train_epoch(
    model: NovaClassifier,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
) -> Tuple[float, float, Dict]:
    """
    Train for one epoch with detailed logging.

    Returns:
        avg_loss, accuracy, gradient_info
    """
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    gradient_norms = []

    num_batches = len(dataloader)

    for batch_idx, batch in enumerate(dataloader):
        input_ids = batch["input_ids"].to(device)
        labels = batch["labels"].to(device)

        # Forward pass
        logits = model(input_ids)
        loss = loss_fn(logits, labels)

        # Backward pass
        optimizer.zero_grad()
        loss.backward()

        # Compute gradient norm
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
        total_loss += batch_loss * len(labels)
        predictions = torch.argmax(logits, dim=1)
        batch_correct = (predictions == labels).sum().item()
        correct += batch_correct
        total += len(labels)

        # Log every 50 batches
        if batch_idx % 50 == 0 or batch_idx == num_batches - 1:
            logger.info(
                f"Epoch {epoch+1} | Batch {batch_idx+1}/{num_batches} | "
                f"Loss: {batch_loss:.4f} | Acc: {correct/total:.2%} | "
                f"Grad Norm: {total_norm:.4f}"
            )

    gradient_info = {
        "mean_grad_norm": float(np.mean(gradient_norms)),
        "max_grad_norm": float(np.max(gradient_norms)),
        "min_grad_norm": float(np.min(gradient_norms)),
    }

    return total_loss / total, correct / total, gradient_info


def evaluate(
    model: NovaClassifier,
    dataloader: DataLoader,
    loss_fn: nn.Module,
    device: str,
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
    all_probs = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)

            logits = model(input_ids)
            loss = loss_fn(logits, labels)
            probs = torch.softmax(logits, dim=1)

            total_loss += loss.item() * len(labels)
            total += len(labels)

            predictions = torch.argmax(logits, dim=1)
            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    predictions = np.array(all_predictions)
    labels = np.array(all_labels)
    probs = np.array(all_probs)

    metrics = compute_metrics(predictions, labels, probs)
    metrics["loss"] = total_loss / total

    return total_loss / total, metrics


def log_validation_results(metrics: Dict, split_name: str, epoch: int):
    """Log comprehensive validation results."""
    logger.info(f"\n{'='*60}")
    logger.info(f"{split_name} Results - Epoch {epoch+1}")
    logger.info(f"{'='*60}")
    logger.info(f"  Loss: {metrics['loss']:.4f}")
    logger.info(f"  Accuracy: {metrics['accuracy']:.2%}")
    logger.info(f"  Macro F1: {metrics['macro_f1']:.4f}")
    logger.info(f"  Weighted F1: {metrics['weighted_f1']:.4f}")

    if "mean_confidence" in metrics:
        logger.info(f"  Mean Confidence: {metrics['mean_confidence']:.2%}")
        logger.info(f"  Confidence (correct): {metrics['confidence_when_correct']:.2%}")
        logger.info(f"  Confidence (wrong): {metrics['confidence_when_wrong']:.2%}")

    logger.info(f"\n  Per-Class Metrics:")
    for name, info in metrics["per_class"].items():
        logger.info(
            f"    {name}: P={info['precision']:.2%} R={info['recall']:.2%} "
            f"F1={info['f1']:.4f} (n={info['support']})"
        )

    if "confusion_matrix" in metrics:
        logger.info(f"\n  Confusion Matrix:")
        cm = np.array(metrics["confusion_matrix"])
        logger.info(f"           {'  '.join(NOVA_NAMES)}")
        for i, row in enumerate(cm):
            logger.info(f"    {NOVA_NAMES[i]}: {row}")

    logger.info(f"{'='*60}\n")


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

    # Override with arguments
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)

    # Device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(f"{'='*60}")
    logger.info("NOVA FOOD CLASSIFIER TRAINING")
    logger.info(f"{'='*60}")
    logger.info(f"Device: {device}")
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Batch Size: {batch_size}")
    logger.info(f"Learning Rate: {learning_rate}")
    logger.info(f"Output Path: {output_path}")

    # Load REAL data only - NO SYNTHETIC
    logger.info("\nLoading training data...")

    processed_path = Path(__file__).parent.parent.parent / "data" / "processed" / "foodscore" / "us_products_scored.parquet"
    raw_path = config.training_data

    if use_processed and processed_path.exists():
        logger.info(f"Loading from processed parquet: {processed_path}")
        ingredients, labels = load_processed_data(processed_path, sample_size=sample_size)
    elif raw_path.exists():
        logger.info(f"Loading from raw OpenFoodFacts: {raw_path}")
        ingredients, labels = load_openfoodfacts_data(raw_path, sample_size=sample_size)
    else:
        raise FileNotFoundError(
            f"No training data found. Expected:\n"
            f"  - {processed_path}\n"
            f"  - {raw_path}"
        )

    logger.info(f"Loaded {len(ingredients):,} products")

    # Split data with stratification
    logger.info("\nSplitting data...")
    (train_ing, train_labels), (val_ing, val_labels), (test_ing, test_labels) = split_data(
        ingredients, labels
    )

    logger.info(f"Train: {len(train_labels):,} | Val: {len(val_labels):,} | Test: {len(test_labels):,}")

    # Class distribution
    for split_name, split_labels in [("Train", train_labels), ("Val", val_labels), ("Test", test_labels)]:
        counts = np.bincount(split_labels, minlength=4)
        logger.info(f"{split_name} distribution: " + " | ".join([f"N{i+1}:{c}" for i, c in enumerate(counts)]))

    # Build tokenizer
    logger.info("\nBuilding tokenizer...")
    tokenizer = IngredientTokenizer(
        vocab_size=config.vocab_size,
        max_length=config.max_length,
    )
    tokenizer.fit(train_ing)
    tokenizer.save(str(config.tokenizer_path))
    logger.info(f"Tokenizer vocab size: {tokenizer.actual_vocab_size}")

    # Create datasets
    train_dataset = NovaDataset(train_ing, train_labels, tokenizer)
    val_dataset = NovaDataset(val_ing, val_labels, tokenizer)
    test_dataset = NovaDataset(test_ing, test_labels, tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Initialize model
    logger.info("\nInitializing model...")
    model = NovaClassifier(
        vocab_size=tokenizer.actual_vocab_size,
        embedding_dim=config.embedding_dim,
        conv_filters=config.conv_filters,
        conv_kernel_size=config.conv_kernel_size,
        hidden_dims=tuple(config.hidden_dims),
        num_classes=config.num_classes,
        dropout=config.dropout,
    )
    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model Architecture:")
    logger.info(f"  Embedding: {tokenizer.actual_vocab_size} x {config.embedding_dim}")
    logger.info(f"  Conv1D: {config.conv_filters} filters, kernel={config.conv_kernel_size}")
    logger.info(f"  Hidden: {config.hidden_dims}")
    logger.info(f"  Total Parameters: {total_params:,}")
    logger.info(f"  Trainable Parameters: {trainable_params:,}")

    # Class weights for imbalanced data
    class_weights = compute_class_weights(train_labels).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    logger.info(f"Class weights: {class_weights.cpu().numpy()}")

    # Optimizer and scheduler
    optimizer = Adam(model.parameters(), lr=learning_rate)
    scheduler = ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3, verbose=True
    )

    # Training loop
    logger.info(f"\n{'='*60}")
    logger.info("STARTING TRAINING")
    logger.info(f"{'='*60}\n")

    best_val_loss = float("inf")
    best_val_f1 = 0
    patience_counter = 0

    for epoch in range(epochs):
        current_lr = optimizer.param_groups[0]["lr"]
        logger.info(f"\nEpoch {epoch+1}/{epochs} | LR: {current_lr:.2e}")
        logger.info("-" * 40)

        # Train
        train_loss, train_acc, grad_info = train_epoch(
            model, train_loader, optimizer, loss_fn, device, epoch
        )

        # Validate
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device)

        # Log summary
        logger.info(f"\nEpoch {epoch+1} Summary:")
        logger.info(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2%}")
        logger.info(f"  Val Loss: {val_loss:.4f} | Val Acc: {val_metrics['accuracy']:.2%}")
        logger.info(f"  Val Macro F1: {val_metrics['macro_f1']:.4f}")
        logger.info(f"  Gradient Norm (mean/max): {grad_info['mean_grad_norm']:.4f}/{grad_info['max_grad_norm']:.4f}")

        # Full validation suite every 5 epochs
        if (epoch + 1) % 5 == 0 or epoch == epochs - 1:
            log_validation_results(val_metrics, "Validation", epoch)

        # Scheduler step
        scheduler.step(val_loss)

        # Save best model (by F1)
        if val_metrics['macro_f1'] > best_val_f1:
            best_val_f1 = val_metrics['macro_f1']
            best_val_loss = val_loss
            model.save(output_path)
            logger.info(f"  *** New best model saved (F1={best_val_f1:.4f})")
            patience_counter = 0
        else:
            patience_counter += 1
            logger.info(f"  No improvement ({patience_counter}/{config.early_stopping_patience})")

        # Early stopping
        if patience_counter >= config.early_stopping_patience:
            logger.info(f"\nEarly stopping triggered after {epoch+1} epochs")
            break

    # Load best model for final evaluation
    logger.info("\nLoading best model for final evaluation...")
    model = NovaClassifier.load(output_path, device=device)

    # Final test evaluation
    logger.info(f"\n{'='*60}")
    logger.info("FINAL TEST SET EVALUATION")
    logger.info(f"{'='*60}")

    test_loss, test_metrics = evaluate(model, test_loader, loss_fn, device)
    log_validation_results(test_metrics, "TEST", epochs - 1)

    # Print classification report
    logger.info("\nClassification Report:")
    logger.info(f"  Accuracy: {test_metrics['accuracy']:.2%}")
    logger.info(f"  Macro F1: {test_metrics['macro_f1']:.4f}")
    logger.info(f"  Weighted F1: {test_metrics['weighted_f1']:.4f}")

    # Calibration
    logger.info("\nCalibrating model with temperature scaling...")
    calibrated_model = TemperatureScaledNovaClassifier(model)
    calibrated_model.calibrate(val_loader, device=device)

    # Save calibration
    torch.save({
        "temperature": calibrated_model.temperature.item(),
    }, str(config.output_model).replace(".pt", "_temperature.pt"))

    # Save training history
    history_path = str(config.output_model).replace(".pt", "_history.json")
    with open(history_path, "w") as f:
        json.dump({
            "config": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
            },
            "final_test_metrics": test_metrics,
            "best_val_f1": best_val_f1,
            "trained_at": datetime.now().isoformat(),
        }, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("TRAINING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Model saved to: {output_path}")
    logger.info(f"History saved to: {history_path}")

    return test_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train NOVA Classifier")
    parser.add_argument("--epochs", type=int, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, help="Batch size")
    parser.add_argument("--learning-rate", type=float, help="Learning rate")
    parser.add_argument("--device", type=str, help="Device (cuda/cpu)")
    parser.add_argument("--output", type=str, help="Output model path")
    parser.add_argument("--use-raw", action="store_true", help="Use raw OpenFoodFacts data")
    parser.add_argument("--sample-size", type=int, help="Limit training samples")

    args = parser.parse_args()

    main(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        device=args.device,
        output_path=args.output,
        use_processed=not args.use_raw,
        sample_size=args.sample_size,
    )
