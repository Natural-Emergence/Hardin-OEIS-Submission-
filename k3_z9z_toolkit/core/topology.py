"""
K₃ × Z/9Z Unified Topology Framework

Universal structure for adaptive coordination systems across any domain.

Implements:
- K₃: Complete triadic graph (3 mutually-coupled operations)
- Z/9Z: Cyclic group of order 9 (9-phase state organization)
- Z₃: Three-stage phase progression (exploration → transition → precision)
- Threshold-based mode switching via scalar control metric

Usage:
    system = K3Z9ZSystem(
        operation_1=lambda state: ...,
        operation_2=lambda state, r1: ...,
        operation_3=lambda state, r1, r2: ...,
        control_metric=lambda state: ...,
        threshold=7/9,
        material="your_domain"
    )

    for step in range(iterations):
        state = system.step(state)
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Any, Dict, Tuple, List
from enum import Enum


class Z3Phase(Enum):
    """Three-stage phase progression"""
    EXPLORATION = 0    # Diverge, sample, generate candidates
    TRANSITION = 1     # Critical threshold crossing
    PRECISION = 2      # Converge, refine, lock in


@dataclass
class HarmonicConstants:
    """Z/9Z harmonic field parameters (universal across domains)"""
    s_universal: float = 7/9          # Mode 7 coupling: universal threshold
    s_base: float = 2/3                # φ(9)/9: base coprime threshold
    cross_overlap: float = 0.0148      # 1.48%: max for intact mechanism
    loop_factor: float = 1 - 1/549     # Finite coherence correction (549 = 9×61)
    grace: int = 63                    # Grace number for corrections
    phase_period: int = 9              # Z/9Z cycle length


@dataclass
class DomainMetrics:
    """Track multi-dimensional quality of state"""
    control_signal: float = 0.5        # Scalar control metric (r, s, coherence, etc.)
    phase: int = 0                     # Current phase in 0-8 cycle
    z3_phase: Z3Phase = Z3Phase.EXPLORATION
    phase_history: List[float] = field(default_factory=list)
    threshold_crossings: int = 0       # Transitions across critical threshold

    def update_phase(self, control: float, threshold: float):
        """Update phase based on control signal and threshold"""
        self.control_signal = control
        self.phase_history.append(control)

        # Determine Z₃ phase
        if control < threshold * 0.6:
            self.z3_phase = Z3Phase.EXPLORATION
        elif control < threshold * 0.95:
            self.z3_phase = Z3Phase.TRANSITION
        else:
            self.z3_phase = Z3Phase.PRECISION

        # Track threshold crossings
        if len(self.phase_history) > 1:
            prev = self.phase_history[-2]
            if (prev < threshold <= control) or (prev >= threshold > control):
                self.threshold_crossings += 1

        # Advance Z/9Z phase
        self.phase = (self.phase + 1) % 9


class K3Operation(ABC):
    """Abstract base for one of the three coupled operations"""

    @abstractmethod
    def execute(self, state: Any, r1: Any = None, r2: Any = None) -> Any:
        """
        Execute this operation.

        Args:
            state: Current system state
            r1: Result from operation 1 (if this is op2 or op3)
            r2: Result from operation 2 (if this is op3)

        Returns:
            Result from this operation
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class K3Z9ZSystem:
    """
    Universal K₃ × Z/9Z adaptive coordination system.

    All systems implementing this pattern share identical topology:
    - Three mutually-coupled operations
    - Nine-dimensional phase organization
    - Three-stage progression
    - Scalar control metric with threshold-based switching
    """

    def __init__(self,
                 operation_1: Callable[[Any], Any],
                 operation_2: Callable[[Any, Any], Any],
                 operation_3: Callable[[Any, Any, Any], Any],
                 control_metric: Callable[[Any], float],
                 threshold: float = 7/9,
                 domain_name: str = "generic",
                 harmonics: HarmonicConstants = None):
        """
        Initialize K₃ × Z/9Z system.

        Args:
            operation_1: First coupled operation: state → result1
            operation_2: Second coupled operation: (state, result1) → result2
            operation_3: Third coupled operation: (state, result1, result2) → result3
            control_metric: Measure system coherence: state → float
            threshold: Critical control signal for mode switching (default 7/9)
            domain_name: Human-readable domain name
            harmonics: Z/9Z parameters (uses defaults if None)
        """
        self.op1 = operation_1
        self.op2 = operation_2
        self.op3 = operation_3
        self.control_metric = control_metric
        self.threshold = threshold
        self.domain_name = domain_name
        self.harmonics = harmonics or HarmonicConstants()

        self.metrics = DomainMetrics()
        self.step_count = 0

    def phase_modulation(self) -> float:
        """
        Compute phase modulation factor based on Z/9Z cycle.

        Returns: factor in [0, 1] with period 9
        """
        t = self.metrics.phase / self.harmonics.phase_period
        return 0.5 + 0.5 * np.cos(2 * np.pi * t)

    def step(self, state: Any) -> Tuple[Any, Dict[str, float]]:
        """
        Execute one complete K₃ step (all three coupled operations).

        Returns:
            (new_state, metrics_dict)

        Note: The actual state update is handled by operation_3.
        The base step just orchestrates the three operations and tracks metrics.
        """
        # Operation 1: Generate/measure
        r1 = self.op1(state)

        # Operation 2: Evaluate/filter (depends on r1)
        r2 = self.op2(state, r1)

        # Operation 3: Organize/refine (depends on r1 and r2)
        # This is where state update actually happens
        new_state = self.op3(state, r1, r2)

        # Measure control signal
        control = self.control_metric(new_state)
        self.metrics.update_phase(control, self.threshold)

        # Phase modulation: couples to Z/9Z cycle
        phase_mod = self.phase_modulation()

        self.step_count += 1

        return new_state, {
            'control': float(control),
            'phase': self.metrics.phase,
            'z3_phase': self.metrics.z3_phase.name,
            'phase_mod': float(phase_mod),
            'threshold_crossings': self.metrics.threshold_crossings,
            'step': self.step_count
        }

    def run(self, state: Any, iterations: int) -> Tuple[Any, List[Dict]]:
        """
        Run for multiple steps.

        Returns:
            (final_state, metrics_history)
        """
        history = []
        for _ in range(iterations):
            state, metrics = self.step(state)
            history.append(metrics)
        return state, history

    def convergence_rate(self, threshold: float = None) -> float:
        """
        Estimate convergence rate: fraction of steps above threshold.
        """
        if not self.metrics.phase_history:
            return 0.0
        t = threshold or self.threshold
        above = sum(1 for c in self.metrics.phase_history if c >= t)
        return above / len(self.metrics.phase_history)

    def synchronization_index(self) -> float:
        """
        Measure phase coherence: how tightly clustered is phase_history?

        Returns: value in [0, 1] where 1 = perfect coherence
        """
        if len(self.metrics.phase_history) < 2:
            return 0.0
        vals = np.array(self.metrics.phase_history)
        # Normalize to [0, 1], then compute "concentration"
        normalized = (vals - vals.min()) / (vals.max() - vals.min() + 1e-10)
        # Coherence: inverse of normalized variance
        var = np.var(normalized)
        return 1.0 / (1.0 + var)


