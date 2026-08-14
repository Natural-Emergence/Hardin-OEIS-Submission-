# ft10 dispatch-state layer census

Supporting code and verification for an OEIS submission:

> **Number of distinct states reachable in exactly n operations under
> earliest-start (semi-active) dispatch of the Fisher–Thompson 10×10 job-shop
> instance ft10.**

```
1, 10, 67, 385, 2071, 10769, 54692, 272514, 1332768, 6383587, 29852012
```

The full sequence is finite with 101 terms (n = 0..100). Eleven are currently
certified.

## What is being counted

A state is a triple `(q, jr, mr)`:

| | |
|---|---|
| `q[j]` | operations of job *j* already scheduled, 0 ≤ `q[j]` ≤ 10 |
| `jr[j]` | earliest time job *j* can resume |
| `mr[m]` | earliest time machine *m* is free |

The initial state is all zeros. A move selects any job *j* with `q[j] < 10` and
schedules its next operation — in ft10's fixed routing — on machine *m* at start
time `max(jr[j], mr[m])`, finishing after ft10's processing time. Two dispatch
prefixes are the same state iff all three vectors agree elementwise.

`a(n)` counts the distinct states at depth *n*.

## The state graph is graded

Every move increases `sum(q)` by exactly 1, so a reachable state occurs at
exactly one depth, namely `n = sum(q)`. Layers are disjoint by construction.

Two consequences:

- **Per-layer deduplication is sufficient.** No global visited set is needed,
  no candidate-minus-visited phase, no visited-file conversion.
- It is cheap to assert. `ft10_census.py` checks `sum(q) == n` on every
  generated key at every level; the assertion has never fired.

## Verification status

| terms | method | status |
|---|---|---|
| a(0)–a(9) | independent clean-room BFS, full 50-byte keys, no hashing | **reproduced exactly** |
| a(10) | dual-witnessed by two independently seeded fingerprint runs | on the Data line; full-key confirmation outstanding |
| a(11) = 135874850 | 64-bit fingerprint only | **withheld** from the Data line |
| a(12) = 600240128 | 64-bit fingerprint only | **withheld** from the Data line |

A 64-bit fingerprint over ~10⁸ states has a non-negligible birthday collision
probability, and a collision silently *undercounts*. a(11) and a(12) stay off
the Data line until certified with full keys or a ≥128-bit fingerprint.

`a(2) = 67` also passes an independent hand-derivation — see
[SUBMISSION.md](SUBMISSION.md), Example field.

## Reproducing

```bash
python3 ft10_census.py --depth 9     # ~1 GB, under a minute
python3 ft10_census.py --depth 10    # ~5 GB
```

States are packed into fixed-width 50-byte keys rather than tuples of tuples.
This is not cosmetic: at a(10) = 29,852,012 the tuple representation needs
upward of 20 GB, the packed form about 5. Terms beyond a(10) require
external-memory deduplication.

```bash
python3 verify_independent.py        # clean-room replication, a(0)..a(9)
python3 duration_dependence.py       # routing vs. processing times
```

## Structural result: routing dominates, durations perturb

`a(n)` depends on ft10's processing times, not only its machine routings — but
the two contribute on very different scales.

Holding the routing byte-identical and swapping only the durations:

| durations | a(6) | a(7) | a(8) | a(9) |
|---|---|---|---|---|
| ft10 actual | 54,692 | 272,514 | 1,332,768 | 6,383,587 |
| all 7 | 54,672 | 271,985 | 1,325,216 | 6,303,872 |
| powers of 2 | 54,606 | 271,388 | 1,321,877 | 6,297,953 |
| random 1..99 | 54,612 | 271,943 | 1,329,768 | 6,371,079 |

**~1.3%.** By contrast, changing the *routing* moves a(9) by a factor of ~17
across random 10×10 instances. So the collision structure is roughly:

- **~99% permutation-equivalence** — two orderings of operations on disjoint
  machines produce identical `(q, jr, mr)` for *any* durations, and collapse.
- **~1% numeric coincidence** — orderings that agree only because particular
  processing times happen to sum equally.

Consistent with this, `all 7` yields the *fewest* states: equal processing
times make same-machine pairs collapse as well, since a-then-b and b-then-a
then produce identical `jr`. The `a(2) = 67` derivation is the visible base
case — it is purely combinatorial in the first-machine multiset and no
duration appears in it.

## Open question

The number of progress vectors `q` at depth *n* is `[x^n] (1 + x + ... + x^10)^10`.
That count is exactly symmetric about n = 50 — the map `q_j ↦ 10 − q_j` sends
`n ↦ 100 − n` — and is maximized there at **1,018,872,811**, with total
`11^10 = 25,937,424,601`.

`a(n)` is that count weighted by the timing multiplicity of each `q`. Whether
the multiplicity factor is also symmetric about 50, and hence where `a(n)`
attains its maximum, is open.

## Instance

ft10 (a.k.a. mt10), Fisher & Thompson 1963; OR-Library `jobshop1.txt`. Optimal
makespan 930, first proved by Carlier & Pinson (1989). Full references in
[SUBMISSION.md](SUBMISSION.md).
