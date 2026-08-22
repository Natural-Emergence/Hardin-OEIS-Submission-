#!/usr/bin/env python3
"""
QUINN + Kuramoto Benchmark - Optimized Version
Faster iteration with focused testing of sync-speedup hypothesis.
"""

import numpy as np
import time
from typing import List, Tuple
import json


class KuramotoOscillatorBank:
    """Optimized Kuramoto oscillators for search modulation"""

    def __init__(self, n_oscillators: int = 560, coupling: float = 1.2,
                 target_r: float = 0.95, seed: int = None):
        if seed is not None:
            np.random.seed(seed)
        self.n = n_oscillators
        self.K = coupling
        self.target_r = target_r
        self.phases = np.random.uniform(0, 2*np.pi, n_oscillators)
        self.frequencies = 1.0 + 0.3 * np.random.randn(n_oscillators)
        self.frequencies = np.clip(self.frequencies, 0.1, 2.0)
        self.coupling_energy = 0.0

    def compute_order_parameter(self) -> float:
        """Fast order parameter computation"""
        complex_avg = np.mean(np.exp(1j * self.phases))
        return np.abs(complex_avg)

    def step(self, dt: float = 0.01) -> float:
        """Optimized single step"""
        r = self.compute_order_parameter()

        # Vectorized coupling
        phase_diff = self.phases[:, np.newaxis] - self.phases[np.newaxis, :]
        coupling_term = (self.K / self.n) * np.sum(np.sin(phase_diff), axis=1)

        # Update
        d_phases = self.frequencies + coupling_term
        self.phases += d_phases * dt
        self.phases = np.mod(self.phases, 2*np.pi)

        self.coupling_energy = -self.K * r ** 2 / 2
        return r

    def maintain_sync(self, steps: int = 5, dt: float = 0.01) -> float:
        """Quick sync maintenance"""
        for _ in range(steps):
            self.step(dt=dt)
        return self.compute_order_parameter()


class FastQUINN:
    """Simplified QUINN search for benchmarking"""

    def __init__(self, oscillators: KuramotoOscillatorBank, depth: int = 30):
        self.osc = oscillators
        self.depth = depth
        self.nodes_explored = 0
        self.best_cost = float('inf')

    def branching_factor(self, r: float) -> float:
        """Modulate branching by sync level"""
        return 1.0 + 2.5 * (1.0 - r)

    def search(self, num_vars: int, clauses: List[Tuple]) -> bool:
        """Faster 3-SAT search with adaptive pruning"""
        self.nodes_explored = 0
        self.best_cost = float('inf')

        max_iterations = min(5000, int(2 ** min(self.depth / 2, 12)))

        for trial in range(max_iterations):
            if trial % 100 == 0:
                self.osc.maintain_sync(steps=3)

            self.nodes_explored += 1

            # Random assignment
            assignment = np.random.randint(0, 2, num_vars)

            # Evaluate
            cost = sum(1 for clause in clauses
                      if not any((assignment[v] ^ neg) for v, neg in clause))

            if cost < self.best_cost:
                self.best_cost = cost
                if cost == 0:
                    return True

            # Adaptive pruning
            if self.best_cost < float('inf'):
                threshold = 0.4 + 0.6 * self.osc.compute_order_parameter()
                if cost > self.best_cost * threshold:
                    continue

        return self.best_cost == 0


def benchmark_fast(r_targets: List[float], trials: int = 3) -> dict:
    """Fast benchmark focusing on sync effect"""
    results = {}

    for r_target in r_targets:
        # Coupling tuning
        K = 2.0 if r_target > 0.9 else (1.2 if r_target > 0.7 else 0.4)

        times = []
        nodes_list = []
        successes = 0

        for trial in range(trials):
            # Generate 3-SAT instance
            num_vars = 15
            n_clauses = int(4.26 * num_vars)
            clauses = []
            for _ in range(n_clauses):
                clause = tuple((np.random.randint(0, num_vars),
                               np.random.random() > 0.5) for _ in range(3))
                clauses.append(clause)

            # Initialize and pre-sync
            osc = KuramotoOscillatorBank(560, K, r_target, seed=trial)
            for _ in range(20):
                osc.maintain_sync(steps=3)

            # Benchmark
            search = FastQUINN(osc, depth=30)

            t0 = time.perf_counter_ns()
            found = search.search(num_vars, clauses)
            t1 = time.perf_counter_ns()

            time_us = (t1 - t0) / 1000
            times.append(time_us)
            nodes_list.append(search.nodes_explored)
            if found:
                successes += 1

        results[r_target] = {
            "time_us": float(np.mean(times)),
            "time_std": float(np.std(times)),
            "nodes": int(np.mean(nodes_list)),
            "success_rate": successes / trials
        }

    return results


if __name__ == '__main__':
    print("=" * 70)
    print("QUINN + Kuramoto Benchmark (Optimized)")
    print("=" * 70)

    R_TARGETS = [0.10, 0.30, 0.50, 0.70, 0.90, 0.95]

    print("\nBenchmarking with 3 trials per r-value...\n")
    results = benchmark_fast(R_TARGETS, trials=3)

    print("Results:")
    print("-" * 70)
    print(f"{'r':>6} | {'Time (µs)':>12} | {'Nodes':>8} | {'Success':>8}")
    print("-" * 70)

    for r in R_TARGETS:
        res = results[r]
        print(f"{r:6.2f} | {res['time_us']:12.2f} | {res['nodes']:8d} | {res['success_rate']:8.1%}")

    # Speedup analysis
    print("\n" + "=" * 70)
    print("SPEEDUP ANALYSIS")
    print("=" * 70)

    baseline = results[0.10]["time_us"]
    print(f"\nBaseline (r=0.10): {baseline:.2f} µs\n")

    for r in R_TARGETS:
        speedup = baseline / results[r]["time_us"]
        print(f"  r={r:.2f}: {results[r]['time_us']:8.2f} µs → {speedup:5.2f}× speedup")

    # Peak efficiency
    peak_r = max(R_TARGETS, key=lambda r: results[0.10]["time_us"] / results[r]["time_us"])
    peak_speedup = results[0.10]["time_us"] / results[peak_r]["time_us"]

    print("\n" + "=" * 70)
    print(f"Peak speedup: {peak_speedup:.2f}× at r={peak_r:.2f}")
    print("=" * 70)

    # Save
    output = {
        "benchmark": "QUINN-Kuramoto Optimized",
        "configuration": {"n_oscillators": 560, "r_targets": R_TARGETS},
        "results": {str(r): results[r] for r in R_TARGETS},
        "summary": {
            "baseline_r": 0.10,
            "peak_speedup": float(peak_speedup),
            "peak_r": float(peak_r)
        }
    }

    with open('quinn_kuramoto_optimized_results.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("\n✓ Results saved to quinn_kuramoto_optimized_results.json")
