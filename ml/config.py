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
    log_interval: int = 10  # Log every N batches

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
    log_interval: int = 50  # Log every N batches

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
    log_interval: int = 5  # Log every N batches

    # Data paths
    training_data: Path = DATA_RAW / "foodscore" / "additive_risks.csv"
    output_model: Path = WEIGHTS_DIR / "additive_scorer.pt"

    # Device - use GPU if available
    device: str = "cuda"


@dataclass
class ChronicRiskPredictorConfig:
    """Configuration for chronic disease risk prediction model."""

    # Input features (environmental + socioeconomic factors)
    # These predict chronic disease outcomes
    input_features: List[str] = field(default_factory=lambda: [
        # Food environment
        "grocery_stores_per_1000",
        "fast_food_restaurants_per_1000",
        "food_environment_index",
        "food_insecurity_rate",
        "pct_limited_food_access",
        # Healthcare access
        "pcp_rate",
        "mental_health_provider_rate",
        "pct_uninsured",
        "preventable_hospitalizations",
        # Socioeconomic
        "median_household_income",
        "child_poverty_rate",
        "income_inequality_ratio",
        "high_school_graduation_rate",
        "pct_some_college",
        # Behavioral
        "physical_inactivity_prevalence",
        "excessive_drinking_prevalence",
        "smoking_prevalence",
        "pct_insufficient_sleep",
        # Demographics
        "pct_rural",
    ])

    # Target chronic disease outcomes to predict
    target_outcomes: List[str] = field(default_factory=lambda: [
        "diabetes_prevalence",
        "obesity_prevalence",
        "heart_disease_prevalence",
        "high_bp_prevalence",
        "copd_prevalence",
        "depression_prevalence",
    ])

    # Model architecture - Multi-task MLP
    hidden_dims: List[int] = field(default_factory=lambda: [256, 128, 64])
    dropout: float = 0.3
    use_batch_norm: bool = True

    # Training
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 200
    early_stopping_patience: int = 20
    validation_split: float = 0.2

    # Loss weights for multi-task learning (can prioritize certain diseases)
    task_weights: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0])

    # Data paths
    training_data: Path = DATA_PROCESSED / "chroniccare" / "chroniccare_merged.parquet"
    output_model: Path = WEIGHTS_DIR / "chronic_risk_predictor.pt"
    feature_scaler: Path = WEIGHTS_DIR / "chronic_feature_scaler.pkl"

    # Device
    device: str = "cuda"


@dataclass
class InterventionPrioritizerConfig:
    """Configuration for MAHA intervention prioritization model."""

    # Input features for prioritization
    input_features: List[str] = field(default_factory=lambda: [
        # Disease burden (what we want to reduce)
        "diabetes_prevalence",
        "obesity_prevalence",
        "heart_disease_prevalence",
        "high_bp_prevalence",
        "chronic_disease_burden_score",
        # Food environment (intervention targets)
        "food_environment_score",
        "grocery_stores_per_1000",
        "fast_food_restaurants_per_1000",
        "food_insecurity_rate",
        "pct_limited_food_access",
        # Healthcare gaps
        "pcp_rate",
        "pct_uninsured",
        "preventable_hospitalizations",
        # Population vulnerability
        "child_poverty_rate",
        "median_household_income",
        "pct_rural",
    ])

    # Priority classes
    priority_classes: List[str] = field(default_factory=lambda: [
        "critical",   # Immediate intervention needed
        "high",       # High priority
        "medium",     # Moderate priority
        "low",        # Lower priority / monitoring
    ])
    num_classes: int = 4

    # Model architecture
    hidden_dims: List[int] = field(default_factory=lambda: [128, 64, 32])
    dropout: float = 0.3
    use_batch_norm: bool = True

    # Training
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 100
    early_stopping_patience: int = 15
    validation_split: float = 0.2

    # Class weights (inverse frequency to handle imbalance)
    class_weights: List[float] = field(default_factory=lambda: [10.0, 3.0, 1.0, 1.0])

    # Data paths
    training_data: Path = DATA_PROCESSED / "chroniccare" / "chroniccare_merged.parquet"
    output_model: Path = WEIGHTS_DIR / "intervention_prioritizer.pt"

    # Device
    device: str = "cuda"


# Default configs
PROCEDURE_ENCODER_CONFIG = ProcedureEncoderConfig()
NOVA_CLASSIFIER_CONFIG = NovaClassifierConfig()
ADDITIVE_SCORER_CONFIG = AdditiveRiskScorerConfig()
CHRONIC_RISK_CONFIG = ChronicRiskPredictorConfig()
INTERVENTION_PRIORITIZER_CONFIG = InterventionPrioritizerConfig()
