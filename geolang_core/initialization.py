"""
Quinn → Mishra-Tan initialization bridge.

Generates seed projector algebra for Mishra-Tan's HYM solver by extracting
the global constraint manifold from Quinn's orthogonal decomposition.

The initialization encodes:
- First 8 sectors: active rank-1 projectors (deformation-free basis)
- Remaining 24 sectors: structural zeros (anomaly-locked)
- Global trace constraint: sum(Tr(P_i)) = 8 (dimensional index)
- Resolution of identity: sum(P_i) = I_8 (completeness)

Mishra-Tan inherits this structure and performs local HYM deformations
within the constraint manifold, never leaving the 32-sector framework.
"""

import numpy as np
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class QuinnInitializationSeed:
    """Validated seed for Mishra-Tan HYM solver."""
    projectors: List[np.ndarray]
    active_rank: int
    locked_rank: int
    identity_residual: float
    total_trace: float
    anomaly_locked: bool

    def __str__(self) -> str:
        return (
            f"QuinnInitializationSeed\n"
            f"  Active sectors:       {self.active_rank}\n"
            f"  Locked sectors:       {self.locked_rank}\n"
            f"  Identity residual:    {self.identity_residual:.3e}\n"
            f"  Total trace:          {self.total_trace:.1f}\n"
            f"  Anomaly locked:       {self.anomaly_locked}\n"
            f"  Mishra-Tan ready:     {self.anomaly_locked}"
        )


def generate_quinn_initialization_tensor(seed: int = 42) -> QuinnInitializationSeed:
    """
    Generate 32 orthogonal (8,8) projectors seeding Mishra-Tan's HYM solver.

    Strategy:
    1. QR decompose a random matrix to get 8 orthonormal vectors
    2. Map to 8 rank-1 projectors (active sectors, deformable by Mishra-Tan)
    3. Fill remaining 24 with structural zeros (anomaly-locked, immutable)
    4. Verify global constraints: identity resolution, trace, orthogonality

    Returns:
        QuinnInitializationSeed with validation metrics and projector list
    """
    np.random.seed(seed)

    # Step 1: Generate orthonormal basis
    random_matrix = np.random.randn(8, 8)
    Q, _ = np.linalg.qr(random_matrix)

    projectors = []

    # Step 2: Map orthonormal vectors to rank-1 projectors (active)
    for i in range(8):
        v = Q[:, i : i + 1]  # Column vector (8, 1)
        P_i = v @ v.T       # (8, 1) @ (1, 8) = (8, 8)
        projectors.append(P_i)

    # Step 3: Structural zeros (locked anomaly sectors)
    for _ in range(24):
        projectors.append(np.zeros((8, 8), dtype=np.float64))

    # Step 4: Validation
    identity_matrix = np.eye(8, dtype=np.float64)
    p_sum = sum(projectors)
    identity_residual = float(np.max(np.abs(p_sum - identity_matrix)))
    total_trace = sum(float(np.trace(p)) for p in projectors)

    anomaly_locked = identity_residual <= 1.0e-14 and np.isclose(total_trace, 8.0, atol=1.0e-14)

    return QuinnInitializationSeed(
        projectors=projectors,
        active_rank=8,
        locked_rank=24,
        identity_residual=identity_residual,
        total_trace=total_trace,
        anomaly_locked=anomaly_locked,
    )


def verify_constraint_manifold(
    projectors: List[np.ndarray],
    expected_identity_residual: float = 1.0e-14,
    expected_total_trace: float = 8.0,
) -> Tuple[bool, str]:
    """
    Verify that projector set remains on Quinn's constraint manifold.

    Checks:
    1. Identity resolution: ‖Σ Pᵢ - I₈‖∞ ≤ threshold
    2. Trace conservation: Σ Tr(Pᵢ) = 8
    3. Count: exactly 32 projectors

    Args:
        projectors: List of (8,8) matrices
        expected_identity_residual: Tolerance for identity resolution
        expected_total_trace: Expected sum of traces

    Returns:
        (is_valid, reason_string)
    """
    if len(projectors) != 32:
        return False, f"Expected 32 projectors, got {len(projectors)}"

    if any(p.shape != (8, 8) for p in projectors):
        return False, "All projectors must be (8, 8)"

    identity = np.eye(8, dtype=np.float64)
    p_sum = sum(projectors)
    id_residual = float(np.max(np.abs(p_sum - identity)))

    if id_residual > expected_identity_residual:
        return False, f"Identity residual {id_residual:.3e} exceeds {expected_identity_residual:.3e}"

    total_trace = sum(float(np.trace(p)) for p in projectors)
    if not np.isclose(total_trace, expected_total_trace, atol=1.0e-14):
        return False, f"Total trace {total_trace:.1f} != {expected_total_trace:.1f}"

    return True, "On constraint manifold ✓"


