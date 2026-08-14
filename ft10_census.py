#!/usr/bin/env python3
"""
Reference implementation: dispatch-state layer census for a job-shop instance.

Counts a(n), the number of distinct states reachable in exactly n operations
under earliest-start (semi-active) dispatch. Default instance is ft10
(Fisher-Thompson 10x10, a.k.a. mt10; OR-Library jobshop1.txt).

A state is a triple (q, jr, mr):
    q[j]   operations of job j already scheduled, 0 <= q[j] <= ops
    jr[j]  earliest time job j can resume
    mr[m]  earliest time machine m is free

A move picks any job j with q[j] < ops and schedules its next operation on its
routed machine m at time max(jr[j], mr[m]).

Every move increases sum(q) by exactly 1, so the state graph is GRADED: a
reachable state occurs at exactly one depth. Per-layer deduplication is
therefore sufficient and no global visited set is required. The script asserts
this invariant on every generated key.

States are packed into fixed-width bytes (10 + 20 + 20 = 50 for ft10) rather
than Python tuples. This matters: at a(10) = 29,852,012 the tuple-of-tuples
representation needs upward of 20 GB, the packed form about 5 GB.

    python3 ft10_census.py --depth 9      # ~1 GB, under a minute
    python3 ft10_census.py --depth 10     # ~5 GB

Terms beyond a(10) need external-memory deduplication; see README.
"""
import argparse
import sys
import time

import numpy as np

# ft10 / mt10: FT10[j] = [(machine, duration), ...] in routing order for job j
FT10 = [
    [(0, 29), (1, 78), (2,  9), (3, 36), (4, 49), (5, 11), (6, 62), (7, 56), (8, 44), (9, 21)],
    [(0, 43), (2, 90), (4, 75), (9, 11), (3, 69), (1, 28), (6, 46), (5, 46), (7, 72), (8, 30)],
    [(1, 91), (0, 85), (3, 39), (2, 74), (8, 90), (5, 10), (7, 12), (6, 89), (9, 45), (4, 33)],
    [(1, 81), (2, 95), (0, 71), (4, 99), (6,  9), (8, 52), (7, 85), (3, 98), (9, 22), (5, 43)],
    [(2, 14), (0,  6), (1, 22), (5, 61), (3, 26), (4, 69), (8, 21), (7, 49), (9, 72), (6, 53)],
    [(2, 84), (1,  2), (5, 52), (3, 95), (8, 48), (9, 72), (0, 47), (6, 65), (4,  6), (7, 25)],
    [(1, 46), (0, 37), (3, 61), (2, 13), (6, 32), (5, 21), (9, 32), (8, 89), (7, 30), (4, 55)],
    [(2, 31), (0, 86), (1, 46), (5, 74), (3, 32), (6, 88), (8, 19), (9, 48), (7, 36), (4, 79)],
    [(0, 76), (1, 69), (3, 76), (5, 51), (2, 85), (9, 11), (6, 40), (7, 89), (4, 26), (8, 74)],
    [(1, 85), (0, 13), (2, 61), (6,  7), (8, 64), (9, 76), (5, 47), (3, 52), (4, 90), (7, 45)],
]

KNOWN = [1, 10, 67, 385, 2071, 10769, 54692, 272514, 1332768, 6383587, 29852012]


def census(jobs, max_depth, check_invariant=True, verbose=True):
    """Return [a(0), a(1), ..., a(max_depth)]."""
    J = len(jobs)
    M = 1 + max(m for job in jobs for m, _ in job)
    ops = len(jobs[0])
    assert all(len(job) == ops for job in jobs), "ragged routing not supported"

    # key layout: J progress bytes | J job-ready uint16 | M machine-ready uint16
    jr_off, mr_off = J, J + 2 * J
    frontier = {bytes(J) + bytes(2 * J) + bytes(2 * M)}
    counts = [1]

    for depth in range(max_depth):
        t0 = time.perf_counter()
        nxt = set()
        add = nxt.add
        for s in frontier:
            q = s[:jr_off]
            jr = np.frombuffer(s[jr_off:mr_off], dtype=np.uint16)
            mr = np.frombuffer(s[mr_off:], dtype=np.uint16)
            for j in range(J):
                op = q[j]
                if op >= ops:
                    continue
                m, p = jobs[j][op]
                end = (jr[j] if jr[j] > mr[m] else mr[m]) + p
                nq = bytearray(q)
                nq[j] += 1
                njr = jr.copy(); njr[j] = end
                nmr = mr.copy(); nmr[m] = end
                add(bytes(nq) + njr.tobytes() + nmr.tobytes())

        if check_invariant:
            bad = next((k for k in nxt if sum(k[:jr_off]) != depth + 1), None)
            assert bad is None, f"graded-graph invariant violated at depth {depth+1}"

        counts.append(len(nxt))
        frontier = nxt
        if verbose:
            print(f"a({depth+1}) = {len(nxt):>12,}   "
                  f"[{time.perf_counter()-t0:6.1f}s]", file=sys.stderr)

    return counts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--depth", type=int, default=9,
                    help="maximum n to compute (default 9; 10 needs ~5 GB)")
    ap.add_argument("--no-check", action="store_true",
                    help="skip the graded-graph invariant assertion")
    args = ap.parse_args()

    counts = census(FT10, args.depth, check_invariant=not args.no_check)

    print("\nn    a(n)")
    ok = True
    for n, v in enumerate(counts):
        mark = ""
        if n < len(KNOWN):
            same = v == KNOWN[n]
            ok &= same
            mark = "  ok" if same else f"  MISMATCH (expected {KNOWN[n]:,})"
        print(f"{n:<4} {v:>12,}{mark}")

    print("\n" + ", ".join(str(v) for v in counts))
    if args.depth < len(KNOWN):
        print(f"\nmatches published terms through a({args.depth}): {ok}")


if __name__ == "__main__":
    main()
