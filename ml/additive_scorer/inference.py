"""
Inference utilities for Additive Risk Scorer

Provides a service class for scoring food additives based on their
regulatory status and chemical properties.
"""

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

from ml.config import ADDITIVE_SCORER_CONFIG
from ml.additive_scorer.model import (
    AdditiveRiskScorer,
    AdditiveFeatureEncoder,
    get_risk_category,
    get_risk_description,
)


@dataclass
class AdditiveRiskResult:
    """Result of additive risk scoring."""
    name: str
    risk_score: float  # 0-100
    risk_category: str  # "low", "moderate", "high"
    risk_description: str
    fda_status: str
    eu_status: str
    additive_type: str
    is_artificial: bool
    notes: Optional[str] = None


class AdditiveRiskService:
    """
    Service for scoring food additives.

    Usage:
        service = AdditiveRiskService.load()
        result = service.score_additive("Red 40")
        print(result.risk_score)  # 85
        print(result.risk_category)  # "high"
    """

    def __init__(
        self,
        model: AdditiveRiskScorer,
        encoder: AdditiveFeatureEncoder,
        lookup_df: pd.DataFrame,
        device: str = "cpu",
    ):
        """
        Initialize the service.

        Args:
            model: Trained AdditiveRiskScorer
            encoder: Feature encoder
            lookup_df: DataFrame with additive information
            device: Device for inference
        """
        self.model = model
        self.encoder = encoder
        self.lookup_df = lookup_df
        self.device = device
        if self.model is not None:
            self.model.eval()

        # Build name lookup index (lowercase)
        self._name_index = {}
        for idx, row in lookup_df.iterrows():
            name = row["name"].lower().strip()
            self._name_index[name] = idx

            # Add aliases if present
            if "aliases" in row and pd.notna(row["aliases"]):
                for alias in str(row["aliases"]).split("|"):
                    alias = alias.lower().strip()
                    if alias:
                        self._name_index[alias] = idx

    @classmethod
    def load(
        cls,
        model_path: Optional[str] = None,
        lookup_path: Optional[str] = None,
        device: str = "cpu",
    ) -> "AdditiveRiskService":
        """
        Load the service from saved files.

        Args:
            model_path: Path to model checkpoint
            lookup_path: Path to additive lookup CSV/parquet
            device: Device for inference

        Returns:
            Initialized AdditiveRiskService
        """
        config = ADDITIVE_SCORER_CONFIG

        model_path = model_path or str(config.output_model)

        # Default lookup paths
        csv_path = Path(__file__).parent.parent.parent / "data" / "raw" / "foodscore" / "additive_risks.csv"
        parquet_path = Path(__file__).parent.parent.parent / "data" / "processed" / "foodscore" / "additive_lookup.parquet"

        # Load lookup data
        if lookup_path:
            lookup_path = Path(lookup_path)
        elif csv_path.exists():
            lookup_path = csv_path
        elif parquet_path.exists():
            lookup_path = parquet_path
        else:
            raise FileNotFoundError("No additive lookup data found")

        if str(lookup_path).endswith(".csv"):
            lookup_df = pd.read_csv(lookup_path)
        else:
            lookup_df = pd.read_parquet(lookup_path)

        print(f"Loaded {len(lookup_df)} additives from {lookup_path}")

        # Load model if exists, otherwise use lookup scores directly
        if Path(model_path).exists():
            model = AdditiveRiskScorer.load(model_path, device=device)
        else:
            print(f"Model not found at {model_path}, using lookup table scores")
            model = None

        encoder = AdditiveFeatureEncoder()

        return cls(
            model=model,
            encoder=encoder,
            lookup_df=lookup_df,
            device=device,
        )

    def _lookup_additive(self, name: str) -> Optional[pd.Series]:
        """Look up additive by name."""
        name_lower = name.lower().strip()

        if name_lower in self._name_index:
            idx = self._name_index[name_lower]
            return self.lookup_df.iloc[idx]

        # Fuzzy match - check if name contains or is contained
        for key, idx in self._name_index.items():
            if name_lower in key or key in name_lower:
                return self.lookup_df.iloc[idx]

        return None

    def score_additive(self, name: str) -> AdditiveRiskResult:
        """
        Score a single additive by name.

        Args:
            name: Additive name (e.g., "Red 40", "E129", "Allura Red")

        Returns:
            AdditiveRiskResult with score and metadata
        """
        # Look up additive
        additive_data = self._lookup_additive(name)

        if additive_data is None:
            # Unknown additive - return moderate risk with warning
            return AdditiveRiskResult(
                name=name,
                risk_score=50.0,
                risk_category="moderate",
                risk_description="Unknown additive - insufficient data",
                fda_status="unknown",
                eu_status="unknown",
                additive_type="unknown",
                is_artificial=False,
                notes="Not found in database. Risk score is estimated.",
            )

        # Get attributes
        fda_status = str(additive_data.get("fda_status", "approved")).lower()
        eu_status = str(additive_data.get("eu_status", "approved")).lower()
        additive_type = str(additive_data.get("type", "other")).lower()
        is_artificial = bool(additive_data.get("is_artificial", False))
        is_petroleum = bool(additive_data.get("is_petroleum_based", False))
        notes = additive_data.get("notes") if "notes" in additive_data else None

        # Get risk score
        if self.model is not None:
            # Use model prediction
            features = self.encoder.encode({
                "type": additive_type,
                "fda_status": fda_status,
                "eu_status": eu_status,
                "is_artificial": is_artificial,
                "is_petroleum_based": is_petroleum,
            })
            features_tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)
            risk_score = self.model.predict(features_tensor).item()
        else:
            # Use lookup table score
            risk_score = float(additive_data.get("risk_score", 50))

        return AdditiveRiskResult(
            name=str(additive_data.get("name", name)),
            risk_score=risk_score,
            risk_category=get_risk_category(risk_score),
            risk_description=get_risk_description(risk_score),
            fda_status=fda_status,
            eu_status=eu_status,
            additive_type=additive_type,
            is_artificial=is_artificial,
            notes=notes,
        )

    def score_batch(self, names: List[str]) -> List[AdditiveRiskResult]:
        """
        Score multiple additives.

        Args:
            names: List of additive names

        Returns:
            List of AdditiveRiskResult
        """
        return [self.score_additive(name) for name in names]

    def score_product_ingredients(self, ingredients_text: str) -> Dict:
        """
        Analyze a product's ingredient list for additive risks.

        Args:
            ingredients_text: Comma-separated ingredient list

        Returns:
            Dict with analysis results
        """
        # Parse ingredients
        ingredients = [i.strip() for i in ingredients_text.split(",") if i.strip()]

        # Find additives
        found_additives = []
        for ing in ingredients:
            additive = self._lookup_additive(ing)
            if additive is not None:
                result = self.score_additive(ing)
                found_additives.append(result)

        # Calculate aggregate metrics
        if found_additives:
            scores = [a.risk_score for a in found_additives]
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            high_risk = [a for a in found_additives if a.risk_category == "high"]
            moderate_risk = [a for a in found_additives if a.risk_category == "moderate"]
        else:
            max_score = 0
            avg_score = 0
            high_risk = []
            moderate_risk = []

        return {
            "ingredient_count": len(ingredients),
            "additive_count": len(found_additives),
            "additives": found_additives,
            "max_risk_score": max_score,
            "avg_risk_score": avg_score,
            "high_risk_additives": high_risk,
            "moderate_risk_additives": moderate_risk,
            "overall_risk": get_risk_category(max_score) if found_additives else "low",
        }

    def get_all_additives(self) -> List[Dict]:
        """
        Get list of all known additives with their scores.

        Returns:
            List of additive dicts
        """
        additives = []
        seen_names = set()

        for _, row in self.lookup_df.iterrows():
            name = row["name"]
            if name.lower() in seen_names:
                continue
            seen_names.add(name.lower())

            additives.append({
                "name": name,
                "risk_score": float(row.get("risk_score", 50)),
                "risk_category": get_risk_category(float(row.get("risk_score", 50))),
                "type": str(row.get("type", "other")),
                "fda_status": str(row.get("fda_status", "approved")),
                "eu_status": str(row.get("eu_status", "approved")),
            })

        return sorted(additives, key=lambda x: x["risk_score"], reverse=True)


# Convenience function
def score_additive(
    name: str,
    service: Optional[AdditiveRiskService] = None,
) -> AdditiveRiskResult:
    """
    Quick function to score a single additive.

    Loads the service if not provided (caches for subsequent calls).

    Args:
        name: Additive name
        service: Optional pre-loaded service

    Returns:
        AdditiveRiskResult
    """
    if service is None:
        if not hasattr(score_additive, "_service"):
            score_additive._service = AdditiveRiskService.load()
        service = score_additive._service

    return service.score_additive(name)
