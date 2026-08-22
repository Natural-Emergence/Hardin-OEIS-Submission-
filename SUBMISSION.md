# OEIS submission fields

Paste each block into the matching box at <https://oeis.org/submit>.
One bracketed item remains: your OEIS-registered name.

---

## Name

```
Number of distinct states reachable in exactly n operations under earliest-start (semi-active) dispatch of the Fisher-Thompson 10 X 10 job-shop instance ft10.
```

## Data

```
1, 10, 67, 385, 2071, 10769, 54692, 272514, 1332768, 6383587, 29852012
```

## Offset

```
0,2
```

## Comments

```
A state is a triple (q, jr, mr): q[j] is the number of operations of job j already scheduled (0 <= q[j] <= 10), jr[j] is the earliest time job j can resume, and mr[m] is the earliest time machine m is free. The initial state is all zeros.

A move selects any job j with q[j] < 10 and schedules its next operation, in ft10's fixed routing, on its machine m at start time max(jr[j], mr[m]), finishing after ft10's processing time; then q[j], jr[j], mr[m] are updated. Two dispatch prefixes are the same state iff the three vectors agree elementwise.

Every move increases Sum(q) by exactly 1, so the state graph is graded: a reachable state occurs at exactly one depth n = Sum(q), and a(n) is the number of reachable states with Sum(q) = n. Consequently per-layer deduplication suffices; no global visited set is needed.

The values depend on ft10's processing times, not only its machine routings: distinct dispatch orders that produce identical (q, jr, mr) collapse to one state. The two effects differ greatly in size. Holding the routing fixed and replacing every processing time (by all 7s, by powers of 2, or by uniform random values in 1..99) changes a(9) by at most 1.3%, whereas varying the routing across random 10 X 10 instances changes a(9) by a factor of about 17. Most coincidences are therefore permutation-equivalence of operations on disjoint machines, which collapse for any processing times; a small residue are numeric coincidences of particular sums.

The sequence is finite, with 101 terms (n = 0..100). a(100) counts the distinct final ready-time profiles of completed semi-active schedules of ft10.

The number of possible progress vectors q at depth n is the coefficient of x^n in (1 + x + ... + x^10)^10; this count is symmetric about n = 50 and is maximized there, at 1018872811 (total over all n is 11^10 = 25937424601). Since a(n) is this progress-vector count weighted by the timing multiplicity of each q, a(n) is not required to be symmetric about 50, and the location of its maximum is an open question.

Empirically the layer ratio a(n)/a(n-1) decreases from 10. No job can finish before n = 10, and at n = 10 exactly 10 states have a completed job (one per job that ran all ten of its operations consecutively), so throughout the computed range the ratio's decline is driven almost entirely by state coincidence rather than by branch extinction. Over the local range 4 <= n <= 9 the layers admit a fit of the form C*lambda^n*n^theta with lambda about 4.4, against a naive branching of 10; no asymptotic behavior is claimed from so short a range.

a(11) = 135874850 and a(12) = 600240128 have also been computed, by 64-bit fingerprint deduplication; they await collision-free (full-key or 128-bit) certification before being added to the Data line.
```

## Links

```
H. Fisher and G. L. Thompson, Probabilistic learning combinations of local job-shop scheduling rules, in J. F. Muth and G. L. Thompson (eds.), Industrial Scheduling, Prentice-Hall, 1963, pp. 225-251. (Origin of the ft10 instance.)

J. Carlier and E. Pinson, An algorithm for solving the job-shop problem, Management Science 35 (1989), 164-176. (First proof that ft10's optimal makespan is 930.)

J. E. Beasley, OR-Library, job shop scheduling data file jobshop1.txt (instance ft10, a.k.a. mt10).

Author's code repository: https://github.com/Natural-Emergence/Hardin-OEIS-Submission-
```

## Example

```
a(1) = 10: from the empty state each of the 10 jobs can place its first operation; the 10 results differ in q.

a(2) = 67 rather than 100: two different jobs whose first operations use different machines give the same (q, jr, mr) in either order and collapse to one state; only pairs sharing a first machine stay order-sensitive. ft10's first machines are [0,0,1,1,2,2,1,2,0,1], so the shared-first-machine pairs number C(3,2)+C(4,2)+C(3,2) = 12, and a(2) = 45 + 12 + 10 = 67 (45 unordered distinct-job pairs, +12 for the second ordering of shared-machine pairs, +10 for a single job taking its first two operations).
```

