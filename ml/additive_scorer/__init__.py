"""
Additive Risk Scorer - MLP for food additive risk assessment.

Predicts a continuous risk score (0-100) for food additives based on:
- Additive type (dye, sweetener, preservative, emulsifier, flavor, other)
- FDA regulatory status (approved, banned)
- EU regulatory status (approved, restricted, banned)
- Is artificial (synthetic vs natural)
- Is petroleum-based

Risk categories:
- 0-30: Low risk (generally safe)
- 30-70: Moderate risk (exercise caution)
- 70-100: High risk (significant concerns)

Data source: additive_risks.csv with 43+ additives including:
- Red 40, Yellow 5, Yellow 6 (artificial dyes)
- Aspartame, Sucralose, Stevia (sweeteners)
- BHA, BHT, Sodium Nitrite (preservatives)
- Carrageenan, Polysorbate 80 (emulsifiers)
"""

from .model import AdditiveRiskScorer, AdditiveFeatureEncoder
from .inference import AdditiveRiskService, AdditiveRiskResult

__all__ = [
    "AdditiveRiskScorer",
    "AdditiveFeatureEncoder",
    "AdditiveRiskService",
    "AdditiveRiskResult",
]
