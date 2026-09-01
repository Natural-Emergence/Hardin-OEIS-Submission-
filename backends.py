"""
Numeric backend adapters for auditing the same computation across different arithmetic systems.
Enables comparison between float, Decimal, Fraction, SymPy, and mpmath backends.
"""

import math
from abc import ABC, abstractmethod
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Union, Any, Callable, Dict, List, Tuple

# Try to import optional backends
try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

try:
    import mpmath as mp
    HAS_MPMATH = True
    mp.dps = 50  # 50 decimal places
except ImportError:
    HAS_MPMATH = False

getcontext().prec = 100


class NumericBackend(ABC):
    """Abstract base for numeric backends."""

    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass

    @abstractmethod
    def cast(self, value: Union[int, float, str]) -> Any:
        """Cast value to backend's numeric type."""
        pass

    @abstractmethod
    def sqrt(self, x: Any) -> Any:
        """Square root."""
        pass

    @abstractmethod
    def add(self, a: Any, b: Any) -> Any:
        """Addition."""
        pass

    @abstractmethod
    def multiply(self, a: Any, b: Any) -> Any:
        """Multiplication."""
        pass

    @abstractmethod
    def divide(self, a: Any, b: Any) -> Any:
        """Division."""
        pass

    @abstractmethod
    def to_float(self, x: Any) -> float:
        """Convert to Python float for comparison."""
        pass

    @abstractmethod
    def equal(self, a: Any, b: Any, tolerance: float = 0) -> bool:
        """Equality comparison with optional tolerance."""
        pass


class FloatBackend(NumericBackend):
    """Python's native float (IEEE 754 double)."""

    def name(self) -> str:
        return "float64"

    def cast(self, value: Union[int, float, str]) -> float:
        return float(value)

    def sqrt(self, x: float) -> float:
        return math.sqrt(x)

    def add(self, a: float, b: float) -> float:
        return a + b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        return a / b

    def to_float(self, x: float) -> float:
        return x

    def equal(self, a: float, b: float, tolerance: float = 0) -> bool:
        if tolerance == 0:
            return a == b
        return abs(a - b) <= tolerance * max(abs(a), abs(b))


class DecimalBackend(NumericBackend):
    """Python's Decimal type (arbitrary precision decimal)."""

    def name(self) -> str:
        return "decimal"

    def cast(self, value: Union[int, float, str]) -> Decimal:
        return Decimal(str(value))

    def sqrt(self, x: Decimal) -> Decimal:
        return x.sqrt()

    def add(self, a: Decimal, b: Decimal) -> Decimal:
        return a + b

    def multiply(self, a: Decimal, b: Decimal) -> Decimal:
        return a * b

    def divide(self, a: Decimal, b: Decimal) -> Decimal:
        return a / b

    def to_float(self, x: Decimal) -> float:
        return float(x)

    def equal(self, a: Decimal, b: Decimal, tolerance: float = 0) -> bool:
        if tolerance == 0:
            return a == b
        return abs(a - b) <= Decimal(str(tolerance)) * max(abs(a), abs(b))


class FractionBackend(NumericBackend):
    """Python's Fraction type (exact rational arithmetic)."""

    def name(self) -> str:
        return "fraction"

    def cast(self, value: Union[int, float, str]) -> Fraction:
        return Fraction(value).limit_denominator() if isinstance(value, float) else Fraction(value)

    def sqrt(self, x: Fraction) -> Fraction:
        # For rationals, compute as sqrt(num)/sqrt(denom) if both are perfect squares
        import math
        num_sqrt = math.isqrt(x.numerator)
        denom_sqrt = math.isqrt(x.denominator)
        if num_sqrt ** 2 == x.numerator and denom_sqrt ** 2 == x.denominator:
            return Fraction(num_sqrt, denom_sqrt)
        # Otherwise fall back to decimal approximation as Fraction
        decimal_sqrt = Decimal(str(x)).sqrt()
        return Fraction(str(decimal_sqrt)).limit_denominator(10**20)

    def add(self, a: Fraction, b: Fraction) -> Fraction:
        return a + b

    def multiply(self, a: Fraction, b: Fraction) -> Fraction:
        return a * b

    def divide(self, a: Fraction, b: Fraction) -> Fraction:
        return a / b

    def to_float(self, x: Fraction) -> float:
        return float(x)

    def equal(self, a: Fraction, b: Fraction, tolerance: float = 0) -> bool:
        if tolerance == 0:
            return a == b
        diff = abs(a - b)
        threshold = Fraction(tolerance) * max(abs(a), abs(b))
        return diff <= threshold


class SympyBackend(NumericBackend):
    """SymPy symbolic algebra backend."""

    def __init__(self):
        if not HAS_SYMPY:
            raise ImportError("SymPy not installed")

    def name(self) -> str:
        return "sympy"

    def cast(self, value: Union[int, float, str]) -> Any:
        return sp.sympify(value)

    def sqrt(self, x: Any) -> Any:
        return sp.sqrt(x)

    def add(self, a: Any, b: Any) -> Any:
        return a + b

    def multiply(self, a: Any, b: Any) -> Any:
        return a * b

    def divide(self, a: Any, b: Any) -> Any:
        return a / b

    def to_float(self, x: Any) -> float:
        return float(sp.N(x))

    def equal(self, a: Any, b: Any, tolerance: float = 0) -> bool:
        diff = sp.simplify(a - b)
        if tolerance == 0:
            return diff == 0
        return abs(float(sp.N(diff))) <= tolerance


