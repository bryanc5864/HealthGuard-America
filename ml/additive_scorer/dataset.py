"""
Dataset for Additive Risk Scorer Training

Loads REAL food additive data from additive_risks.csv
NO SYNTHETIC DATA.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List, Dict
from torch.utils.data import Dataset
import torch


# Default paths relative to project root
DEFAULT_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "foodscore" / "additive_risks.csv"


class AdditiveDataset(Dataset):
    """
    Dataset for additive risk scoring.

    Each sample contains features about an additive and its
    risk score label (0-100).
    """

    def __init__(
        self,
        features: np.ndarray,
        labels: np.ndarray,
    ):
        """
        Initialize dataset.

        Args:
            features: Feature vectors [n_samples, n_features]
            labels: Risk scores [n_samples] in range [0, 100]
        """
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> dict:
        return {
            "features": self.features[idx],
            "labels": self.labels[idx],
        }


def load_additive_csv(data_path: Path = None) -> pd.DataFrame:
    """
    Load additive data from the raw CSV file.

    CSV Schema:
        - name: Additive name
        - aliases: Pipe-separated alternative names
        - type: Category (dye, sweetener, preservative, emulsifier, flavor, other)
        - risk_score: Pre-computed risk score (0-100)
        - fda_status: FDA approval status (approved, banned)
        - eu_status: EU status (approved, restricted, banned)
        - is_artificial: Boolean
        - is_petroleum_based: Boolean
        - notes: Health concern details

    Args:
        data_path: Path to CSV file

    Returns:
        DataFrame with additive data
    """
    data_path = data_path or DEFAULT_CSV_PATH

    if not data_path.exists():
        raise FileNotFoundError(f"Additive data file not found: {data_path}")

    print(f"Loading additive data from {data_path}...")

    df = pd.read_csv(data_path)

    print(f"Loaded {len(df)} additives")
    print(f"Columns: {df.columns.tolist()}")

    # Print risk score distribution
    print(f"\nRisk score range: {df['risk_score'].min()} - {df['risk_score'].max()}")
    print(f"Risk score mean: {df['risk_score'].mean():.1f}")

    # Print type distribution
    print(f"\nAdditive types:")
    for additive_type, count in df['type'].value_counts().items():
        print(f"  {additive_type}: {count}")

    return df


def prepare_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Extract features from additive DataFrame.

    Features extracted (13 total):
        - type: one-hot (6 categories)
        - fda_status: one-hot (2 categories)
        - eu_status: one-hot (3 categories)
        - is_artificial: binary (1)
        - is_petroleum_based: binary (1)

    Args:
        df: Additive DataFrame

    Returns:
        features: Feature matrix [n_samples, n_features]
        labels: Risk scores [n_samples]
        feature_info: Dict with feature names and encoding info
    """
    features_list = []
    feature_names = []

    # Additive type one-hot encoding
    type_categories = ["dye", "sweetener", "preservative", "emulsifier", "flavor", "other"]
    for cat in type_categories:
        col_name = f"type_{cat}"
        features_list.append((df["type"].str.lower() == cat).astype(float).values)
        feature_names.append(col_name)

    # FDA status one-hot
    fda_categories = ["approved", "banned"]
    for cat in fda_categories:
        col_name = f"fda_{cat}"
        features_list.append((df["fda_status"].str.lower() == cat).astype(float).values)
        feature_names.append(col_name)

    # EU status one-hot
    eu_categories = ["approved", "restricted", "banned"]
    for cat in eu_categories:
        col_name = f"eu_{cat}"
        features_list.append((df["eu_status"].str.lower() == cat).astype(float).values)
        feature_names.append(col_name)

    # Binary features
    if "is_artificial" in df.columns:
        features_list.append(df["is_artificial"].astype(float).values)
        feature_names.append("is_artificial")

    if "is_petroleum_based" in df.columns:
        features_list.append(df["is_petroleum_based"].fillna(False).astype(float).values)
        feature_names.append("is_petroleum_based")

    # Stack features
    features = np.column_stack(features_list)
    labels = df["risk_score"].values.astype(np.float32)

    feature_info = {
        "feature_names": feature_names,
        "n_features": len(feature_names),
        "type_categories": type_categories,
        "fda_categories": fda_categories,
        "eu_categories": eu_categories,
    }

    print(f"\nExtracted {feature_info['n_features']} features:")
    for name in feature_names:
        print(f"  - {name}")

    return features.astype(np.float32), labels, feature_info


def split_data(
    features: np.ndarray,
    labels: np.ndarray,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]]:
    """
    Split data into train/val/test sets.

    Args:
        features: Feature matrix
        labels: Risk scores
        train_ratio: Training set ratio
        val_ratio: Validation set ratio
        seed: Random seed

    Returns:
        (train_features, train_labels),
        (val_features, val_labels),
        (test_features, test_labels)
    """
    np.random.seed(seed)

    n = len(labels)
    indices = np.arange(n)
    np.random.shuffle(indices)

    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    train = (features[train_idx], labels[train_idx])
    val = (features[val_idx], labels[val_idx])
    test = (features[test_idx], labels[test_idx])

    print(f"\nData split:")
    print(f"  Train: {len(train[0])} samples ({len(train[0])/n*100:.1f}%)")
    print(f"  Val: {len(val[0])} samples ({len(val[0])/n*100:.1f}%)")
    print(f"  Test: {len(test[0])} samples ({len(test[0])/n*100:.1f}%)")

    return train, val, test
