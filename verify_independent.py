#!/usr/bin/env python3
"""
Clean-room replication of the ft10 layer census, a(0)..a(9).

Deliberately independent of ft10_census.py: written from the definition rather
than adapted from it, using full 50-byte state keys with no hashing anywhere,
so a fingerprint collision cannot silently undercount.

    python3 verify_independent.py            # a(0)..a(9), ~1 GB
    python3 verify_independent.py --depth 8  # faster smoke test

Exits nonzero on any mismatch.
"""
import argparse

import numpy as np

from ft10_census import FT10, KNOWN


def census_fullkey(jobs, max_depth):
    """BFS over exact states. Key = 10 progress bytes + 10 jr + 10 mr (uint16)."""
    frontier = {bytes(10) + bytes(20) + bytes(20)}
    counts = [1]
    for _ in range(max_depth):
        nxt = set()
        for s in frontier:
            q = s[:10]
            jr = np.frombuffer(s[10:30], dtype=np.uint16)
            mr = np.frombuffer(s[30:], dtype=np.uint16)
            for j in range(10):
                op = q[j]
                if op >= 10:
                    continue
                m, p = jobs[j][op]
                end = (jr[j] if jr[j] > mr[m] else mr[m]) + p
                nq = bytearray(q)
                nq[j] += 1
                njr = jr.copy(); njr[j] = end
                nmr = mr.copy(); nmr[m] = end
                nxt.add(bytes(nq) + njr.tobytes() + nmr.tobytes())
        counts.append(len(nxt))
        frontier = nxt
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=9)
    args = ap.parse_args()

    got = census_fullkey(FT10, args.depth)

    print(f"{'n':>3} {'this run':>12} {'published':>12}   match")
    print("-" * 46)
    ok = True
    for n, v in enumerate(got):
        if n >= len(KNOWN):
            print(f"{n:>3} {v:>12,} {'-':>12}")
            continue
        same = v == KNOWN[n]
        ok &= same
        print(f"{n:>3} {v:>12,} {KNOWN[n]:>12,}   {'yes' if same else 'NO'}")

    print(f"\na(0)..a({args.depth}) reproduce exactly: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
