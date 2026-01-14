"""
HealthGuard America - ML Model Configuration

Hyperparameters and paths for all deep learning models.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List

# Base paths
ML_ROOT = Path(__file__).parent
PROJECT_ROOT = ML_ROOT.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
WEIGHTS_DIR = ML_ROOT / "weights"

# Ensure weights directory exists
WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcedureEncoderConfig:
    """Configuration for BioClinicalBERT procedure encoder."""

    # Model
    base_model: str = "emilyalsentzer/Bio_ClinicalBERT"
    embedding_dim: int = 768
    max_length: int = 128

    # Training
    batch_size: int = 32
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    epochs: int = 3

    # Matching thresholds
    match_threshold: float = 0.80  # Confident match
    review_threshold: float = 0.65  # Needs review

    # Data paths
    training_data: Path = DATA_RAW / "pricevision" / "provider_util"
    output_model: Path = WEIGHTS_DIR / "procedure_encoder.pt"
    canonical_embeddings: Path = WEIGHTS_DIR / "canonical_procedure_embeddings.pt"

    # Device
    device: str = "cuda"  # Will fallback to CPU if unavailable


@dataclass
class NovaClassifierConfig:
    """Configuration for NOVA food processing classifier."""

    # Tokenizer
    vocab_size: int = 10000
    max_length: int = 200
    embedding_dim: int = 128

    # Model architecture
    conv_filters: int = 256
    conv_kernel_size: int = 3
    hidden_dims: List[int] = field(default_factory=lambda: [256, 128])
    dropout: float = 0.3
    num_classes: int = 4

    # Training
    batch_size: int = 64
    learning_rate: float = 1e-3
    epochs: int = 20
    early_stopping_patience: int = 5

    # Class weights (inverse frequency: NOVA 1=15%, 2=5%, 3=20%, 4=60%)
    class_weights: List[float] = field(default_factory=lambda: [6.67, 20.0, 5.0, 1.67])

    # Confidence threshold
    confidence_threshold: float = 0.60

    # Data paths
    training_data: Path = DATA_RAW / "foodscore" / "openfoodfacts_us.csv.gz"
    tokenizer_path: Path = WEIGHTS_DIR / "nova_tokenizer.json"
    output_model: Path = WEIGHTS_DIR / "nova_classifier.pt"

    # Device
    device: str = "cuda"


@dataclass
class AdditiveRiskScorerConfig:
    """Configuration for additive risk scoring MLP."""

    # Model architecture
    # Features: type(6) + fda_status(2) + eu_status(3) + is_artificial(1) + is_petroleum_based(1) = 13
    input_features: int = 13
    hidden_dims: List[int] = field(default_factory=lambda: [64, 32])
    dropout: float = 0.2
    output_dim: int = 1

    # Feature categories (matching additive_risks.csv)
    type_categories: List[str] = field(default_factory=lambda: [
        "dye", "sweetener", "preservative", "emulsifier", "flavor", "other"
    ])
    fda_categories: List[str] = field(default_factory=lambda: ["approved", "banned"])
    eu_categories: List[str] = field(default_factory=lambda: ["approved", "restricted", "banned"])

    # Training
    batch_size: int = 32
    learning_rate: float = 1e-3
    epochs: int = 100
    early_stopping_patience: int = 30

    # Data paths
    training_data: Path = DATA_RAW / "foodscore" / "additive_risks.csv"
    output_model: Path = WEIGHTS_DIR / "additive_scorer.pt"

    # Device
    device: str = "cpu"  # Small model, CPU is fine


# Default configs
PROCEDURE_ENCODER_CONFIG = ProcedureEncoderConfig()
NOVA_CLASSIFIER_CONFIG = NovaClassifierConfig()
ADDITIVE_SCORER_CONFIG = AdditiveRiskScorerConfig()
