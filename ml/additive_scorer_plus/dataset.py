"""
FoodScore+ Dataset

Prepares additive data with text (name) and categorical features
for the enhanced model.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, List
from torch.utils.data import Dataset
import torch
from transformers import AutoTokenizer


# Default paths - FoodScore+ uses the LARGER 344-additive dataset
DEFAULT_PARQUET_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "foodscore" / "additive_lookup.parquet"
DEFAULT_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "raw" / "foodscore" / "additive_risks.csv"


# Category mappings
TYPE_TO_IDX = {"dye": 0, "sweetener": 1, "preservative": 2, "emulsifier": 3, "flavor": 4, "other": 5}
FDA_TO_IDX = {"approved": 0, "banned": 1}
EU_TO_IDX = {"approved": 0, "restricted": 1, "banned": 2}


class AdditivePlusDataset(Dataset):
    """
    Dataset for FoodScore+ training.

    Each sample contains:
    - input_ids, attention_mask: Tokenized additive name
    - type_idx, fda_idx, eu_idx: Categorical indices
    - binary_features: [is_artificial, is_petroleum_based]
    - label: Risk score (0-100)
    """

    def __init__(
        self,
        names: List[str],
        types: List[str],
        fda_statuses: List[str],
        eu_statuses: List[str],
        is_artificial: List[bool],
        is_petroleum: List[bool],
        labels: np.ndarray,
        tokenizer: AutoTokenizer,
        max_length: int = 32,
    ):
        self.names = names
        self.types = types
        self.fda_statuses = fda_statuses
        self.eu_statuses = eu_statuses
        self.is_artificial = is_artificial
        self.is_petroleum = is_petroleum
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        # Tokenize name
        tokens = self.tokenizer(
            self.names[idx].lower(),
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        # Categorical indices
        type_idx = TYPE_TO_IDX.get(self.types[idx].lower(), 5)
        fda_idx = FDA_TO_IDX.get(self.fda_statuses[idx].lower(), 0)
        eu_idx = EU_TO_IDX.get(self.eu_statuses[idx].lower(), 0)

        # Binary features
        binary = torch.tensor([
            float(self.is_artificial[idx]),
            float(self.is_petroleum[idx]),
        ], dtype=torch.float32)

        return {
            "input_ids": tokens["input_ids"].squeeze(0),
            "attention_mask": tokens["attention_mask"].squeeze(0),
            "type_idx": torch.tensor(type_idx, dtype=torch.long),
            "fda_idx": torch.tensor(fda_idx, dtype=torch.long),
            "eu_idx": torch.tensor(eu_idx, dtype=torch.long),
            "binary_features": binary,
            "labels": self.labels[idx],
        }


def load_additive_data_plus(data_path: Path = None) -> pd.DataFrame:
    """Load additive data from parquet (344 additives) or CSV."""
    if data_path is None:
        if DEFAULT_PARQUET_PATH is not None and DEFAULT_PARQUET_PATH.exists():
            data_path = DEFAULT_PARQUET_PATH
        elif DEFAULT_CSV_PATH.exists():
            data_path = DEFAULT_CSV_PATH
        else:
            raise FileNotFoundError("No additive data found")

    print(f"Loading additive data from {data_path}...")

    if str(data_path).endswith('.parquet'):
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    # Ensure required columns
    required = ['name', 'risk_score', 'type', 'fda_status', 'eu_status']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Fill missing boolean columns
    if 'is_artificial' not in df.columns:
        df['is_artificial'] = df['type'].str.lower().isin(['dye', 'sweetener', 'preservative'])
    if 'is_petroleum_based' not in df.columns:
        df['is_petroleum_based'] = df['type'].str.lower() == 'dye'

    # Clean data
    df['name'] = df['name'].astype(str).str.lower().str.strip()
    df['type'] = df['type'].astype(str).str.lower().str.strip()
    df['fda_status'] = df['fda_status'].astype(str).str.lower().str.strip()
    df['eu_status'] = df['eu_status'].astype(str).str.lower().str.strip()
    df['is_artificial'] = df['is_artificial'].fillna(False).astype(bool)
    df['is_petroleum_based'] = df['is_petroleum_based'].fillna(False).astype(bool)

    print(f"Loaded {len(df)} additives")
    print(f"Risk score range: {df['risk_score'].min()} - {df['risk_score'].max()}")
    print(f"Types: {df['type'].value_counts().to_dict()}")

    return df


def prepare_data_plus(
    df: pd.DataFrame,
    tokenizer: AutoTokenizer,
    max_length: int = 32,
) -> Tuple[List, List, List, List, List, List, np.ndarray]:
    """
    Prepare data for FoodScore+ dataset.

    Returns:
        names, types, fda_statuses, eu_statuses, is_artificial, is_petroleum, labels
    """
    names = df['name'].tolist()
    types = df['type'].tolist()
    fda_statuses = df['fda_status'].tolist()
    eu_statuses = df['eu_status'].tolist()
    is_artificial = df['is_artificial'].tolist()
    is_petroleum = df['is_petroleum_based'].tolist()
    labels = df['risk_score'].values.astype(np.float32)

    return names, types, fda_statuses, eu_statuses, is_artificial, is_petroleum, labels


def split_data_plus(
    df: pd.DataFrame,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split DataFrame into train/val/test sets.

    Uses stratified splitting based on risk category.
    """
    np.random.seed(seed)

    # Create risk categories for stratification
    df = df.copy()
    df['risk_cat'] = pd.cut(df['risk_score'], bins=[0, 30, 70, 100], labels=['low', 'med', 'high'])

    # Shuffle
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    n = len(df)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_df = df.iloc[:n_train].copy()
    val_df = df.iloc[n_train:n_train + n_val].copy()
    test_df = df.iloc[n_train + n_val:].copy()

    # Drop helper column
    for d in [train_df, val_df, test_df]:
        d.drop('risk_cat', axis=1, inplace=True)

    print(f"\nData split:")
    print(f"  Train: {len(train_df)} ({len(train_df)/n*100:.1f}%)")
    print(f"  Val: {len(val_df)} ({len(val_df)/n*100:.1f}%)")
    print(f"  Test: {len(test_df)} ({len(test_df)/n*100:.1f}%)")

    return train_df, val_df, test_df


def create_datasets(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    tokenizer: AutoTokenizer,
    max_length: int = 32,
) -> Tuple[AdditivePlusDataset, AdditivePlusDataset, AdditivePlusDataset]:
    """Create train/val/test datasets."""
    datasets = []

    for df in [train_df, val_df, test_df]:
        names, types, fda, eu, art, pet, labels = prepare_data_plus(df, tokenizer, max_length)
        ds = AdditivePlusDataset(names, types, fda, eu, art, pet, labels, tokenizer, max_length)
        datasets.append(ds)

    return tuple(datasets)
