"""
Training Script for Procedure Encoder

Fine-tunes BioClinicalBERT using contrastive learning with
Multiple Negatives Ranking Loss.

Data Source: Hospital MRF natural variations (360K+ samples)

Usage:
    python -m ml.procedure_encoder.train
    python -m ml.procedure_encoder.train --epochs 5 --batch-size 16
"""

# Allow loading older model formats (BioClinicalBERT doesn't have safetensors)
import os
os.environ["TRANSFORMERS_ALLOW_UNSAFE_DESERIALIZATION"] = "1"

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import get_linear_schedule_with_warmup
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, List
import argparse
import logging
import time

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ml.config import PROCEDURE_ENCODER_CONFIG
from ml.procedure_encoder.model import ProcedureEncoder
from ml.procedure_encoder.dataset import (
    ProcedureDataset, split_data, create_canonical_procedures, load_procedure_training_data,
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


class MultipleNegativesRankingLoss(nn.Module):
    """Multiple Negatives Ranking Loss for contrastive learning."""
    def __init__(self, scale: float = 20.0):
        super().__init__()
        self.scale = scale

    def forward(self, anchor: torch.Tensor, positive: torch.Tensor) -> torch.Tensor:
        similarities = torch.matmul(anchor, positive.T) * self.scale
        labels = torch.arange(len(anchor), device=similarities.device)
        return F.cross_entropy(similarities, labels)


def train_epoch(
    model: ProcedureEncoder,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    loss_fn: nn.Module,
    device: str,
    epoch: int,
    log_interval: int = 10,
) -> Tuple[float, Dict, GradientStats]:
    """Train one epoch with comprehensive logging."""
    model.train()
    total_loss = 0
    num_batches = 0
    all_grad_stats = []

    num_total = len(dataloader)
    lr = optimizer.param_groups[0]["lr"]

    # Track batch-level metrics
    batch_losses = []
    batch_similarities = []

    for batch_idx, batch in enumerate(dataloader):
        anchor_ids = batch["anchor_input_ids"].to(device)
        anchor_mask = batch["anchor_attention_mask"].to(device)
        pos_ids = batch["positive_input_ids"].to(device)
        pos_mask = batch["positive_attention_mask"].to(device)

        anchor_emb = model(anchor_ids, anchor_mask)
        pos_emb = model(pos_ids, pos_mask)

        loss = loss_fn(anchor_emb, pos_emb)

        optimizer.zero_grad()
        loss.backward()

        grad_stats = compute_gradient_stats(model)
        all_grad_stats.append(grad_stats)

        if grad_stats.has_nan or grad_stats.has_inf:
            logger.warning(f"⚠️ Gradient issue at batch {batch_idx}")

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        batch_loss = loss.item()
        total_loss += batch_loss
        num_batches += 1
        batch_losses.append(batch_loss)

        # Compute batch similarity stats
        with torch.no_grad():
            sims = torch.matmul(anchor_emb, pos_emb.T)
            diag_sims = sims.diag().mean().item()
            batch_similarities.append(diag_sims)

        if batch_idx % log_interval == 0 or batch_idx == num_total - 1:
            log_batch(epoch, batch_idx, num_total, batch_loss,
                     {"pos_sim": diag_sims, "running_loss": total_loss/num_batches},
                     grad_stats, lr)

    avg_grad = GradientStats(
        total_norm=np.mean([g.total_norm for g in all_grad_stats]),
        max_norm=np.max([g.max_norm for g in all_grad_stats]),
        min_norm=np.min([g.min_norm for g in all_grad_stats]),
        mean_norm=np.mean([g.mean_norm for g in all_grad_stats]),
    )

    train_metrics = {
        "loss": total_loss / num_batches,
        "mean_pos_similarity": np.mean(batch_similarities),
        "loss_std": np.std(batch_losses),
        "loss_min": np.min(batch_losses),
        "loss_max": np.max(batch_losses),
    }

    return total_loss / num_batches, train_metrics, avg_grad


def evaluate(model: ProcedureEncoder, dataloader: DataLoader, loss_fn: nn.Module, device: str) -> Tuple[float, Dict]:
    """Evaluate with loss and similarity metrics."""
    model.eval()
    total_loss = 0
    num_batches = 0
    all_sims = []

    with torch.no_grad():
        for batch in dataloader:
            anchor_ids = batch["anchor_input_ids"].to(device)
            anchor_mask = batch["anchor_attention_mask"].to(device)
            pos_ids = batch["positive_input_ids"].to(device)
            pos_mask = batch["positive_attention_mask"].to(device)

            anchor_emb = model(anchor_ids, anchor_mask)
            pos_emb = model(pos_ids, pos_mask)

            loss = loss_fn(anchor_emb, pos_emb)
            total_loss += loss.item()
            num_batches += 1

            sims = torch.matmul(anchor_emb, pos_emb.T)
            all_sims.extend(sims.diag().cpu().numpy())

    metrics = {
        "loss": total_loss / num_batches,
        "mean_pos_similarity": np.mean(all_sims),
        "similarity_std": np.std(all_sims),
        "similarity_min": np.min(all_sims),
        "similarity_max": np.max(all_sims),
    }
    return total_loss / num_batches, metrics


def compute_matching_metrics(model: ProcedureEncoder, descriptions: List[str], codes: List[str], device: str) -> Dict:
    """Compute comprehensive matching metrics (10+)."""
    model.eval()
    logger.info("Encoding validation descriptions...")
    embeddings = model.encode(descriptions, device=device, show_progress=False)

    similarities = np.dot(embeddings, embeddings.T)

    # Threshold metrics
    thresholds = [0.60, 0.70, 0.80, 0.90]
    threshold_metrics = {}
    for thresh in thresholds:
        correct, total = 0, 0
        for i in range(len(descriptions)):
            sims = similarities[i].copy()
            sims[i] = -1
            best_idx = np.argmax(sims)
            if sims[best_idx] >= thresh:
                if codes[i] == codes[best_idx]:
                    correct += 1
                total += 1
        threshold_metrics[f"acc@{thresh}"] = {
            "accuracy": correct / total if total > 0 else 0,
            "matched": total, "correct": correct,
        }

    # MRR
    mrr_sum, mrr_count = 0, 0
    reciprocal_ranks = []
    for i in range(len(descriptions)):
        target = codes[i]
        same_code = [j for j in range(len(codes)) if codes[j] == target and j != i]
        if same_code:
            sims = similarities[i].copy()
            sims[i] = -1
            ranked = np.argsort(-sims)
            for rank, idx in enumerate(ranked, 1):
                if idx in same_code:
                    mrr_sum += 1.0 / rank
                    mrr_count += 1
                    reciprocal_ranks.append(1.0 / rank)
                    break

    mrr = mrr_sum / mrr_count if mrr_count > 0 else 0

    # Hits@K
    hits_at_1, hits_at_5, hits_at_10 = 0, 0, 0
    for i in range(len(descriptions)):
        target = codes[i]
        same_code = set(j for j in range(len(codes)) if codes[j] == target and j != i)
        if same_code:
            sims = similarities[i].copy()
            sims[i] = -1
            top_k = np.argsort(-sims)[:10]
            if top_k[0] in same_code: hits_at_1 += 1
            if any(k in same_code for k in top_k[:5]): hits_at_5 += 1
            if any(k in same_code for k in top_k): hits_at_10 += 1

    n_with_pairs = mrr_count

    return {
        "threshold_metrics": threshold_metrics,
        "mrr": mrr,
        "hits_at_1": hits_at_1 / n_with_pairs if n_with_pairs else 0,
        "hits_at_5": hits_at_5 / n_with_pairs if n_with_pairs else 0,
        "hits_at_10": hits_at_10 / n_with_pairs if n_with_pairs else 0,
        "mean_reciprocal_rank": mrr,
        "num_samples": len(descriptions),
        "num_with_pairs": n_with_pairs,
        "mean_similarity": float(np.mean(similarities[np.triu_indices(len(similarities), k=1)])),
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
    epochs = epochs or config.epochs
    batch_size = batch_size or config.batch_size
    learning_rate = learning_rate or config.learning_rate
    output_path = output_path or str(config.output_model)
    log_interval = config.log_interval

    device, gpu_info = setup_device(device or config.device)

    # Load data
    logger.info("Loading training data...")
    descriptions, cpt_codes = load_procedure_training_data()
    logger.info(f"Loaded {len(descriptions):,} procedure descriptions")

    # Split
    (train_d, train_c), (val_d, val_c) = split_data(descriptions, cpt_codes)

    # Model
    model = ProcedureEncoder(model_name=config.base_model).to(device)

    # Log config
    train_config = {
        "epochs": epochs, "batch_size": batch_size, "learning_rate": learning_rate,
        "base_model": config.base_model, "max_length": config.max_length,
        "weight_decay": config.weight_decay, "warmup_ratio": config.warmup_ratio,
    }
    log_training_start("Procedure Encoder", train_config, gpu_info, model, len(train_c), len(val_c))

    # Datasets
    train_dataset = ProcedureDataset(train_d, train_c, model.tokenizer, config.max_length)
    val_dataset = ProcedureDataset(val_d, val_c, model.tokenizer, config.max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    logger.info(f"Train batches: {len(train_loader)} | Val batches: {len(val_loader)}")

    # Tracker
    tracker = TrainingTracker("procedure_encoder", Path(output_path).parent)
    tracker.config = train_config
    tracker.gpu_info = gpu_info

    # Loss, optimizer, scheduler
    loss_fn = MultipleNegativesRankingLoss(scale=20.0)
    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=config.weight_decay)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * config.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    logger.info(f"Total steps: {total_steps} | Warmup: {warmup_steps}")

    # Training
    logger.info(f"\n{'='*70}\nSTARTING TRAINING\n{'='*70}\n")
    best_val_loss = float("inf")

    for epoch in range(epochs):
        epoch_start = time.time()
        lr = optimizer.param_groups[0]["lr"]

        train_loss, train_metrics, grad_stats = train_epoch(
            model, train_loader, optimizer, scheduler, loss_fn, device, epoch, log_interval
        )
        val_loss, val_metrics = evaluate(model, val_loader, loss_fn, device)

        epoch_duration = time.time() - epoch_start
        is_best = val_loss < best_val_loss

        # Log (5-10 metrics)
        log_epoch_summary(
            epoch, epochs, train_loss, val_loss,
            {k: train_metrics[k] for k in ['loss', 'mean_pos_similarity', 'loss_std', 'loss_min', 'loss_max']},
            {k: val_metrics[k] for k in ['loss', 'mean_pos_similarity', 'similarity_std', 'similarity_min', 'similarity_max']},
            grad_stats, lr, epoch_duration, is_best
        )

        tracker.log_epoch(epoch, train_loss, val_loss, train_metrics, val_metrics,
                         grad_stats, lr, epoch_duration, is_best)

        if is_best:
            best_val_loss = val_loss
            model.save(output_path)

    # Final eval (10+ metrics)
    logger.info(f"\n{'='*70}\nFINAL EVALUATION\n{'='*70}")
    matching_metrics = compute_matching_metrics(model, val_d, val_c, device)
    log_final_metrics("VALIDATION", matching_metrics)

    # Generate canonical embeddings
    logger.info("Generating canonical procedure embeddings...")
    canonical_d, canonical_c = create_canonical_procedures()
    canonical_emb = model.encode(canonical_d, device=device)
    torch.save({
        "embeddings": canonical_emb,
        "descriptions": canonical_d,
        "codes": canonical_c,
    }, config.canonical_embeddings)
    logger.info(f"Saved {len(canonical_d)} canonical embeddings")

    history_path = tracker.save(matching_metrics)

    logger.info(f"\n{'='*70}\nTRAINING COMPLETE\n{'='*70}")
    logger.info(f"Model: {output_path}")
    logger.info(f"Canonical: {config.canonical_embeddings}")
    logger.info(f"History: {history_path}")

    return matching_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Procedure Encoder")
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--device", type=str)
    parser.add_argument("--output", type=str)
    args = parser.parse_args()

    main(args.epochs, args.batch_size, args.learning_rate, args.device, args.output)
