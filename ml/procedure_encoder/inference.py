"""
Inference utilities for Procedure Encoder

Provides a service class for matching hospital procedure descriptions
to canonical CPT codes using the fine-tuned BioClinicalBERT model.
"""

import torch
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from ml.config import PROCEDURE_ENCODER_CONFIG
from ml.procedure_encoder.model import ProcedureEncoder, cosine_similarity


@dataclass
class ProcedureMatch:
    """Result of procedure matching."""
    input_description: str
    matched_code: Optional[str]
    matched_description: Optional[str]
    confidence: float
    status: str  # "matched", "review", "unmatched"


class ProcedureMatchingService:
    """
    Service for matching procedure descriptions to canonical CPT codes.

    Usage:
        service = ProcedureMatchingService.load()
        result = service.match("MRI BRAIN W/O CONTRAST")
        print(result.matched_code)  # "70551"
        print(result.confidence)    # 0.92
    """

    def __init__(
        self,
        model: ProcedureEncoder,
        canonical_embeddings: np.ndarray,
        canonical_descriptions: List[str],
        canonical_codes: List[str],
        match_threshold: float = 0.80,
        review_threshold: float = 0.65,
        device: str = "cpu",
    ):
        """
        Initialize the matching service.

        Args:
            model: Trained ProcedureEncoder
            canonical_embeddings: Pre-computed embeddings for canonical procedures
            canonical_descriptions: Canonical procedure descriptions
            canonical_codes: CPT codes
            match_threshold: Threshold for confident match
            review_threshold: Threshold for review (below this = unmatched)
            device: Device for inference
        """
        self.model = model
        self.canonical_embeddings = canonical_embeddings
        self.canonical_descriptions = canonical_descriptions
        self.canonical_codes = canonical_codes
        self.match_threshold = match_threshold
        self.review_threshold = review_threshold
        self.device = device

        # Build code to description mapping
        self.code_to_description = {
            code: desc for code, desc in zip(canonical_codes, canonical_descriptions)
        }

    @classmethod
    def load(
        cls,
        model_path: Optional[str] = None,
        embeddings_path: Optional[str] = None,
        device: str = "cpu",
    ) -> "ProcedureMatchingService":
        """
        Load the matching service from saved files.

        Args:
            model_path: Path to model checkpoint
            embeddings_path: Path to canonical embeddings
            device: Device for inference

        Returns:
            Initialized ProcedureMatchingService
        """
        config = PROCEDURE_ENCODER_CONFIG

        model_path = model_path or str(config.output_model)
        embeddings_path = embeddings_path or str(config.canonical_embeddings)

        # Load model
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. "
                "Please train the model first: python -m ml.procedure_encoder.train"
            )

        model = ProcedureEncoder.load(model_path, device=device)

        # Load canonical embeddings
        if not Path(embeddings_path).exists():
            raise FileNotFoundError(
                f"Canonical embeddings not found at {embeddings_path}. "
                "Please train the model first."
            )

        canonical_data = torch.load(embeddings_path)

        return cls(
            model=model,
            canonical_embeddings=canonical_data["embeddings"],
            canonical_descriptions=canonical_data["descriptions"],
            canonical_codes=canonical_data["codes"],
            match_threshold=config.match_threshold,
            review_threshold=config.review_threshold,
            device=device,
        )

    def match(self, description: str) -> ProcedureMatch:
        """
        Match a single procedure description to a canonical CPT code.

        Args:
            description: Hospital procedure description

        Returns:
            ProcedureMatch with code, description, confidence, and status
        """
        results = self.match_batch([description])
        return results[0]

    def match_batch(self, descriptions: List[str]) -> List[ProcedureMatch]:
        """
        Match multiple procedure descriptions.

        Args:
            descriptions: List of procedure descriptions

        Returns:
            List of ProcedureMatch results
        """
        # Encode input descriptions
        input_embeddings = self.model.encode(
            descriptions,
            device=self.device,
            show_progress=len(descriptions) > 100,
        )

        # Compute similarities to all canonical procedures
        similarities = cosine_similarity(input_embeddings, self.canonical_embeddings)

        results = []
        for i, desc in enumerate(descriptions):
            # Find best match
            best_idx = np.argmax(similarities[i])
            confidence = float(similarities[i, best_idx])

            # Determine status
            if confidence >= self.match_threshold:
                status = "matched"
                matched_code = self.canonical_codes[best_idx]
                matched_desc = self.canonical_descriptions[best_idx]
            elif confidence >= self.review_threshold:
                status = "review"
                matched_code = self.canonical_codes[best_idx]
                matched_desc = self.canonical_descriptions[best_idx]
            else:
                status = "unmatched"
                matched_code = None
                matched_desc = None

            results.append(ProcedureMatch(
                input_description=desc,
                matched_code=matched_code,
                matched_description=matched_desc,
                confidence=confidence,
                status=status,
            ))

        return results

    def find_similar(
        self,
        description: str,
        top_k: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """
        Find the top-k most similar canonical procedures.

        Args:
            description: Procedure description
            top_k: Number of results to return

        Returns:
            List of (cpt_code, description, similarity) tuples
        """
        # Encode input
        input_embedding = self.model.encode([description], device=self.device)

        # Compute similarities
        similarities = cosine_similarity(input_embedding, self.canonical_embeddings)[0]

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append((
                self.canonical_codes[idx],
                self.canonical_descriptions[idx],
                float(similarities[idx]),
            ))

        return results

    def add_canonical_procedure(
        self,
        code: str,
        description: str,
    ) -> None:
        """
        Add a new canonical procedure to the index.

        Args:
            code: CPT code
            description: Canonical description
        """
        # Encode new description
        new_embedding = self.model.encode([description], device=self.device)

        # Add to index
        self.canonical_embeddings = np.vstack([
            self.canonical_embeddings,
            new_embedding,
        ])
        self.canonical_codes.append(code)
        self.canonical_descriptions.append(description)
        self.code_to_description[code] = description

    def get_embedding(self, description: str) -> np.ndarray:
        """
        Get the embedding for a procedure description.

        Useful for storing embeddings in the database.

        Args:
            description: Procedure description

        Returns:
            768-dimensional embedding vector
        """
        return self.model.encode([description], device=self.device)[0]


# Convenience function for quick matching
def match_procedure(
    description: str,
    service: Optional[ProcedureMatchingService] = None,
) -> ProcedureMatch:
    """
    Quick function to match a single procedure.

    Loads the service if not provided (caches for subsequent calls).

    Args:
        description: Procedure description
        service: Optional pre-loaded service

    Returns:
        ProcedureMatch result
    """
    if service is None:
        if not hasattr(match_procedure, "_service"):
            match_procedure._service = ProcedureMatchingService.load()
        service = match_procedure._service

    return service.match(description)
