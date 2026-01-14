"""
Dataset for Procedure Encoder Training

Loads Medicare Provider Utilization data and creates training pairs
for contrastive learning:
- Positive pairs: Procedures with same CPT code
- Negative pairs: Procedures with different CPT codes (in-batch negatives)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from torch.utils.data import Dataset, DataLoader
from collections import defaultdict
import random


class ProcedureDataset(Dataset):
    """
    Dataset for contrastive learning on procedure descriptions.

    Each sample is a (anchor, positive) pair where both procedures
    share the same CPT code. Negatives are sampled in-batch.
    """

    def __init__(
        self,
        descriptions: List[str],
        cpt_codes: List[str],
        tokenizer,
        max_length: int = 128,
    ):
        """
        Initialize dataset.

        Args:
            descriptions: List of procedure descriptions
            cpt_codes: Corresponding CPT/HCPCS codes
            tokenizer: HuggingFace tokenizer
            max_length: Maximum sequence length
        """
        self.tokenizer = tokenizer
        self.max_length = max_length

        # Group descriptions by CPT code
        self.code_to_descriptions: Dict[str, List[str]] = defaultdict(list)
        for desc, code in zip(descriptions, cpt_codes):
            if desc and code:  # Skip empty
                self.code_to_descriptions[code].append(desc)

        # Filter to codes with multiple descriptions (needed for positive pairs)
        self.valid_codes = [
            code for code, descs in self.code_to_descriptions.items()
            if len(descs) >= 2
        ]

        # Create list of (anchor_idx, code) for sampling
        self.samples = []
        for code in self.valid_codes:
            descs = self.code_to_descriptions[code]
            for i in range(len(descs)):
                self.samples.append((code, i))

        print(f"Created dataset with {len(self.samples)} samples from {len(self.valid_codes)} CPT codes")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict:
        """
        Get a training sample (anchor, positive pair).

        Returns tokenized anchor and positive texts.
        """
        code, anchor_idx = self.samples[idx]
        descriptions = self.code_to_descriptions[code]

        # Get anchor
        anchor_text = descriptions[anchor_idx]

        # Get positive (different description, same code)
        positive_idx = anchor_idx
        while positive_idx == anchor_idx:
            positive_idx = random.randint(0, len(descriptions) - 1)
        positive_text = descriptions[positive_idx]

        # Tokenize
        anchor_encoded = self.tokenizer(
            anchor_text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        positive_encoded = self.tokenizer(
            positive_text,
            padding="max_length",
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        return {
            "anchor_input_ids": anchor_encoded["input_ids"].squeeze(0),
            "anchor_attention_mask": anchor_encoded["attention_mask"].squeeze(0),
            "positive_input_ids": positive_encoded["input_ids"].squeeze(0),
            "positive_attention_mask": positive_encoded["attention_mask"].squeeze(0),
            "cpt_code": code,
        }


def load_medicare_provider_data(data_path: Path) -> Tuple[List[str], List[str]]:
    """
    Load procedure descriptions and CPT codes from Medicare Provider Utilization data.

    Args:
        data_path: Path to provider utilization directory

    Returns:
        descriptions: List of procedure descriptions
        cpt_codes: Corresponding CPT/HCPCS codes
    """
    # Find the CSV file
    csv_files = list(data_path.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_path}")

    # Use the largest file (main data file)
    main_file = max(csv_files, key=lambda x: x.stat().st_size)
    print(f"Loading data from: {main_file.name}")

    # Read in chunks due to large file size
    descriptions = []
    cpt_codes = []

    # Column names from Medicare Provider Utilization file
    desc_col = "HCPCS_Desc"
    code_col = "HCPCS_Cd"

    chunk_size = 100000
    for chunk in pd.read_csv(main_file, chunksize=chunk_size, dtype=str, low_memory=False):
        if desc_col in chunk.columns and code_col in chunk.columns:
            # Get unique description-code pairs
            subset = chunk[[code_col, desc_col]].drop_duplicates()
            descriptions.extend(subset[desc_col].tolist())
            cpt_codes.extend(subset[code_col].tolist())

    # Deduplicate
    seen = set()
    unique_descriptions = []
    unique_codes = []

    for desc, code in zip(descriptions, cpt_codes):
        if pd.notna(desc) and pd.notna(code):
            key = (desc.strip().upper(), code.strip())
            if key not in seen:
                seen.add(key)
                unique_descriptions.append(desc.strip())
                unique_codes.append(code.strip())

    print(f"Loaded {len(unique_descriptions)} unique procedure descriptions")
    print(f"Covering {len(set(unique_codes))} unique CPT/HCPCS codes")

    return unique_descriptions, unique_codes


def create_canonical_procedures() -> Tuple[List[str], List[str]]:
    """
    Create canonical procedure descriptions for common CPT codes.

    These are used as reference embeddings for matching.

    Returns:
        descriptions: Canonical procedure names
        cpt_codes: CPT codes
    """
    # Common procedures with canonical descriptions
    canonical = [
        ("70551", "MRI Brain without Contrast"),
        ("70552", "MRI Brain with Contrast"),
        ("70553", "MRI Brain without and with Contrast"),
        ("71046", "Chest X-Ray 2 Views"),
        ("71047", "Chest X-Ray 3 Views"),
        ("71048", "Chest X-Ray 4 or More Views"),
        ("72148", "MRI Lumbar Spine without Contrast"),
        ("73721", "MRI Lower Extremity Joint without Contrast"),
        ("74177", "CT Abdomen and Pelvis with Contrast"),
        ("76856", "Ultrasound Pelvis Complete"),
        ("80053", "Comprehensive Metabolic Panel"),
        ("85025", "Complete Blood Count with Differential"),
        ("93000", "Electrocardiogram Complete"),
        ("93306", "Echocardiography Transthoracic Complete"),
        ("99213", "Office Visit Established Patient Level 3"),
        ("99214", "Office Visit Established Patient Level 4"),
        ("99215", "Office Visit Established Patient Level 5"),
        ("99283", "Emergency Department Visit Level 3"),
        ("99284", "Emergency Department Visit Level 4"),
        ("99285", "Emergency Department Visit Level 5"),
        ("27447", "Total Knee Replacement"),
        ("27130", "Total Hip Replacement"),
        ("43239", "Upper GI Endoscopy with Biopsy"),
        ("45380", "Colonoscopy with Biopsy"),
        ("47562", "Laparoscopic Cholecystectomy"),
        ("49505", "Inguinal Hernia Repair"),
        ("66984", "Cataract Surgery with IOL"),
    ]

    codes = [c[0] for c in canonical]
    descriptions = [c[1] for c in canonical]

    return descriptions, codes


def split_data(
    descriptions: List[str],
    cpt_codes: List[str],
    train_ratio: float = 0.8,
    seed: int = 42,
) -> Tuple[Tuple[List[str], List[str]], Tuple[List[str], List[str]]]:
    """
    Split data into train and validation sets.

    Splits by CPT code to ensure no data leakage.
    """
    random.seed(seed)

    # Group by code
    code_to_descs = defaultdict(list)
    for desc, code in zip(descriptions, cpt_codes):
        code_to_descs[code].append(desc)

    # Split codes
    codes = list(code_to_descs.keys())
    random.shuffle(codes)

    split_idx = int(len(codes) * train_ratio)
    train_codes = set(codes[:split_idx])
    val_codes = set(codes[split_idx:])

    # Create splits
    train_descs, train_codes_list = [], []
    val_descs, val_codes_list = [], []

    for desc, code in zip(descriptions, cpt_codes):
        if code in train_codes:
            train_descs.append(desc)
            train_codes_list.append(code)
        else:
            val_descs.append(desc)
            val_codes_list.append(code)

    print(f"Train: {len(train_descs)} samples, {len(train_codes)} codes")
    print(f"Val: {len(val_descs)} samples, {len(val_codes)} codes")

    return (train_descs, train_codes_list), (val_descs, val_codes_list)
