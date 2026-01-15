"""
ChronicCare Dataset Loader

Handles loading and preprocessing of county-level health data for ML training.
"""

import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Import paths from config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ml.config import DATA_PROCESSED


class ChronicCareDataset(Dataset):
    """PyTorch Dataset for ChronicCare data."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        fips_codes: Optional[np.ndarray] = None,
    ):
        self.features = torch.FloatTensor(features)
        if targets.ndim > 1:
            self.targets = torch.FloatTensor(targets)
        else:
            self.targets = torch.LongTensor(targets)
        self.fips_codes = fips_codes

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.targets[idx]


def load_chroniccare_data(data_path: Optional[Path] = None) -> pd.DataFrame:
    """Load the merged ChronicCare dataset."""
    if data_path is None:
        data_path = DATA_PROCESSED / "chroniccare" / "chroniccare_merged.parquet"

    if not data_path.exists():
        raise FileNotFoundError(f"Data not found at {data_path}")

    df = pd.read_parquet(data_path)
    logger.info(f"Loaded {len(df):,} counties from {data_path}")
    return df


def prepare_risk_prediction_data(
    df: Optional[pd.DataFrame] = None,
    feature_cols: Optional[List[str]] = None,
    target_cols: Optional[List[str]] = None,
    validation_split: float = 0.2,
    random_state: int = 42,
) -> Tuple[ChronicCareDataset, ChronicCareDataset, "FeatureEncoder", Dict]:
    """Prepare data for chronic risk prediction model."""
    from ml.chroniccare.model import FeatureEncoder
    from ml.config import CHRONIC_RISK_CONFIG

    if df is None:
        df = load_chroniccare_data()

    if feature_cols is None:
        feature_cols = CHRONIC_RISK_CONFIG.input_features
    if target_cols is None:
        target_cols = CHRONIC_RISK_CONFIG.target_outcomes

    # Get available columns
    available_features = [c for c in feature_cols if c in df.columns]
    available_targets = [c for c in target_cols if c in df.columns]

    logger.info(f"Using {len(available_features)} features, {len(available_targets)} targets")

    # Extract data
    X = df[available_features].values.astype(np.float32)
    y = df[available_targets].values.astype(np.float32)
    fips = df["fips"].values if "fips" in df.columns else None

    # Filter valid rows
    valid_mask = ~np.all(np.isnan(y), axis=1)
    X, y = X[valid_mask], y[valid_mask]
    if fips is not None:
        fips = fips[valid_mask]

    # Fit encoder
    encoder = FeatureEncoder(feature_names=available_features, scale=True)
    X_scaled = encoder.fit_transform(X)

    # Impute NaN targets
    for i in range(y.shape[1]):
        col_mean = np.nanmean(y[:, i])
        y[np.isnan(y[:, i]), i] = col_mean

    # Split
    np.random.seed(random_state)
    n_val = int(len(X_scaled) * validation_split)
    indices = np.random.permutation(len(X_scaled))

    train_ds = ChronicCareDataset(X_scaled[indices[n_val:]], y[indices[n_val:]],
                                   fips[indices[n_val:]] if fips is not None else None)
    val_ds = ChronicCareDataset(X_scaled[indices[:n_val]], y[indices[:n_val]],
                                 fips[indices[:n_val]] if fips is not None else None)

    metadata = {
        "n_train": len(train_ds), "n_val": len(val_ds),
        "n_features": len(available_features), "n_targets": len(available_targets),
        "feature_names": available_features, "target_names": available_targets,
    }

    return train_ds, val_ds, encoder, metadata


def prepare_prioritization_data(
    df: Optional[pd.DataFrame] = None,
    feature_cols: Optional[List[str]] = None,
    validation_split: float = 0.2,
    random_state: int = 42,
) -> Tuple[ChronicCareDataset, ChronicCareDataset, "FeatureEncoder", Dict]:
    """Prepare data for intervention prioritization model."""
    from ml.chroniccare.model import FeatureEncoder, MAHAIndexCalculator
    from ml.config import INTERVENTION_PRIORITIZER_CONFIG

    if df is None:
        df = load_chroniccare_data()

    if feature_cols is None:
        feature_cols = INTERVENTION_PRIORITIZER_CONFIG.input_features

    available_features = [c for c in feature_cols if c in df.columns]
    logger.info(f"Using {len(available_features)} features")

    X = df[available_features].values.astype(np.float32)
    fips = df["fips"].values if "fips" in df.columns else None

    # Generate labels using MAHA index
    calculator = MAHAIndexCalculator(weights="balanced")
    disease = df.get("chronic_disease_burden_score", pd.Series([50]*len(df))).fillna(50).values
    food = df.get("food_environment_score", pd.Series([50]*len(df))).fillna(50).values
    healthcare = np.clip((df.get("pcp_rate", pd.Series([50]*len(df))).fillna(50).values - 20) / 80 * 100, 0, 100)
    economic = df.get("child_poverty_rate", pd.Series([20]*len(df))).fillna(20).values

    _, labels = calculator.calculate_batch(disease, food, healthcare, economic)

    # Filter valid
    valid_mask = np.isnan(X).sum(axis=1) < (len(available_features) * 0.5)
    X, labels = X[valid_mask], labels[valid_mask]
    if fips is not None:
        fips = fips[valid_mask]

    encoder = FeatureEncoder(feature_names=available_features, scale=True)
    X_scaled = encoder.fit_transform(X)

    # Split
    np.random.seed(random_state)
    n_val = int(len(X_scaled) * validation_split)
    indices = np.random.permutation(len(X_scaled))

    train_ds = ChronicCareDataset(X_scaled[indices[n_val:]], labels[indices[n_val:]])
    val_ds = ChronicCareDataset(X_scaled[indices[:n_val]], labels[indices[:n_val]])

    class_names = INTERVENTION_PRIORITIZER_CONFIG.priority_classes
    metadata = {
        "n_train": len(train_ds), "n_val": len(val_ds),
        "n_features": len(available_features), "n_classes": len(class_names),
        "feature_names": available_features, "class_names": class_names,
        "class_distribution": {name: int((labels == i).sum()) for i, name in enumerate(class_names)},
    }

    return train_ds, val_ds, encoder, metadata


def create_data_loaders(
    train_dataset: ChronicCareDataset,
    val_dataset: ChronicCareDataset,
    batch_size: int = 64,
) -> Tuple[DataLoader, DataLoader]:
    """Create DataLoaders from datasets."""
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader
