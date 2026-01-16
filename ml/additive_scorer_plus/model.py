"""
FoodScore+ Model Architecture (v2 - Lightweight)

Simple but effective additive risk scorer using:
- Character n-gram text features (no heavy transformers)
- Categorical embeddings
- Small MLP with residual connections
- ~50K parameters (not 67M!)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List
from pathlib import Path
import json
import re


class CharNGramEncoder(nn.Module):
    """
    Simple character n-gram encoder for additive names.
    Much lighter than BERT, works well for small datasets.
    """

    def __init__(self, vocab_size: int = 1000, embedding_dim: int = 64, output_dim: int = 128):
        super().__init__()
        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim

        # Character n-gram embeddings
        self.embedding = nn.EmbeddingBag(vocab_size, embedding_dim, mode='mean')

        # Project to output dimension
        self.projection = nn.Sequential(
            nn.Linear(embedding_dim, output_dim),
            nn.LayerNorm(output_dim),
            nn.GELU(),
        )

        # N-gram vocabulary (will be built during first forward pass or loaded)
        self.ngram_to_idx = {}
        self.fitted = False

    def _get_ngrams(self, text: str, n_range: tuple = (2, 4)) -> List[str]:
        """Extract character n-grams from text."""
        text = text.lower().strip()
        ngrams = []
        for n in range(n_range[0], n_range[1] + 1):
            for i in range(len(text) - n + 1):
                ngrams.append(text[i:i+n])
        return ngrams

    def fit(self, texts: List[str]):
        """Build n-gram vocabulary from training texts."""
        ngram_counts = {}
        for text in texts:
            for ng in self._get_ngrams(text):
                ngram_counts[ng] = ngram_counts.get(ng, 0) + 1

        # Keep top vocab_size-1 n-grams (0 reserved for unknown)
        sorted_ngrams = sorted(ngram_counts.items(), key=lambda x: -x[1])
        self.ngram_to_idx = {ng: i + 1 for i, (ng, _) in enumerate(sorted_ngrams[:self.vocab_size - 1])}
        self.fitted = True

    def _text_to_indices(self, text: str) -> torch.Tensor:
        """Convert text to n-gram indices."""
        ngrams = self._get_ngrams(text)
        indices = [self.ngram_to_idx.get(ng, 0) for ng in ngrams]
        if not indices:
            indices = [0]  # Unknown token
        return torch.tensor(indices, dtype=torch.long)

    def forward(self, texts: List[str]) -> torch.Tensor:
        """Encode batch of texts."""
        device = self.embedding.weight.device

        # Get indices and offsets for EmbeddingBag
        all_indices = []
        offsets = [0]

        for text in texts:
            indices = self._text_to_indices(text)
            all_indices.append(indices)
            offsets.append(offsets[-1] + len(indices))

        all_indices = torch.cat(all_indices).to(device)
        offsets = torch.tensor(offsets[:-1], dtype=torch.long).to(device)

        # Get embeddings
        embedded = self.embedding(all_indices, offsets)
        return self.projection(embedded)

    def save_vocab(self, path: str):
        """Save n-gram vocabulary."""
        with open(path, 'w') as f:
            json.dump(self.ngram_to_idx, f)

    def load_vocab(self, path: str):
        """Load n-gram vocabulary."""
        with open(path, 'r') as f:
            self.ngram_to_idx = json.load(f)
        self.fitted = True


class AdditiveRiskScorerPlus(nn.Module):
    """
    FoodScore+ Lightweight Additive Risk Scorer

    Architecture:
    1. CharNGramEncoder: Character n-grams -> 128d
    2. Categorical embeddings: type/status -> 48d
    3. Fusion MLP with residual: 176d -> 128 -> 64 -> 1
    4. Output: Risk score (0-100)

    Total: ~50K parameters (vs 67M before)
    """

    def __init__(
        self,
        ngram_vocab_size: int = 1000,
        ngram_embedding_dim: int = 64,
        text_output_dim: int = 128,
        cat_embedding_dim: int = 16,
        hidden_dims: tuple = (128, 64),
        dropout: float = 0.3,
    ):
        super().__init__()

        # Text encoder
        self.text_encoder = CharNGramEncoder(
            vocab_size=ngram_vocab_size,
            embedding_dim=ngram_embedding_dim,
            output_dim=text_output_dim,
        )

        # Categorical embeddings
        self.type_embedding = nn.Embedding(6, cat_embedding_dim)  # 6 types
        self.fda_embedding = nn.Embedding(2, cat_embedding_dim)   # approved/banned
        self.eu_embedding = nn.Embedding(3, cat_embedding_dim)    # approved/restricted/banned

        # Binary features projection
        self.binary_proj = nn.Linear(2, cat_embedding_dim)

        # Total categorical dim
        cat_total_dim = cat_embedding_dim * 4  # 64

        # Fusion dimension
        fusion_dim = text_output_dim + cat_total_dim  # 128 + 64 = 192

        # MLP with residual
        layers = []
        in_dim = fusion_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(in_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
            ])
            in_dim = hidden_dim

        self.mlp = nn.Sequential(*layers)

        # Output head
        self.output = nn.Linear(hidden_dims[-1], 1)

        # Category mappings
        self.type_to_idx = {
            "dye": 0, "sweetener": 1, "preservative": 2,
            "emulsifier": 3, "flavor": 4, "other": 5
        }
        self.fda_to_idx = {"approved": 0, "banned": 1}
        self.eu_to_idx = {"approved": 0, "restricted": 1, "banned": 2}

    def forward(
        self,
        names: List[str],
        type_idx: torch.Tensor,
        fda_idx: torch.Tensor,
        eu_idx: torch.Tensor,
        binary_features: torch.Tensor,
    ) -> torch.Tensor:
        # Text encoding
        text_emb = self.text_encoder(names)

        # Categorical embeddings
        type_emb = self.type_embedding(type_idx)
        fda_emb = self.fda_embedding(fda_idx)
        eu_emb = self.eu_embedding(eu_idx)
        binary_emb = self.binary_proj(binary_features)

        # Concatenate all
        cat_emb = torch.cat([type_emb, fda_emb, eu_emb, binary_emb], dim=-1)
        fused = torch.cat([text_emb, cat_emb], dim=-1)

        # MLP
        hidden = self.mlp(fused)

        # Output
        risk_score = self.output(hidden).squeeze(-1)
        risk_score = torch.clamp(risk_score, 0, 100)

        return risk_score

    def fit_text_encoder(self, names: List[str]):
        """Fit the text encoder on training names."""
        self.text_encoder.fit(names)

    def predict(
        self,
        name: str,
        additive_type: str,
        fda_status: str,
        eu_status: str,
        is_artificial: bool = True,
        is_petroleum_based: bool = False,
        device: str = "cuda",
    ) -> float:
        """Predict risk score for a single additive."""
        self.eval()

        type_idx = torch.tensor([self.type_to_idx.get(additive_type.lower(), 5)]).to(device)
        fda_idx = torch.tensor([self.fda_to_idx.get(fda_status.lower(), 0)]).to(device)
        eu_idx = torch.tensor([self.eu_to_idx.get(eu_status.lower(), 0)]).to(device)
        binary = torch.tensor([[float(is_artificial), float(is_petroleum_based)]]).to(device)

        with torch.no_grad():
            score = self([name], type_idx, fda_idx, eu_idx, binary)

        return score.item()

    def save(self, path: str):
        """Save model weights and vocabulary."""
        # Save model
        torch.save({
            "state_dict": self.state_dict(),
            "ngram_vocab": self.text_encoder.ngram_to_idx,
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cuda") -> "AdditiveRiskScorerPlus":
        """Load model from weights."""
        checkpoint = torch.load(path, map_location=device, weights_only=False)

        model = cls()
        model.text_encoder.ngram_to_idx = checkpoint["ngram_vocab"]
        model.text_encoder.fitted = True
        model.load_state_dict(checkpoint["state_dict"])
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model
