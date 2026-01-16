"""
Procedure Encoder Model - BioClinicalBERT with Mean Pooling

Architecture:
    BioClinicalBERT → Token Embeddings → Mean Pooling → 768-dim Sentence Embedding

The model is fine-tuned using contrastive learning to produce embeddings
where procedures with the same CPT code have high cosine similarity.
"""

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer
from typing import Dict, List, Optional, Union
import numpy as np


class ProcedureEncoder(nn.Module):
    """
    BioClinicalBERT-based encoder for medical procedure descriptions.

    Produces fixed-size 768-dimensional embeddings suitable for
    cosine similarity matching.
    """

    def __init__(
        self,
        model_name: str = "emilyalsentzer/Bio_ClinicalBERT",
        pooling: str = "mean",
        normalize: bool = True,
    ):
        """
        Initialize the procedure encoder.

        Args:
            model_name: HuggingFace model identifier
            pooling: Pooling strategy ('mean', 'cls', 'max')
            normalize: Whether to L2-normalize output embeddings
        """
        super().__init__()

        self.model_name = model_name
        self.pooling = pooling
        self.normalize = normalize

        # Load pre-trained medical BERT with safetensors
        self.encoder = AutoModel.from_pretrained(model_name, use_safetensors=True)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Embedding dimension (768 for BERT-base)
        self.embedding_dim = self.encoder.config.hidden_size

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass to generate procedure embeddings.

        Args:
            input_ids: Token IDs [batch_size, seq_len]
            attention_mask: Attention mask [batch_size, seq_len]
            token_type_ids: Token type IDs (optional)

        Returns:
            embeddings: Procedure embeddings [batch_size, 768]
        """
        # Get BERT outputs
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            return_dict=True,
        )

        # Get token embeddings
        token_embeddings = outputs.last_hidden_state  # [batch, seq, 768]

        # Pool to sentence embedding
        if self.pooling == "mean":
            # Mean pooling with attention mask
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
            sum_mask = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
            embeddings = sum_embeddings / sum_mask
        elif self.pooling == "cls":
            # CLS token embedding
            embeddings = token_embeddings[:, 0, :]
        elif self.pooling == "max":
            # Max pooling
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            token_embeddings[input_mask_expanded == 0] = -1e9
            embeddings = torch.max(token_embeddings, dim=1)[0]
        else:
            raise ValueError(f"Unknown pooling: {self.pooling}")

        # L2 normalize for cosine similarity
        if self.normalize:
            embeddings = nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        max_length: int = 128,
        show_progress: bool = False,
        device: Optional[str] = None,
    ) -> np.ndarray:
        """
        Encode procedure descriptions to embeddings.

        Args:
            texts: Single text or list of texts to encode
            batch_size: Batch size for encoding
            max_length: Maximum sequence length
            show_progress: Show progress bar
            device: Device to use (default: model's device)

        Returns:
            embeddings: Numpy array of shape [n_texts, 768]
        """
        if isinstance(texts, str):
            texts = [texts]

        if device is None:
            device = next(self.parameters()).device

        self.eval()
        all_embeddings = []

        # Process in batches
        iterator = range(0, len(texts), batch_size)
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(iterator, desc="Encoding")
            except ImportError:
                pass

        with torch.no_grad():
            for i in iterator:
                batch_texts = texts[i:i + batch_size]

                # Tokenize
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=max_length,
                    return_tensors="pt",
                )

                # Move to device
                input_ids = encoded["input_ids"].to(device)
                attention_mask = encoded["attention_mask"].to(device)
                token_type_ids = encoded.get("token_type_ids")
                if token_type_ids is not None:
                    token_type_ids = token_type_ids.to(device)

                # Encode
                embeddings = self(input_ids, attention_mask, token_type_ids)
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)

    def save(self, path: str):
        """Save model weights and config."""
        torch.save({
            "model_state_dict": self.state_dict(),
            "model_name": self.model_name,
            "pooling": self.pooling,
            "normalize": self.normalize,
        }, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu") -> "ProcedureEncoder":
        """Load model from checkpoint."""
        checkpoint = torch.load(path, map_location=device)

        model = cls(
            model_name=checkpoint["model_name"],
            pooling=checkpoint["pooling"],
            normalize=checkpoint["normalize"],
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()

        print(f"Model loaded from {path}")
        return model


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between embeddings.

    Args:
        a: Embeddings [n, dim] or [dim]
        b: Embeddings [m, dim] or [dim]

    Returns:
        similarities: [n, m] or scalar
    """
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)

    # Normalize (should already be normalized, but just in case)
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)

    return np.dot(a_norm, b_norm.T)
