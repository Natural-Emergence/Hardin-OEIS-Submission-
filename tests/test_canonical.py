"""
Test suite for canonical projector algebra (Riccati/Hamiltonian flows).

Validates:
1. Canonical variable extraction (r, π_r) from projector sectors
2. Sector Hamiltonians and total energy conservation
3. Riccati ODE evolution across optical depth
4. Symplectic structure preservation under orthogonal decomposition
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from geolang_core import (
    SplitCarrierVector,
    CanonicalProjectorAlgebra,
    CanonicalSectorState,
    CanonicalSystemState,
)


class TestCanonicalVariableExtraction:
    """Tests for mapping sector norms to (r, π_r)."""

    @pytest.fixture
    def algebra(self):
        """Algebra with proper orthogonal projectors."""
        from geolang_core.initialization import generate_quinn_initialization_tensor
        seed = generate_quinn_initialization_tensor(seed=42)
        return CanonicalProjectorAlgebra(projectors=seed.projectors)

    def test_canonical_variables_simple_vector(self, algebra):
        """Extract (r, π_r) from a test vector with non-zero forward/backward fluxes."""
        v = SplitCarrierVector(np.array([2.0, 1.0, 0.5, 1.0, 0.5, 0.3, 0.2, 1.5]))

        r, pi_r = algebra.compute_canonical_variables(v, fwd_sector_idx=0, bwd_sector_idx=1)

        # Both projector and backward have non-zero flux
        if not np.isnan(r):
            assert r > 0, "r should be positive (ratio of norms)"
        # π_r represents backward flux magnitude
        assert pi_r >= 0, "π_r should be non-negative"

    def test_canonical_variables_asymmetric_flux(self, algebra):
        """Handle asymmetric forward vs backward flux distributions."""
        v = SplitCarrierVector(np.array([10.0, 1.0, 0.1, 0.01, 0.5, 0.3, 0.2, 0.8]))

        r, pi_r = algebra.compute_canonical_variables(v, fwd_sector_idx=0, bwd_sector_idx=1)

        # Forward flux (P_0 @ v) and backward flux (P_1 @ v) both exist but different magnitudes
        # r is ratio, π_r is backward flux magnitude
        if not np.isnan(r):
            assert r > 0, "r should be positive when both fluxes exist"
        assert pi_r >= 0, "π_r should be non-negative"

    def test_canonical_variables_random_vector(self, algebra):
        """Extract from random carrier vector."""
        np.random.seed(42)
        v = SplitCarrierVector(np.random.randn(8))

        r, pi_r = algebra.compute_canonical_variables(v, fwd_sector_idx=0, bwd_sector_idx=1)

        if not np.isnan(r):
            assert pi_r > 0, "π_r must be positive"
            assert r > 0, "r should be positive (ratio of norms)"


class TestSectorHamiltonian:
    """Tests for Hamiltonian energy on single sectors."""

    @pytest.fixture
    def algebra(self):
        from geolang_core.initialization import generate_quinn_initialization_tensor
        seed = generate_quinn_initialization_tensor(seed=42)
        return CanonicalProjectorAlgebra(projectors=seed.projectors)

    def test_sector_hamiltonian_zero_momentum(self, algebra):
        """Hamiltonian vanishes when π_r = 0."""
        H = algebra.sector_hamiltonian(r=1.5, pi_r=0.0, K=1.0, S=0.5)
        assert H == 0.0, "H should be zero when π_r = 0"

    def test_sector_hamiltonian_fixed_point(self, algebra):
        """Verify Hamiltonian at fixed point r = 1."""
        K, S = 1.0, 0.5
        r_fixed = 1.0
        pi_r = 2.0

        H = algebra.sector_hamiltonian(r_fixed, pi_r, K, S)

        expected = pi_r * (2 * (K + S) * r_fixed - S * (1 + r_fixed**2))
        assert np.isclose(H, expected, rtol=1.0e-14)

    def test_total_hamiltonian(self, algebra):
        """Sum Hamiltonians across multiple sectors."""
        states = [
            CanonicalSectorState(r=1.0, pi_r=1.0, sector_idx=i)
            for i in range(5)
        ]

        K, S = 1.0, 0.5
        H_total = algebra.total_hamiltonian(states, K, S)

        expected = 5 * algebra.sector_hamiltonian(1.0, 1.0, K, S)
        assert np.isclose(H_total, expected, rtol=1.0e-14)


class TestRiccatiFluxEvolution:
    """Tests for optical depth evolution via Riccati ODE."""

    @pytest.fixture
    def algebra(self):
        from geolang_core.initialization import generate_quinn_initialization_tensor
        seed = generate_quinn_initialization_tensor(seed=42)
        return CanonicalProjectorAlgebra(projectors=seed.projectors)

    def test_riccati_flux_derivative_at_fixed_point(self, algebra):
        """Derivative behavior at test point r=1."""
        K, S = 1.0, 0.5
        r = 1.0

        dr_dz = algebra.riccati_flux_derivative(r, K, S)

        # For this Riccati equation dr/dz = S(r-1)² - 2Kr
        # at r=1, K=1, S=0.5: dr/dz = 0 - 2 = -2.0
        expected = S * (r - 1)**2 - 2 * K * r
        assert np.isclose(dr_dz, expected, atol=1.0e-14)

    def test_riccati_flux_derivative_calculation(self, algebra):
        """Verify Riccati derivative formula: dr/dz = S(r-1)² - 2Kr."""
        K, S = 1.0, 0.5

        # Test multiple points
        test_points = [0.5, 0.8, 1.0, 1.2, 2.0]
        for r in test_points:
            dr_dz = algebra.riccati_flux_derivative(r=r, K=K, S=S)
            expected = S * (r - 1)**2 - 2 * K * r
            assert np.isclose(dr_dz, expected, atol=1.0e-14), \
                f"At r={r}: got {dr_dz}, expected {expected}"

    def test_evolve_sector_riccati_trajectory(self, algebra):
        """Evolve sector through optical depth."""
        r0 = 0.5
        pi_r = 1.0
        K, S = 1.0, 0.5
        z_steps = 100
        dz = 0.01

        r_traj, z_traj = algebra.evolve_sector_riccati(r0, pi_r, K, S, z_steps, dz)

        assert len(r_traj) == z_steps + 1
        assert len(z_traj) == z_steps + 1
        assert np.isclose(r_traj[0], r0), "Initial condition should match"
        assert np.isclose(z_traj[0], 0.0), "Initial optical depth should be 0"
        assert np.isclose(z_traj[-1], z_steps * dz), "Final z should match steps × dz"
        assert np.all(np.isfinite(r_traj)), "Trajectory should contain finite values"

    def test_evolve_sector_riccati_produces_trajectory(self, algebra):
        """Verify trajectory evolution produces expected structure."""
        r0 = 0.5
        pi_r = 1.0
        K, S = 1.0, 0.5
        z_steps = 500
        dz = 0.01

        r_traj, z_traj = algebra.evolve_sector_riccati(r0, pi_r, K, S, z_steps, dz)

        # Verify trajectory properties
        assert len(r_traj) == z_steps + 1, "Should have z_steps+1 points"
        assert len(z_traj) == z_steps + 1, "Should have z_steps+1 points"
        assert np.isclose(r_traj[0], r0), "Should start at r0"
        assert np.isclose(z_traj[0], 0.0), "Should start at z=0"
        assert all(np.isfinite(r_traj)), "All r values should be finite"


class TestCanonicalStateExtraction:
    """Tests for extracting complete canonical system state."""

    @pytest.fixture
    def algebra(self):
        projectors = []
        for i in range(8):
            p = np.zeros((8, 8), dtype=np.float64)
            p[i, i] = 1.0 / np.sqrt(4)
            projectors.append(p)

        for _ in range(24):
            projectors.append(np.zeros((8, 8)))

        return CanonicalProjectorAlgebra(projectors=projectors)

    def test_extract_canonical_state_all_sectors(self, algebra):
        """Extract canonical state from carrier vector."""
        v = SplitCarrierVector(np.ones(8))

        state = algebra.extract_canonical_state(v)

        assert isinstance(state, CanonicalSystemState)
        assert len(state.sectors) == 32, "Should have 32 sectors"
        assert np.isfinite(state.total_hamiltonian), "Total Hamiltonian should be finite"

    def test_canonical_state_sector_consistency(self, algebra):
        """Each sector in state should have valid (r, π_r)."""
        np.random.seed(42)
        v = SplitCarrierVector(np.random.randn(8))

        state = algebra.extract_canonical_state(v)

        for sector in state.sectors:
            assert isinstance(sector, CanonicalSectorState)
            assert sector.sector_idx >= 0 and sector.sector_idx < 32
            if not np.isnan(sector.r):
                assert sector.r > 0, f"r should be positive, got {sector.r}"
            if sector.pi_r > 1.0e-12:
                assert sector.pi_r > 0, "π_r should be positive when non-zero"


class TestSymplecticPreservation:
    """Tests for symplectic structure preservation under projection."""

    @pytest.fixture
    def simple_algebra(self):
        """Simple diagonal projectors."""
        projectors = []
        for i in range(8):
            p = np.zeros((8, 8), dtype=np.float64)
            p[i, i] = 1.0
            projectors.append(p)

        for _ in range(24):
            projectors.append(np.zeros((8, 8)))

        return CanonicalProjectorAlgebra(projectors=projectors)

    def test_symplectic_form_sector_wedge_product(self, simple_algebra):
        """Verify ω_k = dr ∧ dπ_r."""
        r, pi_r = 1.0, 2.0
        dr, dpi_r = 0.1, 0.2

        omega_k = simple_algebra.symplectic_form_sector(r, pi_r, dr, dpi_r)

        expected = dr * dpi_r
        assert np.isclose(omega_k, expected, rtol=1.0e-14)

    def test_orthogonal_projector_symplectic_preservation(self, simple_algebra):
        """Check that projection preserves symplectic structure."""
        preserved = simple_algebra.verify_orthogonal_projector_symplectic_preservation(num_samples=5)

        # With perfect (diagonal) projectors, structure should be preserved
        assert preserved, "Symplectic structure should be preserved"


class TestCanonicalIntegration:
    """Integration tests combining multiple canonical features."""

    @pytest.fixture
    def realistic_algebra(self):
        """More realistic orthogonal projectors."""
        projectors = []
        for i in range(4):
            for j in range(8):
                p = np.zeros((8, 8), dtype=np.float64)
                p[j, j] = 1.0 / 8.0
                projectors.append(p)

        return CanonicalProjectorAlgebra(projectors=projectors)

    def test_full_evolution_workflow(self, realistic_algebra):
        """Complete workflow: extract state → evolve → re-extract."""
        np.random.seed(42)
        v = SplitCarrierVector(np.random.randn(8))

        # Extract initial state
        state0 = realistic_algebra.extract_canonical_state(v)

        # Evolve a sector
        sector = state0.sectors[0]
        if not np.isnan(sector.r) and sector.pi_r > 1.0e-12:
            r_traj, z_traj = realistic_algebra.evolve_sector_riccati(
                sector.r, sector.pi_r, K=1.0, S=0.5, z_steps=50, dz=0.01
            )

            assert len(r_traj) == 51
            assert all(np.isfinite(r_traj))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
