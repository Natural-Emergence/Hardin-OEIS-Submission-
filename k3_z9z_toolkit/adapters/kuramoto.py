"""
Kuramoto Synchronization as K₃ × Z/9Z System

Adapts the Kuramoto phase synchronization model to the universal topology.

K₃ Operations:
  1. Phase threading: oscillate phases with natural frequencies + coupling
  2. Memory geometry: compute order parameter and curvature
  3. Entropy checkpointing: measure path entropy and information flow

Z/9Z Structure:
  - 9-dimensional state space implicit in coupled dynamics
  - κ × C × E = coupling × curvature × entropy

Z₃ Phases:
  - Exploration: low coupling, high phase variance
  - Transition: adaptive coupling, critical threshold crossing
  - Precision: high coupling, locked phases
"""

import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass

from k3_z9z_toolkit.core.topology import K3Z9ZBlueprint, K3Z9ZSystem, HarmonicConstants


@dataclass
class KuramotoState:
    """State of N oscillators with phases and coupling"""
    phases: np.ndarray          # [N] oscillator phases
    frequencies: np.ndarray    # [N] natural frequencies
    coupling: float             # Global coupling strength κ
    time: float = 0.0          # Simulation time


class KuramotoSystemAdapter(K3Z9ZBlueprint):
    """Kuramoto synchronization implemented as K₃ × Z/9Z"""

    def __init__(self, N: int = 128, freq_width: float = 0.02):
        """
        Args:
            N: Number of oscillators
            freq_width: Width of natural frequency distribution (σ)
        """
        self.N = N
        self.freq_width = freq_width
        self.domain_name = "kuramoto_synchronization"

        # Natural frequencies: Lorentzian distribution
        gamma = 1.0
        self.base_frequencies = gamma * np.tan((np.random.rand(N) - 0.5) * np.pi)
        self.base_frequencies = np.clip(self.base_frequencies, -5, 5)

        # Small Gaussian variation
        self.base_frequencies += np.random.randn(N) * freq_width

    def init_state(self) -> KuramotoState:
        """Initialize with random phases and low coupling"""
        return KuramotoState(
            phases=np.random.rand(self.N) * 2 * np.pi,
            frequencies=self.base_frequencies.copy(),
            coupling=0.15
        )

    def operation_1(self, state: KuramotoState) -> np.ndarray:
        """
        Phase threading: advance phases with natural frequencies + mutual coupling

        Returns: updated phases [N]
        """
        dt = 0.01
        mean_phase = np.mean(np.exp(1j * state.phases))
        order_param = np.abs(mean_phase)

        # Kuramoto equation: dθ/dt = ω + κ*sin(θ_mean - θ)
        phase_diff = np.angle(mean_phase) - state.phases
        dphases = state.frequencies + state.coupling * np.sin(phase_diff)

        new_phases = state.phases + dt * dphases
        return new_phases % (2 * np.pi)

    def operation_2(self, state: KuramotoState, r1: np.ndarray) -> Tuple[float, float]:
        """
        Memory geometry: compute order parameter (coherence) and curvature

        Args:
            state: Current KuramotoState
            r1: Updated phases from operation_1

        Returns: (order_parameter, curvature)
        """
        # Order parameter: r = |mean(exp(iθ))|
        mean_exp = np.mean(np.exp(1j * r1))
        order_param = np.abs(mean_exp)

        # Curvature: rate of change in coherence
        if hasattr(self, '_prev_order'):
            curvature = order_param - self._prev_order
        else:
            curvature = 0.0
        self._prev_order = order_param

        return order_param, curvature

    def operation_3(self, state: KuramotoState, r1: np.ndarray, r2: Tuple) -> KuramotoState:
        """
        Entropy checkpointing: update coupling based on synchronization feedback

        Args:
            state: Original state
            r1: Updated phases from operation_1
            r2: (order_param, curvature) from operation_2

        Returns: Updated KuramotoState
        """
        order_param, curvature = r2

        # Adaptive coupling: increase κ as system desynchronizes
        target_r = 0.85  # Critical threshold
        if order_param < target_r:
            state.coupling += 0.02 * (1 - order_param)
        else:
            state.coupling *= 0.98  # Gentle decay when synchronized

        state.coupling = np.clip(state.coupling, 0.0, 2.0)

        # Update state
        state.phases = r1
        state.time += 0.01

        return state

    def control_metric(self, state: KuramotoState) -> float:
        """
        Measure: order parameter (synchronization level)

        Returns: r in [0, 1]
        """
        mean_exp = np.mean(np.exp(1j * state.phases))
        return np.abs(mean_exp)

    def validate(self, state: KuramotoState, expected_r: float = 0.85) -> Dict[str, float]:
        """
        Compare achieved order parameter against target

        Returns:
            {
                'order_parameter': measured r,
                'error': |measured - expected|,
                'phase_variance': variance of phases,
                'coherence': 1 - variance
            }
        """
        mean_exp = np.mean(np.exp(1j * state.phases))
        order_param = np.abs(mean_exp)

        # Phase variance
        phase_var = np.var(state.phases)

        return {
            'order_parameter': float(order_param),
            'error': float(abs(order_param - expected_r)),
            'phase_variance': float(phase_var),
            'coherence': float(1.0 - phase_var / (np.pi**2)),
            'coupling': float(state.coupling)
        }


def test_kuramoto():
    """Test Kuramoto adapter against known synchronization behavior"""
    print("=" * 70)
    print("Testing Kuramoto Synchronization as K₃ × Z/9Z")
    print("=" * 70)

    # Build system
    adapter = KuramotoSystemAdapter(N=128, freq_width=0.02)
    system = adapter.build_system(threshold=0.85)

    # Initialize
    state = adapter.init_state()
    print(f"\nInitial state:")
    print(f"  Order parameter: {adapter.control_metric(state):.4f}")
    print(f"  Coupling: {state.coupling:.4f}")

    # Run simulation
    print(f"\nRunning 500 iterations...")
    state, history = system.run(state, 500)

    # Analyze results
    controls = [h['control'] for h in history]
    print(f"\nFinal state:")
    print(f"  Order parameter: {controls[-1]:.4f}")
    print(f"  Coupling: {state.coupling:.4f}")
    print(f"  Convergence rate (r ≥ 0.85): {system.convergence_rate():.2%}")
    print(f"  Synchronization index: {system.synchronization_index():.4f}")
    print(f"  Threshold crossings: {system.metrics.threshold_crossings}")

    # Validation
    val = adapter.validate(state, expected_r=0.85)
    print(f"\nValidation:")
    for k, v in val.items():
        print(f"  {k}: {v:.4f}")

    # Phase distribution
    phases_final = state.phases
    print(f"\nPhase statistics:")
    print(f"  Mean: {np.mean(phases_final):.4f}")
    print(f"  Std:  {np.std(phases_final):.4f}")
    print(f"  Min:  {np.min(phases_final):.4f}")
    print(f"  Max:  {np.max(phases_final):.4f}")

    print("\n✓ Test complete\n")

    return system, state, history


if __name__ == "__main__":
    test_kuramoto()
