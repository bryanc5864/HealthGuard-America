"""
ChronicCare Model Training Pipeline

Training scripts for:
    1. ChronicRiskPredictor - Multi-task regression for disease prediction
    2. InterventionPrioritizer - Classification for MAHA intervention targeting
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import (
    CHRONIC_RISK_CONFIG,
    INTERVENTION_PRIORITIZER_CONFIG,
    WEIGHTS_DIR,
)
from ml.chroniccare.model import (
    ChronicRiskPredictor,
    InterventionPrioritizer,
    compute_feature_importance,
)
from ml.chroniccare.dataset import (
    prepare_risk_prediction_data,
    prepare_prioritization_data,
    create_data_loaders,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EarlyStopping:
    """Early stopping to prevent overfitting."""

    def __init__(self, patience: int = 10, min_delta: float = 1e-4):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.should_stop = False

    def __call__(self, val_loss: float) -> bool:
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
        else:
            self.best_loss = val_loss
            self.counter = 0
        return self.should_stop


def train_risk_predictor(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
) -> Tuple[ChronicRiskPredictor, Dict]:
    """
    Train the ChronicRiskPredictor model.

    Args:
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        device: Device to train on

    Returns:
        Tuple of (trained_model, training_history)
    """
    config = CHRONIC_RISK_CONFIG
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    device = device or config.device

    # Check CUDA availability
    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU")
        device = "cpu"

    logger.info("=" * 60)
    logger.info("TRAINING CHRONIC RISK PREDICTOR")
    logger.info("=" * 60)
    logger.info(f"Device: {device}")
    logger.info(f"Epochs: {epochs}, Batch Size: {batch_size}, LR: {learning_rate}")

    # Prepare data
    logger.info("Loading and preparing data...")
    train_ds, val_ds, encoder, metadata = prepare_risk_prediction_data(
        validation_split=config.validation_split
    )
    train_loader, val_loader = create_data_loaders(train_ds, val_ds, batch_size)

    logger.info(f"Train samples: {metadata['n_train']:,}")
    logger.info(f"Val samples: {metadata['n_val']:,}")
    logger.info(f"Features: {metadata['n_features']}")
    logger.info(f"Targets: {metadata['target_names']}")

    # Create model
    model = ChronicRiskPredictor(
        input_dim=metadata["n_features"],
        num_targets=metadata["n_targets"],
        hidden_dims=config.hidden_dims,
        dropout=config.dropout,
        use_batch_norm=config.use_batch_norm,
        target_names=metadata["target_names"],
    ).to(device)

    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)
    early_stopping = EarlyStopping(patience=config.early_stopping_patience)

    # Training history
    history = {
        "train_loss": [],
        "val_loss": [],
        "val_mae": [],
        "best_epoch": 0,
        "best_val_loss": float("inf"),
    }

    best_model_state = None

    # Training loop
    logger.info("Starting training...")
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(X_batch)

        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss = 0.0
        val_mae = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                predictions = model(X_batch)
                val_loss += criterion(predictions, y_batch).item() * len(X_batch)
                val_mae += torch.abs(predictions - y_batch).mean().item() * len(X_batch)

        val_loss /= len(val_ds)
        val_mae /= len(val_ds)

        # Update scheduler
        scheduler.step(val_loss)

        # Record history
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_mae"].append(val_mae)

        # Check for best model
        if val_loss < history["best_val_loss"]:
            history["best_val_loss"] = val_loss
            history["best_epoch"] = epoch
            best_model_state = model.state_dict().copy()

        # Log progress
        if (epoch + 1) % 10 == 0 or epoch == 0:
            logger.info(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val MAE: {val_mae:.2f}"
            )

        # Early stopping
        if early_stopping(val_loss):
            logger.info(f"Early stopping at epoch {epoch+1}")
            break

    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    logger.info(f"Best model from epoch {history['best_epoch']+1} (val_loss: {history['best_val_loss']:.4f})")

    # Compute feature importance
    logger.info("Computing feature importance...")
    X_sample = torch.FloatTensor(train_ds.features[:500]).to(device)
    model.feature_importance = compute_feature_importance(
        model, X_sample, metadata["feature_names"]
    )

    # Save model and encoder
    model.save(str(config.output_model))
    encoder.save(str(config.feature_scaler))

    # Save training history
    history_path = WEIGHTS_DIR / "chronic_risk_training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    logger.info(f"Training history saved to {history_path}")

    # Print target-wise performance
    logger.info("\nPer-target validation MAE:")
    model.eval()
    with torch.no_grad():
        all_preds = []
        all_targets = []
        for X_batch, y_batch in val_loader:
            X_batch = X_batch.to(device)
            all_preds.append(model(X_batch).cpu())
            all_targets.append(y_batch)
        all_preds = torch.cat(all_preds)
        all_targets = torch.cat(all_targets)

        for i, name in enumerate(metadata["target_names"]):
            mae = torch.abs(all_preds[:, i] - all_targets[:, i]).mean().item()
            logger.info(f"  {name}: {mae:.2f}")

    return model, history


def train_intervention_prioritizer(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
) -> Tuple[InterventionPrioritizer, Dict]:
    """
    Train the InterventionPrioritizer model.

    Args:
        epochs: Number of training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        device: Device to train on

    Returns:
        Tuple of (trained_model, training_history)
    """
    config = INTERVENTION_PRIORITIZER_CONFIG
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    device = device or config.device

    if device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU")
        device = "cpu"

    logger.info("=" * 60)
    logger.info("TRAINING INTERVENTION PRIORITIZER")
    logger.info("=" * 60)
    logger.info(f"Device: {device}")
    logger.info(f"Epochs: {epochs}, Batch Size: {batch_size}, LR: {learning_rate}")

    # Prepare data
    logger.info("Loading and preparing data...")
    train_ds, val_ds, encoder, metadata = prepare_prioritization_data(
        validation_split=config.validation_split
    )
    train_loader, val_loader = create_data_loaders(train_ds, val_ds, batch_size)

    logger.info(f"Train samples: {metadata['n_train']:,}")
    logger.info(f"Val samples: {metadata['n_val']:,}")
    logger.info(f"Class distribution: {metadata['class_distribution']}")

    # Create model
    model = InterventionPrioritizer(
        input_dim=metadata["n_features"],
        num_classes=metadata["n_classes"],
        hidden_dims=config.hidden_dims,
        dropout=config.dropout,
        use_batch_norm=config.use_batch_norm,
        class_names=metadata["class_names"],
    ).to(device)

    logger.info(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Loss with class weights
    class_weights = torch.FloatTensor(config.class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=5)
    early_stopping = EarlyStopping(patience=config.early_stopping_patience)

    history = {
        "train_loss": [],
        "val_loss": [],
        "val_accuracy": [],
        "best_epoch": 0,
        "best_val_loss": float("inf"),
    }

    best_model_state = None

    logger.info("Starting training...")
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            logits = model(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item() * len(X_batch)

        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss = 0.0
        correct = 0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                logits = model(X_batch)
                val_loss += criterion(logits, y_batch).item() * len(X_batch)
                preds = torch.argmax(logits, dim=1)
                correct += (preds == y_batch).sum().item()

        val_loss /= len(val_ds)
        val_accuracy = correct / len(val_ds)

        scheduler.step(val_loss)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_accuracy"].append(val_accuracy)

        if val_loss < history["best_val_loss"]:
            history["best_val_loss"] = val_loss
            history["best_epoch"] = epoch
            best_model_state = model.state_dict().copy()

        if (epoch + 1) % 10 == 0 or epoch == 0:
            logger.info(
                f"Epoch {epoch+1:3d}/{epochs} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Acc: {val_accuracy:.1%}"
            )

        if early_stopping(val_loss):
            logger.info(f"Early stopping at epoch {epoch+1}")
            break

    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    logger.info(f"Best model from epoch {history['best_epoch']+1}")

    # Save
    model.save(str(config.output_model))

    # Save encoder
    encoder_path = WEIGHTS_DIR / "intervention_feature_scaler.pkl"
    encoder.save(str(encoder_path))

    history_path = WEIGHTS_DIR / "intervention_training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    logger.info(f"Training history saved to {history_path}")

    # Confusion matrix
    logger.info("\nClass-wise validation accuracy:")
    model.eval()
    class_correct = {name: 0 for name in metadata["class_names"]}
    class_total = {name: 0 for name in metadata["class_names"]}

    with torch.no_grad():
        for X_batch, y_batch in val_loader:
            X_batch = X_batch.to(device)
            preds = torch.argmax(model(X_batch), dim=1).cpu()
            for pred, true in zip(preds, y_batch):
                true_name = metadata["class_names"][true.item()]
                class_total[true_name] += 1
                if pred == true:
                    class_correct[true_name] += 1

    for name in metadata["class_names"]:
        if class_total[name] > 0:
            acc = class_correct[name] / class_total[name]
            logger.info(f"  {name}: {acc:.1%} ({class_correct[name]}/{class_total[name]})")

    return model, history


def train_all():
    """Train all ChronicCare models."""
    logger.info("=" * 60)
    logger.info("CHRONICCARE ML TRAINING PIPELINE")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Train risk predictor
    risk_model, risk_history = train_risk_predictor()

    logger.info("\n")

    # Train prioritizer
    prioritizer_model, prioritizer_history = train_intervention_prioritizer()

    logger.info("\n" + "=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Risk Predictor - Best Val Loss: {risk_history['best_val_loss']:.4f}")
    logger.info(f"Prioritizer - Best Val Acc: {max(prioritizer_history['val_accuracy']):.1%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ChronicCare ML models")
    parser.add_argument("--model", choices=["risk", "prioritizer", "all"], default="all",
                        help="Which model to train")
    parser.add_argument("--epochs", type=int, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, help="Batch size")
    parser.add_argument("--lr", type=float, help="Learning rate")
    parser.add_argument("--device", choices=["cpu", "cuda"], help="Device")

    args = parser.parse_args()

    if args.model == "risk":
        train_risk_predictor(args.epochs, args.batch_size, args.lr, args.device)
    elif args.model == "prioritizer":
        train_intervention_prioritizer(args.epochs, args.batch_size, args.lr, args.device)
    else:
        train_all()
