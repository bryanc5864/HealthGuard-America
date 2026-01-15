"""
ChronicCare ML Models

Models for chronic disease risk prediction and intervention prioritization.

Models:
    1. ChronicRiskPredictor: Multi-task regression model
       - Predicts multiple chronic disease prevalences from environmental factors
       - Uses shared representation learning for related outcomes

    2. InterventionPrioritizer: Classification model
       - Classifies counties into intervention priority tiers
       - Supports MAHA initiative targeting

Architecture:
    Both models use MLP with batch normalization and dropout for regularization.
    Feature scaling is applied externally via FeatureEncoder.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
import numpy as np
import json
import pickle
from pathlib import Path


class ChronicRiskPredictor(nn.Module):
    """
    Multi-task regression model for chronic disease prediction.

    Predicts multiple chronic disease prevalences simultaneously from
    environmental, socioeconomic, and behavioral factors.

    Architecture:
        Input → Shared Encoder → Task-Specific Heads

        Shared Encoder:
            Linear → BatchNorm → ReLU → Dropout (repeated)

        Task Heads:
            One output head per target disease
    """

    def __init__(
        self,
        input_dim: int,
        num_targets: int = 6,
        hidden_dims: List[int] = [256, 128, 64],
        dropout: float = 0.3,
        use_batch_norm: bool = True,
        target_names: Optional[List[str]] = None,
    ):
        """
        Initialize the predictor.

        Args:
            input_dim: Number of input features
            num_targets: Number of chronic diseases to predict
            hidden_dims: Dimensions of hidden layers in shared encoder
            dropout: Dropout rate
            use_batch_norm: Whether to use batch normalization
            target_names: Names of target variables (for interpretability)
        """
        super().__init__()

        self.input_dim = input_dim
        self.num_targets = num_targets
        self.hidden_dims = hidden_dims
        self.dropout_rate = dropout
        self.use_batch_norm = use_batch_norm
        self.target_names = target_names or [f"target_{i}" for i in range(num_targets)]

        # Build shared encoder
        encoder_layers = []
        in_features = input_dim

        for hidden_dim in hidden_dims:
            encoder_layers.append(nn.Linear(in_features, hidden_dim))
            if use_batch_norm:
                encoder_layers.append(nn.BatchNorm1d(hidden_dim))
            encoder_layers.append(nn.ReLU())
            encoder_layers.append(nn.Dropout(dropout))
            in_features = hidden_dim

        self.shared_encoder = nn.Sequential(*encoder_layers)

        # Build task-specific heads (one per target)
        self.task_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dims[-1], 32),
                nn.ReLU(),
                nn.Linear(32, 1)
            )
            for _ in range(num_targets)
        ])

        # Store feature importance (updated during training)
        self.feature_importance = None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input features [batch_size, input_dim]

        Returns:
            predictions: [batch_size, num_targets] - predicted prevalences
        """
        # Shared encoding
        shared_repr = self.shared_encoder(x)

        # Task-specific predictions
        outputs = []
        for head in self.task_heads:
            outputs.append(head(shared_repr))

        return torch.cat(outputs, dim=1)

    def predict(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Get predictions with target names (inference mode).

        Args:
            x: Input features [batch_size, input_dim]

        Returns:
            Dict mapping target names to predictions
        """
        self.eval()
        with torch.no_grad():
            preds = self.forward(x)
            return {
                name: preds[:, i]
                for i, name in enumerate(self.target_names)
            }

    def get_shared_representation(self, x: torch.Tensor) -> torch.Tensor:
        """Get the shared representation for analysis."""
        self.eval()
        with torch.no_grad():
            return self.shared_encoder(x)

    def save(self, path: str) -> None:
        """Save model weights and config."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "config": {
                "input_dim": self.input_dim,
                "num_targets": self.num_targets,
                "hidden_dims": self.hidden_dims,
                "dropout": self.dropout_rate,
                "use_batch_norm": self.use_batch_norm,
                "target_names": self.target_names,
            },
            "feature_importance": self.feature_importance,
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "ChronicRiskPredictor":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device, weights_only=False)

        config = checkpoint["config"]
        model = cls(
            input_dim=config["input_dim"],
            num_targets=config["num_targets"],
            hidden_dims=config["hidden_dims"],
            dropout=config.get("dropout", 0.3),
            use_batch_norm=config.get("use_batch_norm", True),
            target_names=config.get("target_names"),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.feature_importance = checkpoint.get("feature_importance")
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model


class InterventionPrioritizer(nn.Module):
    """
    Classification model for MAHA intervention prioritization.

    Classifies counties into priority tiers:
        - Critical: Immediate intervention needed
        - High: High priority for intervention
        - Medium: Moderate priority
        - Low: Lower priority / monitoring

    Architecture:
        MLP classifier with softmax output
    """

    def __init__(
        self,
        input_dim: int,
        num_classes: int = 4,
        hidden_dims: List[int] = [128, 64, 32],
        dropout: float = 0.3,
        use_batch_norm: bool = True,
        class_names: Optional[List[str]] = None,
    ):
        """
        Initialize the prioritizer.

        Args:
            input_dim: Number of input features
            num_classes: Number of priority classes
            hidden_dims: Dimensions of hidden layers
            dropout: Dropout rate
            use_batch_norm: Whether to use batch normalization
            class_names: Names of priority classes
        """
        super().__init__()

        self.input_dim = input_dim
        self.num_classes = num_classes
        self.hidden_dims = hidden_dims
        self.dropout_rate = dropout
        self.use_batch_norm = use_batch_norm
        self.class_names = class_names or ["critical", "high", "medium", "low"]

        # Build classifier
        layers = []
        in_features = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(in_features, hidden_dim))
            if use_batch_norm:
                layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            in_features = hidden_dim

        self.encoder = nn.Sequential(*layers)
        self.classifier = nn.Linear(hidden_dims[-1], num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input features [batch_size, input_dim]

        Returns:
            logits: [batch_size, num_classes]
        """
        encoded = self.encoder(x)
        return self.classifier(encoded)

    def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get class predictions and probabilities (inference mode).

        Args:
            x: Input features [batch_size, input_dim]

        Returns:
            Tuple of (predicted_classes, probabilities)
        """
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            probs = F.softmax(logits, dim=1)
            classes = torch.argmax(probs, dim=1)
            return classes, probs

    def predict_with_names(self, x: torch.Tensor) -> List[Dict]:
        """
        Get predictions with class names and confidence.

        Args:
            x: Input features [batch_size, input_dim]

        Returns:
            List of dicts with 'priority', 'confidence', and 'all_probs'
        """
        classes, probs = self.predict(x)

        results = []
        for i in range(len(classes)):
            class_idx = classes[i].item()
            results.append({
                "priority": self.class_names[class_idx],
                "priority_index": class_idx,
                "confidence": probs[i, class_idx].item(),
                "all_probabilities": {
                    name: probs[i, j].item()
                    for j, name in enumerate(self.class_names)
                }
            })
        return results

    def save(self, path: str) -> None:
        """Save model weights and config."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "config": {
                "input_dim": self.input_dim,
                "num_classes": self.num_classes,
                "hidden_dims": self.hidden_dims,
                "dropout": self.dropout_rate,
                "use_batch_norm": self.use_batch_norm,
                "class_names": self.class_names,
            },
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "InterventionPrioritizer":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device, weights_only=False)

        config = checkpoint["config"]
        model = cls(
            input_dim=config["input_dim"],
            num_classes=config["num_classes"],
            hidden_dims=config["hidden_dims"],
            dropout=config.get("dropout", 0.3),
            use_batch_norm=config.get("use_batch_norm", True),
            class_names=config.get("class_names"),
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model


class FeatureEncoder:
    """
    Feature encoder for ChronicCare models.

    Handles:
        - Feature selection from raw data
        - Missing value imputation
        - Feature scaling (standardization)
        - Feature validation
    """

    def __init__(
        self,
        feature_names: List[str],
        scale: bool = True,
    ):
        """
        Initialize the encoder.

        Args:
            feature_names: List of feature column names to use
            scale: Whether to apply standardization
        """
        self.feature_names = feature_names
        self.scale = scale
        self.n_features = len(feature_names)

        # Scaling parameters (set during fit)
        self.means: Optional[np.ndarray] = None
        self.stds: Optional[np.ndarray] = None
        self.is_fitted = False

        # Feature statistics (for analysis)
        self.feature_stats: Dict = {}

    def fit(self, data: np.ndarray) -> "FeatureEncoder":
        """
        Fit the encoder on training data.

        Args:
            data: Feature matrix [n_samples, n_features]

        Returns:
            self
        """
        if data.shape[1] != self.n_features:
            raise ValueError(
                f"Expected {self.n_features} features, got {data.shape[1]}"
            )

        # Compute scaling parameters
        self.means = np.nanmean(data, axis=0)
        self.stds = np.nanstd(data, axis=0)

        # Prevent division by zero
        self.stds[self.stds < 1e-8] = 1.0

        # Store feature statistics
        for i, name in enumerate(self.feature_names):
            self.feature_stats[name] = {
                "mean": float(self.means[i]),
                "std": float(self.stds[i]),
                "min": float(np.nanmin(data[:, i])),
                "max": float(np.nanmax(data[:, i])),
                "missing_pct": float(np.isnan(data[:, i]).mean() * 100),
            }

        self.is_fitted = True
        return self

    def transform(self, data: np.ndarray) -> np.ndarray:
        """
        Transform features.

        Args:
            data: Feature matrix [n_samples, n_features]

        Returns:
            Transformed features
        """
        if not self.is_fitted:
            raise RuntimeError("Encoder must be fitted before transform")

        # Impute missing values with mean
        result = data.copy()
        for i in range(self.n_features):
            mask = np.isnan(result[:, i])
            result[mask, i] = self.means[i]

        # Scale if requested
        if self.scale:
            result = (result - self.means) / self.stds

        return result

    def fit_transform(self, data: np.ndarray) -> np.ndarray:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def inverse_transform(self, data: np.ndarray) -> np.ndarray:
        """Reverse the scaling transformation."""
        if not self.is_fitted:
            raise RuntimeError("Encoder must be fitted before inverse_transform")

        if self.scale:
            return data * self.stds + self.means
        return data

    def save(self, path: str) -> None:
        """Save encoder state."""
        state = {
            "feature_names": self.feature_names,
            "scale": self.scale,
            "means": self.means.tolist() if self.means is not None else None,
            "stds": self.stds.tolist() if self.stds is not None else None,
            "is_fitted": self.is_fitted,
            "feature_stats": self.feature_stats,
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)
        print(f"Encoder saved to {path}")

    @classmethod
    def load(cls, path: str) -> "FeatureEncoder":
        """Load encoder from file."""
        with open(path, "rb") as f:
            state = pickle.load(f)

        encoder = cls(
            feature_names=state["feature_names"],
            scale=state["scale"],
        )
        encoder.means = np.array(state["means"]) if state["means"] else None
        encoder.stds = np.array(state["stds"]) if state["stds"] else None
        encoder.is_fitted = state["is_fitted"]
        encoder.feature_stats = state.get("feature_stats", {})

        print(f"Encoder loaded from {path}")
        return encoder


class MAHAIndexCalculator:
    """
    Calculate MAHA (Make America Healthy Again) intervention priority index.

    Combines multiple factors into a single actionable score:
        - Disease burden (high = more urgent)
        - Food environment quality (low = more urgent)
        - Healthcare access (low = more urgent)
        - Economic vulnerability (high = more urgent)

    Score range: 0-100 (higher = more urgent intervention needed)
    """

    # Weight presets for different intervention focuses
    WEIGHT_PRESETS = {
        "balanced": {
            "disease_burden": 0.30,
            "food_environment": 0.25,
            "healthcare_access": 0.20,
            "economic_vulnerability": 0.25,
        },
        "disease_focused": {
            "disease_burden": 0.50,
            "food_environment": 0.20,
            "healthcare_access": 0.15,
            "economic_vulnerability": 0.15,
        },
        "food_focused": {
            "disease_burden": 0.20,
            "food_environment": 0.45,
            "healthcare_access": 0.15,
            "economic_vulnerability": 0.20,
        },
        "access_focused": {
            "disease_burden": 0.20,
            "food_environment": 0.20,
            "healthcare_access": 0.40,
            "economic_vulnerability": 0.20,
        },
    }

    def __init__(self, weights: str = "balanced"):
        """
        Initialize the calculator.

        Args:
            weights: Weight preset name or dict of custom weights
        """
        if isinstance(weights, str):
            if weights not in self.WEIGHT_PRESETS:
                raise ValueError(f"Unknown weight preset: {weights}")
            self.weights = self.WEIGHT_PRESETS[weights]
        else:
            self.weights = weights

    def calculate(
        self,
        disease_burden: float,
        food_environment: float,
        healthcare_access: float,
        economic_vulnerability: float,
    ) -> Dict:
        """
        Calculate MAHA index for a single county.

        Args:
            disease_burden: 0-100 (higher = worse health outcomes)
            food_environment: 0-100 (higher = better food access)
            healthcare_access: 0-100 (higher = better access)
            economic_vulnerability: 0-100 (higher = more vulnerable)

        Returns:
            Dict with index, components, and priority tier
        """
        # Invert food_environment and healthcare_access
        # (low scores = high intervention need)
        components = {
            "disease_burden": disease_burden * self.weights["disease_burden"],
            "food_environment": (100 - food_environment) * self.weights["food_environment"],
            "healthcare_access": (100 - healthcare_access) * self.weights["healthcare_access"],
            "economic_vulnerability": economic_vulnerability * self.weights["economic_vulnerability"],
        }

        maha_index = sum(components.values())

        # Determine priority tier
        if maha_index >= 75:
            tier = "critical"
        elif maha_index >= 55:
            tier = "high"
        elif maha_index >= 35:
            tier = "medium"
        else:
            tier = "low"

        return {
            "maha_index": round(maha_index, 2),
            "priority_tier": tier,
            "components": {k: round(v, 2) for k, v in components.items()},
            "weights_used": self.weights,
        }

    def calculate_batch(
        self,
        disease_burden: np.ndarray,
        food_environment: np.ndarray,
        healthcare_access: np.ndarray,
        economic_vulnerability: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate MAHA index for multiple counties.

        Returns:
            Tuple of (maha_indices, priority_tiers)
        """
        # Component scores
        db_score = disease_burden * self.weights["disease_burden"]
        fe_score = (100 - food_environment) * self.weights["food_environment"]
        ha_score = (100 - healthcare_access) * self.weights["healthcare_access"]
        ev_score = economic_vulnerability * self.weights["economic_vulnerability"]

        maha_indices = db_score + fe_score + ha_score + ev_score

        # Assign tiers
        tiers = np.zeros(len(maha_indices), dtype=int)
        tiers[maha_indices >= 75] = 0  # critical
        tiers[(maha_indices >= 55) & (maha_indices < 75)] = 1  # high
        tiers[(maha_indices >= 35) & (maha_indices < 55)] = 2  # medium
        tiers[maha_indices < 35] = 3  # low

        return maha_indices, tiers


def compute_feature_importance(
    model: ChronicRiskPredictor,
    X: torch.Tensor,
    feature_names: List[str],
) -> Dict[str, Dict[str, float]]:
    """
    Compute feature importance using gradient-based attribution.

    Args:
        model: Trained ChronicRiskPredictor
        X: Input features [n_samples, n_features]
        feature_names: Names of input features

    Returns:
        Dict mapping target names to feature importance scores
    """
    model.eval()
    X.requires_grad_(True)

    importance = {}

    for target_idx, target_name in enumerate(model.target_names):
        # Forward pass
        predictions = model(X)
        target_pred = predictions[:, target_idx]

        # Backward pass
        model.zero_grad()
        target_pred.sum().backward(retain_graph=True)

        # Gradient magnitude as importance
        grads = X.grad.abs().mean(dim=0).detach().numpy()

        # Normalize to sum to 1
        grads = grads / (grads.sum() + 1e-8)

        importance[target_name] = {
            name: float(grads[i])
            for i, name in enumerate(feature_names)
        }

        X.grad.zero_()

    return importance
