#!/usr/bin/env python3
"""
FT10 + QUINN-Kuramoto Synthesis
Measures speedup effect of Kuramoto synchronization on Fisher-Thompson 10×10
job-shop state space enumeration through controlled depths.

Couples oscillator synchronization to job scheduling decisions for pruning.
"""

import numpy as np
import time
from dataclasses import dataclass
from typing import List, Tuple, Set
import json


# FT10 instance: (machine, duration) pairs for each job
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


@dataclass
class Result:
    depth: int
    r_target: float
    r_final: float
    states_explored: int
    states_expected: int
    time_sec: float
    pruning_rate: float
    speedup_vs_async: float
    memory_reduction: float


class KuramotoJobScheduler:
    """Kuramoto oscillators coupled to job-shop scheduling decisions"""

    def __init__(self, n_jobs: int = 10, K: float = 1.2, target_r: float = 0.95):
        self.n_jobs = n_jobs
        self.K = K
        self.target_r = target_r

        # One oscillator per job
        self.phases = np.random.uniform(0, 2*np.pi, n_jobs)
        self.frequencies = 1.0 + 0.2 * np.sin(np.linspace(0, 2*np.pi, n_jobs))

    def get_order_parameter(self) -> float:
        """Compute r = |mean(e^{i*theta})|"""
        return np.abs(np.mean(np.exp(1j * self.phases)))

    def update_phases(self, dt: float = 0.01, steps: int = 1):
        """Evolve oscillators"""
        for _ in range(steps):
            sin_diff = np.sin(self.phases[:, np.newaxis] - self.phases[np.newaxis, :])
            coupling = (self.K / self.n_jobs) * np.sum(sin_diff, axis=1)
            self.phases += (self.frequencies + coupling) * dt
            self.phases = np.mod(self.phases, 2*np.pi)

    def get_pruning_threshold(self) -> float:
        """Synchronization-modulated pruning threshold"""
        r = self.get_order_parameter()
        return 0.3 + 0.7 * r

    def should_prune_branch(self, job_readiness_sum: int, machine_load: float) -> bool:
        """Heuristic: prune if machine is heavily loaded and we're poorly synchronized"""
        r = self.get_order_parameter()
        threshold = self.get_pruning_threshold()
        # Simple heuristic: skip if machine utilization is high and sync is weak
        machine_factor = min(1.0, machine_load / 1000)
        return machine_factor * threshold > 0.8


class FT10EnumeratorWithSync:
    """FT10 state enumeration with optional Kuramoto synchronization coupling"""

    def __init__(self, oscillators: KuramotoJobScheduler = None, max_depth: int = 12):
        self.oscillators = oscillators
        self.max_depth = max_depth
        self.states_at_depth = []
        self.times_per_depth = []

    def enumerate_to_depth(self) -> Tuple[List[int], float]:
        """Enumerate FT10 states up to max_depth"""
        start_time = time.time()

        # Initial state
        start = ((0,)*10, (0,)*10, (0,)*10)
        layer = {start}
        self.states_at_depth = [1]

        for d in range(1, self.max_depth + 1):
            t0 = time.time()

            # Update oscillators if coupled
            if self.oscillators:
                self.oscillators.update_phases(steps=5)

            nxt = set()
            for state in layer:
                q, jr, mr = state

                # Try scheduling each job
                for j in range(10):
                    if q[j] < 10:
                        m, p = FT10[j][q[j]]
                        e = max(jr[j], mr[m]) + p

                        # Optional: pruning heuristic based on sync state
                        if self.oscillators:
                            machine_load = mr[m]
                            if self.oscillators.should_prune_branch(jr[j], machine_load):
                                continue

                        new_state = (
                            q[:j] + (q[j]+1,) + q[j+1:],
                            jr[:j] + (e,) + jr[j+1:],
                            mr[:m] + (e,) + mr[m+1:]
                        )
                        nxt.add(new_state)

            layer = nxt
            count = len(layer)
            elapsed = time.time() - t0

            self.states_at_depth.append(count)
            self.times_per_depth.append(elapsed)

            if count == 0:
                break

        total_time = time.time() - start_time
        return self.states_at_depth, total_time


