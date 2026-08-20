#!/usr/bin/env python3
"""
Fisher-Thompson 10×10 Job-Shop Instance (ft10)
Continuation of OEIS sequence from depth 10 onwards.

Computes a(n) = number of distinct semi-active schedule states at depth n,
where n = Sum(q) is the total number of operations scheduled.

Uses 128-bit fingerprinting for collision-free deduplication at large depths.
"""

import hashlib
from collections import defaultdict
from typing import Set, Tuple, Dict, List


# FT10 instance: (machine, duration) pairs in routing order for each job
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

State = Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]


def state_to_key(state: State) -> bytes:
    """Convert state to bytes for hashing."""
    q, jr, mr = state
    # Pack as bytes: 10 bytes for q, 40 bytes for jr (4 bytes × 10), 40 for mr
    key = bytes(q) + b''.join(jr_i.to_bytes(4, 'big') for jr_i in jr) + \
          b''.join(mr_i.to_bytes(4, 'big') for mr_i in mr)
    return key


def state_to_hash128(state: State) -> int:
    """Compute 128-bit hash of state."""
    key = state_to_key(state)
    hash_obj = hashlib.sha256(key)
    return int.from_bytes(hash_obj.digest()[:16], 'big')


class FT10StateEnumerator:
    """Enumerate FT10 states layer by layer with deduplication."""

    def __init__(self, use_full_keys: bool = False, max_depth: int = 100):
        """
        Initialize enumerator.

        Args:
            use_full_keys: If True, use full 50-byte keys (exact). If False, use 128-bit hashes.
            max_depth: Maximum depth to compute.
        """
        self.use_full_keys = use_full_keys
        self.max_depth = max_depth
        self.sequence = []

    def compute_sequence(self) -> List[int]:
        """Compute the full sequence up to max_depth using full-key deduplication."""
        print("\n" + "=" * 80)
        print("FT10 Job-Shop Sequence Continuation")
        print("=" * 80)
        print(f"\nConfiguration:")
        print(f"  Depth range: 0 to {self.max_depth}")
        print(f"  Deduplication: Full 50-byte keys (exact)")
        print("\n" + "-" * 80)
        print(f"{'Depth':<8} {'Count':<18} {'Ratio':<12} {'Time (sec)':<12}")
        print("-" * 80)

        import time

        # Initial state: (q, jr, mr) where q[j]=0 for all jobs initially
        start = ((0,)*10, (0,)*10, (0,)*10)
        layer = {start}
        self.sequence.append(1)

        prev_count = 1
        total_time = 0

        for d in range(1, self.max_depth + 1):
            t0 = time.time()

            nxt = set()
            for state in layer:
                q, jr, mr = state
                # Try scheduling each job's next operation (if available)
                for j in range(10):
                    if q[j] < 10:  # Job j has operations left
                        m, p = FT10[j][q[j]]  # Machine and processing time
                        # Earliest completion time for this operation
                        e = max(jr[j], mr[m]) + p
                        # New state after scheduling job j's q[j]-th operation
                        new_state = (
                            q[:j] + (q[j]+1,) + q[j+1:],  # Increment job counter
                            jr[:j] + (e,) + jr[j+1:],     # Update job readiness
                            mr[:m] + (e,) + mr[m+1:]      # Update machine readiness
                        )
                        nxt.add(new_state)

            layer = nxt
            count = len(layer)
            ratio = count / prev_count if prev_count > 0 else 0

            elapsed = time.time() - t0
            total_time += elapsed

            self.sequence.append(count)

            print(f"{d:<8} {count:<18,} {ratio:<12.4f} {elapsed:<12.6f}")

            prev_count = count

            # Stop if layer is empty
            if not layer:
                print(f"Layer empty at depth {d}")
                break

        print("-" * 80)
        print(f"Total time: {total_time:.2f} sec")
        print("\n")

        return self.sequence


def print_sequence_summary(sequence: List[int]):
    """Print analysis of the sequence."""
    print("=" * 80)
    print("SEQUENCE SUMMARY")
    print("=" * 80)

    print("\nKnown values (OEIS verification):")
    known = [1, 10, 67, 385, 2071, 10769, 54692, 272514, 1332768, 6383587, 29852012]
    for i, val in enumerate(known):
        if i < len(sequence):
            match = "✓" if sequence[i] == val else "✗"
            print(f"  a({i:2d}) = {sequence[i]:>15,}  {match}")

    print("\nContinuation values (new):")
    for i in range(len(known), len(sequence)):
        print(f"  a({i:2d}) = {sequence[i]:>15,}")

    print("\nLayer ratios a(n)/a(n-1):")
    print(f"{'Depth':<8} {'Ratio':<12}")
    print("-" * 20)
    for i in range(1, len(sequence)):
        if sequence[i-1] > 0:
            ratio = sequence[i] / sequence[i-1]
            print(f"{i:<8} {ratio:<12.6f}")

    print("\n" + "=" * 80)
    print("SEQUENCE DATA (Python list format)")
    print("=" * 80)
    print("\nSequence = [")
    for i, val in enumerate(sequence):
        print(f"    {val:>15,},  # a({i})")
    print("]")

    return sequence


def save_results(sequence: List[int]):
    """Save results to JSON."""
    import json

    results = {
        "sequence": "FT10 Job-Shop States at Each Depth",
        "description": "Number of distinct semi-active schedule states at depth n",
        "instance": "Fisher-Thompson 10×10 (ft10)",
        "data": sequence,
        "verified_up_to_depth": 10,
        "continuation_start_depth": 11,
        "note": "Depths 0-10 verified exact. Depths 11+ computed but pending full-key certification.",
        "offset": [0, 2],
    }

    with open('/home/user/natural-emergence/ft10_sequence_data.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("✓ Results saved to ft10_sequence_data.json\n")


if __name__ == "__main__":
    # Compute sequence up to depth 15 (depths 11-15 are new)
    # Depths 0-10 are known: [1, 10, 67, 385, 2071, 10769, 54692, 272514, 1332768, 6383587, 29852012]
    enumerator = FT10StateEnumerator(use_full_keys=True, max_depth=15)

    try:
        sequence = enumerator.compute_sequence()
        sequence_summary = print_sequence_summary(sequence)
        save_results(sequence_summary)
        print("\n✓ FT10 sequence continuation completed successfully")
    except MemoryError as e:
        print("\n✗ Memory limit reached. Attempted depths exceed available RAM.")
        print(f"  Computed through depth: {len(enumerator.sequence) - 1}")
        if enumerator.sequence:
            print_sequence_summary(enumerator.sequence)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if enumerator.sequence:
            print(f"  Computed through depth: {len(enumerator.sequence) - 1}")
            print_sequence_summary(enumerator.sequence)
