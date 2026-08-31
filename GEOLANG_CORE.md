# GeoLang Core Algebra Framework

A lightweight, deterministic Python framework implementing Quinn's "Different Algebra" on the split five-sector product carrier space.

## Overview

The GeoLang Core Algebra Framework provides:

- **SplitCarrierVector**: 8D vector wrapper with explicit sector views into ℝ ⊕ ℂ³ ⊕ ℝ
- **ProjectorAlgebra**: Management and validation of 32 orthogonal projectors with full resolution of identity
- **SeamInvolutionGate**: Orientation gates and physical signature enforcement
- **Comprehensive test suite**: Validates all algebraic properties to float64 precision

## Mathematical Model

### Carrier Space

The framework operates on the 8-dimensional split carrier space:

$$\mathbb{S} = \mathbb{R}_0 \oplus \mathbb{C}_1 \oplus \mathbb{C}_2 \oplus \mathbb{C}_3 \oplus \mathbb{R}_7 \cong \mathbb{R}^8$$

Memory layout: `[r0, c1_re, c1_im, c2_re, c2_im, c3_re, c3_im, r7]`

### Projector Algebra

32 orthogonal projection operators $\{P_i\}_{i=1}^{32}$ satisfy:

1. **Resolution of Identity**: $\sum_{i=1}^{32} P_i = I_8$ with residual $\le 1.0 \times 10^{-14}$
2. **Idempotency**: $P_i^2 = P_i$ with error $\le 1.0 \times 10^{-15}$
3. **Orthogonality**: $P_i P_j = \delta_{ij} P_i$ with error $\le 1.0 \times 10^{-15}$
4. **Vector Reconstruction**: $\forall v, \|v - \sum P_i v\| \le 2.220 \times 10^{-16}$

### Seam Involution Gates

The seam projector $P_{\text{seam}} = I - \sum P_{\text{active}}$ encodes orientation transitions between physical branches, enforcing $(1,2)$ signature on the K3 Hodge structure.

## Installation

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Quick Start

### Loading Projectors

```python
from geolang_core import ProjectorAlgebra
import numpy as np

# Load from .npz file
algebra = ProjectorAlgebra(npz_path='data/quinn_seam_projector_matrices.npz')

# Or provide explicit list
projectors = [np.zeros((8, 8)) for _ in range(32)]
algebra = ProjectorAlgebra(projectors=projectors)
```

### Validating Algebra Properties

```python
report = algebra.verify_algebra_properties(num_samples=100)
print(report)

if report.passed:
    print("✓ All algebraic properties verified")
else:
    print("✗ Validation failed")
    print(f"  Identity residual: {report.identity_residual:.3e}")
    print(f"  Max orthogonality error: {report.max_orthogonality_error:.3e}")
```

### Working with Vectors

```python
from geolang_core import SplitCarrierVector

# Create vector from array
v = SplitCarrierVector(np.ones(8))

# Access sectors
print(f"r0 = {v.r0}")          # Real component 0
print(f"c1 = {v.c1}")          # Complex component 1
print(f"c2 = {v.c2}")          # Complex component 2
print(f"c3 = {v.c3}")          # Complex component 3
print(f"r7 = {v.r7}")          # Real component 7

# Project to specific sector
v_proj = algebra.project_sector(v, sector_idx=0)

# Reconstruct from projections
v_reconstructed, residual = algebra.reconstruct(v, return_residual=True)
print(f"Reconstruction error: {residual:.3e}")
```

### Seam Involution Gates

```python
from geolang_core import SeamInvolutionGate

# Construct from active projectors
active_projectors = algebra.projectors[:28]
gate = SeamInvolutionGate.from_active_projectors(active_projectors)

# Validate physical signature
sig_report = gate.validate_physical_signature()
print(sig_report)

if sig_report.physical_bounds_satisfied:
    print(f"✓ Physical signature verified: {sig_report.signature}")
else:
    print(f"✗ Signature mismatch: got {sig_report.signature}, expected (1, 2)")

# Compute physical metric
a_matrix = np.array([[1.0, 0.2], [0.2, 2.0]])
j_vector = np.array([1.0, 0.0])
g_physical = gate.compute_physical_metric(a_matrix, j_vector)
```

## Test Suite

Run the complete validation suite:

```bash
pytest tests/test_algebra.py -v
```

Coverage includes:

- **Vector operations**: Construction, sector access, array interface
- **Projector validation**: Identity resolution, orthogonality, idempotency, reconstruction
- **Seam gates**: Matrix construction, signature validation, metric computation
- **Data integration**: Loading from .npz files

## Numerical Validation Thresholds

| Property | Threshold | Interpretation |
|----------|-----------|-----------------|
| Identity resolution | 1.0e-14 | ‖Σ Pᵢ - I‖∞ |
| Orthogonality | 1.0e-15 | ‖PᵢPⱼ - δᵢⱼPᵢ‖∞ |
| Idempotency | 1.0e-15 | ‖Pᵢ² - Pᵢ‖∞ |
| Reconstruction | 2.220e-16 | ‖v - Σ Pᵢv‖∞ (float64 machine epsilon) |
| Complex eigenvalues | 1.0e-14 | max(Im(λ)) for seam signature |

## Architecture

```
geolang_core/
├── __init__.py          # Package exports
├── algebra.py           # ProjectorAlgebra, SplitCarrierVector
└── seam.py              # SeamInvolutionGate

tests/
├── __init__.py
└── test_algebra.py      # Comprehensive test suite

data/
├── quinn_seam_projector_matrices.npz
├── k3_16_hodge_matrices.npz
└── quinn_k3_fundamental_class_orientation_seam_matrices.npz
```

## References

- **RUN_FINDINGS.md**: Validated K3 topology and experimental results
- **INTEGRITY_ISSUES.md**: Outstanding parametrization conflicts and framing fixes
- **NEXT_PHASE.md**: Holomorphic bundle construction roadmap

## License

Proprietary. All rights reserved.

---

*Generated by Claude Code.*
