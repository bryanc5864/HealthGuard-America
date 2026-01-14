"""
Additive Risk Scorer Model - Simple MLP

Architecture:
    Input(13 features after one-hot)
    → Dense(64) → ReLU → Dropout
    → Dense(32) → ReLU → Dropout
    → Dense(1) → Sigmoid → Scale to 0-100

Features (from additive_risks.csv):
    - type: dye, sweetener, preservative, emulsifier, flavor, other (6)
    - fda_status: approved, banned (2)
    - eu_status: approved, restricted, banned (3)
    - is_artificial: binary (1)
    - is_petroleum_based: binary (1)
    Total: 13 features

Predicts a continuous risk score where:
- 0-30: Low risk (safe)
- 30-70: Moderate risk (caution)
- 70-100: High risk (concerning)
"""

import torch
import torch.nn as nn
from typing import Dict, List, Optional
import numpy as np
import json


class AdditiveRiskScorer(nn.Module):
    """
    MLP for predicting additive risk scores.

    Takes feature vector and outputs risk score 0-100.
    """

    def __init__(
        self,
        input_features: int = 13,
        hidden_dims: tuple = (64, 32),
        dropout: float = 0.2,
        output_scale: float = 100.0,
    ):
        """
        Initialize the scorer.

        Args:
            input_features: Number of input features (after one-hot encoding)
            hidden_dims: Dimensions of hidden layers
            dropout: Dropout rate for regularization
            output_scale: Scale for output (default 100 for 0-100 range)
        """
        super().__init__()

        self.input_features = input_features
        self.hidden_dims = hidden_dims
        self.dropout_rate = dropout
        self.output_scale = output_scale

        # Build MLP
        layers = []
        in_features = input_features

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            in_features = hidden_dim

        # Output layer
        layers.extend([
            nn.Linear(in_features, 1),
            nn.Sigmoid(),
        ])

        self.mlp = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Feature tensor [batch_size, input_features]

        Returns:
            risk_scores: Risk scores [batch_size, 1] in range [0, output_scale]
        """
        return self.mlp(x) * self.output_scale

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get risk score predictions (inference mode).

        Args:
            x: Feature tensor [batch_size, input_features]

        Returns:
            risk_scores: Risk scores [batch_size] in range [0, 100]
        """
        self.eval()
        with torch.no_grad():
            return self.forward(x).squeeze(-1)

    def save(self, path: str) -> None:
        """Save model weights and config."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "config": {
                "input_features": self.input_features,
                "hidden_dims": self.hidden_dims,
                "dropout": self.dropout_rate,
                "output_scale": self.output_scale,
            },
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "AdditiveRiskScorer":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device, weights_only=False)

        config = checkpoint["config"]
        model = cls(
            input_features=config["input_features"],
            hidden_dims=tuple(config.get("hidden_dims", (64, 32))),
            dropout=config.get("dropout", 0.2),
            output_scale=config["output_scale"],
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model


class AdditiveFeatureEncoder:
    """
    Encodes additive attributes into feature vectors for the risk scorer.

    Matches the schema from additive_risks.csv:
        - type: Additive category (one-hot)
        - fda_status: FDA approval status (one-hot)
        - eu_status: EU regulatory status (one-hot)
        - is_artificial: Boolean
        - is_petroleum_based: Boolean
    """

    # Feature categories matching additive_risks.csv
    TYPE_CATEGORIES = ["dye", "sweetener", "preservative", "emulsifier", "flavor", "other"]
    FDA_CATEGORIES = ["approved", "banned"]
    EU_CATEGORIES = ["approved", "restricted", "banned"]

    def __init__(self):
        """Initialize the encoder."""
        self.feature_names = self._build_feature_names()

    def _build_feature_names(self) -> List[str]:
        """Build list of feature names."""
        names = []
        for cat in self.TYPE_CATEGORIES:
            names.append(f"type_{cat}")
        for cat in self.FDA_CATEGORIES:
            names.append(f"fda_{cat}")
        for cat in self.EU_CATEGORIES:
            names.append(f"eu_{cat}")
        names.append("is_artificial")
        names.append("is_petroleum_based")
        return names

    @property
    def n_features(self) -> int:
        """Return number of output features."""
        return len(self.feature_names)

    def encode(self, additive: Dict) -> np.ndarray:
        """
        Encode a single additive to feature vector.

        Args:
            additive: Dict with keys: type, fda_status, eu_status, is_artificial, is_petroleum_based

        Returns:
            Feature vector of shape (n_features,)
        """
        features = []

        # Type one-hot
        additive_type = str(additive.get("type", "other")).lower()
        for cat in self.TYPE_CATEGORIES:
            features.append(1.0 if additive_type == cat else 0.0)

        # FDA status one-hot
        fda_status = str(additive.get("fda_status", "approved")).lower()
        for cat in self.FDA_CATEGORIES:
            features.append(1.0 if fda_status == cat else 0.0)

        # EU status one-hot
        eu_status = str(additive.get("eu_status", "approved")).lower()
        for cat in self.EU_CATEGORIES:
            features.append(1.0 if eu_status == cat else 0.0)

        # Binary features
        features.append(1.0 if additive.get("is_artificial", False) else 0.0)
        features.append(1.0 if additive.get("is_petroleum_based", False) else 0.0)

        return np.array(features, dtype=np.float32)

    def encode_batch(self, additives: List[Dict]) -> np.ndarray:
        """
        Encode multiple additives.

        Args:
            additives: List of additive dicts

        Returns:
            Feature matrix of shape (n_additives, n_features)
        """
        return np.stack([self.encode(a) for a in additives])

    def save(self, path: str) -> None:
        """Save encoder configuration."""
        data = {
            "type_categories": self.TYPE_CATEGORIES,
            "fda_categories": self.FDA_CATEGORIES,
            "eu_categories": self.EU_CATEGORIES,
            "feature_names": self.feature_names,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Encoder saved to {path}")

    @classmethod
    def load(cls, path: str) -> "AdditiveFeatureEncoder":
        """Load encoder (categories are fixed, so just validates)."""
        encoder = cls()
        print(f"Encoder loaded from {path}")
        return encoder


def get_risk_category(score: float) -> str:
    """
    Get risk category from score.

    Args:
        score: Risk score 0-100

    Returns:
        Category string: "low", "moderate", or "high"
    """
    if score < 30:
        return "low"
    elif score < 70:
        return "moderate"
    else:
        return "high"


def get_risk_description(score: float) -> str:
    """
    Get human-readable risk description.

    Args:
        score: Risk score 0-100

    Returns:
        Description string
    """
    if score < 30:
        return "Low risk - Generally considered safe"
    elif score < 50:
        return "Low-moderate risk - Some concerns noted"
    elif score < 70:
        return "Moderate risk - Exercise caution"
    elif score < 85:
        return "High risk - Significant health concerns"
    else:
        return "Very high risk - Avoid if possible"
