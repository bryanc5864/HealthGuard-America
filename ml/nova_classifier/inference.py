"""
Inference utilities for NOVA Classifier

Provides a service class for classifying food products into NOVA 1-4
based on ingredient lists.
"""

import torch
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from ml.config import NOVA_CLASSIFIER_CONFIG
from ml.nova_classifier.model import NovaClassifier
from ml.nova_classifier.tokenizer import IngredientTokenizer


# NOVA group descriptions
NOVA_DESCRIPTIONS = {
    1: "Unprocessed or minimally processed foods",
    2: "Processed culinary ingredients",
    3: "Processed foods",
    4: "Ultra-processed food and drink products",
}


@dataclass
class NovaClassification:
    """Result of NOVA classification."""
    ingredients_text: str
    nova_group: int  # 1-4
    confidence: float
    description: str
    probabilities: List[float]  # [NOVA1_prob, NOVA2_prob, NOVA3_prob, NOVA4_prob]
    is_confident: bool  # True if confidence >= threshold


class NovaClassificationService:
    """
    Service for classifying food products into NOVA groups.

    Usage:
        service = NovaClassificationService.load()
        result = service.classify("water, high fructose corn syrup, artificial flavors")
        print(result.nova_group)  # 4
        print(result.confidence)  # 0.95
    """

    def __init__(
        self,
        model: NovaClassifier,
        tokenizer: IngredientTokenizer,
        confidence_threshold: float = 0.60,
        temperature: float = 1.0,
        device: str = "cpu",
    ):
        """
        Initialize the classification service.

        Args:
            model: Trained NovaClassifier
            tokenizer: Fitted tokenizer
            confidence_threshold: Minimum confidence for "confident" classification
            temperature: Temperature for calibrated confidence
            device: Device for inference
        """
        self.model = model
        self.tokenizer = tokenizer
        self.confidence_threshold = confidence_threshold
        self.temperature = temperature
        self.device = device

        self.model.eval()

    @classmethod
    def load(
        cls,
        model_path: Optional[str] = None,
        tokenizer_path: Optional[str] = None,
        device: str = "cpu",
    ) -> "NovaClassificationService":
        """
        Load the classification service from saved files.

        Args:
            model_path: Path to model checkpoint
            tokenizer_path: Path to tokenizer
            device: Device for inference

        Returns:
            Initialized NovaClassificationService
        """
        config = NOVA_CLASSIFIER_CONFIG

        model_path = model_path or str(config.output_model)
        tokenizer_path = tokenizer_path or str(config.tokenizer_path)

        # Load model
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Please train the model first: python -m ml.nova_classifier.train"
            )

        model = NovaClassifier.load(model_path, device=device)

        # Load tokenizer
        if not Path(tokenizer_path).exists():
            raise FileNotFoundError(
                f"Tokenizer not found at {tokenizer_path}. "
                "Please train the model first."
            )

        tokenizer = IngredientTokenizer.load(tokenizer_path)

        # Load temperature if available
        temperature = 1.0
        temp_path = model_path.replace(".pt", "_temperature.pt")
        if Path(temp_path).exists():
            temp_data = torch.load(temp_path)
            temperature = temp_data["temperature"]

        return cls(
            model=model,
            tokenizer=tokenizer,
            confidence_threshold=config.confidence_threshold,
            temperature=temperature,
            device=device,
        )

    def classify(self, ingredients_text: str) -> NovaClassification:
        """
        Classify a single product.

        Args:
            ingredients_text: Ingredient list text

        Returns:
            NovaClassification result
        """
        results = self.classify_batch([ingredients_text])
        return results[0]

    def classify_batch(self, ingredients_list: List[str]) -> List[NovaClassification]:
        """
        Classify multiple products.

        Args:
            ingredients_list: List of ingredient texts

        Returns:
            List of NovaClassification results
        """
        # Tokenize
        input_ids = torch.tensor(
            self.tokenizer.encode_batch(ingredients_list),
            dtype=torch.long,
        ).to(self.device)

        # Inference
        with torch.no_grad():
            logits = self.model(input_ids)

            # Apply temperature scaling
            logits = logits / self.temperature

            # Get probabilities
            probs = torch.softmax(logits, dim=1).cpu().numpy()

        results = []
        for i, ingredients in enumerate(ingredients_list):
            # Get prediction
            nova_group = int(np.argmax(probs[i])) + 1  # Convert to 1-4
            confidence = float(probs[i, nova_group - 1])
            probabilities = probs[i].tolist()

            results.append(NovaClassification(
                ingredients_text=ingredients,
                nova_group=nova_group,
                confidence=confidence,
                description=NOVA_DESCRIPTIONS[nova_group],
                probabilities=probabilities,
                is_confident=confidence >= self.confidence_threshold,
            ))

        return results

    def get_nova_indicators(self, ingredients_text: str) -> dict:
        """
        Analyze ingredients for NOVA indicators.

        Returns a breakdown of what pushed the classification.

        Args:
            ingredients_text: Ingredient list

        Returns:
            Dict with indicator analysis
        """
        # Ultra-processed (NOVA 4) indicators
        nova4_indicators = [
            "high fructose corn syrup", "corn syrup", "maltodextrin",
            "monosodium glutamate", "msg", "artificial flavor",
            "natural flavor", "modified food starch", "hydrogenated",
            "carrageenan", "sodium nitrite", "sodium nitrate",
            "red 40", "yellow 5", "yellow 6", "blue 1", "blue 2",
            "caramel color", "bht", "bha", "tbhq", "polysorbate",
            "sodium benzoate", "potassium sorbate", "aspartame",
            "sucralose", "acesulfame", "saccharin", "xanthan gum",
            "guar gum", "lecithin", "mono and diglycerides",
            "autolyzed yeast", "mechanically separated",
        ]

        # Processed (NOVA 3) indicators
        nova3_indicators = [
            "canned", "cured", "smoked", "pickled", "preserved",
        ]

        text_lower = ingredients_text.lower()

        found_nova4 = [ind for ind in nova4_indicators if ind in text_lower]
        found_nova3 = [ind for ind in nova3_indicators if ind in text_lower]

        # Count ingredients (more ingredients often = more processed)
        ingredient_count = len([x for x in ingredients_text.split(",") if x.strip()])

        return {
            "nova4_indicators": found_nova4,
            "nova3_indicators": found_nova3,
            "ingredient_count": ingredient_count,
            "likely_ultra_processed": len(found_nova4) >= 2,
        }


# Convenience function for quick classification
def classify_nova(
    ingredients_text: str,
    service: Optional[NovaClassificationService] = None,
) -> NovaClassification:
    """
    Quick function to classify a single product.

    Loads the service if not provided (caches for subsequent calls).

    Args:
        ingredients_text: Ingredient list
        service: Optional pre-loaded service

    Returns:
        NovaClassification result
    """
    if service is None:
        if not hasattr(classify_nova, "_service"):
            classify_nova._service = NovaClassificationService.load()
        service = classify_nova._service

    return service.classify(ingredients_text)