class MpmathBackend(NumericBackend):
    """mpmath arbitrary-precision floating-point backend."""

    def __init__(self, dps: int = 50):
        if not HAS_MPMATH:
            raise ImportError("mpmath not installed")
        self.dps = dps

    def name(self) -> str:
        return f"mpmath({self.dps}dps)"

    def cast(self, value: Union[int, float, str]) -> Any:
        return mp.mpf(value)

    def sqrt(self, x: Any) -> Any:
        return mp.sqrt(x)

    def add(self, a: Any, b: Any) -> Any:
        return a + b

    def multiply(self, a: Any, b: Any) -> Any:
        return a * b

    def divide(self, a: Any, b: Any) -> Any:
        return a / b

    def to_float(self, x: Any) -> float:
        return float(x)

    def equal(self, a: Any, b: Any, tolerance: float = 0) -> bool:
        diff = abs(a - b)
        if tolerance == 0:
            return diff == 0
        return diff <= tolerance * max(abs(a), abs(b))


class BackendComparison:
    """Runs a computation across all available backends and compares results."""

    def __init__(self):
        self.backends: Dict[str, NumericBackend] = {
            'float64': FloatBackend(),
            'decimal': DecimalBackend(),
            'fraction': FractionBackend(),
        }

        if HAS_SYMPY:
            self.backends['sympy'] = SympyBackend()
        if HAS_MPMATH:
            self.backends['mpmath'] = MpmathBackend(dps=50)

    def run_computation(self, name: str, fn: Callable, inputs: Dict[str, Union[int, float, str]]) -> Dict[str, Any]:
        """
        Run a computation across all backends.

        Args:
            name: Operation name
            fn: Function taking backend and cast inputs
            inputs: Input values keyed by name

        Returns:
            Dict mapping backend names to results
        """
        results = {}

        for backend_name, backend in self.backends.items():
            try:
                cast_inputs = {k: backend.cast(v) for k, v in inputs.items()}
                result = fn(backend, cast_inputs)
                results[backend_name] = {
                    'value': result,
                    'float': backend.to_float(result),
                    'success': True,
                    'error': None
                }
            except Exception as e:
                results[backend_name] = {
                    'value': None,
                    'float': float('nan'),
                    'success': False,
                    'error': str(e)
                }

        return results

    def compare_results(self, name: str, fn: Callable, inputs: Dict[str, Union[int, float, str]],
                       reference_backend: str = 'decimal') -> Dict[str, Any]:
        """
        Run computation and compare all backends against a reference.

        Returns:
            Comparison results with deviations from reference
        """
        results = self.run_computation(name, fn, inputs)

        if reference_backend not in results or not results[reference_backend]['success']:
            return {
                'operation': name,
                'reference_backend': reference_backend,
                'error': f"Reference backend {reference_backend} failed",
                'results': results
            }

        reference = results[reference_backend]['float']

        comparison = {
            'operation': name,
            'reference_backend': reference_backend,
            'reference_value': reference,
            'results': results,
            'deviations': {}
        }

        for backend_name, result in results.items():
            if backend_name == reference_backend:
                continue
            if not result['success']:
                comparison['deviations'][backend_name] = {
                    'error': result['error'],
                    'relative_error': float('inf')
                }
            else:
                value = result['float']
                if reference != 0:
                    rel_error = abs(value - reference) / abs(reference)
                else:
                    rel_error = float('inf') if value != 0 else 0.0

                comparison['deviations'][backend_name] = {
                    'value': value,
                    'absolute_error': value - reference,
                    'relative_error': rel_error
                }

        return comparison

    def report_comparison(self, comparisons: List[Dict[str, Any]]) -> str:
        """Generate formatted comparison report."""
        lines = []
        lines.append("=" * 80)
        lines.append("BACKEND COMPARISON REPORT")
        lines.append("=" * 80)

        for comp in comparisons:
            lines.append(f"\nOperation: {comp['operation']}")
            if 'error' in comp:
                lines.append(f"  ERROR: {comp['error']}")
                continue

            lines.append(f"  Reference: {comp['reference_backend']} = {comp['reference_value']:.15e}")

            for backend_name, deviation in comp.get('deviations', {}).items():
                if 'error' in deviation:
                    lines.append(f"  {backend_name}: FAILED - {deviation['error']}")
                else:
                    abs_err = deviation['absolute_error']
                    rel_err = deviation['relative_error']
                    lines.append(f"  {backend_name}:")
                    lines.append(f"    Value: {deviation['value']:.15e}")
                    lines.append(f"    Absolute Error: {abs_err:.2e}")
                    lines.append(f"    Relative Error: {rel_err:.2e}")

        return "\n".join(lines)


def get_available_backends() -> List[str]:
    """List names of available backends."""
    backends = ['float64', 'decimal', 'fraction']
    if HAS_SYMPY:
        backends.append('sympy')
    if HAS_MPMATH:
        backends.append('mpmath')
    return backends
