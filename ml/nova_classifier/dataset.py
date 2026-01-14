"""
Dataset for NOVA Classifier Training

Loads OpenFoodFacts data and creates training samples with
ingredient text and NOVA labels.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List, Optional
from torch.utils.data import Dataset, DataLoader
import torch

from ml.nova_classifier.tokenizer import IngredientTokenizer


class NovaDataset(Dataset):
    """
    Dataset for NOVA classification.

    Loads products with ingredient text and NOVA labels.
    """

    def __init__(
        self,
        ingredients: List[str],
        labels: List[int],
        tokenizer: IngredientTokenizer,
    ):
        """
        Initialize dataset.

        Args:
            ingredients: List of ingredient texts
            labels: NOVA labels (0-3 for NOVA 1-4)
            tokenizer: Fitted tokenizer
        """
        self.ingredients = ingredients
        self.labels = labels
        self.tokenizer = tokenizer

    def __len__(self) -> int:
        return len(self.ingredients)

    def __getitem__(self, idx: int) -> dict:
        input_ids = self.tokenizer.encode(self.ingredients[idx])
        label = self.labels[idx]

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "labels": torch.tensor(label, dtype=torch.long),
        }


def load_openfoodfacts_data(
    data_path: Path,
    sample_size: Optional[int] = None,
) -> Tuple[List[str], List[int]]:
    """
    Load OpenFoodFacts data with NOVA labels.

    Args:
        data_path: Path to OpenFoodFacts CSV (gzipped)
        sample_size: Optional limit on number of samples

    Returns:
        ingredients: List of ingredient texts
        labels: NOVA labels (0-3)
    """
    print(f"Loading data from {data_path}...")

    # Columns to load
    usecols = ["ingredients_text", "nova_group", "countries_tags"]

    # Read data
    try:
        df = pd.read_csv(
            data_path,
            compression="gzip",
            sep="\t",
            usecols=lambda x: x in usecols,
            dtype=str,
            low_memory=False,
            on_bad_lines="skip",
        )
    except Exception as e:
        print(f"Error loading CSV: {e}")
        raise

    print(f"Loaded {len(df)} total rows")

    # Filter to products with NOVA labels and ingredients
    df = df.dropna(subset=["nova_group", "ingredients_text"])

    # Filter to US products if countries column exists
    if "countries_tags" in df.columns:
        us_mask = df["countries_tags"].str.contains("united-states", na=False, case=False)
        df = df[us_mask]
        print(f"Filtered to {len(df)} US products")

    # Convert NOVA group to integer (1-4)
    df["nova_group"] = pd.to_numeric(df["nova_group"], errors="coerce")
    df = df.dropna(subset=["nova_group"])
    df = df[df["nova_group"].isin([1, 2, 3, 4])]

    # Convert to 0-indexed labels (0-3)
    df["label"] = df["nova_group"].astype(int) - 1

    print(f"Products with valid NOVA labels: {len(df)}")

    # Sample if requested
    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)
        print(f"Sampled to {len(df)} products")

    # Get ingredients and labels
    ingredients = df["ingredients_text"].tolist()
    labels = df["label"].tolist()

    # Print class distribution
    label_counts = pd.Series(labels).value_counts().sort_index()
    print("\nClass distribution:")
    for i, count in label_counts.items():
        pct = count / len(labels) * 100
        print(f"  NOVA {i+1}: {count:,} ({pct:.1f}%)")

    return ingredients, labels


def load_processed_data(
    data_path: Path,
    sample_size: Optional[int] = None,
) -> Tuple[List[str], List[int]]:
    """
    Load from processed parquet file.

    Args:
        data_path: Path to processed parquet
        sample_size: Optional limit

    Returns:
        ingredients, labels
    """
    print(f"Loading processed data from {data_path}...")

    df = pd.read_parquet(data_path)

    # Filter to products with NOVA and ingredients
    df = df.dropna(subset=["nova_group", "ingredients_text"])

    # Convert NOVA to 0-indexed label
    df["label"] = df["nova_group"].astype(int) - 1
    df = df[df["label"].isin([0, 1, 2, 3])]

    if sample_size and len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=42)

    print(f"Loaded {len(df)} products")

    return df["ingredients_text"].tolist(), df["label"].tolist()


def split_data(
    ingredients: List[str],
    labels: List[int],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> Tuple[Tuple[List[str], List[int]], Tuple[List[str], List[int]], Tuple[List[str], List[int]]]:
    """
    Split data into train/val/test with stratification.

    Args:
        ingredients: Ingredient texts
        labels: NOVA labels
        train_ratio: Training set ratio
        val_ratio: Validation set ratio
        seed: Random seed

    Returns:
        (train_ingredients, train_labels),
        (val_ingredients, val_labels),
        (test_ingredients, test_labels)
    """
    np.random.seed(seed)

    n = len(ingredients)
    indices = np.arange(n)

    # Stratified split
    from collections import defaultdict
    class_indices = defaultdict(list)
    for i, label in enumerate(labels):
        class_indices[label].append(i)

    train_indices = []
    val_indices = []
    test_indices = []

    for label, idx_list in class_indices.items():
        np.random.shuffle(idx_list)
        n_class = len(idx_list)
        n_train = int(n_class * train_ratio)
        n_val = int(n_class * val_ratio)

        train_indices.extend(idx_list[:n_train])
        val_indices.extend(idx_list[n_train:n_train + n_val])
        test_indices.extend(idx_list[n_train + n_val:])

    # Shuffle
    np.random.shuffle(train_indices)
    np.random.shuffle(val_indices)
    np.random.shuffle(test_indices)

    def select(indices):
        return [ingredients[i] for i in indices], [labels[i] for i in indices]

    train = select(train_indices)
    val = select(val_indices)
    test = select(test_indices)

    print(f"\nData split:")
    print(f"  Train: {len(train[0]):,}")
    print(f"  Val: {len(val[0]):,}")
    print(f"  Test: {len(test[0]):,}")

    return train, val, test


def compute_class_weights(labels: List[int]) -> torch.Tensor:
    """
    Compute class weights inversely proportional to frequency.

    Args:
        labels: List of labels

    Returns:
        Tensor of class weights
    """
    counts = np.bincount(labels, minlength=4)
    # Inverse frequency
    weights = 1.0 / (counts + 1)  # +1 to avoid division by zero
    # Normalize
    weights = weights / weights.sum() * len(weights)

    print(f"\nClass weights: {weights}")

    return torch.tensor(weights, dtype=torch.float32)


    # NO SYNTHETIC DATA - Use only real OpenFoodFacts data
