"""
HealthGuard ML Training Utilities

Common utilities for GPU detection, logging, metrics tracking,
and training monitoring across all ML models.
"""

import torch
import torch.nn as nn
import numpy as np
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# =============================================================================
# GPU DETECTION AND SETUP
# =============================================================================

@dataclass
class GPUInfo:
    """Information about available GPU."""
    available: bool = False
    device_name: str = "CPU"
    device_id: int = 0
    cuda_version: str = "N/A"
    cudnn_version: str = "N/A"
    total_memory_gb: float = 0.0
    compute_capability: str = "N/A"


def get_gpu_info() -> GPUInfo:
    """Detect and return GPU information."""
    info = GPUInfo()
    if not torch.cuda.is_available():
        return info

    info.available = True
    info.device_id = torch.cuda.current_device()
    info.device_name = torch.cuda.get_device_name(info.device_id)
    info.cuda_version = torch.version.cuda or "Unknown"
    info.cudnn_version = str(torch.backends.cudnn.version()) if torch.backends.cudnn.is_available() else "N/A"
    props = torch.cuda.get_device_properties(info.device_id)
    info.total_memory_gb = props.total_memory / (1024 ** 3)
    info.compute_capability = f"{props.major}.{props.minor}"
    return info


def setup_device(preferred: str = "cuda") -> Tuple[str, GPUInfo]:
    """Setup and return best available device."""
    gpu_info = get_gpu_info()
    if preferred == "cuda" and gpu_info.available:
        device = f"cuda:{gpu_info.device_id}"
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    else:
        device = "cpu"
    return device, gpu_info


def log_gpu_info(gpu_info: GPUInfo):
    """Log GPU information."""
    logger.info(f"{'─'*60}")
    logger.info("DEVICE CONFIGURATION")
    logger.info(f"{'─'*60}")
    if gpu_info.available:
        logger.info(f"  GPU: {gpu_info.device_name}")
        logger.info(f"  CUDA: {gpu_info.cuda_version} | cuDNN: {gpu_info.cudnn_version}")
        logger.info(f"  Memory: {gpu_info.total_memory_gb:.1f} GB | Compute: {gpu_info.compute_capability}")
        logger.info(f"  TF32: {torch.backends.cuda.matmul.allow_tf32} | cuDNN Benchmark: {torch.backends.cudnn.benchmark}")
    else:
        logger.info(f"  Device: CPU | PyTorch: {torch.__version__}")
    logger.info(f"{'─'*60}")


def get_memory_stats() -> Dict[str, float]:
    """Get GPU memory statistics."""
    if not torch.cuda.is_available():
        return {"allocated_gb": 0, "max_allocated_gb": 0}
    return {
        "allocated_gb": torch.cuda.memory_allocated() / (1024 ** 3),
        "max_allocated_gb": torch.cuda.max_memory_allocated() / (1024 ** 3),
    }


# =============================================================================
# GRADIENT MONITORING
# =============================================================================

@dataclass
class GradientStats:
    """Gradient statistics."""
    total_norm: float = 0.0
    max_norm: float = 0.0
    min_norm: float = float('inf')
    mean_norm: float = 0.0
    layer_norms: Dict[str, float] = field(default_factory=dict)
    has_nan: bool = False
    has_inf: bool = False


def compute_gradient_stats(model: nn.Module, top_k: int = 5) -> GradientStats:
    """Compute gradient statistics with per-layer breakdown."""
    stats = GradientStats()
    all_norms = []

    for name, param in model.named_parameters():
        if param.grad is not None:
            grad = param.grad.data
            if torch.isnan(grad).any():
                stats.has_nan = True
            if torch.isinf(grad).any():
                stats.has_inf = True

            norm = grad.norm(2).item()
            all_norms.append(norm)
            stats.total_norm += norm ** 2
            short_name = name.replace('.weight', '.W').replace('.bias', '.b')
            stats.layer_norms[short_name] = norm

    if all_norms:
        stats.total_norm = stats.total_norm ** 0.5
        stats.max_norm = max(all_norms)
        stats.min_norm = min(all_norms)
        stats.mean_norm = np.mean(all_norms)

    return stats


