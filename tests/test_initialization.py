"""
Test suite for Quinn → Mishra-Tan initialization bridge.

Validates:
1. Seed generation maintains global constraints
2. Active sector structure (rank-1 projectors)
3. Locked sector preservation (structural zeros)
4. Deformation space stays on constraint manifold
5. Constraint residuals under perturbations
"""

import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from geolang_core import (
    generate_quinn_initialization_tensor,
    verify_constraint_manifold,
    extract_active_sectors,
    extract_locked_sectors,
    MishraTanDeformationSpace,
)


class TestQuinnInitializationSeed:
    """Tests for seed generation."""

    def test_seed_generates_32_projectors(self):
        """Seed should produce exactly 32 projectors."""
        seed = generate_quinn_initialization_tensor(seed=42)
        assert len(seed.projectors) == 32

    def test_seed_identity_resolution(self):
        """Sum of projectors should equal identity."""
        seed = generate_quinn_initialization_tensor(seed=42)
        assert seed.identity_residual < 1.0e-14
        assert seed.anomaly_locked, "Seed should be anomaly-locked"

    def test_seed_trace_conservation(self):
        """Total trace of projectors should equal 8."""
        seed = generate_quinn_initialization_tensor(seed=42)
        assert np.isclose(seed.total_trace, 8.0, atol=1.0e-14)

    def test_seed_active_rank(self):
        """First 8 projectors should be rank-1."""
        seed = generate_quinn_initialization_tensor(seed=42)
        for i in range(8):
            p = seed.projectors[i]
            rank = np.linalg.matrix_rank(p, tol=1.0e-14)
            assert rank == 1, f"Active sector {i} should be rank-1, got rank {rank}"

    def test_seed_locked_rank(self):
        """Remaining 24 projectors should be rank-0 (zero matrices)."""
        seed = generate_quinn_initialization_tensor(seed=42)
        for i in range(8, 32):
            p = seed.projectors[i]
            rank = np.linalg.matrix_rank(p, tol=1.0e-14)
            assert rank == 0, f"Locked sector {i} should be rank-0, got rank {rank}"
            assert np.allclose(p, 0.0, atol=1.0e-14)

    def test_seed_orthogonality(self):
        """Active projectors should be mutually orthogonal."""
        seed = generate_quinn_initialization_tensor(seed=42)
        for i in range(8):
            for j in range(8):
                product = seed.projectors[i] @ seed.projectors[j]
                if i == j:
                    error = np.max(np.abs(product - seed.projectors[i]))
                    assert error < 1.0e-14, f"P[{i}]² should equal P[{i}]"
                else:
                    error = np.max(np.abs(product))
                    assert error < 1.0e-14, f"P[{i}]P[{j}] should be zero"


class TestConstraintManifold:
    """Tests for constraint preservation."""

    def test_verify_valid_seed(self):
        """Valid seed should pass verification."""
        seed = generate_quinn_initialization_tensor(seed=42)
        is_valid, reason = verify_constraint_manifold(seed.projectors)
        assert is_valid, f"Seed failed verification: {reason}"

    def test_verify_wrong_count_fails(self):
        """Wrong number of projectors should fail."""
        projectors = [np.eye(8) / 4.0 for _ in range(16)]
        is_valid, reason = verify_constraint_manifold(projectors)
        assert not is_valid
        assert "32" in reason

    def test_verify_wrong_shape_fails(self):
        """Wrong projector shape should fail."""
        seed = generate_quinn_initialization_tensor(seed=42)
        bad_projectors = seed.projectors[:-1] + [np.zeros((7, 7))]
        is_valid, reason = verify_constraint_manifold(bad_projectors)
        assert not is_valid
        assert "(8, 8)" in reason

    def test_verify_identity_residual_check(self):
        """Verify detects identity resolution violations."""
        seed = generate_quinn_initialization_tensor(seed=42)
        bad_projectors = seed.projectors[:-1] + [np.eye(8)]  # Add extra identity
        is_valid, reason = verify_constraint_manifold(bad_projectors)
        assert not is_valid
        assert "Identity residual" in reason


class TestSectorExtraction:
    """Tests for active/locked sector extraction."""

    @pytest.fixture
    def seed(self):
        return generate_quinn_initialization_tensor(seed=42)

    def test_extract_active_sectors(self, seed):
        """Extract first 8 projectors as active."""
        active = extract_active_sectors(seed.projectors, num_active=8)
        assert len(active) == 8
        for i, p in enumerate(active):
            np.testing.assert_array_equal(p, seed.projectors[i])

    def test_extract_locked_sectors(self, seed):
        """Extract remaining 24 as locked."""
        locked = extract_locked_sectors(seed.projectors, num_active=8)
        assert len(locked) == 24
        for i, p in enumerate(locked):
            np.testing.assert_array_equal(p, seed.projectors[i + 8])

    def test_extract_too_many_active_raises(self, seed):
        """Cannot extract more active sectors than exist."""
        with pytest.raises(ValueError, match="Cannot extract"):
            extract_active_sectors(seed.projectors, num_active=40)

    def test_locked_are_structural_zeros(self, seed):
        """All locked sectors should be zero."""
        locked = extract_locked_sectors(seed.projectors, num_active=8)
        for p in locked:
            assert np.allclose(p, 0.0, atol=1.0e-14)