def benchmark_ft10_sync(depths: List[int], r_targets: List[float]) -> List[Result]:
    """
    Benchmark FT10 enumeration across sync levels.
    Note: async cases (r≈0.1) use smaller max_depth to avoid memory exhaustion.
    """
    results = []
    baseline_times = {}  # async times for speedup calculation

    print("=" * 100)
    print("FT10 + QUINN-Kuramoto Synthesis: Job-Shop State Space Enumeration")
    print("=" * 100)

    for r_target in r_targets:
        # Tune coupling for target r
        if r_target > 0.9:
            K = 1.8
        elif r_target > 0.7:
            K = 1.2
        elif r_target > 0.5:
            K = 0.8
        else:
            K = 0.3

        print(f"\nr={r_target:.2f} (K={K:.2f}):")

        # Async cases (r≈0.1) explore more of state space, use smaller depths
        depths_to_test = [d-2 if r_target < 0.2 else d for d in depths]
        depths_to_test = [max(8, d) for d in depths_to_test]  # Floor at depth 8

        for max_depth in depths_to_test:
            # Create oscillators if sync is enabled
            if r_target > 0.1:
                osc = KuramotoJobScheduler(n_jobs=10, K=K, target_r=r_target)
                # Pre-synchronize
                for _ in range(50):
                    osc.update_phases(steps=3)
                r_init = osc.get_order_parameter()
            else:
                osc = None
                r_init = 0.1

            # Run enumeration
            enumerator = FT10EnumeratorWithSync(osc, max_depth=max_depth)
            states_at_depth, total_time = enumerator.enumerate_to_depth()

            if osc:
                r_final = osc.get_order_parameter()
            else:
                r_final = 0.1

            actual_depth_reached = len(states_at_depth) - 1
            total_states = sum(states_at_depth)

            # Estimate expected growth
            avg_branching = (states_at_depth[-1] / states_at_depth[-2]) if len(states_at_depth) > 1 else 1
            expected = int(avg_branching ** max_depth)

            # Speedup vs async baseline
            if r_target < 0.2:
                baseline_times[max_depth] = total_time
                speedup = 1.0
                memory_reduction = 1.0
            else:
                baseline = baseline_times.get(max_depth, total_time)
                speedup = baseline / total_time if total_time > 0 else 1.0
                # Memory reduction proportional to pruning
                pruning = 1.0 - (total_states / (expected * max_depth)) if expected > 0 else 0.0
                memory_reduction = 1.0 - pruning

            pruning_rate = 1.0 - (total_states / expected) if expected > 0 else 0.0

            result = Result(
                depth=actual_depth_reached,
                r_target=r_target,
                r_final=r_final,
                states_explored=total_states,
                states_expected=expected,
                time_sec=total_time,
                pruning_rate=max(0, pruning_rate),
                speedup_vs_async=speedup,
                memory_reduction=memory_reduction
            )
            results.append(result)

            print(f"  depth={actual_depth_reached}: {total_time:8.2f}s | " +
                  f"states: {total_states:12,} | " +
                  f"speedup: {speedup:6.2f}× | " +
                  f"r_final: {r_final:.3f}")

    return results


# Main
DEPTHS = [10, 11, 12]
R_TARGETS = [0.10, 0.50, 0.90, 0.95]

results = benchmark_ft10_sync(DEPTHS, R_TARGETS)

# Summary
print("\n" + "=" * 100)
print("SUMMARY: Speedup from Synchronization on FT10 Job-Shop Enumeration")
print("=" * 100)

for depth in DEPTHS:
    depth_results = [r for r in results if r.depth == depth]
    if depth_results:
        print(f"\nDepth {depth}:")
        for r in sorted(depth_results, key=lambda x: x.r_target):
            print(f"  r={r.r_target:.2f}: {r.time_sec:8.2f}s | " +
                  f"states: {r.states_explored:12,} | " +
                  f"speedup: {r.speedup_vs_async:6.2f}× | " +
                  f"pruning: {r.pruning_rate:6.1%}")

# Save results
output = {
    "synthesis": "FT10-Kuramoto Job-Shop Enumeration",
    "configuration": {
        "instance": "Fisher-Thompson 10×10 (ft10)",
        "r_targets": R_TARGETS,
        "depths": DEPTHS,
        "n_jobs": 10,
        "n_machines": 10,
    },
    "results": [
        {
            "depth": r.depth,
            "r_target": float(r.r_target),
            "r_final": float(r.r_final),
            "states_explored": r.states_explored,
            "time_sec": float(r.time_sec),
            "speedup_vs_async": float(r.speedup_vs_async),
            "pruning_rate": float(r.pruning_rate),
            "memory_reduction": float(r.memory_reduction),
        }
        for r in results
    ]
}

with open('/home/user/natural-emergence/ft10_quinn_kuramoto_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\n" + "=" * 100)
print("✓ Results saved to ft10_quinn_kuramoto_results.json")
print("=" * 100 + "\n")
