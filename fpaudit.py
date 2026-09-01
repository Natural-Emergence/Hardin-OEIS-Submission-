"""
Floating-point auditing framework for detecting numeric errors in OEIS solutions.
Tracks ULP distance, relative error, and shadow computation in exact arithmetic.
"""

import struct
import math
from decimal import Decimal, getcontext
from fractions import Fraction
from typing import Union, Tuple, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Set high precision for Decimal backend
getcontext().prec = 100


class ErrorType(Enum):
    """Categories of floating-point errors detected."""
    ULP_OVERFLOW = "ULP overflow: precision loss exceeds representable range"
    CATASTROPHIC_CANCELLATION = "Catastrophic cancellation detected"
    SIGN_FLIP = "Sign flip from rounding"
    INVERSION_ERROR = "Inversion error: 1/x has wrong sign or magnitude"
    ACCUMULATED_ROUNDING = "Accumulated rounding error"
    UNDERFLOW = "Underflow to zero"
    OVERFLOW = "Overflow to infinity"
    PRECISION_LOSS = "Precision loss > threshold"


@dataclass
class NumericError:
    """A single detected error."""
    error_type: ErrorType
    value_float: float
    value_exact: Union[Decimal, Fraction]
    context: str = ""
    severity: float = 0.0  # ULP distance or relative error
    operation: str = ""

    def __str__(self):
        return f"{self.error_type.value} | {self.operation} | severity={self.severity:.2e}"


@dataclass
class FloatAuditResult:
    """Results from auditing a single numeric computation."""
    operation: str
    result_float: float
    result_exact: Union[Decimal, Fraction]
    errors: List[NumericError] = field(default_factory=list)
    relative_error: float = 0.0
    ulp_distance: float = 0.0
    shadow_value: Union[Decimal, Fraction, None] = None

    def passed(self) -> bool:
        return len(self.errors) == 0

    def has_severity_above(self, threshold: float) -> bool:
        return any(e.severity > threshold for e in self.errors)