# =============================================================================
# TRAINING TRACKER
# =============================================================================

class TrainingTracker:
    """Track training progress and save history."""

    def __init__(self, model_name: str, output_dir: Path):
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.start_time = datetime.now()
        self.epochs = []
        self.best_val_metric = float('inf')
        self.best_epoch = 0
        self.config = {}
        self.gpu_info = None

    def log_epoch(self, epoch: int, train_loss: float, val_loss: float,
                  train_metrics: Dict, val_metrics: Dict, grad_stats: GradientStats,
                  lr: float, duration: float, is_best: bool = False):
        """Log and store epoch results."""
        mem = get_memory_stats()
        epoch_data = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "gradient_norm": grad_stats.total_norm,
            "gradient_max": grad_stats.max_norm,
            "gradient_mean": grad_stats.mean_norm,
            "learning_rate": lr,
            "duration_sec": duration,
            "gpu_memory_gb": mem["allocated_gb"],
        }
        self.epochs.append(epoch_data)

        if is_best:
            self.best_epoch = epoch + 1
            self.best_val_metric = val_loss

    def save(self, final_metrics: Dict = None) -> Path:
        """Save training history."""
        history = {
            "model_name": self.model_name,
            "config": self.config,
            "gpu_info": asdict(self.gpu_info) if self.gpu_info else None,
            "started": self.start_time.isoformat(),
            "completed": datetime.now().isoformat(),
            "total_epochs": len(self.epochs),
            "best_epoch": self.best_epoch,
            "best_val_metric": self.best_val_metric,
            "epochs": self.epochs,
            "final_metrics": final_metrics,
        }
        path = self.output_dir / f"{self.model_name}_history.json"
        with open(path, 'w') as f:
            json.dump(history, f, indent=2, default=str)
        return path


# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

def log_batch(epoch: int, batch: int, total: int, loss: float, metrics: Dict,
              grad_stats: GradientStats, lr: float):
    """Log batch progress."""
    pct = (batch + 1) / total * 100
    m_str = " | ".join([f"{k}: {v:.4f}" for k, v in list(metrics.items())[:3]])
    logger.info(
        f"E{epoch+1} B{batch+1}/{total} ({pct:5.1f}%) | Loss: {loss:.4f} | {m_str} | "
        f"Grad: {grad_stats.total_norm:.4f} | LR: {lr:.2e}"
    )


def log_epoch_summary(epoch: int, total_epochs: int, train_loss: float, val_loss: float,
                      train_metrics: Dict, val_metrics: Dict, grad_stats: GradientStats,
                      lr: float, duration: float, is_best: bool = False):
    """Log epoch summary with 5-10 metrics."""
    logger.info(f"\n{'─'*70}")
    logger.info(f"EPOCH {epoch+1}/{total_epochs} SUMMARY {'★ BEST' if is_best else ''}")
    logger.info(f"{'─'*70}")
    logger.info(f"  Loss      | Train: {train_loss:.6f} | Val: {val_loss:.6f}")

    # Train metrics (up to 5)
    t_items = list(train_metrics.items())[:5]
    if t_items:
        logger.info(f"  Train     | " + " | ".join([f"{k}: {v:.4f}" for k, v in t_items]))

    # Val metrics (up to 5)
    v_items = list(val_metrics.items())[:5]
    if v_items:
        logger.info(f"  Val       | " + " | ".join([f"{k}: {v:.4f}" for k, v in v_items]))

    logger.info(f"  Gradients | Total: {grad_stats.total_norm:.4f} | Max: {grad_stats.max_norm:.4f} | Mean: {grad_stats.mean_norm:.4f}")

    mem = get_memory_stats()
    if mem["allocated_gb"] > 0:
        logger.info(f"  Memory    | {mem['allocated_gb']:.2f} GB / {mem['max_allocated_gb']:.2f} GB max")

    logger.info(f"  LR: {lr:.2e} | Duration: {duration:.1f}s")
    logger.info(f"{'─'*70}\n")


