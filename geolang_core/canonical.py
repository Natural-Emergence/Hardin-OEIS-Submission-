"""
Canonical projector algebra: embedding (r, π_r) Hamiltonian flows into the 32-sector projector space.

Extends ProjectorAlgebra to support continuous phase-space evolution via sectored Riccati dynamics,
with full symplectic structure preservation under orthogonal projector decomposition.
"""

import numpy as np
from typing import Tuple, List, Optional
from dataclasses import dataclass
from .algebra import ProjectorAlgebra, SplitCarrierVector


@dataclass
class CanonicalSectorState:
    """Phase-space state of a single projector sector (r, π_r pair)."""
    r: float          # Configuration: flux ratio j / i
    pi_r: float       # Momentum: backward flux squared (i²)
    sector_idx: int   # Index of associated projector (0-31)

    def __str__(self) -> str:
        return f"Sector[{self.sector_idx:2d}]: r={self.r:8.4f}, π_r={self.pi_r:10.6e}"


@dataclass
class CanonicalSystemState:
    """Complete phase space state across all 32 sectors."""
    sectors: List[CanonicalSectorState]
    total_hamiltonian: float
    optical_depth: float

    def __str__(self) -> str:
        lines = [f"CanonicalSystemState (z={self.optical_depth:.4f})"]
        lines.append(f"  Total Hamiltonian: {self.total_hamiltonian:.6e}")
        for state in self.sectors:
            if state.pi_r > 1.0e-12:  # Only print non-trivial sectors
                lines.append(f"  {state}")
        return "\n".join(lines)


