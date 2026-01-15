"""
ChronicCare Inference Service

Production inference for chronic disease risk prediction and intervention prioritization.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import torch

from ml.config import CHRONIC_RISK_CONFIG, INTERVENTION_PRIORITIZER_CONFIG, WEIGHTS_DIR
from ml.chroniccare.model import (
    ChronicRiskPredictor,
    InterventionPrioritizer,
    FeatureEncoder,
    MAHAIndexCalculator,
)

logger = logging.getLogger(__name__)


class ChronicRiskService:
    """
    Service for chronic disease risk prediction.

    Predicts multiple chronic disease prevalences from environmental,
    socioeconomic, and behavioral factors.
    """

    def __init__(self, device: str = "cpu"):
        """
        Initialize the service.

        Args:
            device: Device to run inference on
        """
        self.device = device
        self.model: Optional[ChronicRiskPredictor] = None
        self.encoder: Optional[FeatureEncoder] = None
        self.is_loaded = False

    def load(self) -> bool:
        """Load model and encoder from disk."""
        try:
            model_path = CHRONIC_RISK_CONFIG.output_model
            encoder_path = CHRONIC_RISK_CONFIG.feature_scaler

            if not model_path.exists():
                logger.warning(f"Model not found at {model_path}")
                return False

            if not encoder_path.exists():
                logger.warning(f"Encoder not found at {encoder_path}")
                return False

            self.model = ChronicRiskPredictor.load(str(model_path), self.device)
            self.encoder = FeatureEncoder.load(str(encoder_path))
            self.is_loaded = True

            logger.info("ChronicRiskService loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load ChronicRiskService: {e}")
            return False

    def predict(self, features: Dict[str, float]) -> Dict[str, float]:
        """
        Predict chronic disease risks for a single county.

        Args:
            features: Dict mapping feature names to values

        Returns:
            Dict mapping disease names to predicted prevalences
        """
        if not self.is_loaded:
            raise RuntimeError("Service not loaded. Call load() first.")

        # Build feature vector
        feature_vector = np.zeros((1, len(self.encoder.feature_names)), dtype=np.float32)
        for i, name in enumerate(self.encoder.feature_names):
            feature_vector[0, i] = features.get(name, np.nan)

        # Transform and predict
        X = self.encoder.transform(feature_vector)
        X_tensor = torch.FloatTensor(X).to(self.device)

        predictions = self.model.predict(X_tensor)

        return {
            name: float(pred[0])
            for name, pred in predictions.items()
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predict chronic disease risks for multiple counties.

        Args:
            df: DataFrame with feature columns

        Returns:
            DataFrame with prediction columns added
        """
        if not self.is_loaded:
            raise RuntimeError("Service not loaded. Call load() first.")

        # Extract features
        available = [c for c in self.encoder.feature_names if c in df.columns]
        X = df[available].values.astype(np.float32)

        # Pad missing features
        if len(available) < len(self.encoder.feature_names):
            full_X = np.full((len(df), len(self.encoder.feature_names)), np.nan)
            for i, name in enumerate(self.encoder.feature_names):
                if name in df.columns:
                    full_X[:, i] = df[name].values
            X = full_X

        # Transform and predict
        X_scaled = self.encoder.transform(X)
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)

        predictions = self.model.predict(X_tensor)

        # Add predictions to dataframe
        result = df.copy()
        for name, preds in predictions.items():
            result[f"predicted_{name}"] = preds.numpy()

        return result

    def get_feature_importance(self) -> Optional[Dict[str, Dict[str, float]]]:
        """Get feature importance for each target."""
        if not self.is_loaded or self.model.feature_importance is None:
            return None
        return self.model.feature_importance


