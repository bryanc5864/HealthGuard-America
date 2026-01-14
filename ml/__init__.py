"""
HealthGuard America - Machine Learning Models

Three deep learning models for healthcare data standardization:
1. Procedure Encoder - BioClinicalBERT for matching hospital procedure names
2. NOVA Classifier - CNN for food processing level classification
3. Additive Scorer - MLP for food additive risk assessment

Usage:
    from ml.services import get_ml_services, classify_nova, score_additive

    # Get all services
    services = get_ml_services()

    # Or use convenience functions
    nova = classify_nova("water, sugar, high fructose corn syrup")
    risk = score_additive("Red 40")
"""

from .config import (
    PROCEDURE_ENCODER_CONFIG,
    NOVA_CLASSIFIER_CONFIG,
    ADDITIVE_SCORER_CONFIG,
    WEIGHTS_DIR,
)

from .services import (
    get_ml_services,
    match_procedure,
    classify_nova,
    score_additive,
    analyze_product,
    MLServices,
)

__all__ = [
    # Configs
    "PROCEDURE_ENCODER_CONFIG",
    "NOVA_CLASSIFIER_CONFIG",
    "ADDITIVE_SCORER_CONFIG",
    "WEIGHTS_DIR",
    # Services
    "get_ml_services",
    "MLServices",
    # Convenience functions
    "match_procedure",
    "classify_nova",
    "score_additive",
    "analyze_product",
]