class FloatAuditor:
    """Main auditing engine."""

    def __init__(self, ulp_threshold: float = 2.0, rel_error_threshold: float = 1e-14):
        self.ulp_threshold = ulp_threshold
        self.rel_error_threshold = rel_error_threshold
        self.results: List[FloatAuditResult] = []

    def audit(self, op_name: str, float_result: float, exact_result: Union[Decimal, Fraction, float],
              shadow_fn=None) -> FloatAuditResult:
        """
        Audit a single operation.

        Args:
            op_name: Name of operation (e.g., "sqrt(2)")
            float_result: Result from float arithmetic
            exact_result: Ground truth (Decimal or Fraction)
            shadow_fn: Optional function to compute in higher precision

        Returns:
            FloatAuditResult with errors and metrics
        """
        if isinstance(exact_result, (int, float)):
            exact_result = Decimal(str(exact_result))

        result = FloatAuditResult(
            operation=op_name,
            result_float=float_result,
            result_exact=exact_result,
            shadow_value=shadow_fn() if shadow_fn else None,
        )

        # Handle special cases
        if math.isnan(float_result):
            if exact_result != 0:  # NaN when shouldn't be
                result.errors.append(NumericError(
                    ErrorType.PRECISION_LOSS,
                    float_result,
                    exact_result,
                    "NaN result",
                    float('inf'),
                    op_name
                ))
            self.results.append(result)
            return result

        if math.isinf(float_result):
            result.errors.append(NumericError(
                ErrorType.OVERFLOW,
                float_result,
                exact_result,
                "Overflow to infinity",
                float('inf'),
                op_name
            ))
            self.results.append(result)
            return result

        # Compute error metrics
        if isinstance(exact_result, Decimal):
            exact_dec = exact_result
        elif isinstance(exact_result, Fraction):
            exact_dec = Decimal(exact_result.numerator) / Decimal(exact_result.denominator)
        else:
            exact_dec = Decimal(str(exact_result))

        try:
            if exact_dec != 0:
                # Relative error: |float - exact| / |exact|
                abs_error = abs(Decimal(str(float_result)) - exact_dec)
                result.relative_error = float(abs_error / abs(exact_dec))

                # ULP distance (as proxy for precision loss)
                result.ulp_distance = self._ulp_distance(float_result, exact_dec)
        except:
            pass

        # Run detectors
        self._detect_sign_flip(result, exact_dec)
        self._detect_cancellation(result, op_name)
        self._detect_inversion_error(result, exact_dec)
        self._detect_precision_loss(result)

        self.results.append(result)
        return result

    def _ulp_distance(self, float_val: float, exact_val: Union[Decimal, Fraction]) -> float:
        """Compute ULP (Units in Last Place) distance, surviving total precision loss."""
        try:
            # Convert to Decimal if needed
            if isinstance(exact_val, Fraction):
                exact_val = Decimal(exact_val.numerator) / Decimal(exact_val.denominator)

            if float_val == 0.0:
                # Smallest positive float
                min_positive = 2.2250738585072014e-308
                return float(abs(exact_val) / Decimal(str(min_positive)))

            # Get mantissa and exponent
            mantissa, exp = math.frexp(float_val)
            ulp = 2.0 ** (exp - 52)  # 52 bits in double mantissa

            error = abs(float(exact_val) - float_val)
            distance = error / ulp if ulp > 0 else float('inf')

            # Clamp to avoid overflow from total loss
            return min(distance, 1e16)
        except:
            return float('inf')

    def _detect_sign_flip(self, result: FloatAuditResult, exact_val: Union[Decimal, Fraction]):
        """Detect when rounding flips the sign."""
        float_sign = 1 if result.result_float > 0 else (-1 if result.result_float < 0 else 0)
        if isinstance(exact_val, Fraction):
            exact_sign = 1 if exact_val > 0 else (-1 if exact_val < 0 else 0)
        else:
            exact_sign = 1 if exact_val > 0 else (-1 if exact_val < 0 else 0)

        if float_sign != exact_sign and exact_sign != 0:
            result.errors.append(NumericError(
                ErrorType.SIGN_FLIP,
                result.result_float,
                exact_val,
                f"Sign: {exact_sign} → {float_sign}",
                float('inf'),
                result.operation
            ))

    def _detect_cancellation(self, result: FloatAuditResult, op_name: str):
        """Detect catastrophic cancellation (e.g., (a+b) - a where a >> b)."""
        # Simple heuristic: if relative error is surprisingly large for a single op
        if result.relative_error > 1e-7 and "subtract" not in op_name.lower():
            result.errors.append(NumericError(
                ErrorType.CATASTROPHIC_CANCELLATION,
                result.result_float,
                result.result_exact,
                "Unexpectedly large relative error",
                result.relative_error,
                op_name
            ))

    def _detect_inversion_error(self, result: FloatAuditResult, exact_val: Union[Decimal, Fraction]):
        """Detect errors in reciprocal or inversion operations."""
        if "1/" in result.operation or "reciprocal" in result.operation.lower():
            if exact_val != 0:
                # Convert to Decimal if needed
                if isinstance(exact_val, Fraction):
                    exact_dec = Decimal(exact_val.numerator) / Decimal(exact_val.denominator)
                else:
                    exact_dec = exact_val
                expected_reciprocal = 1 / exact_dec
                actual = Decimal(str(result.result_float))
                rel_err = abs(actual - expected_reciprocal) / abs(expected_reciprocal)

                if rel_err > self.rel_error_threshold:
                    result.errors.append(NumericError(
                        ErrorType.INVERSION_ERROR,
                        result.result_float,
                        exact_val,
                        f"Inversion relative error: {float(rel_err):.2e}",
                        float(rel_err),
                        result.operation
                    ))

    def _detect_precision_loss(self, result: FloatAuditResult):
        """Detect precision loss based on ULP and relative error."""
        if result.ulp_distance > self.ulp_threshold:
            result.errors.append(NumericError(
                ErrorType.PRECISION_LOSS,
                result.result_float,
                result.result_exact,
                f"ULP distance: {result.ulp_distance:.2e}",
                result.ulp_distance,
                result.operation
            ))

    def summary(self) -> Dict[str, Any]:
        """Generate audit summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed())
        failed = total - passed

        error_counts: Dict[ErrorType, int] = {}
        for result in self.results:
            for error in result.errors:
                error_counts[error.error_type] = error_counts.get(error.error_type, 0) + 1

        return {
            "total_operations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "error_breakdown": {et.name: count for et, count in error_counts.items()},
            "max_relative_error": max((r.relative_error for r in self.results), default=0.0),
            "max_ulp_distance": max((r.ulp_distance for r in self.results), default=0.0),
        }

    def report(self) -> str:
        """Generate a formatted audit report."""
        lines = []
        summary = self.summary()

        lines.append("=" * 70)
        lines.append("FLOATING-POINT AUDIT REPORT")
        lines.append("=" * 70)
        lines.append(f"Total Operations: {summary['total_operations']}")
        lines.append(f"Passed: {summary['passed']} ({summary['pass_rate']*100:.1f}%)")
        lines.append(f"Failed: {summary['failed']}")
        lines.append(f"Max Relative Error: {summary['max_relative_error']:.2e}")
        lines.append(f"Max ULP Distance: {summary['max_ulp_distance']:.2e}")
        lines.append("")

        if summary['error_breakdown']:
            lines.append("Error Breakdown:")
            for error_type, count in sorted(summary['error_breakdown'].items()):
                lines.append(f"  {error_type}: {count}")

        lines.append("")
        lines.append("Failed Operations:")
        for result in self.results:
            if not result.passed():
                lines.append(f"  {result.operation}")
                for error in result.errors:
                    lines.append(f"    → {error}")

        return "\n".join(lines)
