"""
GeoLang Core Algebra Framework.

Implements Quinn's "Different Algebra" on the split five-sector product carrier space:
    S = ℝ × ℂ × ℂ × ℂ × ℝ ≅ ℝ^8

Provides:
- Projector algebra with 32 block-sum projection operators
- Seam involution gates for orientation transitions
- Canonical (r, π_r) Hamiltonian evolution via Riccati flows
- Full algebraic and symplectic validation
"""

from .algebra import (
    SplitCarrierVector,
    ProjectorAlgebra,
    AlgebraValidationReport,
)
from .seam import SeamInvolutionGate
from .canonical import (
    CanonicalProjectorAlgebra,
    CanonicalSectorState,
    CanonicalSystemState,
)

__version__ = "0.2.0"
__all__ = [
    "SplitCarrierVector",
    "ProjectorAlgebra",
    "AlgebraValidationReport",
    "SeamInvolutionGate",
    "CanonicalProjectorAlgebra",
    "CanonicalSectorState",
    "CanonicalSystemState",
]
