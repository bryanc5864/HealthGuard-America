"""
Dataset for Procedure Encoder Training

Uses Medicare Provider Utilization data (canonical descriptions) and creates
augmented variations for contrastive learning.

Training pairs:
- Anchor: Canonical or augmented description
- Positive: Different augmentation of same CPT code
- Negatives: In-batch descriptions with different CPT codes
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from torch.utils.data import Dataset, DataLoader
from collections import defaultdict
import random
import re


# ============================================================================
# PROCEDURE NAME AUGMENTATION
# ============================================================================

# Common medical abbreviations and their expansions
ABBREVIATIONS = {
    "without": ["w/o", "wo", "w/out"],
    "with": ["w/", "w"],
    "and": ["&", "+"],
    "magnetic resonance imaging": ["mri", "mr imaging", "mr"],
    "magnetic resonance": ["mr"],
    "computed tomography": ["ct", "cat scan", "cat"],
    "x-ray": ["xray", "x ray", "radiograph"],
    "electrocardiogram": ["ecg", "ekg"],
    "electrocardiography": ["ecg", "ekg"],
    "ultrasound": ["us", "sono", "sonogram"],
    "examination": ["exam"],
    "evaluation": ["eval"],
    "procedure": ["proc"],
    "management": ["mgmt", "mgt"],
    "established": ["estab", "est"],
    "subsequent": ["subseq", "subs"],
    "initial": ["init"],
    "complete": ["comp", "compl"],
    "comprehensive": ["comp", "compr"],
    "moderate": ["mod"],
    "hospital": ["hosp"],
    "emergency": ["emerg", "er", "ed"],
    "department": ["dept"],
    "intravenous": ["iv"],
    "injection": ["inj"],
    "infusion": ["inf"],
    "bilateral": ["bilat", "bil"],
    "unilateral": ["unilat", "uni"],
    "anterior": ["ant"],
    "posterior": ["post"],
    "diagnostic": ["dx", "diag"],
    "therapeutic": ["tx", "ther"],
    "minutes": ["min", "mins"],
    "level": ["lvl", "lv"],
    "contrast": ["con", "contr"],
    "contrast material": ["dye", "contrast"],
}

# Reverse mapping for expansion
EXPANSIONS = {}
for full, abbrevs in ABBREVIATIONS.items():
    for abbrev in abbrevs:
        if abbrev not in EXPANSIONS:
            EXPANSIONS[abbrev] = full


def augment_procedure_name(description: str, num_augmentations: int = 5) -> List[str]:
    """
    Create augmented variations of a procedure description.

    Augmentation strategies:
    1. Case variations (upper, lower, title)
    2. Abbreviation substitution
    3. Word order variations
    4. Remove optional words
    5. Add/remove punctuation

    Args:
        description: Original procedure description
        num_augmentations: Number of variations to create

    Returns:
        List of augmented descriptions (including original)
    """
    variations = [description]  # Always include original
    desc_lower = description.lower()

    # Strategy 1: Case variations
    variations.append(description.upper())
    variations.append(description.lower())
    variations.append(description.title())

    # Strategy 2: Abbreviation substitution
    for full, abbrevs in ABBREVIATIONS.items():
        if full in desc_lower:
            for abbrev in abbrevs[:2]:  # Use top 2 abbreviations
                new_desc = re.sub(re.escape(full), abbrev, desc_lower, flags=re.IGNORECASE)
                variations.append(new_desc)
                variations.append(new_desc.upper())

    # Strategy 3: Expand abbreviations
    words = desc_lower.split()
    for i, word in enumerate(words):
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in EXPANSIONS:
            new_words = words.copy()
            new_words[i] = EXPANSIONS[clean_word]
            variations.append(' '.join(new_words))

    # Strategy 4: Remove common filler words
    filler_patterns = [
        r'\bper day\b', r'\bper visit\b', r'\beach\b',
        r'\busing a microscope\b', r'\bif using time\b',
        r', at least \d+ minutes', r', \d+ minutes or less',
        r', more than \d+ minutes',
    ]
    for pattern in filler_patterns:
        new_desc = re.sub(pattern, '', description, flags=re.IGNORECASE).strip()
        if new_desc != description and len(new_desc) > 10:
            variations.append(new_desc)

    # Strategy 5: Punctuation variations
    variations.append(description.replace(',', ''))
    variations.append(description.replace('-', ' '))
    variations.append(description.replace('/', ' '))

    # Strategy 6: Add common prefixes/suffixes
    prefixes = ['', 'CPT ', 'HCPCS ', 'Proc: ']
    for prefix in prefixes[1:]:
        variations.append(prefix + description)

    # Remove duplicates and empty strings, limit to num_augmentations
    unique_variations = []
    seen = set()
    for v in variations:
        v_clean = v.strip()
        v_lower = v_clean.lower()
        if v_clean and v_lower not in seen and len(v_clean) > 5:
            seen.add(v_lower)
            unique_variations.append(v_clean)
            if len(unique_variations) >= num_augmentations:
                break

    return unique_variations


# ============================================================================
# DATASET
# ============================================================================

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
        use_augmentation: bool = False,
    ):
        """
        Initialize dataset.

        Args:
            descriptions: List of procedure descriptions
            cpt_codes: Corresponding CPT/HCPCS codes
            tokenizer: HuggingFace tokenizer
            max_length: Maximum sequence length
            use_augmentation: Whether to augment descriptions (only needed for small datasets)
        """
        self.tokenizer = tokenizer
        self.max_length = max_length

        # Group descriptions by CPT code
        self.code_to_descriptions: Dict[str, List[str]] = defaultdict(list)

        for desc, code in zip(descriptions, cpt_codes):
            if desc and code:
                self.code_to_descriptions[code].append(desc)

        # Only augment if explicitly requested (for small canonical datasets)
        if use_augmentation:
            print("Applying synthetic augmentation to descriptions...")
            augmented_codes = {}
            for code, descs in self.code_to_descriptions.items():
                all_augmented = []
                for d in descs:
                    all_augmented.extend(augment_procedure_name(d, 5))
                augmented_codes[code] = list(set(all_augmented))
            self.code_to_descriptions = augmented_codes

        # Filter to codes with at least 2 descriptions (needed for positive pairs)
        self.valid_codes = [
            code for code, descs in self.code_to_descriptions.items()
            if len(descs) >= 2
        ]

        # Create list of (code, desc_idx) for sampling
        self.samples = []
        for code in self.valid_codes:
            descs = self.code_to_descriptions[code]
            for i in range(len(descs)):
                self.samples.append((code, i))

        print(f"Created dataset with {len(self.samples)} samples from {len(self.valid_codes)} CPT codes")
        print(f"Average variations per code: {len(self.samples) / len(self.valid_codes):.1f}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict:
        """
        Get a training sample (anchor, positive pair).
        """
        code, anchor_idx = self.samples[idx]
        descriptions = self.code_to_descriptions[code]

        # Get anchor
        anchor_text = descriptions[anchor_idx]

        # Get positive (different description, same code)
        positive_idx = anchor_idx
        attempts = 0
        while positive_idx == anchor_idx and attempts < 10:
            positive_idx = random.randint(0, len(descriptions) - 1)
            attempts += 1
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


# ============================================================================
# DATA LOADING
# ============================================================================

def load_medicare_procedures(data_path: Optional[Path] = None) -> Tuple[List[str], List[str]]:
    """
    Load procedure descriptions from processed Medicare data.

    Args:
        data_path: Path to medicare_procedures.csv

    Returns:
        descriptions: List of procedure descriptions
        cpt_codes: Corresponding CPT/HCPCS codes
    """
    if data_path is None:
        data_path = Path(__file__).parent.parent.parent / "data" / "processed" / "pricevision" / "medicare_procedures.csv"

    if not data_path.exists():
        raise FileNotFoundError(f"Medicare procedures file not found: {data_path}")

    df = pd.read_csv(data_path)

    descriptions = df['canonical_description'].tolist()
    cpt_codes = df['hcpcs_code'].astype(str).tolist()

    print(f"Loaded {len(descriptions)} canonical procedures from Medicare data")

    return descriptions, cpt_codes


def load_procedure_training_data() -> Tuple[List[str], List[str]]:
    """
    Load procedure training data from hospital MRF natural variations.

    Source: Hospital price transparency files with real procedure name variations.
    ~360K variations across ~11K CPT codes.

    Returns:
        descriptions: List of procedure descriptions
        cpt_codes: Corresponding CPT/HCPCS codes
    """
    # Primary: Hospital MRF natural variations (best for contrastive learning)
    variations_path = Path(__file__).parent.parent.parent / "data" / "processed" / "pricevision" / "procedure_variations_training.csv"

    if variations_path.exists():
        df = pd.read_csv(variations_path)
        print(f"Loaded {len(df):,} natural procedure variations from hospital MRF data")
        print(f"Unique CPT codes: {df['cpt_code'].nunique():,}")
        print(f"Average variations per code: {len(df) / df['cpt_code'].nunique():.1f}")
        return df['description'].tolist(), df['cpt_code'].astype(str).tolist()

    # Fallback: Medicare canonical descriptions (requires augmentation)
    medicare_path = Path(__file__).parent.parent.parent / "data" / "processed" / "pricevision" / "medicare_procedures.csv"

    if medicare_path.exists():
        print("WARNING: Using Medicare canonical data - requires synthetic augmentation")
        return load_medicare_procedures(medicare_path)

    raise FileNotFoundError("No procedure training data found. Run data extraction first.")


def create_canonical_procedures() -> Tuple[List[str], List[str]]:
    """
    Get canonical procedure descriptions for embedding index.
    Uses Medicare data if available.
    """
    # Try Medicare processed data
    medicare_path = Path(__file__).parent.parent.parent / "data" / "processed" / "pricevision" / "medicare_procedures.csv"

    if medicare_path.exists():
        df = pd.read_csv(medicare_path)
        return df['canonical_description'].tolist(), df['hcpcs_code'].astype(str).tolist()

    # Fall back to hardcoded canonical procedures
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
    Split data into train and validation sets by CPT code.
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