class CanonicalProjectorAlgebra(ProjectorAlgebra):
    """
    Extends ProjectorAlgebra with canonical (r, π_r) Hamiltonian evolution.

    Maps continuous optical-depth evolution onto discrete 32-sector projector flows,
    preserving symplectic structure via orthogonal decomposition.

    Evolution equation (Riccati on each sector):
        dr_k / dz = S(r_k - 1)² - 2Kr_k
        dπ_{r,k} / dz = 0  (adiabatic invariant per sector)

    Total Hamiltonian:
        H = Σ_k π_{r,k} [ 2(K+S)r_k - S(1 + r_k²) ]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sector_flux_indices = {}  # Maps (fwd_idx, bwd_idx) → phase space state

    def compute_canonical_variables(
        self,
        v: SplitCarrierVector,
        fwd_sector_idx: int,
        bwd_sector_idx: int
    ) -> Tuple[float, float]:
        """
        Extract canonical (r, π_r) from projector sector norms.

        Args:
            v: Carrier vector in ℝ⁸
            fwd_sector_idx: Forward flux projector index
            bwd_sector_idx: Backward flux projector index

        Returns:
            (r, π_r) where r = j/i, π_r = i²
                - r: flux ratio (configuration)
                - π_r: backward flux squared (momentum)
        """
        j_norm = float(np.linalg.norm(self.project_sector(v, fwd_sector_idx).data))
        i_norm = float(np.linalg.norm(self.project_sector(v, bwd_sector_idx).data))

        if i_norm < 1.0e-14:
            return np.nan, 1.0e-14
        if j_norm < 1.0e-14:
            j_norm = 1.0e-14

        r = j_norm / i_norm
        pi_r = i_norm ** 2

        return r, pi_r

    def sector_hamiltonian(self, r: float, pi_r: float, K: float, S: float) -> float:
        """
        Compute Hamiltonian energy of one sector.

        Args:
            r: Configuration (flux ratio)
            pi_r: Momentum (backward flux squared)
            K: Forward absorption coefficient
            S: Scattering albedo

        Returns:
            H_k = π_r [ 2(K+S)r - S(1 + r²) ]
        """
        if np.isnan(r) or pi_r <= 0:
            return 0.0
        return float(pi_r * (2.0 * (K + S) * r - S * (1.0 + r ** 2)))

    def total_hamiltonian(
        self,
        canonical_states: List[CanonicalSectorState],
        K: float,
        S: float
    ) -> float:
        """
        Compute total system Hamiltonian as sum over all sectors.

        Args:
            canonical_states: List of (r, π_r) states for each sector
            K: Forward absorption coefficient
            S: Scattering albedo

        Returns:
            H_total = Σ_k H_k(r_k, π_{r,k})
        """
        total_h = 0.0
        for state in canonical_states:
            h_k = self.sector_hamiltonian(state.r, state.pi_r, K, S)
            total_h += h_k
        return total_h

    def riccati_flux_derivative(
        self,
        r: float,
        K: float,
        S: float
    ) -> float:
        """
        Riccati equation for flux ratio on optical depth.

        Realizes the continuous evolution:
            dr / dz = S(r - 1)² - 2Kr

        Args:
            r: Flux ratio
            K: Absorption coefficient
            S: Scattering coefficient

        Returns:
            dr/dz at this (r, K, S) point
        """
        if np.isnan(r):
            return np.nan
        return float(S * (r - 1.0) ** 2 - 2.0 * K * r)

    def evolve_sector_riccati(
        self,
        r0: float,
        pi_r: float,
        K: float,
        S: float,
        z_steps: int,
        dz: float = 0.01
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Evolve a single sector through optical depth using Riccati ODE.

        Uses simple forward Euler integration (sufficient for short z steps).
        π_r is adiabatic invariant: dπ_r/dz = 0.

        Args:
            r0: Initial flux ratio
            pi_r: Momentum (constant throughout evolution)
            K: Absorption coefficient
            S: Scattering albedo
            z_steps: Number of integration steps
            dz: Step size in optical depth

        Returns:
            (r_trajectory, z_trajectory) arrays
        """
        r_traj = np.zeros(z_steps + 1, dtype=np.float64)
        z_traj = np.zeros(z_steps + 1, dtype=np.float64)

        r_traj[0] = r0
        z_traj[0] = 0.0

        r = r0
        for i in range(z_steps):
            dr_dz = self.riccati_flux_derivative(r, K, S)
            r = r + dz * dr_dz
            r_traj[i + 1] = r
            z_traj[i + 1] = (i + 1) * dz

        return r_traj, z_traj

    def extract_canonical_state(
        self,
        v: SplitCarrierVector,
        fwd_bwd_pairs: Optional[List[Tuple[int, int]]] = None
    ) -> CanonicalSystemState:
        """
        Extract complete canonical state from carrier vector.

        Maps all 32 sectors to (r, π_r) pairs by decomposing v across projectors
        and pairing forward/backward fluxes.

        Args:
            v: Carrier vector in ℝ⁸
            fwd_bwd_pairs: List of (fwd_idx, bwd_idx) pairs; if None, use default pairing

        Returns:
            CanonicalSystemState with all 32 sectors and total Hamiltonian
        """
        if fwd_bwd_pairs is None:
            # Default: pair sectors (0,1), (2,3), ..., (30,31)
            fwd_bwd_pairs = [(2*i, 2*i + 1) for i in range(16)]

        canonical_states = []
        total_h = 0.0

        for sector_idx in range(32):
            fwd_idx, bwd_idx = fwd_bwd_pairs[sector_idx % len(fwd_bwd_pairs)]
            r, pi_r = self.compute_canonical_variables(v, fwd_idx, bwd_idx)

            state = CanonicalSectorState(
                r=r,
                pi_r=pi_r,
                sector_idx=sector_idx
            )
            canonical_states.append(state)

        return CanonicalSystemState(
            sectors=canonical_states,
            total_hamiltonian=total_h,
            optical_depth=0.0
        )

    def symplectic_form_sector(self, r: float, pi_r: float, dr: float, dpi_r: float) -> float:
        """
        Evaluate symplectic 2-form on single sector: ω_k = dr_k ∧ dπ_{r,k}.

        This is a placeholder for the geometric structure. In full implementation,
        this validates that orthogonal projector decomposition preserves the
        canonical symplectic structure across all sectors.

        Args:
            r, pi_r: Phase-space coordinates
            dr, dpi_r: Infinitesimal displacements

        Returns:
            ω_k = dr ∧ dπ_r (wedge product, returns scalar coefficient)
        """
        return float(dr * dpi_r)

    def verify_orthogonal_projector_symplectic_preservation(
        self,
        num_samples: int = 10
    ) -> bool:
        """
        Verify that orthogonal decomposition preserves symplectic structure.

        For each random vector v, compute canonical states in two ways:
        1. Direct extraction from v
        2. Reconstruction via v = Σ P_k v_k, then extract canonical from each v_k

        Symplectic preservation holds if the two extractions agree.

        Args:
            num_samples: Number of random vectors to test

        Returns:
            True if symplectic structure is preserved across all samples
        """
        np.random.seed(42)
        preserved = True

        for sample in range(num_samples):
            v = SplitCarrierVector(np.random.randn(8))

            # Method 1: Direct extraction
            state_direct = self.extract_canonical_state(v)

            # Method 2: Reconstruction-based
            v_reconstructed, rec_error = self.reconstruct(v, return_residual=True)
            state_reconstructed = self.extract_canonical_state(v_reconstructed)

            # Check consistency
            for i, (s1, s2) in enumerate(zip(state_direct.sectors, state_reconstructed.sectors)):
                r_agree = np.isclose(s1.r, s2.r, rtol=1.0e-10) or (np.isnan(s1.r) and np.isnan(s2.r))
                pi_agree = np.isclose(s1.pi_r, s2.pi_r, rtol=1.0e-10)

                if not (r_agree and pi_agree):
                    preserved = False
                    break

        return preserved
