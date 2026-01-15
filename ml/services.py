"""
HealthGuard ML Services - Unified API for all ML models

Provides singleton services for:
- ProcedureMatchingService: Match hospital procedures to canonical names
- NovaClassificationService: Classify foods into NOVA 1-4 groups
- AdditiveRiskService: Score food additives for health risks
- ChronicCareMLService: Chronic disease risk prediction and intervention prioritization

Usage:
    from ml.services import get_ml_services

    services = get_ml_services()

    # Procedure matching
    match = services.procedure.match("CT scan abdomen")

    # NOVA classification
    nova = services.nova.classify("water, sugar, corn syrup, artificial flavors")

    # Additive risk
    risk = services.additive.score_additive("Red 40")

    # ChronicCare analysis
    analysis = services.chroniccare.analyze_county({"diabetes_prevalence": 12.5, ...})
"""

from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MLServices:
    """Container for all ML services."""
    procedure: Optional["ProcedureMatchingService"] = None
    nova: Optional["NovaClassificationService"] = None
    additive: Optional["AdditiveRiskService"] = None
    chroniccare: Optional["ChronicCareMLService"] = None

    @property
    def all_loaded(self) -> bool:
        """Check if all services are loaded."""
        return all([self.procedure, self.nova, self.additive, self.chroniccare])

    @property
    def loaded_services(self) -> list:
        """List of loaded service names."""
        services = []
        if self.procedure:
            services.append("procedure")
        if self.nova:
            services.append("nova")
        if self.additive:
            services.append("additive")
        if self.chroniccare:
            services.append("chroniccare")
        return services


# Global singleton
_ml_services: Optional[MLServices] = None


def get_ml_services(
    load_procedure: bool = True,
    load_nova: bool = True,
    load_additive: bool = True,
    load_chroniccare: bool = True,
    device: str = "cpu",
) -> MLServices:
    """
    Get the ML services singleton.

    Services are lazily loaded on first access.

    Args:
        load_procedure: Whether to load procedure matching service
        load_nova: Whether to load NOVA classification service
        load_additive: Whether to load additive risk service
        load_chroniccare: Whether to load ChronicCare ML service
        device: Device for inference (cpu/cuda)

    Returns:
        MLServices container with loaded services
    """
    global _ml_services

    if _ml_services is None:
        _ml_services = MLServices()

    # Load procedure service
    if load_procedure and _ml_services.procedure is None:
        try:
            from ml.procedure_encoder.inference import ProcedureMatchingService
            _ml_services.procedure = ProcedureMatchingService.load(device=device)
            logger.info("Loaded Procedure Matching Service")
        except Exception as e:
            logger.warning(f"Could not load Procedure Matching Service: {e}")

    # Load NOVA service
    if load_nova and _ml_services.nova is None:
        try:
            from ml.nova_classifier.inference import NovaClassificationService
            _ml_services.nova = NovaClassificationService.load(device=device)
            logger.info("Loaded NOVA Classification Service")
        except Exception as e:
            logger.warning(f"Could not load NOVA Classification Service: {e}")

    # Load additive service
    if load_additive and _ml_services.additive is None:
        try:
            from ml.additive_scorer.inference import AdditiveRiskService
            _ml_services.additive = AdditiveRiskService.load(device=device)
            logger.info("Loaded Additive Risk Service")
        except Exception as e:
            logger.warning(f"Could not load Additive Risk Service: {e}")

    # Load ChronicCare service
    if load_chroniccare and _ml_services.chroniccare is None:
        try:
            from ml.chroniccare.inference import ChronicCareMLService
            _ml_services.chroniccare = ChronicCareMLService(device=device)
            _ml_services.chroniccare.load()
            logger.info("Loaded ChronicCare ML Service")
        except Exception as e:
            logger.warning(f"Could not load ChronicCare ML Service: {e}")

    return _ml_services


def reset_services():
    """Reset all services (useful for testing)."""
    global _ml_services
    _ml_services = None


# Convenience functions for direct access

def match_procedure(procedure_name: str, top_k: int = 5) -> dict:
    """
    Match a procedure name to canonical procedures.

    Args:
        procedure_name: Hospital's procedure name
        top_k: Number of top matches to return

    Returns:
        Dict with matched procedure info
    """
    services = get_ml_services(load_nova=False, load_additive=False)

    if services.procedure is None:
        return {
            "error": "Procedure matching service not available",
            "procedure_name": procedure_name,
        }

    result = services.procedure.match(procedure_name, top_k=top_k)
    return {
        "input": procedure_name,
        "matched_code": result.matched_code,
        "matched_description": result.matched_description,
        "confidence": result.confidence,
        "status": result.match_status,
        "alternatives": [
            {"code": m.code, "description": m.description, "score": m.score}
            for m in result.top_matches
        ],
    }


