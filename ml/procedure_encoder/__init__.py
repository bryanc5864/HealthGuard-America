"""
Procedure Encoder - BioClinicalBERT fine-tuned for medical procedure matching.

Solves the problem of inconsistent hospital procedure naming:
- "MRI BRAIN W/O CONTRAST"
- "MAGNETIC RESONANCE IMAGING HEAD WITHOUT DYE"
- "MR HEAD WO"
All refer to CPT 70551, but string matching fails.

This model generates 768-dim embeddings where semantically similar
procedures cluster together, enabling cosine similarity matching.
"""

from .model import ProcedureEncoder
from .inference import ProcedureMatchingService

__all__ = ["ProcedureEncoder", "ProcedureMatchingService"]
