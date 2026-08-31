"""
Seam involution module: orientation gates and physical signature enforcement.

Implements SeamInvolutionGate to extract P_seam from the complement of active
projectors, enforcing (1,2) physical signature without complex mode leakage.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class SeamSignatureReport:
    """Results of seam signature validation."""
    eigenvalues: np.ndarray
    signature: Tuple[int, int]
    has_complex: bool
    max_imaginary_part: float
    physical_bounds_satisfied: bool

    def __str__(self) -> str:
        status = "VALID" if self.physical_bounds_satisfied else "INVALID"
        return (
            f"SeamSignatureReport [{status}]\n"
            f"  Signature (pos, neg):       {self.signature}\n"
            f"  Max imaginary part:         {self.max_imaginary_part:.3e}\n"
            f"  Has complex eigenvalues:    {self.has_complex}\n"
            f"  Physical bounds satisfied:  {self.physical_bounds_satisfied}"
        )


class SeamInvolutionGate:
    """
    Realizes orientation gates on the seam between H⁺ (3 positive modes)
    and H⁻ (19 negative modes) in the K3 signature structure.

    The seam projector P_seam encodes the transition between active orientation
    branches (Q ↔ -Q), enforcing physical (1,2) signature without generating
    complex mode artifacts.

    Key invariant: g^{phys} = -A_kl + 2j_k j_l / |J|² must stay strictly
    within (1,2) signature bounds.
    """

    SIGNATURE_TARGET = (1, 2)
    PHYSICAL_SIGNATURE_TOLERANCE = 1.0e-12
    COMPLEX_TOLERANCE = 1.0e-14

    def __init__(self, seam_matrix: Optional[np.ndarray] = None):
        """
        Initialize with an explicit seam matrix or from None (for lazy loading).

        Args:
            seam_matrix: (8,8) or similar shape matrix representing P_seam
        """
        if seam_matrix is not None:
            seam_matrix = np.asarray(seam_matrix, dtype=np.float64)
            if seam_matrix.ndim != 2 or seam_matrix.shape[0] != seam_matrix.shape[1]:
                raise ValueError(f"Seam matrix must be square, got shape {seam_matrix.shape}")
        self.seam_matrix = seam_matrix
        self._eigenvalues_cached = None
        self._signature_cached = None

    @classmethod
    def from_active_projectors(cls, active_projectors: list) -> "SeamInvolutionGate":
        """
        Construct seam gate from active projectors via complement:
            P_seam = I - Σ P_active

        Args:
            active_projectors: List of active (non-seam) projector matrices

        Returns:
            SeamInvolutionGate instance
        """
        if not active_projectors:
            raise ValueError("Must provide at least one active projector")

        dim = active_projectors[0].shape[0]
        if any(p.shape != (dim, dim) for p in active_projectors):
            raise ValueError("All projectors must have the same shape")

        identity = np.eye(dim, dtype=np.float64)
        p_sum = sum(active_projectors)
        p_seam = identity - p_sum

        return cls(p_seam)

    def validate_physical_signature(self) -> SeamSignatureReport:
        """
        Check that seam matrix eigenvalues produce (1,2) physical signature.

        Returns:
            SeamSignatureReport with eigenvalues, signature, and validation status
        """
        if self.seam_matrix is None:
            raise RuntimeError("Seam matrix not initialized")

        eigenvalues = np.linalg.eigvalsh(self.seam_matrix)
        eigenvalues_complex = np.linalg.eigvals(self.seam_matrix)

        max_imag = float(np.max(np.abs(eigenvalues_complex.imag)))
        has_complex = max_imag > self.COMPLEX_TOLERANCE

        pos_count = float(np.sum(eigenvalues > self.PHYSICAL_SIGNATURE_TOLERANCE))
        neg_count = float(np.sum(eigenvalues < -self.PHYSICAL_SIGNATURE_TOLERANCE))

        signature = (int(pos_count), int(neg_count))

        physical_bounds_ok = (
            signature == self.SIGNATURE_TARGET
            and not has_complex
            and max_imag < self.COMPLEX_TOLERANCE
        )

        return SeamSignatureReport(
            eigenvalues=eigenvalues,
            signature=signature,
            has_complex=has_complex,
            max_imaginary_part=max_imag,
            physical_bounds_satisfied=physical_bounds_ok,
        )

    def compute_physical_metric(self, a_matrix: np.ndarray, j_vector: np.ndarray) -> np.ndarray:
        """
        Compute physical metric from orientation data:
            g^{phys} = -A_kl + 2 j_k j_l / |J|²

        Args:
            a_matrix: (n, n) matrix of connection coefficients
            j_vector: (n,) vector of local orientation currents

        Returns:
            Physical metric matrix (same shape as a_matrix)
        """
        a_matrix = np.asarray(a_matrix, dtype=np.float64)
        j_vector = np.asarray(j_vector, dtype=np.float64)

        j_norm_sq = float(np.dot(j_vector, j_vector))
        if j_norm_sq < 1.0e-14:
            raise ValueError("Current vector has negligible norm")

        j_outer = np.outer(j_vector, j_vector) / j_norm_sq
        g_phys = -a_matrix + 2.0 * j_outer

        return g_phys

    def __repr__(self) -> str:
        if self.seam_matrix is None:
            return "SeamInvolutionGate(uninitialized)"
        return f"SeamInvolutionGate(shape={self.seam_matrix.shape})"