@dataclass
class K3Z9ZBlueprint:
    """
    Template for implementing K₃ × Z/9Z in a new domain.
    Fill in these methods to create a domain-specific system.
    """
    domain_name: str

    @abstractmethod
    def init_state(self) -> Any:
        """Create initial state"""
        pass

    @abstractmethod
    def operation_1(self, state: Any) -> Any:
        """Generate/sample candidates"""
        pass

    @abstractmethod
    def operation_2(self, state: Any, r1: Any) -> Any:
        """Evaluate/score candidates"""
        pass

    @abstractmethod
    def operation_3(self, state: Any, r1: Any, r2: Any) -> Any:
        """Organize/refine results"""
        pass

    @abstractmethod
    def control_metric(self, state: Any) -> float:
        """Measure system coherence"""
        pass

    @abstractmethod
    def validate(self, state: Any, expected: Any) -> Dict[str, float]:
        """
        Compare predicted state against known/expected result.

        Returns:
            {'metric_name': correlation/error/etc}
        """
        pass

    def build_system(self, threshold: float = 7/9) -> K3Z9ZSystem:
        """Construct the actual system from this blueprint"""
        return K3Z9ZSystem(
            operation_1=self.operation_1,
            operation_2=self.operation_2,
            operation_3=self.operation_3,
            control_metric=self.control_metric,
            threshold=threshold,
            domain_name=self.domain_name
        )