def log_final_metrics(split: str, metrics: Dict, class_names: List[str] = None):
    """Log final evaluation with 10+ metrics."""
    logger.info(f"\n{'='*70}")
    logger.info(f"FINAL {split.upper()} EVALUATION (10+ Metrics)")
    logger.info(f"{'='*70}")

    # 1-4: Core metrics
    logger.info(f"\n[1-4] CORE METRICS:")
    for k in ['loss', 'accuracy', 'mse', 'rmse']:
        if k in metrics:
            v = metrics[k]
            logger.info(f"  {k}: {v:.6f}" if k != 'accuracy' else f"  {k}: {v:.2%}")

    # 5-7: F1 metrics
    logger.info(f"\n[5-7] F1 METRICS:")
    for k in ['macro_f1', 'weighted_f1', 'mae']:
        if k in metrics:
            logger.info(f"  {k}: {metrics[k]:.4f}")

    # 8-9: Correlation
    logger.info(f"\n[8-9] CORRELATION:")
    for k in ['pearson_r', 'spearman_r', 'r2']:
        if k in metrics:
            logger.info(f"  {k}: {metrics[k]:.4f}")

    # 10-11: Confidence
    if 'mean_confidence' in metrics:
        logger.info(f"\n[10-11] CONFIDENCE:")
        logger.info(f"  mean_confidence: {metrics['mean_confidence']:.2%}")
        logger.info(f"  confidence_correct: {metrics.get('confidence_when_correct', 0):.2%}")
        logger.info(f"  confidence_wrong: {metrics.get('confidence_when_wrong', 0):.2%}")

    # 12+: Per-class
    if 'per_class' in metrics and class_names:
        logger.info(f"\n[12+] PER-CLASS METRICS:")
        for name in class_names:
            if name in metrics['per_class']:
                info = metrics['per_class'][name]
                logger.info(f"  {name}: P={info.get('precision',0):.2%} R={info.get('recall',0):.2%} F1={info.get('f1',0):.4f} n={info.get('support',0)}")

    # Category accuracy
    if 'category_accuracy' in metrics:
        logger.info(f"\n[CATEGORY]:")
        logger.info(f"  category_accuracy: {metrics['category_accuracy']:.2%}")
        if 'per_category' in metrics:
            for cat, info in metrics['per_category'].items():
                logger.info(f"  {cat}: acc={info.get('accuracy',0):.2%} mae={info.get('mean_error',0):.2f}")

    # Threshold metrics
    if 'threshold_metrics' in metrics:
        logger.info(f"\n[THRESHOLDS]:")
        for t, info in metrics['threshold_metrics'].items():
            logger.info(f"  {t}: {info['accuracy']:.2%} ({info['correct']}/{info['matched']})")

    if 'mrr' in metrics:
        logger.info(f"  MRR: {metrics['mrr']:.4f}")

    # Confusion matrix
    if 'confusion_matrix' in metrics and class_names:
        logger.info(f"\n[CONFUSION MATRIX]:")
        cm = np.array(metrics['confusion_matrix'])
        logger.info("        " + " ".join([f"{n[:5]:>5}" for n in class_names]))
        for i, row in enumerate(cm):
            logger.info(f"  {class_names[i][:5]:>5}: {row}")

    logger.info(f"\n{'='*70}\n")


def log_training_start(name: str, config: Dict, gpu_info: GPUInfo, model: nn.Module,
                       train_n: int, val_n: int, test_n: int = 0):
    """Log training configuration at start."""
    logger.info(f"\n{'='*70}")
    logger.info(f"{name.upper()} TRAINING")
    logger.info(f"{'='*70}")

    log_gpu_info(gpu_info)

    total_p = sum(p.numel() for p in model.parameters())
    train_p = sum(p.numel() for p in model.parameters() if p.requires_grad)

    logger.info(f"\nDATA: Train={train_n:,} | Val={val_n:,}" + (f" | Test={test_n:,}" if test_n else ""))
    logger.info(f"MODEL: {total_p:,} params ({train_p:,} trainable) | {total_p*4/1024**2:.1f} MB")
    logger.info(f"\nCONFIG:")
    for k, v in config.items():
        logger.info(f"  {k}: {v}")
    logger.info(f"{'='*70}\n")
