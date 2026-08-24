# K3 Triangulation Topology: Validated Findings

## Core Topology Verified

**From `ck16_geometry_bundle.npz`:**
- f-vector: (16, 120, 560, 720, 288)
- Euler characteristic χ = 24 ✓
- Boundary composites: ∂∘∂ = 0 at all three levels, zero nonzero entries ✓
- Fundamental class: genuine ±1 4-cycle with B₄·μ = 0 ✓
- Rational Betti numbers: (1, 0, 22, 0, 1)
- Rank sequence: (15, 105, 433, 287)
- Rational homology: exactly symmetric with signature (3, 19), no null directions
- Generator order: `generator_15_H2` has exact order 15, preserves Q to 4.2e-16

**Residuals:** 7.15e-17 endpoint, 2.57e-16 isometry — expected order for float64.

**Verdict:** Correct Casella–Kühnel triangulation with correct K3 cohomology.

---

## Negative Results (Substantive)

### 1. Gauge Freedom: Paper-style Auxiliary Transition Loss
- **Status:** PASS WITH TRIVIALIZATION
- **Loss:** 4.55e-31
- **Distance to exact gauge projection:** 2.19e-15
- **Interpretation:** Every zero-loss solution is pure gauge. The optimizer found a perfectly coherent global field carrying exactly zero physical information. This is the empirical proof that convention leaves no residue.

### 2. Flat Branch-Swap Holonomy
- **Status:** NO-GO (exhaustive, not sampled)
- **Scope:** All 32,768 flat orientation-transition systems classified
- **Finding:** All vertex-gauge coboundaries; zero holonomy around the order-15 cycle
- **Implication:** Flat data on unmodified K3 produces no persistent seams.

### 3. Forced Seam Holonomy
- **Status:** DEFECT REQUIRED
- **Minimum real loss:** 0.5333
- **Implication:** Persistent seams require curvature, singular support, boundary modification, or topology change.

### 4. Coefficient Independence
- **Status:** NO-GO
- **Finding:** Idempotent projector counts vary 2–256 across tested fields. Over F₂ only 0 and I are equivariant; over ℝ there are 32.
- **Scope limitation:** §4 claim that "topological invariants supply a zero point completely free of frame choices" is contradicted. Topology does not dissolve the frame problem; it relocates it into the coefficient ring.
- **Working thesis:** Use multi-coefficient atlas—F₂ for topology, signed/Galois for orientation, positive metrics for energy. Three frames, chosen by hand, to describe one object.

---

## Physics Scope: What Is Not Here

Grepped all 98MB. Physics vocabulary appears only in Mishra–Tan comparison scorecard:
- HYM connection: 0 vs 5
- Ricci-flat metric: 1 vs 5
- Bundle-valued harmonic representatives: 1 vs 5
- Physically normalised Yukawa amplitudes: 0 vs 5

**Current status:** QUINN does not yet exceed the Mishra–Tan paper overall.

**Explicitly absent:** hypercharge, coupling constant, scale, k_Y / Schwinger / CF-1 physics.

This run was *not* designed to address those objections. It does not.

---

## Integrity Issues Requiring Resolution

### Issue 1: C-INTEGRAL-GLUE Lattice Conflict
**Catalog entry:** rank-4 moving lattice, determinant 80, glue (ℤ/2)⁴+ℤ/5, marked `registered_not_recomputed`

**Shard 090 computation:** moving_rank: 4, moving_determinant: 9, fixed_determinant: -9

**Status:** These are different lattices under the same description.
- Either they are two distinct constructions requiring separate names, or
- One supersedes the other.

**Action required:** Resolve the naming and parametrization before this can be cited.

### Issue 2: Galois Exchange Framing
**Current text claim:** Orientation flip

**Measured reality:** ‖Γ(Q)+Q‖ = 0.2276, normalizer generator error 0.380 (not numerical roundoff)

**Correct framing:** Semilinear/groupoid relation, not forced into AGL. The Galois exchange is one of two composed factors in form-space factorization, *not* the orientation flip itself.

**Status:** Replacement text is correct. Update documentation accordingly.

---

## Disciplinary Governance

The following practices preserved readability and integrity:
- Preserved the failed `.010_orientation_inversion.tmp-*` shard rather than reclassifying
- Left runs 001–003 unrenamed despite their failure status
- Refused to uniformly reclassify mixed FAIL / NO-GO into a single category

This discipline is what makes the rest of this work readable.

---

## Next Phase: Open Problem (Well-Defined)

**Target:** A valid holomorphic bundle realising the three-family projector on the K3 geometry established above.

**Why here:** Everything upstream is now exhaustively mapped. The failure mode from here is not under-verification—it is building more atlas instead of building the bundle.

**Falsifiability:** This is a concrete, measurable target with a clear success condition.