class InterventionPrioritizationService:
    """
    Service for MAHA intervention prioritization.

    Classifies counties into priority tiers for intervention targeting.
    """

    def __init__(self, device: str = "cpu"):
        """
        Initialize the service.

        Args:
            device: Device to run inference on
        """
        self.device = device
        self.model: Optional[InterventionPrioritizer] = None
        self.encoder: Optional[FeatureEncoder] = None
        self.maha_calculator = MAHAIndexCalculator(weights="balanced")
        self.is_loaded = False

    def load(self) -> bool:
        """Load model and encoder from disk."""
        try:
            model_path = INTERVENTION_PRIORITIZER_CONFIG.output_model
            encoder_path = WEIGHTS_DIR / "intervention_feature_scaler.pkl"

            if not model_path.exists():
                logger.warning(f"Model not found at {model_path}")
                return False

            if not encoder_path.exists():
                logger.warning(f"Encoder not found at {encoder_path}")
                return False

            self.model = InterventionPrioritizer.load(str(model_path), self.device)
            self.encoder = FeatureEncoder.load(str(encoder_path))
            self.is_loaded = True

            logger.info("InterventionPrioritizationService loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load InterventionPrioritizationService: {e}")
            return False

    def prioritize(self, features: Dict[str, float]) -> Dict:
        """
        Get intervention priority for a single county.

        Args:
            features: Dict mapping feature names to values

        Returns:
            Dict with priority, confidence, and component scores
        """
        if not self.is_loaded:
            raise RuntimeError("Service not loaded. Call load() first.")

        # Build feature vector
        feature_vector = np.zeros((1, len(self.encoder.feature_names)), dtype=np.float32)
        for i, name in enumerate(self.encoder.feature_names):
            feature_vector[0, i] = features.get(name, np.nan)

        # Transform and predict
        X = self.encoder.transform(feature_vector)
        X_tensor = torch.FloatTensor(X).to(self.device)

        results = self.model.predict_with_names(X_tensor)
        result = results[0]

        # Add MAHA index calculation
        maha_result = self.maha_calculator.calculate(
            disease_burden=features.get("chronic_disease_burden_score", 50),
            food_environment=features.get("food_environment_score", 50),
            healthcare_access=min(100, max(0, (features.get("pcp_rate", 50) - 20) / 80 * 100)),
            economic_vulnerability=features.get("child_poverty_rate", 20),
        )

        result["maha_index"] = maha_result["maha_index"]
        result["maha_components"] = maha_result["components"]

        return result

    def prioritize_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get intervention priorities for multiple counties.

        Args:
            df: DataFrame with feature columns

        Returns:
            DataFrame with priority columns added
        """
        if not self.is_loaded:
            raise RuntimeError("Service not loaded. Call load() first.")

        # Extract features
        available = [c for c in self.encoder.feature_names if c in df.columns]
        X = df[available].values.astype(np.float32)

        # Pad missing features
        if len(available) < len(self.encoder.feature_names):
            full_X = np.full((len(df), len(self.encoder.feature_names)), np.nan)
            for i, name in enumerate(self.encoder.feature_names):
                if name in df.columns:
                    full_X[:, i] = df[name].values
            X = full_X

        # Transform and predict
        X_scaled = self.encoder.transform(X)
        X_tensor = torch.FloatTensor(X_scaled).to(self.device)

        classes, probs = self.model.predict(X_tensor)

        # Add to dataframe
        result = df.copy()
        result["priority_class"] = [self.model.class_names[c] for c in classes.numpy()]
        result["priority_index"] = classes.numpy()
        result["priority_confidence"] = probs.max(dim=1).values.numpy()

        # Add MAHA index
        disease = df.get("chronic_disease_burden_score", pd.Series([50] * len(df))).fillna(50).values
        food = df.get("food_environment_score", pd.Series([50] * len(df))).fillna(50).values
        healthcare = np.clip((df.get("pcp_rate", pd.Series([50] * len(df))).fillna(50).values - 20) / 80 * 100, 0, 100)
        economic = df.get("child_poverty_rate", pd.Series([20] * len(df))).fillna(20).values

        maha_indices, _ = self.maha_calculator.calculate_batch(disease, food, healthcare, economic)
        result["maha_index"] = maha_indices

        return result

    def get_top_priorities(
        self,
        df: pd.DataFrame,
        n: int = 100,
        tier: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get top priority counties for intervention.

        Args:
            df: DataFrame with county data
            n: Number of top counties to return
            tier: Filter by specific tier (critical, high, medium, low)

        Returns:
            DataFrame with top priority counties
        """
        result = self.prioritize_batch(df)

        if tier:
            result = result[result["priority_class"] == tier]

        return result.nlargest(n, "maha_index")


class ChronicCareMLService:
    """
    Unified ML service for all ChronicCare models.

    Provides a single interface for risk prediction and prioritization.
    """

    def __init__(self, device: str = "cpu"):
        """
        Initialize the unified service.

        Args:
            device: Device to run inference on
        """
        self.device = device
        self.risk_service = ChronicRiskService(device)
        self.prioritization_service = InterventionPrioritizationService(device)
        self._loaded = False

    def load(self) -> bool:
        """Load all models."""
        risk_ok = self.risk_service.load()
        prioritization_ok = self.prioritization_service.load()

        self._loaded = risk_ok or prioritization_ok

        if self._loaded:
            logger.info("ChronicCareMLService ready")
        else:
            logger.warning("No ChronicCare models loaded")

        return self._loaded

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def analyze_county(self, features: Dict[str, float]) -> Dict:
        """
        Full analysis for a single county.

        Args:
            features: Dict mapping feature names to values

        Returns:
            Dict with risk predictions and intervention priority
        """
        result = {
            "risk_predictions": None,
            "intervention_priority": None,
        }

        if self.risk_service.is_loaded:
            result["risk_predictions"] = self.risk_service.predict(features)

        if self.prioritization_service.is_loaded:
            result["intervention_priority"] = self.prioritization_service.prioritize(features)

        return result

    def analyze_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Full analysis for multiple counties.

        Args:
            df: DataFrame with county data

        Returns:
            DataFrame with all predictions added
        """
        result = df.copy()

        if self.risk_service.is_loaded:
            result = self.risk_service.predict_batch(result)

        if self.prioritization_service.is_loaded:
            result = self.prioritization_service.prioritize_batch(result)

        return result


# Singleton instance
_chroniccare_service: Optional[ChronicCareMLService] = None


def get_chroniccare_service(device: str = "cpu") -> ChronicCareMLService:
    """
    Get or create the ChronicCare ML service singleton.

    Args:
        device: Device to run inference on

    Returns:
        ChronicCareMLService instance
    """
    global _chroniccare_service

    if _chroniccare_service is None:
        _chroniccare_service = ChronicCareMLService(device)
        _chroniccare_service.load()

    return _chroniccare_service
