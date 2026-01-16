"""
FoodScore+ Additive Risk Scorer

Enhanced model using text embeddings + categorical features
for better performance on large additive datasets.
"""

from .model import AdditiveRiskScorerPlus
from .dataset import AdditivePlusDataset, load_additive_data_plus

__all__ = ["AdditiveRiskScorerPlus", "AdditivePlusDataset", "load_additive_data_plus"]
