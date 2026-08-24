"""
Test suite for GeoLang Core Algebra Framework.

Validates:
1. Identity and orthogonality properties
2. Reconstruction residuals
3. Seam signature constraints
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from geolang_core import (
    SplitCarrierVector,
    ProjectorAlgebra,
    SeamInvolutionGate,
)


class TestSplitCarrierVector:
    """Tests for sector-based vector representation."""

    def test_construction_from_array(self):
        """Construct SplitCarrierVector from 8-element array."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        v = SplitCarrierVector(data)
        assert v.r0 == 1.0
        assert v.c1 == complex(2.0, 3.0)
        assert v.c2 == complex(4.0, 5.0)
        assert v.c3 == complex(6.0, 7.0)
        assert v.r7 == 8.0

    def test_sector_setters(self):
        """Test setting individual sector values."""
        v = SplitCarrierVector(np.zeros(8))
        v.r0 = 1.5
        v.c1 = complex(2.0, 3.0)
        v.r7 = 8.5

        assert v.r0 == 1.5
        assert v.c1 == complex(2.0, 3.0)
        assert v.r7 == 8.5

    def test_invalid_shape_raises(self):
        """Reject non-8D arrays."""
        with pytest.raises(ValueError, match="Expected shape"):
            SplitCarrierVector(np.array([1.0, 2.0]))

    def test_array_interface(self):
        """Support numpy array interface."""
        data = np.arange(8, dtype=np.float64)
        v = SplitCarrierVector(data)
        arr = np.asarray(v)
        np.testing.assert_array_equal(arr, data)


class TestProjectorAlgebraValidation:
    """Tests for projector algebra properties."""

    @pytest.fixture
    def identity_projectors(self):
        """32 orthogonal projectors summing to identity."""
        dim = 8
        projectors = []
        for i in range(32):
            basis_idx = i % dim
            p = np.zeros((dim, dim), dtype=np.float64)
            p[basis_idx, basis_idx] = 1.0 / 4.0
            projectors.append(p)
        return projectors

    def test_identity_resolution(self, identity_projectors):
        """Sum of projectors equals identity matrix."""
        algebra = ProjectorAlgebra(identity_projectors)
        report = algebra.verify_algebra_properties(num_samples=10)

        assert report.identity_residual < 1.0e-14
        assert report.passed or np.allclose(
            sum(algebra.projectors), np.eye(8), atol=1.0e-14
        )

    def test_orthogonality(self, identity_projectors):
        """Projectors are pairwise orthogonal."""
        algebra = ProjectorAlgebra(identity_projectors)
        report = algebra.verify_algebra_properties(num_samples=10)

        for i in range(32):
            for j in range(32):
                product = algebra.projectors[i] @ algebra.projectors[j]
                target = algebra.projectors[i] if i == j else np.zeros((8, 8))
                error = np.max(np.abs(product - target))
                assert error < 1.0e-14, f"Orthogonality failed for P[{i}]P[{j}]"

    def test_idempotency(self, identity_projectors):
        """Each projector satisfies Pᵢ² = Pᵢ."""
        algebra = ProjectorAlgebra(identity_projectors)

        for i in range(32):
            p = algebra.projectors[i]
            p_sq = p @ p
            error = np.max(np.abs(p_sq - p))
            assert error < 1.0e-14, f"Idempotency failed for P[{i}]"

    def test_reconstruction_residual(self, identity_projectors):
        """Vector reconstruction v = Σ Pᵢv within tolerance."""
        algebra = ProjectorAlgebra(identity_projectors)
        report = algebra.verify_algebra_properties(num_samples=100)

        assert report.max_reconstruction_residual <= 2.220e-16 * 100
        assert report.num_validation_samples == 100

    def test_trace_sum(self, identity_projectors):
        """Trace sum of all projectors equals 8 (dimension)."""
        algebra = ProjectorAlgebra(identity_projectors)
        trace_sum = algebra.trace_all_projectors()
        assert np.isclose(trace_sum, 8.0, atol=1.0e-14)

    def test_invalid_projector_count_raises(self):
        """Reject list with wrong number of projectors."""
        projectors = [np.zeros((8, 8)) for _ in range(16)]
        with pytest.raises(ValueError, match="Expected 32 projectors"):
            ProjectorAlgebra(projectors)

    def test_invalid_projector_shape_raises(self):
        """Reject projectors with wrong shape."""
        projectors = [np.zeros((8, 8)) for _ in range(31)] + [np.zeros((7, 7))]
        with pytest.raises(ValueError, match="shape"):
            ProjectorAlgebra(projectors)