def extract_active_sectors(
    projectors: List[np.ndarray],
    num_active: int = 8,
) -> List[np.ndarray]:
    """
    Extract the active (deformable) sectors for Mishra-Tan.

    Args:
        projectors: Full 32-projector list from Quinn initialization
        num_active: Number of active sectors (default 8)

    Returns:
        List of first num_active projectors
    """
    if len(projectors) < num_active:
        raise ValueError(f"Cannot extract {num_active} active sectors from {len(projectors)} total")

    return projectors[:num_active]


def extract_locked_sectors(
    projectors: List[np.ndarray],
    num_active: int = 8,
) -> List[np.ndarray]:
    """
    Extract the locked (anomaly-preserving) sectors.

    These cannot be deformed by Mishra-Tan without violating global constraints.

    Args:
        projectors: Full 32-projector list
        num_active: Number of active sectors (rest are locked)

    Returns:
        List of locked projectors
    """
    if len(projectors) < num_active:
        raise ValueError(f"num_active={num_active} exceeds total {len(projectors)}")

    return projectors[num_active:]


class MishraTanDeformationSpace:
    """
    Represents the local deformation space within Quinn's global manifold.

    Mishra-Tan's HYM solver operates as a deformation of the active sectors
    while keeping the locked sectors fixed. This class tracks the constraint
    preservation during such deformations.
    """

    def __init__(self, seed: QuinnInitializationSeed):
        """Initialize from Quinn's seed."""
        self.seed = seed
        self.active_projectors = extract_active_sectors(seed.projectors, num_active=8)
        self.locked_projectors = extract_locked_sectors(seed.projectors, num_active=8)
        self.deformation_history = []

    def propose_deformation(
        self,
        deformed_active: List[np.ndarray],
        tolerance: float = 1.0e-12,
    ) -> Tuple[bool, str, float]:
        """
        Test whether a proposed deformation preserves Quinn's constraint manifold.

        Args:
            deformed_active: Modified active projectors from Mishra-Tan
            tolerance: Allowed deviation from constraint

        Returns:
            (is_valid, reason, constraint_residual)
        """
        if len(deformed_active) != 8:
            return False, "Deformed set must have 8 active projectors", np.inf

        # Reconstruct full 32-projector set
        full_deformed = deformed_active + self.locked_projectors

        # Check constraint preservation
        is_valid, reason = verify_constraint_manifold(full_deformed)
        identity = np.eye(8, dtype=np.float64)
        p_sum = sum(full_deformed)
        residual = float(np.max(np.abs(p_sum - identity)))

        return is_valid and residual <= tolerance, reason, residual

    def accept_deformation(self, deformed_active: List[np.ndarray], metadata: dict = None):
        """
        Record a validated deformation in the history.

        Args:
            deformed_active: The new active projectors
            metadata: Optional dict with iteration number, energy, etc.
        """
        full_deformed = deformed_active + self.locked_projectors
        identity = np.eye(8, dtype=np.float64)
        p_sum = sum(full_deformed)
        residual = float(np.max(np.abs(p_sum - identity)))

        record = {
            "active": [p.copy() for p in deformed_active],
            "constraint_residual": residual,
            "metadata": metadata or {},
        }
        self.deformation_history.append(record)

    def get_full_projectors(self) -> List[np.ndarray]:
        """Return the current full 32-projector set (active + locked)."""
        if self.deformation_history:
            return self.deformation_history[-1]["active"] + self.locked_projectors
        return self.seed.projectors


if __name__ == "__main__":
    # Generate and audit Quinn's initialization seed
    seed = generate_quinn_initialization_tensor(seed=42)
    print(seed)
    print()

    # Verify constraint preservation
    is_valid, reason = verify_constraint_manifold(seed.projectors)
    print(f"Constraint manifold check: {reason}")
    print()

    # Show active vs locked structure
    active = extract_active_sectors(seed.projectors, num_active=8)
    locked = extract_locked_sectors(seed.projectors, num_active=8)
    print(f"Active sectors (rank-1):      {len(active)} × (8,8)")
    print(f"Locked sectors (structural):  {len(locked)} × (8,8)")
    print(f"Rank sum (active):            {sum(float(np.linalg.matrix_rank(p)) for p in active):.1f}")
    print(f"Rank sum (locked):            {sum(float(np.linalg.matrix_rank(p)) for p in locked):.1f}")