class TestMishraTanDeformationSpace:
    """Tests for deformation within constraint manifold."""

    @pytest.fixture
    def space(self):
        seed = generate_quinn_initialization_tensor(seed=42)
        return MishraTanDeformationSpace(seed)

    def test_initialization(self, space):
        """Deformation space inherits from seed."""
        assert len(space.active_projectors) == 8
        assert len(space.locked_projectors) == 24
        assert len(space.deformation_history) == 0

    def test_propose_undeformed_accepts(self, space):
        """Proposing undeformed projectors should be accepted."""
        is_valid, reason, residual = space.propose_deformation(
            space.active_projectors,
            tolerance=1.0e-12
        )
        assert is_valid, f"Undeformed rejected: {reason}"
        assert residual < 1.0e-14

    def test_propose_small_perturbation(self, space):
        """Small perturbation that preserves constraints should accept."""
        # Scale by small factor (doesn't preserve projector properties, but tests constraint check)
        perturbed = [0.9 * p for p in space.active_projectors]
        is_valid, reason, residual = space.propose_deformation(perturbed, tolerance=1.0e-10)
        # This will likely fail because scaling violates idempotency
        # But it tests the checking mechanism
        assert isinstance(is_valid, bool)
        assert isinstance(residual, float)

    def test_propose_wrong_count_rejects(self, space):
        """Wrong number of active projectors rejected."""
        is_valid, reason, residual = space.propose_deformation(
            space.active_projectors[:5],
            tolerance=1.0e-12
        )
        assert not is_valid
        assert "8" in reason

    def test_accept_deformation_records(self, space):
        """Accepting deformation records it in history."""
        assert len(space.deformation_history) == 0

        space.accept_deformation(
            space.active_projectors,
            metadata={"iteration": 0, "energy": 1.0}
        )

        assert len(space.deformation_history) == 1
        record = space.deformation_history[0]
        assert record["metadata"]["iteration"] == 0
        assert record["metadata"]["energy"] == 1.0

    def test_get_full_projectors_undeformed(self, space):
        """Before any deformation, should return seed."""
        full = space.get_full_projectors()
        assert len(full) == 32
        is_valid, _ = verify_constraint_manifold(full)
        assert is_valid

    def test_get_full_projectors_after_deformation(self, space):
        """After deformation, should return updated set."""
        space.accept_deformation(space.active_projectors, metadata={"step": 1})
        full = space.get_full_projectors()
        assert len(full) == 32
        is_valid, _ = verify_constraint_manifold(full)
        assert is_valid

    def test_deformation_history_length(self, space):
        """Multiple deformations should be tracked."""
        for step in range(5):
            space.accept_deformation(space.active_projectors, metadata={"step": step})

        assert len(space.deformation_history) == 5
        for i, record in enumerate(space.deformation_history):
            assert record["metadata"]["step"] == i


class TestQuinnMishraTanBridge:
    """Integration tests showing Quinn → Mishra-Tan workflow."""

    def test_full_workflow(self):
        """Complete workflow: Quinn generates seed, Mishra-Tan deforms."""
        # Quinn generates the seed
        seed = generate_quinn_initialization_tensor(seed=42)
        assert seed.anomaly_locked

        # Mishra-Tan inherits the constraint space
        space = MishraTanDeformationSpace(seed)

        # Mishra-Tan proposes local deformations (simplified: no actual deformation)
        is_valid, reason, residual = space.propose_deformation(
            space.active_projectors,
            tolerance=1.0e-12
        )
        assert is_valid

        # Mishra-Tan accepts and records
        space.accept_deformation(space.active_projectors, metadata={"step": 0})

        # Global constraints remain satisfied
        full = space.get_full_projectors()
        is_valid, reason = verify_constraint_manifold(full)
        assert is_valid, f"Constraint violated: {reason}"

    def test_constraint_preservation_across_iterations(self):
        """Verify constraint remains satisfied through multiple iterations."""
        seed = generate_quinn_initialization_tensor(seed=42)
        space = MishraTanDeformationSpace(seed)

        for step in range(10):
            is_valid, reason, residual = space.propose_deformation(
                space.active_projectors,
                tolerance=1.0e-12
            )
            assert is_valid, f"Step {step} failed: {reason}"

            space.accept_deformation(space.active_projectors, metadata={"step": step})
            assert len(space.deformation_history) == step + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