def classify_nova(ingredients_text: str) -> dict:
    """
    Classify a product into NOVA 1-4 groups.

    Args:
        ingredients_text: Comma-separated ingredient list

    Returns:
        Dict with NOVA classification
    """
    services = get_ml_services(load_procedure=False, load_additive=False)

    if services.nova is None:
        return {
            "error": "NOVA classification service not available",
            "ingredients": ingredients_text,
        }

    result = services.nova.classify(ingredients_text)
    indicators = services.nova.get_nova_indicators(ingredients_text)

    return {
        "nova_group": result.nova_group,
        "description": result.description,
        "confidence": result.confidence,
        "probabilities": {
            f"nova_{i+1}": p for i, p in enumerate(result.probabilities)
        },
        "is_confident": result.is_confident,
        "indicators": indicators,
    }


def score_additive(additive_name: str) -> dict:
    """
    Score a food additive for health risk.

    Args:
        additive_name: Name of the additive (e.g., "Red 40")

    Returns:
        Dict with risk score and metadata
    """
    services = get_ml_services(load_procedure=False, load_nova=False)

    if services.additive is None:
        return {
            "error": "Additive risk service not available",
            "additive_name": additive_name,
        }

    result = services.additive.score_additive(additive_name)

    return {
        "name": result.name,
        "risk_score": result.risk_score,
        "risk_category": result.risk_category,
        "risk_description": result.risk_description,
        "fda_status": result.fda_status,
        "eu_status": result.eu_status,
        "type": result.additive_type,
        "is_artificial": result.is_artificial,
        "notes": result.notes,
    }


def analyze_product(ingredients_text: str) -> dict:
    """
    Full product analysis: NOVA classification + additive risk scoring.

    Args:
        ingredients_text: Comma-separated ingredient list

    Returns:
        Dict with complete analysis
    """
    services = get_ml_services(load_procedure=False)

    result = {
        "ingredients_text": ingredients_text,
    }

    # NOVA classification
    if services.nova:
        nova_result = services.nova.classify(ingredients_text)
        result["nova"] = {
            "group": nova_result.nova_group,
            "description": nova_result.description,
            "confidence": nova_result.confidence,
        }

    # Additive analysis
    if services.additive:
        additive_result = services.additive.score_product_ingredients(ingredients_text)
        result["additives"] = {
            "count": additive_result["additive_count"],
            "max_risk": additive_result["max_risk_score"],
            "avg_risk": additive_result["avg_risk_score"],
            "overall_risk": additive_result["overall_risk"],
            "high_risk": [
                {"name": a.name, "score": a.risk_score}
                for a in additive_result["high_risk_additives"]
            ],
        }

    return result


# ChronicCare convenience functions

def predict_chronic_risk(features: dict) -> dict:
    """
    Predict chronic disease risks for a county.

    Args:
        features: Dict of county features (food environment, socioeconomic, etc.)

    Returns:
        Dict with predicted disease prevalences
    """
    services = get_ml_services(
        load_procedure=False, load_nova=False, load_additive=False
    )

    if services.chroniccare is None or not services.chroniccare.risk_service.is_loaded:
        return {
            "error": "ChronicCare risk prediction service not available",
        }

    return services.chroniccare.risk_service.predict(features)


def get_intervention_priority(features: dict) -> dict:
    """
    Get MAHA intervention priority for a county.

    Args:
        features: Dict of county features

    Returns:
        Dict with priority tier, confidence, and MAHA index
    """
    services = get_ml_services(
        load_procedure=False, load_nova=False, load_additive=False
    )

    if services.chroniccare is None or not services.chroniccare.prioritization_service.is_loaded:
        return {
            "error": "ChronicCare prioritization service not available",
        }

    return services.chroniccare.prioritization_service.prioritize(features)


def analyze_county(features: dict) -> dict:
    """
    Full ChronicCare analysis for a county.

    Combines risk prediction and intervention prioritization.

    Args:
        features: Dict of county features

    Returns:
        Dict with risk predictions and priority assessment
    """
    services = get_ml_services(
        load_procedure=False, load_nova=False, load_additive=False
    )

    if services.chroniccare is None:
        return {
            "error": "ChronicCare service not available",
        }

    return services.chroniccare.analyze_county(features)