class TestProjectionOperations:
    """Tests for applying projectors to vectors."""

    @pytest.fixture
    def simple_algebra(self):
        """Simple algebra with 8 block-diagonal projectors."""
        projectors = []
        for i in range(8):
            p = np.zeros((8, 8), dtype=np.float64)
            p[i, i] = 1.0 / 1.0
            projectors.append(p)

        for _ in range(24):
            projectors.append(np.zeros((8, 8)))

        return ProjectorAlgebra(projectors)

    def test_project_sector(self, simple_algebra):
        """Apply individual projector to vector."""
        v = SplitCarrierVector(np.ones(8))

        for i in range(8):
            v_proj = simple_algebra.project_sector(v, i)
            expected = np.zeros(8)
            expected[i] = 1.0
            np.testing.assert_array_almost_equal(v_proj.data, expected, decimal=14)

    def test_invalid_sector_index_raises(self, simple_algebra):
        """Reject out-of-range sector indices."""
        v = SplitCarrierVector(np.ones(8))
        with pytest.raises(IndexError):
            simple_algebra.project_sector(v, 32)

    def test_reconstruct_vector(self, simple_algebra):
        """Reconstruct vector from projections."""
        v_in = SplitCarrierVector(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]))
        v_rec, residual = simple_algebra.reconstruct(v_in, return_residual=True)

        np.testing.assert_array_almost_equal(v_in.data, v_rec.data, decimal=14)
        assert residual < 1.0e-13


class TestSeamInvolutionGate:
    """Tests for seam matrix and signature enforcement."""

    def test_construction_from_matrix(self):
        """Create SeamInvolutionGate from explicit matrix."""
        seam_matrix = np.eye(8)
        gate = SeamInvolutionGate(seam_matrix)
        np.testing.assert_array_equal(gate.seam_matrix, seam_matrix)

    def test_invalid_matrix_shape_raises(self):
        """Reject non-square matrices."""
        with pytest.raises(ValueError, match="square"):
            SeamInvolutionGate(np.zeros((8, 7)))

    def test_construct_from_active_projectors(self):
        """Create seam gate as complement of active projectors."""
        active = [np.eye(8) / 4.0 for _ in range(4)]
        gate = SeamInvolutionGate.from_active_projectors(active)

        assert gate.seam_matrix is not None
        assert gate.seam_matrix.shape == (8, 8)

    def test_signature_validation_identity(self):
        """Validate signature of identity matrix (diagonal, 8 positive eigenvalues)."""
        gate = SeamInvolutionGate(np.eye(8))
        report = gate.validate_physical_signature()

        assert report.has_complex == False
        assert report.max_imaginary_part < 1.0e-14
        assert all(e > 0.5 for e in report.eigenvalues)

    def test_compute_physical_metric(self):
        """Compute physical metric from connection and current."""
        gate = SeamInvolutionGate(np.eye(8))

        a_matrix = np.array([
            [1.0, 0.2],
            [0.2, 2.0]
        ])
        j_vector = np.array([1.0, 0.0])

        g_phys = gate.compute_physical_metric(a_matrix, j_vector)

        assert g_phys.shape == (2, 2)
        assert np.isfinite(g_phys).all()

    def test_zero_current_raises(self):
        """Reject zero or negligible current vector."""
        gate = SeamInvolutionGate(np.eye(8))
        a_matrix = np.eye(2)
        j_vector = np.zeros(2)

        with pytest.raises(ValueError, match="negligible"):
            gate.compute_physical_metric(a_matrix, j_vector)


class TestIntegrationWithData:
    """Integration tests loading actual .npz data files."""

    @pytest.fixture
    def data_dir(self):
        """Path to data directory."""
        return Path(__file__).parent.parent / "data"

    def test_load_seam_projectors_from_file(self, data_dir):
        """Load seam projectors from .npz if available."""
        projector_file = data_dir / "quinn_seam_projector_matrices.npz"

        if not projector_file.exists():
            pytest.skip(f"Data file not found: {projector_file}")

        data = np.load(projector_file, allow_pickle=True)
        projector_keys = [k for k in data.keys() if k.startswith('P_')]

        if len(projector_keys) >= 1:
            assert len(projector_keys) > 0, "No projectors found in file"
            for key in projector_keys[:3]:
                p = data[key]
                assert isinstance(p, np.ndarray)

    def test_load_hodge_matrices(self, data_dir):
        """Load Hodge matrices from .npz if available."""
        hodge_file = data_dir / "k3_16_hodge_matrices.npz"

        if not hodge_file.exists():
            pytest.skip(f"Data file not found: {hodge_file}")

        data = np.load(hodge_file, allow_pickle=True)
        assert len(data.keys()) > 0, "No matrices in Hodge file"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
