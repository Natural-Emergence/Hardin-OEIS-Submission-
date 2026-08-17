"""
QUINN Optimizer as K₃ × Z/9Z System

Adapts QUINN (spectral filtering + geodesic correction) to universal topology.

K₃ Operations:
  1. Spectral filter: extract top-k frequency components (exploration)
  2. Sync score: measure coherence across orthants (evaluation)
  3. Geodesic correction: apply phase-modulated update (refinement)

Z/9Z Structure:
  - 9-step phase cycle explicit
  - s* = 7/9 universal threshold
  - Top 2/9 frequency modes selected

Z₃ Phases:
  - Exploration: high learning rate, broad exploration
  - Transition: balanced updates
  - Precision: refined, phase-modulated steps
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass

from k3_z9z_toolkit.core.topology import K3Z9ZBlueprint, K3Z9ZSystem


@dataclass
class QUINNState:
    """State of QUINN optimization: parameters + gradient history"""
    params: np.ndarray              # [D] parameter vector
    grad_history: List[np.ndarray]  # Past gradients for filtering
    best_params: np.ndarray = None  # Best found so far
    best_loss: float = float('inf') # Best loss found


class QUINNSystemAdapter(K3Z9ZBlueprint):
    """QUINN optimizer as K₃ × Z/9Z"""

    def __init__(self, D: int = 64, problem: str = "quadratic"):
        """
        Args:
            D: Dimensionality
            problem: "quadratic", "ill_conditioned", or "noisy"
        """
        self.D = D
        self.problem = problem
        self.domain_name = f"quinn_optimization_{problem}"

        # Define problem
        if problem == "quadratic":
            self.A = np.eye(D)
            self.b = np.ones(D)
        elif problem == "ill_conditioned":
            # Ill-conditioned: condition number ~100
            evals = np.logspace(0, 2, D)
            Q = np.random.randn(D, D)
            Q, _ = np.linalg.qr(Q)
            self.A = Q @ np.diag(evals) @ Q.T
            self.b = np.ones(D)
        elif problem == "noisy":
            self.A = np.eye(D)
            self.b = np.ones(D)
        else:
            raise ValueError(f"Unknown problem: {problem}")

        self.step_count = 0

    def compute_gradient(self, params: np.ndarray) -> np.ndarray:
        """Compute gradient of quadratic loss: ∇f = A @ params - b"""
        grad = self.A @ params - self.b
        if self.problem == "noisy":
            grad += np.random.randn(self.D) * 0.1 * np.linalg.norm(grad)
        return grad

    def compute_loss(self, params: np.ndarray) -> float:
        """Loss: ||A @ params - b||²"""
        residual = self.A @ params - self.b
        return float(np.sum(residual**2))

    def init_state(self) -> QUINNState:
        """Initialize with random parameters"""
        params = np.random.randn(self.D) * 0.1
        state = QUINNState(
            params=params.copy(),
            grad_history=[self.compute_gradient(params)],
            best_params=params.copy(),
            best_loss=self.compute_loss(params)
        )
        return state

    def operation_1(self, state: QUINNState) -> np.ndarray:
        """
        Spectral filter: FFT of gradient history, keep top 2/9 frequencies

        Returns: filtered gradient
        """
        # Compute current gradient
        grad = self.compute_gradient(state.params)
        state.grad_history.append(grad)

        # Use FFT to get frequency spectrum
        if len(state.grad_history) < 3:
            return grad  # Not enough history yet

        # Stack recent gradients
        grad_stack = np.array(state.grad_history[-9:])  # Last 9 steps

        # FFT along time axis
        fft_result = np.fft.fft(grad_stack, axis=0)

        # Keep top 2/9 frequencies
        n_keep = max(2, int(len(grad_stack) * 2/9))
        freqs = np.abs(fft_result)
        top_indices = np.argsort(np.mean(freqs, axis=1))[-n_keep:]

        # Reconstruct from top frequencies
        fft_result[~np.isin(np.arange(len(grad_stack)), top_indices)] = 0
        filtered = np.fft.ifft(fft_result, axis=0).real

        # Return last row (current gradient, filtered)
        return filtered[-1]

    def operation_2(self, state: QUINNState, r1: np.ndarray) -> float:
        """
        Sync score: measure coherence/alignment

        Returns: s in [0, 1], where s = 7/9 is universal threshold
        """
        # Sync score: alignment between recent gradients
        if len(state.grad_history) < 2:
            return 0.5

        # Compute pairwise cosine similarities
        grads = np.array(state.grad_history[-5:])
        similarities = []
        for i in range(len(grads) - 1):
            g1, g2 = grads[i], grads[i+1]
            norm_prod = np.linalg.norm(g1) * np.linalg.norm(g2)
            if norm_prod > 1e-10:
                sim = np.dot(g1, g2) / norm_prod
                similarities.append(max(0, sim))  # Clip to [0, 1]

        if not similarities:
            return 0.5

        # Sync score: mean similarity, scaled to [0, 1]
        s = np.clip(np.mean(similarities), 0, 1)
        return s

    def operation_3(self, state: QUINNState, r1: np.ndarray, r2: float) -> QUINNState:
        """
        Geodesic correction: apply phase-modulated update step

        Args:
            state: Current state
            r1: Filtered gradient from operation_1
            r2: Sync score from operation_2

        Returns: Updated state
        """
        s = r2
        lr = 0.01  # Base learning rate

        # Mode-dependent step size
        if s < 2/3:  # Exploration
            step_size = lr * 2.0
        elif s < 7/9:  # Transition
            step_size = lr * 1.0
        else:  # Precision
            step_size = lr * 0.5

        # Apply gradient update
        state.params = state.params - step_size * r1

        # Track best
        loss = self.compute_loss(state.params)
        if loss < state.best_loss:
            state.best_loss = loss
            state.best_params = state.params.copy()

        self.step_count += 1
        return state

    def control_metric(self, state: QUINNState) -> float:
        """
        Measure: sync score (0-1 scale)
        """
        # Compute current sync score
        if len(state.grad_history) < 2:
            return 0.5

        grads = np.array(state.grad_history[-5:])
        similarities = []
        for i in range(len(grads) - 1):
            g1, g2 = grads[i], grads[i+1]
            norm_prod = np.linalg.norm(g1) * np.linalg.norm(g2)
            if norm_prod > 1e-10:
                sim = np.dot(g1, g2) / norm_prod
                similarities.append(max(0, sim))

        if similarities:
            return np.clip(np.mean(similarities), 0, 1)
        return 0.5

    def validate(self, state: QUINNState, expected_loss: float = 1e-6) -> Dict[str, float]:
        """
        Compare achieved loss against expected

        Returns validation metrics
        """
        current_loss = self.compute_loss(state.params)
        best_loss = state.best_loss

        return {
            'current_loss': float(current_loss),
            'best_loss': float(best_loss),
            'loss_reduction': float((1.0 - best_loss / (1.0 + current_loss))),
            'gradient_norm': float(np.linalg.norm(self.compute_gradient(state.params))),
            'steps_taken': self.step_count
        }


def test_quinn():
    """Test QUINN adapter"""
    print("=" * 70)
    print("Testing QUINN Optimizer as K₃ × Z/9Z")
    print("=" * 70)

    for problem in ["quadratic", "ill_conditioned", "noisy"]:
        print(f"\n--- Problem: {problem} ---")

        # Build system
        adapter = QUINNSystemAdapter(D=64, problem=problem)
        system = adapter.build_system(threshold=7/9)

        # Initialize
        state = adapter.init_state()
        print(f"Initial loss: {adapter.compute_loss(state.params):.6f}")

        # Run optimization
        print(f"Running 200 steps...")
        state, history = system.run(state, 200)

        # Analyze
        controls = [h['control'] for h in history]
        print(f"Final loss: {adapter.compute_loss(state.params):.6f}")
        print(f"Best loss: {state.best_loss:.6f}")
        print(f"Convergence rate (s ≥ 7/9): {system.convergence_rate():.2%}")
        print(f"Sync score: {controls[-1]:.4f}")

        # Validation
        val = adapter.validate(state)
        print(f"Loss reduction: {val['loss_reduction']:.2%}")
        print(f"Gradient norm: {val['gradient_norm']:.6f}")

    print("\n✓ Test complete\n")


if __name__ == "__main__":
    test_quinn()
