#!/bin/bash
# ============================================================================
# HealthGuard ML Model Training Commands
# ============================================================================
# GPU: NVIDIA RTX 4050 (6GB VRAM)
# All models configured for CUDA with TF32 enabled
#
# Training includes:
#   - Batch-level logging (loss, gradients, metrics)
#   - Per-epoch validation (5-10 metrics)
#   - Final evaluation (10+ metrics)
#   - GPU memory monitoring
#   - Training history saved to JSON
# ============================================================================

# Change to project root
cd "$(dirname "$0")/.." || exit 1

echo "=============================================="
echo "HealthGuard ML Training Scripts"
echo "=============================================="
echo "GPU: RTX 4050 (6GB VRAM)"
echo ""

# ============================================================================
# 1. ADDITIVE RISK SCORER (~5 min on CPU/GPU)
# ============================================================================
# - Small MLP for additive risk scoring (0-100)
# - Data: 42 real additives from additive_risks.csv
# - Metrics: MSE, RMSE, MAE, R², Pearson/Spearman correlation, category accuracy
echo "1. Additive Risk Scorer"
echo "   python -m ml.additive_scorer.train --epochs 200 --batch-size 8"
echo ""

# ============================================================================
# 2. NOVA CLASSIFIER (~30-60 min on GPU)
# ============================================================================
# - Custom CNN for NOVA 1-4 food classification
# - Data: 1M+ products from OpenFoodFacts
# - Metrics: Accuracy, F1 (macro/weighted), precision, recall, ECE, confidence
echo "2. NOVA Classifier"
echo "   python -m ml.nova_classifier.train --epochs 20 --batch-size 64"
echo ""

# Full dataset training:
echo "   # Full dataset (1M products):"
echo "   python -m ml.nova_classifier.train --epochs 20 --batch-size 64"
echo ""

# Smaller sample for testing:
echo "   # Quick test (50K sample):"
echo "   python -m ml.nova_classifier.train --epochs 5 --batch-size 64 --sample-size 50000"
echo ""

# ============================================================================
# 3. PROCEDURE ENCODER (~2-5 hrs on GPU)
# ============================================================================
# - BioClinicalBERT fine-tuning with contrastive learning
# - Data: 360K+ procedure variations from hospital MRF
# - Metrics: MRR, Hits@K, threshold accuracy, embedding similarity
echo "3. Procedure Encoder"
echo "   python -m ml.procedure_encoder.train --epochs 3 --batch-size 32"
echo ""

# Lower batch size if VRAM limited:
echo "   # Lower VRAM usage:"
echo "   python -m ml.procedure_encoder.train --epochs 3 --batch-size 16"
echo ""

# ============================================================================
# FULL TRAINING PIPELINE
# ============================================================================
echo "=============================================="
echo "Full Training Pipeline (recommended order):"
echo "=============================================="
echo ""
echo "# Step 1: Additive Scorer (fastest, validates setup)"
echo "python -m ml.additive_scorer.train"
echo ""
echo "# Step 2: NOVA Classifier"
echo "python -m ml.nova_classifier.train"
echo ""
echo "# Step 3: Procedure Encoder (longest)"
echo "python -m ml.procedure_encoder.train"
echo ""

# ============================================================================
# GPU MONITORING
# ============================================================================
echo "=============================================="
echo "GPU Monitoring Commands:"
echo "=============================================="
echo ""
echo "# Check GPU status:"
echo "nvidia-smi"
echo ""
echo "# Monitor GPU during training:"
echo "watch -n 1 nvidia-smi"
echo ""
echo "# Check CUDA availability:"
echo "python -c \"import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')\""
echo ""
