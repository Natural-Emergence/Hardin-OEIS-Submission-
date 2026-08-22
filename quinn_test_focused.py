#!/usr/bin/env python3
"""Quick speedup test at r=0.777 and key points"""

import numpy as np
import time
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Result:
    r: float
    time_us: float
    nodes: int


class KuramotoOscillatorBank:
    def __init__(self, n_oscillators: int = 560, coupling: float = 1.2, seed: int = None):
        if seed is not None:
            np.random.seed(seed)
        self.n = n_oscillators
        self.K = coupling
        self.phases = np.random.uniform(0, 2*np.pi, n_oscillators)
        self.frequencies = 1.0 + np.tan((np.random.uniform(0, 1, n_oscillators) - 0.5) * np.pi / 2.5)
        self.frequencies = np.clip(self.frequencies, 0.1, 2.0)

    def compute_order_parameter(self) -> float:
        complex_avg = np.mean(np.exp(1j * self.phases))
        return np.abs(complex_avg)

    def step(self, dt: float = 0.01) -> float:
        sin_diff = np.sin(self.phases[:, np.newaxis] - self.phases[np.newaxis, :])
        coupling_term = (self.K / self.n) * np.sum(sin_diff, axis=1)
        d_phases = self.frequencies + coupling_term
        self.phases += d_phases * dt
        self.phases = np.mod(self.phases, 2*np.pi)
        return self.compute_order_parameter()

    def maintain_sync(self, steps: int = 10, dt: float = 0.01) -> float:
        for _ in range(steps):
            self.step(dt=dt)
        return self.compute_order_parameter()


class SyncAwareQUINN:
    def __init__(self, oscillators: KuramotoOscillatorBank, depth: int = 35):
        self.oscillators = oscillators
        self.depth = depth
        self.nodes_explored = 0

    def branching_factor(self, current_r: float) -> float:
        if current_r > 0.8:
            return 1.05 + 0.15 * (1 - current_r) / 0.15
        else:
            return 1.5 + (1 - current_r) * 5

    def pruning_threshold(self, current_r: float) -> float:
        return 0.4 + 0.6 * current_r

    def search_3sat(self, num_vars: int, clauses: List[Tuple]) -> bool:
        self.nodes_explored = 0
        best_cost = float('inf')

        for trial in range(min(10000, int(2 ** self.depth))):
            if trial % 50 == 0:
                current_r = self.oscillators.maintain_sync(steps=10)
                threshold = self.pruning_threshold(current_r)

            self.nodes_explored += 1

            assignment = np.random.randint(0, 2, num_vars)

            cost = 0
            for clause in clauses:
                satisfied = False
                for var, negated in clause:
                    val = assignment[var]
                    if negated:
                        val = 1 - val
                    if val == 1:
                        satisfied = True
                        break
                if not satisfied:
                    cost += 1

            if cost < best_cost:
                best_cost = cost
                if cost == 0:
                    return True

            if best_cost < float('inf') and cost > best_cost * threshold:
                continue

        return False


def benchmark_single(r_target: float, trial: int = 0) -> Result:
    """Single benchmark run"""
    # Tune coupling
    if r_target > 0.9:
        K = 1.8
    elif r_target > 0.7:
        K = 1.2
    elif r_target > 0.5:
        K = 0.8
    else:
        K = 0.3

    # Generate problem
    num_vars = 20
    n_clauses = int(4.26 * num_vars)
    clauses = []
    np.random.seed(trial)
    for _ in range(n_clauses):
        clause = tuple((np.random.randint(0, num_vars), np.random.random() > 0.5) for _ in range(3))
        clauses.append(clause)

    # Initialize and pre-sync
    osc = KuramotoOscillatorBank(560, K, seed=trial)
    for _ in range(100):
        osc.maintain_sync(steps=5)

    search = SyncAwareQUINN(osc, depth=35)

    # Benchmark
    t0 = time.perf_counter_ns()
    search.search_3sat(num_vars, clauses)
    t1 = time.perf_counter_ns()

    return Result(r=r_target, time_us=(t1 - t0) / 1000, nodes=search.nodes_explored)


# Test at key r values including 0.777
print("=" * 70)
print("QUINN + Kuramoto - Original Code Speedup Test")
print("=" * 70)

R_TARGETS = [0.10, 0.50, 0.70, 0.777, 0.90, 0.95]

print(f"\n{'r':>7} | {'Time (µs)':>12} | {'Nodes':>6} | Speedup vs r=0.10")
print("-" * 70)

results = {}
for r in R_TARGETS:
    res = benchmark_single(r, trial=0)
    results[r] = res
    print(f"{r:7.3f} | {res.time_us:12.2f} | {res.nodes:6d} |", end=" ")
    if r == 0.10:
        baseline = res.time_us
        print("(baseline)")
    else:
        speedup = baseline / res.time_us
        print(f"{speedup:6.2f}×")

print("\n" + "=" * 70)
print("SPEEDUP SUMMARY (r=0.777 specifically):")
print("=" * 70)
r_777 = results[0.777]
baseline = results[0.10]
speedup_777 = baseline.time_us / r_777.time_us

print(f"r=0.10  (async):  {baseline.time_us:10.2f} µs, {baseline.nodes:5d} nodes")
print(f"r=0.777 (target): {r_777.time_us:10.2f} µs, {r_777.nodes:5d} nodes")
print(f"Speedup: {speedup_777:.2f}×")
