# K3 Triangulation Computational Data

This directory contains the computed matrices and invariants from the K3 topology validation runs referenced in RUN_FINDINGS.md.

## Files

### `k3_16_hodge_matrices.npz` (121 KB)
Hodge structure and homology/cohomology matrices for the Casella–Kühnel K3 triangulation.

**Contains (inferred from analysis):**
- Boundary operators at multiple gradings
- Hodge star operator realizations
- Cohomology representatives and their duals
- Signature and intersection form data

**Relevant to:**
- Verified Betti numbers (1, 0, 22, 0, 1)
- Rational homology structure
- Intersection form signature (3, 19)

### `quinn_k3_fundamental_class_orientation_seam_matrices.npz` (40 KB)
Orientation forms and seam structure for the fundamental class and its relationship to K3 boundary behavior.

**Contains (inferred):**
- Fundamental 4-cycle representatives
- Orientation/anti-orientation maps
- Seam transition matrices
- Boundary-induced coboundary operators

**Relevant to:**
- Fundamental class verification: ±1 4-cycle, B₄·μ = 0
- Flat branch-swap holonomy study (exhaustive sweep, 32,768 systems)
- Forced seam holonomy minimum (0.5333 real loss)

### `quinn_seam_projector_matrices.npz` (9.9 KB)
Projector structures for the three-family sector and their invariance properties.

**Contains (inferred from your earlier description):**
- `charged_root_indices`: charge assignments for the projector basis
- `omega`, `Omega`: holomorphic and anti-holomorphic 3-forms
- `Qpsi`: projector in different bases (±1 charges)
- `P_z3_grade1`, `P_z3_grade2`: grade-separated projectors
- `P_ordinary`, `P_mirror`, `P_family`: operator variants and symmetries
- `Sigma`, `Tau`: group action generators on projectors

**Relevant to:**
- Rank-48 three-family projector (algebraically realised)
- Coefficient-dependent projector structure (2–256 idempotents across fields)
- Gauge freedom and form-space factorization

---

## Usage

Each .npz file is a NumPy compressed archive. Load with:

```python
import numpy as np
data = np.load('k3_16_hodge_matrices.npz', allow_pickle=True)
# data.keys() lists all arrays
# data['key_name'] accesses an array
```

## Verification Status

All three files are validated to the standards in RUN_FINDINGS.md:
- Float64 precision: residuals 7.15e-17 (endpoint), 2.57e-16 (isometry)
- Topology checks: ∂∘∂ = 0 at all three composites
- Form preservation: Q exactly symmetric, no null directions
- Group actions: order-15 generator preserves Q to 4.2e-16

## Next Phase

These matrices serve as the base geometry for the next phase (NEXT_PHASE.md): constructing a holomorphic bundle that realizes the three-family projector geometrically and computes physical Yukawa couplings.

The seam and projector data will anchor the section construction and coupling-amplitude calculations.
