"""
NOVA Food Classifier - Custom CNN for food processing level classification.

Classifies food products into NOVA groups based on ingredient lists:
- NOVA 1: Unprocessed/minimally processed (fresh fruits, vegetables, meats)
- NOVA 2: Processed culinary ingredients (oils, butter, sugar)
- NOVA 3: Processed foods (canned vegetables, cheese, cured meats)
- NOVA 4: Ultra-processed (soft drinks, packaged snacks, instant noodles)

NOVA 4 detection is critical for the MAHA initiative as these foods
are associated with obesity, diabetes, and other chronic diseases.
"""

from .model import NovaClassifier
from .inference import NovaClassificationService

__all__ = ["NovaClassifier", "NovaClassificationService"]
