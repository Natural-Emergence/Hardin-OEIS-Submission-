#!/usr/bin/env python3
"""
Does a(n) depend on ft10's PROCESSING TIMES, or only on its ROUTING?

Both, but on very different scales. This script holds ft10's machine routing
byte-for-byte identical and replaces every processing time, then reports the
resulting layer counts.

Result (see README): swapping all durations moves a(9) by at most ~1.3%,
while changing the routing across random 10x10 instances moves it by a factor
of ~17. So most state coincidences are permutation-equivalence -- two orderings
of operations on disjoint machines yield identical (q, jr, mr) for ANY
durations -- and only a small residue are numeric coincidences of sums.

Note that "all 7" gives the FEWEST states. Equal processing times make
same-machine pairs collapse as well: a-then-b and b-then-a leave identical jr
when p_a == p_b, whereas with distinct durations they stay separate. This is
the same mechanism visible in the a(2) = 67 hand-derivation.

    python3 duration_dependence.py
"""
import argparse

import numpy as np

from ft10_census import FT10, census

MODES = ("all 7", "powers of 2", "random 1..99")


def swap_durations(jobs, mode, seed=0):
    """Keep every (machine) routing entry; replace every duration."""
    rng = np.random.default_rng(seed)
    out = []
    for j, job in enumerate(jobs):
        row = []
        for k, (m, _p) in enumerate(job):
            if mode == "all 7":
                d = 7
            elif mode == "powers of 2":
                d = int(1 << ((j + k) % 10))
            elif mode == "random 1..99":
                d = int(rng.integers(1, 100))
            else:
                raise ValueError(mode)
            row.append((m, d))
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=9)
    ap.add_argument("--from-n", type=int, default=6,
                    help="first layer to display (default 6)")
    args = ap.parse_args()

    base = census(FT10, args.depth, verbose=False)
    lo = args.from_n

    header = " ".join(f"{'a(%d)' % n:>11}" for n in range(lo, args.depth + 1))
    print(f"{'durations':<16} {header}   {'vs ft10':>9}")
    print("-" * (18 + 12 * (args.depth - lo + 1) + 12))
    print(f"{'ft10 actual':<16} " + " ".join(f"{v:>11,}" for v in base[lo:]) +
          f"   {'--':>9}")

    for mode in MODES:
        got = census(swap_durations(FT10, mode), args.depth, verbose=False)
        delta = (got[-1] - base[-1]) / base[-1]
        print(f"{mode:<16} " + " ".join(f"{v:>11,}" for v in got[lo:]) +
              f"   {delta:>+8.2%}")

    print("\nRouting fixed throughout; only processing times differ.")


if __name__ == "__main__":
    main()