## Program

```
(Python) See ft10_census.py in the author's repository for a memory-efficient
version using packed 50-byte keys, which is what actually reaches a(10).
The following is the same algorithm written for legibility.

# ft10 (Fisher-Thompson 10x10, a.k.a. mt10; OR-Library jobshop1.txt).
# FT10[j] = list of 10 (machine, duration) pairs, in routing order, for job j.
FT10 = [
 [(0,29),(1,78),(2,9),(3,36),(4,49),(5,11),(6,62),(7,56),(8,44),(9,21)],
 [(0,43),(2,90),(4,75),(9,11),(3,69),(1,28),(6,46),(5,46),(7,72),(8,30)],
 [(1,91),(0,85),(3,39),(2,74),(8,90),(5,10),(7,12),(6,89),(9,45),(4,33)],
 [(1,81),(2,95),(0,71),(4,99),(6,9),(8,52),(7,85),(3,98),(9,22),(5,43)],
 [(2,14),(0,6),(1,22),(5,61),(3,26),(4,69),(8,21),(7,49),(9,72),(6,53)],
 [(2,84),(1,2),(5,52),(3,95),(8,48),(9,72),(0,47),(6,65),(4,6),(7,25)],
 [(1,46),(0,37),(3,61),(2,13),(6,32),(5,21),(9,32),(8,89),(7,30),(4,55)],
 [(2,31),(0,86),(1,46),(5,74),(3,32),(6,88),(8,19),(9,48),(7,36),(4,79)],
 [(0,76),(1,69),(3,76),(5,51),(2,85),(9,11),(6,40),(7,89),(4,26),(8,74)],
 [(1,85),(0,13),(2,61),(6,7),(8,64),(9,76),(5,47),(3,52),(4,90),(7,45)],
]

start = ((0,)*10, (0,)*10, (0,)*10)   # (q, jr, mr)
layer = {start}
d = 0
while layer and d <= 9:
    print(d, len(layer))
    nxt = set()
    for q, jr, mr in layer:
        for j in range(10):
            if q[j] < 10:
                m, p = FT10[j][q[j]]
                e = max(jr[j], mr[m]) + p
                nxt.add((q[:j] + (q[j]+1,) + q[j+1:],
                         jr[:j] + (e,)   + jr[j+1:],
                         mr[:m] + (e,)   + mr[m+1:]))
    layer = nxt
    d += 1
# Graded by Sum(q): no state recurs at a later depth, so per-layer sets suffice.
# Terms n <= 9 are reproducible on one machine in this representation. a(10)
# needs upward of 20 GB here and about 5 GB with packed fixed-width keys; deeper
# layers need external-memory deduplication and a >= 128-bit state fingerprint
# to keep the count exact.
```

## Keywords

```
nonn, fini, hard, more
```

## Author

```
[FILL] Jeffrey S. Hardin (use the exact name on your OEIS account), Aug 2026
```

---

## Changes from the earlier draft

Three corrections and one addition, all verifiable from the scripts in this
repository.

1. **`n <= 10` → `n <= 9` for branch extinction.** The earlier text said no job
   has finished for n <= 10. A job needs ten operations, so the earliest
   completion is exactly n = 10, where 10 states (one per job) already have a
   finished job. The corrected sentence states this explicitly rather than
   moving the bound.

2. **The `C*lambda^n*n^theta` fit is now marked local.** Six points against
   three parameters, with lambda ~ 4.4 essentially restating the last observed
   ratio. The claim is kept but no asymptotics are asserted, which removes the
   line most likely to draw editorial objection.

3. **Program section memory note corrected.** "Reproducible on one machine" is
   true for n <= 9 in the tuple representation, not n <= 10; a(10) needs
   packed keys. The listing is also depth-bounded so it terminates.

4. **Added: the quantitative routing/duration split** (~1.3% vs ~17x). This
   supports the existing claim that processing times matter while bounding how
   much, and identifies permutation-equivalence as the dominant mechanism. See
   `duration_dependence.py`.
