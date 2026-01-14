"""
Training Script for Procedure Encoder

Fine-tunes BioClinicalBERT using contrastive learning with
Multiple Negatives Ranking Loss.

Data Source: Medicare Provider Utilization (6,405 canonical procedure codes)
Training uses augmented variations of canonical descriptions.

Usage:
    python -m ml.procedure_encoder.train
    python -m ml.procedure_encoder.train --epochs 5 --batch-size 16
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
import numpy as np
from scipy import stats
from sklearn.metrics import precision_recall_fscore_support
from pathlib import Path
from typing import Tuple, Dict, List
import argparse
import logging
import json
from datetime import datetime
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import PROCEDURE_ENCODER_CONFIG
from ml.procedure_encoder.model import ProcedureEncoder
from ml.procedure_encoder.dataset import (
    ProcedureDataset,
    split_data,
    create_canonical_procedures,
    load_procedure_training_data,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MultipleNegativesRankingLoss(nn.Module):
    """
    Multiple Negatives Ranking Loss for contrastive learning.

    Given a batch of (anchor, positive) pairs, treats all other positives
    in the batch as negatives.
    """

    def __init__(self, scale: float = 20.0):
        super().__init__()
        self.scale = scale

    def forward(
        self,
        anchor_embeddings: torch.Tensor,
        positive_embeddings: torch.Tensor,
    ) -> torch.Tensor:
        # Compute similarity matrix [batch, batch]
        similarities = torch.matmul(anchor_embeddings, positive_embeddings.T) * self.scale
        labels = torch.arange(len(anchor_embeddings), device=similarities.device)
        loss = F.cross_entropy(similarities, labels)
        return loss




def train_epoch(
    model: ProcedureEncoder,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
) -> Tuple[float, Dict]:
    """Train for one epoch with detailed logging."""
    model.train()
    total_loss = 0
    num_batches = 0
    gradient_norms = []

    num_total_batches = len(dataloader)

    for batch_idx, batch in enumerate(dataloader):
        # Move to device
        anchor_input_ids = batch["anchor_input_ids"].to(device)
        anchor_attention_mask = batch["anchor_attention_mask"].to(device)
        positive_input_ids = batch["positive_input_ids"].to(device)
        positive_attention_mask = batch["positive_attention_mask"].to(device)

        # Forward pass
        anchor_embeddings = model(anchor_input_ids, anchor_attention_mask)
        positive_embeddings = model(positive_input_ids, positive_attention_mask)

        # Compute loss
        loss = loss_fn(anchor_embeddings, positive_embeddings)

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

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        num_batches += 1

        # Log every 10 batches
        if batch_idx % 10 == 0 or batch_idx == num_total_batches - 1:
            logger.info(
                f"Epoch {epoch+1} | Batch {batch_idx+1}/{num_total_batches} | "
                f"Loss: {loss.item():.4f} | Grad Norm: {total_norm:.4f}"
            )

    gradient_info = {
        "mean_grad_norm": float(np.mean(gradient_norms)),
        "max_grad_norm": float(np.max(gradient_norms)),
    }

    return total_loss / num_batches, gradient_info


def evaluate(
    model: ProcedureEncoder,
    dataloader: DataLoader,
    loss_fn: nn.Module,
    device: str,
) -> float:
    """Evaluate model on validation set."""
    model.eval()
    total_loss = 0
    num_batches = 0

    with torch.no_grad():
        for batch in dataloader:
            anchor_input_ids = batch["anchor_input_ids"].to(device)
            anchor_attention_mask = batch["anchor_attention_mask"].to(device)
            positive_input_ids = batch["positive_input_ids"].to(device)
            positive_attention_mask = batch["positive_attention_mask"].to(device)

            anchor_embeddings = model(anchor_input_ids, anchor_attention_mask)
            positive_embeddings = model(positive_input_ids, positive_attention_mask)

            loss = loss_fn(anchor_embeddings, positive_embeddings)
            total_loss += loss.item()
            num_batches += 1

    return total_loss / num_batches


def compute_matching_metrics(
    model: ProcedureEncoder,
    val_descriptions: List[str],
    val_codes: List[str],
    device: str,
) -> Dict:
    """
    Compute comprehensive procedure matching metrics.

    Returns metrics including accuracy at different thresholds,
    Precision@K, and MRR (Mean Reciprocal Rank).
    """
    model.eval()

    # Encode all descriptions
    logger.info("Encoding validation descriptions...")
    embeddings = model.encode(val_descriptions, device=device, show_progress=False)

    # Compute similarity matrix
    similarities = np.dot(embeddings, embeddings.T)

    # Metrics at different thresholds
    thresholds = [0.60, 0.70, 0.80, 0.90]
    threshold_metrics = {}

    for threshold in thresholds:
        correct = 0
        total = 0

        for i in range(len(val_descriptions)):
            sims = similarities[i].copy()
            sims[i] = -1  # Exclude self

            best_idx = np.argmax(sims)
            best_sim = sims[best_idx]

            if best_sim >= threshold:
                if val_codes[i] == val_codes[best_idx]:
                    correct += 1
                total += 1

        accuracy = correct / total if total > 0 else 0
        threshold_metrics[f"acc@{threshold}"] = {
            "accuracy": accuracy,
            "matched": total,
            "correct": correct,
        }

    # Mean Reciprocal Rank (for same-code matches)
    mrr_sum = 0
    mrr_count = 0

    for i in range(len(val_descriptions)):
        target_code = val_codes[i]

        # Get indices with same code (excluding self)
        same_code_indices = [j for j in range(len(val_codes)) if val_codes[j] == target_code and j != i]

        if same_code_indices:
            sims = similarities[i].copy()
            sims[i] = -1

            # Rank all by similarity
            ranked_indices = np.argsort(-sims)

            # Find rank of first same-code item
            for rank, idx in enumerate(ranked_indices, 1):
                if idx in same_code_indices:
                    mrr_sum += 1.0 / rank
                    mrr_count += 1
                    break

    mrr = mrr_sum / mrr_count if mrr_count > 0 else 0

    return {
        "threshold_metrics": threshold_metrics,
        "mrr": mrr,
        "num_samples": len(val_descriptions),
    }


def main(
    epochs: int = None,
    batch_size: int = None,
    learning_rate: float = None,
    device: str = None,
    output_path: str = None,
):
    """Main training function."""
    config = PROCEDURE_ENCODER_CONFIG

    # Override with arguments
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)

    # Device
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info(f"{'='*60}")
    logger.info("PROCEDURE ENCODER TRAINING")
    logger.info(f"{'='*60}")
    logger.info(f"Device: {device}")
    logger.info(f"Epochs: {epochs}")
    logger.info(f"Batch Size: {batch_size}")
    logger.info(f"Learning Rate: {learning_rate}")
    logger.info(f"Base Model: {config.base_model}")
    logger.info(f"Output Path: {output_path}")

    # Load REAL data only - NO SYNTHETIC
    logger.info("\nLoading training data...")
    descriptions, cpt_codes = load_procedure_training_data()

    # Split data
    logger.info("\nSplitting data...")
    (train_descs, train_codes), (val_descs, val_codes) = split_data(descriptions, cpt_codes)

    # Initialize model
    logger.info("\nInitializing model...")
    model = ProcedureEncoder(model_name=config.base_model)
    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Total Parameters: {total_params:,}")
    logger.info(f"Trainable Parameters: {trainable_params:,}")

    # Create datasets
    train_dataset = ProcedureDataset(
        train_descs, train_codes, model.tokenizer, max_length=config.max_length
    )
    val_dataset = ProcedureDataset(
        val_descs, val_codes, model.tokenizer, max_length=config.max_length
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    logger.info(f"Train batches: {len(train_loader)}")
    logger.info(f"Val batches: {len(val_loader)}")

    # Loss function
    loss_fn = MultipleNegativesRankingLoss(scale=20.0)

    # Optimizer
    optimizer = AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=config.weight_decay,
    )

    # Scheduler with warmup
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * config.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    logger.info(f"Total steps: {total_steps}, Warmup steps: {warmup_steps}")

    # Training loop
    logger.info(f"\n{'='*60}")
    logger.info("STARTING TRAINING")
    logger.info(f"{'='*60}\n")

    best_val_loss = float("inf")

    for epoch in range(epochs):
        current_lr = optimizer.param_groups[0]["lr"]
        logger.info(f"\nEpoch {epoch+1}/{epochs} | LR: {current_lr:.2e}")
        logger.info("-" * 40)

        # Train
        train_loss, grad_info = train_epoch(
            model, train_loader, optimizer, scheduler, loss_fn, device, epoch
        )

        # Validate
        val_loss = evaluate(model, val_loader, loss_fn, device)

        logger.info(f"\nEpoch {epoch+1} Summary:")
        logger.info(f"  Train Loss: {train_loss:.4f}")
        logger.info(f"  Val Loss: {val_loss:.4f}")
        logger.info(f"  Gradient Norm (mean/max): {grad_info['mean_grad_norm']:.4f}/{grad_info['max_grad_norm']:.4f}")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save(output_path)
            logger.info(f"  *** New best model saved (val_loss={val_loss:.4f})")

    # Final evaluation
    logger.info(f"\n{'='*60}")
    logger.info("FINAL EVALUATION")
    logger.info(f"{'='*60}")

    matching_metrics = compute_matching_metrics(model, val_descs, val_codes, device)

    logger.info("\nMatching Accuracy at Different Thresholds:")
    for key, info in matching_metrics["threshold_metrics"].items():
        logger.info(f"  {key}: {info['accuracy']:.2%} ({info['correct']}/{info['matched']} matched)")

    logger.info(f"\nMean Reciprocal Rank (MRR): {matching_metrics['mrr']:.4f}")

    # Generate canonical embeddings
    logger.info("\nGenerating canonical procedure embeddings...")
    canonical_descs, canonical_codes = create_canonical_procedures()
    canonical_embeddings = model.encode(canonical_descs, device=device)

    torch.save({
        "embeddings": canonical_embeddings,
        "descriptions": canonical_descs,
        "codes": canonical_codes,
    }, config.canonical_embeddings)
    logger.info(f"Saved canonical embeddings to {config.canonical_embeddings}")

    # Save training history
    history_path = str(config.output_model).replace(".pt", "_history.json")
    with open(history_path, "w") as f:
        json.dump({
            "config": {
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "base_model": config.base_model,
            },
            "final_metrics": {
                "best_val_loss": best_val_loss,
                "matching_metrics": matching_metrics,
            },
            "trained_at": datetime.now().isoformat(),
        }, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("TRAINING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Model saved to: {output_path}")
    logger.info(f"History saved to: {history_path}")

    return matching_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Procedure Encoder")
    parser.add_argument("--epochs", type=int, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, help="Batch size")
    parser.add_argument("--learning-rate", type=float, help="Learning rate")
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
