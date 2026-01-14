"""
Ingredient Tokenizer for NOVA Classifier

Tokenizes ingredient text into sequences of token IDs for the neural network.
Uses a vocabulary of the 10,000 most common ingredient terms.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter
import numpy as np


class IngredientTokenizer:
    """
    Tokenizer for food ingredient lists.

    Handles:
    - Lowercasing and normalization
    - Comma-separated ingredients
    - Parenthetical sub-ingredients
    - Percentages and quantities
    - Unknown tokens (OOV)
    """

    PAD_TOKEN = "<PAD>"
    UNK_TOKEN = "<UNK>"
    PAD_ID = 0
    UNK_ID = 1

    def __init__(
        self,
        vocab_size: int = 10000,
        max_length: int = 200,
    ):
        """
        Initialize tokenizer.

        Args:
            vocab_size: Maximum vocabulary size
            max_length: Maximum sequence length
        """
        self.vocab_size = vocab_size
        self.max_length = max_length

        # Initialize with special tokens
        self.token_to_id: Dict[str, int] = {
            self.PAD_TOKEN: self.PAD_ID,
            self.UNK_TOKEN: self.UNK_ID,
        }
        self.id_to_token: Dict[int, str] = {
            self.PAD_ID: self.PAD_TOKEN,
            self.UNK_ID: self.UNK_TOKEN,
        }

        self._fitted = False

    def _normalize(self, text: str) -> str:
        """Normalize ingredient text."""
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove percentages (e.g., "sugar (5%)")
        text = re.sub(r'\d+\.?\d*\s*%', '', text)

        # Remove quantities (e.g., "2g", "100mg")
        text = re.sub(r'\d+\.?\d*\s*(g|mg|kg|ml|l|oz)\b', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _tokenize_text(self, text: str) -> List[str]:
        """Split text into tokens."""
        text = self._normalize(text)
        if not text:
            return []

        # Split on commas, parentheses, and other delimiters
        # Keep meaningful ingredient terms together
        tokens = re.split(r'[,;:()\[\]{}]', text)

        # Further split on spaces and clean
        result = []
        for token in tokens:
            # Split on spaces
            words = token.strip().split()
            for word in words:
                # Clean word
                word = re.sub(r'[^a-z0-9-]', '', word)
                if word and len(word) > 1:  # Skip single chars
                    result.append(word)

        return result

    def fit(self, ingredient_texts: List[str]) -> "IngredientTokenizer":
        """
        Fit tokenizer on training data.

        Args:
            ingredient_texts: List of ingredient list texts

        Returns:
            self
        """
        # Count all tokens
        token_counts = Counter()
        for text in ingredient_texts:
            tokens = self._tokenize_text(text)
            token_counts.update(tokens)

        # Keep top vocab_size - 2 tokens (reserve 2 for special tokens)
        most_common = token_counts.most_common(self.vocab_size - 2)

        # Build vocabulary
        for token, count in most_common:
            if token not in self.token_to_id:
                idx = len(self.token_to_id)
                self.token_to_id[token] = idx
                self.id_to_token[idx] = token

        self._fitted = True
        print(f"Tokenizer fitted with {len(self.token_to_id)} tokens")

        return self

    def encode(
        self,
        text: str,
        padding: bool = True,
        truncation: bool = True,
    ) -> np.ndarray:
        """
        Encode ingredient text to token IDs.

        Args:
            text: Ingredient list text
            padding: Pad to max_length
            truncation: Truncate to max_length

        Returns:
            Array of token IDs
        """
        tokens = self._tokenize_text(text)

        # Convert to IDs
        ids = []
        for token in tokens:
            if token in self.token_to_id:
                ids.append(self.token_to_id[token])
            else:
                ids.append(self.UNK_ID)

        # Truncate
        if truncation and len(ids) > self.max_length:
            ids = ids[:self.max_length]

        # Pad
        if padding:
            while len(ids) < self.max_length:
                ids.append(self.PAD_ID)

        return np.array(ids, dtype=np.int64)

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode multiple texts.

        Args:
            texts: List of ingredient texts

        Returns:
            Array of shape [batch_size, max_length]
        """
        return np.stack([self.encode(text) for text in texts])

    def decode(self, ids: np.ndarray) -> str:
        """
        Decode token IDs back to text.

        Args:
            ids: Array of token IDs

        Returns:
            Decoded text
        """
        tokens = []
        for idx in ids:
            if idx == self.PAD_ID:
                break
            tokens.append(self.id_to_token.get(idx, self.UNK_TOKEN))

        return " ".join(tokens)

    def save(self, path: str) -> None:
        """Save tokenizer to file."""
        data = {
            "vocab_size": self.vocab_size,
            "max_length": self.max_length,
            "token_to_id": self.token_to_id,
        }
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"Tokenizer saved to {path}")

    @classmethod
    def load(cls, path: str) -> "IngredientTokenizer":
        """Load tokenizer from file."""
        with open(path, "r") as f:
            data = json.load(f)

        tokenizer = cls(
            vocab_size=data["vocab_size"],
            max_length=data["max_length"],
        )
        tokenizer.token_to_id = data["token_to_id"]
        tokenizer.id_to_token = {int(v): k for k, v in data["token_to_id"].items()}
        tokenizer._fitted = True

        print(f"Tokenizer loaded from {path}")
        return tokenizer

    @property
    def actual_vocab_size(self) -> int:
        """Return actual vocabulary size after fitting."""
        return len(self.token_to_id)
