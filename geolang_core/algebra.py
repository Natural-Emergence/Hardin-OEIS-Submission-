"""
Core algebra module: projector operators over the split carrier space S = ℝ^8.

Implements SplitCarrierVector (wrapping 8D vectors with sector views) and
ProjectorAlgebra (validating 32 orthogonal projectors and their composition).
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path


@dataclass
class AlgebraValidationReport:
    """Results of algebraic property verification."""
    identity_residual: float
    max_orthogonality_error: float
    max_idempotency_error: float
    max_reconstruction_residual: float
    num_validation_samples: int
    passed: bool

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"AlgebraValidationReport [{status}]\n"
            f"  Identity resolution:        {self.identity_residual:.3e}\n"
            f"  Max orthogonality error:    {self.max_orthogonality_error:.3e}\n"
            f"  Max idempotency error:      {self.max_idempotency_error:.3e}\n"
            f"  Max reconstruction residual: {self.max_reconstruction_residual:.3e}\n"
            f"  Validation samples:         {self.num_validation_samples}"
        )


class SplitCarrierVector:
    """
    8D vector wrapper providing explicit sector views into the 5-part decomposition:
        ℝ^8 = ℝ₀ ⊕ ℂ₁ ⊕ ℂ₂ ⊕ ℂ₃ ⊕ ℝ₇

    Memory layout: [r0, c1_re, c1_im, c2_re, c2_im, c3_re, c3_im, r7]
    """

    def __init__(self, data: np.ndarray):
        """Initialize from 8-element numpy array."""
        if data.shape != (8,):
            raise ValueError(f"Expected shape (8,), got {data.shape}")
        self._data = np.asarray(data, dtype=np.float64)

    @property
    def data(self) -> np.ndarray:
        """Access underlying 8D array."""
        return self._data

    @property
    def r0(self) -> float:
        """Real scalar sector 0."""
        return float(self._data[0])

    @r0.setter
    def r0(self, value: float):
        self._data[0] = value

    @property
    def c1(self) -> complex:
        """Complex sector 1."""
        return complex(self._data[1], self._data[2])

    @c1.setter
    def c1(self, value: complex):
        self._data[1] = value.real
        self._data[2] = value.imag

    @property
    def c2(self) -> complex:
        """Complex sector 2."""
        return complex(self._data[3], self._data[4])

    @c2.setter
    def c2(self, value: complex):
        self._data[3] = value.real
        self._data[4] = value.imag

    @property
    def c3(self) -> complex:
        """Complex sector 3."""
        return complex(self._data[5], self._data[6])

    @c3.setter
    def c3(self, value: complex):
        self._data[5] = value.real
        self._data[6] = value.imag

    @property
    def r7(self) -> float:
        """Real scalar sector 7."""
        return float(self._data[7])

    @r7.setter
    def r7(self, value: float):
        self._data[7] = value

    def __repr__(self) -> str:
        return f"SplitCarrierVector({self._data})"

    def __array__(self) -> np.ndarray:
        return self._data


class ProjectorAlgebra:
    """
    Manages 32 orthogonal projection operators on ℝ^8.

    Enforces:
    - Resolution of identity: Σ Pᵢ = I₈
    - Idempotency: Pᵢ² = Pᵢ
    - Orthogonality: PᵢPⱼ = δᵢⱼPᵢ
    - Reconstruction: ∀v, ‖v - Σ Pᵢv‖ ≤ 2.220e-16
    """

    IDENTITY_RESIDUAL_THRESHOLD = 1.0e-14
    ORTHOGONALITY_THRESHOLD = 1.0e-15
    IDEMPOTENCY_THRESHOLD = 1.0e-15
    RECONSTRUCTION_THRESHOLD = 2.220e-16

    def __init__(self, projectors: Optional[List[np.ndarray]] = None, npz_path: Optional[str] = None):
        """
        Initialize from either a list of projectors or an .npz file path.

        Args:
            projectors: List of 32 (8,8) numpy arrays, or None to load from file
            npz_path: Path to .npz file containing projectors, or None
        """
        if projectors is not None:
            self.projectors = self._validate_and_store_projectors(projectors)
        elif npz_path is not None:
            self.projectors = self._load_from_npz(npz_path)
        else:
            raise ValueError("Either projectors or npz_path must be provided")

        self.dim = self.projectors[0].shape[0]
        self.identity = np.eye(self.dim, dtype=np.float64)

    def _validate_and_store_projectors(self, projectors: List[np.ndarray]) -> List[np.ndarray]:
        """Validate projector count and dimensionality."""
        if len(projectors) != 32:
            raise ValueError(f"Expected 32 projectors, got {len(projectors)}")
        if any(p.shape != (8, 8) for p in projectors):
            raise ValueError(f"All projectors must have shape (8, 8)")
        return [np.asarray(p, dtype=np.float64) for p in projectors]

    def _load_from_npz(self, npz_path: str) -> List[np.ndarray]:
        """Load projectors from .npz file."""
        path = Path(npz_path)
        if not path.exists():
            raise FileNotFoundError(f"NPZ file not found: {path}")

        data = np.load(path, allow_pickle=True)
        projector_keys = sorted([k for k in data.keys() if k.startswith('P_')])

        if len(projector_keys) != 32:
            raise ValueError(f"Expected 32 projectors (P_*), found {len(projector_keys)} in {npz_path}")

        projectors = [data[k] for k in projector_keys]
        return self._validate_and_store_projectors(projectors)

    def verify_algebra_properties(self, num_samples: int = 100) -> AlgebraValidationReport:
        """
        Comprehensive validation of algebraic properties.

        Returns:
            AlgebraValidationReport with all validation metrics
        """
        p_sum = sum(self.projectors)
        identity_residual = float(np.max(np.abs(p_sum - self.identity)))

        max_ortho = 0.0
        max_idemp = 0.0
        for i in range(32):
            p_i = self.projectors[i]
            p_i_sq = p_i @ p_i
            idemp_err = float(np.max(np.abs(p_i_sq - p_i)))
            max_idemp = max(max_idemp, idemp_err)

            for j in range(32):
                p_j = self.projectors[j]
                product = p_i @ p_j
                target = p_i if i == j else np.zeros((self.dim, self.dim))
                ortho_err = float(np.max(np.abs(product - target)))
                max_ortho = max(max_ortho, ortho_err)

        max_rec = 0.0
        np.random.seed(42)
        for _ in range(num_samples):
            v = np.random.randn(self.dim)
            v_reconstructed = sum(p @ v for p in self.projectors)
            rec_err = float(np.max(np.abs(v - v_reconstructed)))
            max_rec = max(max_rec, rec_err)

        passed = (
            identity_residual <= self.IDENTITY_RESIDUAL_THRESHOLD
            and max_ortho <= self.ORTHOGONALITY_THRESHOLD
            and max_idemp <= self.IDEMPOTENCY_THRESHOLD
            and max_rec <= self.RECONSTRUCTION_THRESHOLD
        )

        return AlgebraValidationReport(
            identity_residual=identity_residual,
            max_orthogonality_error=max_ortho,
            max_idempotency_error=max_idemp,
            max_reconstruction_residual=max_rec,
            num_validation_samples=num_samples,
            passed=passed,
        )

    def project_sector(self, v: SplitCarrierVector, sector_idx: int) -> SplitCarrierVector:
        """Apply the i-th projector to vector v."""
        if not 0 <= sector_idx < 32:
            raise IndexError(f"Sector index must be in [0, 32), got {sector_idx}")
        projected = self.projectors[sector_idx] @ v.data
        return SplitCarrierVector(projected)

    def reconstruct(self, v: SplitCarrierVector, return_residual: bool = True) -> Tuple[SplitCarrierVector, float]:
        """
        Reconstruct vector from projection sum: v_rec = Σ Pᵢv.

        Returns:
            (reconstructed_vector, residual_error) if return_residual=True
            (reconstructed_vector, 0.0) otherwise
        """
        v_reconstructed = sum(p @ v.data for p in self.projectors)
        v_rec = SplitCarrierVector(v_reconstructed)

        if return_residual:
            residual = float(np.max(np.abs(v.data - v_reconstructed)))
            return v_rec, residual
        return v_rec, 0.0

    def operator_norm(self, idx: int) -> float:
        """Compute operator norm (largest singular value) of Pᵢ."""
        if not 0 <= idx < 32:
            raise IndexError(f"Sector index must be in [0, 32), got {idx}")
        s = np.linalg.svd(self.projectors[idx], compute_uv=False)
        return float(np.max(s))

    def trace_all_projectors(self) -> float:
        """Sum of traces of all 32 projectors (should equal 8 for full resolution)."""
        traces = [float(np.trace(p)) for p in self.projectors]
        return sum(traces)
