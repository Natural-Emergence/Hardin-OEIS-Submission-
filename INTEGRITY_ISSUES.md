# Integrity Issues for Resolution

## Issue 1: C-INTEGRAL-GLUE Lattice Parametrization

**Severity:** High (blocks citation)

**Problem Statement:**
Two conflicting lattice descriptions share the same catalog name "C-INTEGRAL-GLUE":

| Source | rank | moving_determinant | fixed_determinant | glue | Status |
|--------|------|-------------------|------------------|------|--------|
| Catalog (markdown) | 4 | 80 | — | (ℤ/2)⁴+ℤ/5 | registered_not_recomputed |
| Shard 090 computation | 4 | 9 | -9 | — | computed |

**Resolution options:**
1. **Distinction:** These are two different constructions. Rename one, e.g., `C-INTEGRAL-GLUE-v1` and `C-INTEGRAL-GLUE-v2`, with separate catalog entries explaining the relationship.
2. **Supersession:** The shard 090 computation supersedes the catalog entry. Update catalog to reflect shard 090 parameters and mark the old entry as deprecated.
3. **Synthesis:** Both parametrizations are valid for different contexts. Document which context each applies to, and update the catalog with context-dependent references.

**Next action:** Choose resolution path and update catalog and shard documentation.

---

## Issue 2: Galois Exchange Factorization

**Severity:** Medium (affects theoretical framing)

**Problem Statement:**
The exchange between form-space and bundle-structure coordinates was initially framed as an orientation flip. Measured residuals show this is not a single operation:

- ‖Γ(Q)+Q‖ = 0.2276 (not numerical roundoff)
- Normalizer generator error 0.380 (not roundoff)
- Form-space factorization reveals: The Galois exchange is one of two composed factors, not the entire transformation.

**Correct framing:**
The relationship is semilinear/groupoid-valued, not forced into the affine general linear group (AGL) structure. It is a composition of:
1. One component that behaves like an orientation flip (locally)
2. One component that is genuinely groupoid-valued (not AGL-reducible)

**Current documentation:** Uses the simpler "orientation flip" language.

**Action required:**
1. Update text to semilinear/groupoid framing
2. Document the two-factor decomposition explicitly
3. Explain why AGL reduction fails (coefficient non-closure under the second factor)
4. Clarify which calculations depend on which factor

---

## Tracking Status

- [ ] C-INTEGRAL-GLUE: Choose resolution path
- [ ] C-INTEGRAL-GLUE: Update catalog accordingly
- [ ] C-INTEGRAL-GLUE: Update shard 090 documentation with resolution
- [ ] Galois framing: Rewrite exposition with semilinear/groupoid language
- [ ] Galois framing: Document two-factor decomposition
- [ ] Galois framing: Update any dependent calculations or theorems
- [ ] Final review: Verify all cross-references are consistent
