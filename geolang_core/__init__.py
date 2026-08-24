"""
GeoLang Core Algebra Framework.

Implements Quinn's "Different Algebra" on the split five-sector product carrier space:
    S = ℝ × ℂ × ℂ × ℂ × ℝ ≅ ℝ^8

Provides projector algebra with 32 block-sum projection operators, seam involution gates,
and full algebraic validation.
"""

from .algebra import (
    SplitCarrierVector,
    ProjectorAlgebra,
    AlgebraValidationReport,
)
from .seam import SeamInvolutionGate

__version__ = "0.1.0"
__all__ = [
    "SplitCarrierVector",
    "ProjectorAlgebra",
    "AlgebraValidationReport",
    "SeamInvolutionGate",
]
