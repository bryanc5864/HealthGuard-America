"""
FoodScore Module - Food Safety and MAHA Scoring

This module provides food product analysis:
- Food product information from OpenFoodFacts
- NOVA food processing classification
- Additive detection and risk scoring
- MAHA Score calculation (0-100 health score)
- SNAP eligibility analysis
"""

from .models import (
    FoodProduct,
    Additive,
    ProductAdditive,
    FoodCategory,
    NovaGroup,
    NutriScore,
    AdditiveType,
    RegulatoryStatus,
)

__all__ = [
    "FoodProduct",
    "Additive",
    "ProductAdditive",
    "FoodCategory",
    "NovaGroup",
    "NutriScore",
    "AdditiveType",
    "RegulatoryStatus",
]
