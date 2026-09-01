"""
Probes for detecting floating-point errors in numeric computations.
Each probe targets a specific category of errors or operations.
"""

import math
from decimal import Decimal
from fractions import Fraction
from typing import Callable, List, Tuple, Dict, Any
from fpaudit import FloatAuditor, FloatAuditResult, NumericError, ErrorType


class NumericProbe:
    """Base class for numeric error probes."""

    def __init__(self, name: str, auditor: FloatAuditor = None):
        self.name = name
        self.auditor = auditor or FloatAuditor(ulp_threshold=2.0, rel_error_threshold=1e-14)
        self.results: List[FloatAuditResult] = []

    def run(self) -> Dict[str, Any]:
        """Run the probe and return results."""
        raise NotImplementedError

    def add_result(self, result: FloatAuditResult):
        self.results.append(result)
        self.auditor.results.append(result)

    def passed(self) -> bool:
        return all(r.passed() for r in self.results)


class CatastrophicCancellationProbe(NumericProbe):
    """Detects catastrophic cancellation: (a + b) - a ≈ 0 when b is tiny."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Classic case: large + tiny - large
        a = 1e16
        b = 1.0

        # Float arithmetic
        float_result = (a + b) - a

        # Exact arithmetic
        exact = Decimal('1.0')

        result = self.auditor.audit(
            "catastrophic_cancellation: (1e16 + 1.0) - 1e16",
            float_result,
            exact
        )
        self.add_result(result)

        # Variant: subtraction of nearly equal numbers
        x = 0.1
        y = 0.1 + 1e-15
        float_diff = y - x
        exact_diff = Decimal('1e-15')

        result = self.auditor.audit(
            "nearly_equal_subtraction: (0.1 + 1e-15) - 0.1",
            float_diff,
            exact_diff
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


class SignFlipProbe(NumericProbe):
    """Detects sign flips due to rounding near zero."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Case 1: Subtraction near zero
        a = 1e-150
        b = 1e-150 + 1e-170

        float_diff = a - b
        exact_diff = Decimal('-1e-170')

        result = self.auditor.audit(
            "sign_flip: 1e-150 - (1e-150 + 1e-170)",
            float_diff,
            exact_diff
        )
        self.add_result(result)

        # Case 2: Accumulated rounding near sign boundary
        x = 1.0
        for _ in range(1000):
            x = x - 1.0 / 1e6

        # Should be slightly negative but might round to zero or positive
        exact = Decimal('1.0') - 1000 * Decimal('1.0') / Decimal('1e6')

        result = self.auditor.audit(
            "accumulated_subtraction_sign_flip: 1.0 - 1000*(1/1e6)",
            x,
            exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


class InversionErrorProbe(NumericProbe):
    """Detects errors in reciprocal and division operations."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Case 1: Simple reciprocal
        x = 3.0
        float_reciprocal = 1.0 / x
        exact_reciprocal = Fraction(1, 3)

        result = self.auditor.audit(
            "inversion: 1/3",
            float_reciprocal,
            exact_reciprocal
        )
        self.add_result(result)

        # Case 2: Reciprocal of tiny number (potential underflow)
        x = 1e-200
        float_reciprocal = 1.0 / x
        exact_reciprocal = Decimal('1.0') / Decimal('1e-200')

        result = self.auditor.audit(
            "inversion: 1/1e-200",
            float_reciprocal,
            exact_reciprocal
        )
        self.add_result(result)

        # Case 3: Reciprocal chain (accumulated error)
        x = 2.0
        for _ in range(10):
            x = 1.0 / x

        # After 10 reciprocals, should get back close to 2 but with accumulated error
        exact = Decimal('2.0')
        result = self.auditor.audit(
            "inversion_chain: (1/(1/(1/....(1/2))))",
            x,
            exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 3,
            'passed': self.passed(),
            'results': self.results
        }


class SummationErrorProbe(NumericProbe):
    """Detects accumulated rounding errors in summation."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Case 1: Sum of small + large (Kahan summation problem)
        large = 1e10
        small_terms = [1.0] * 1000000

        naive_sum = large
        for term in small_terms:
            naive_sum += term

        exact_sum = Decimal(str(large)) + 1000000

        result = self.auditor.audit(
            "summation_naive: 1e10 + 1000000*1.0",
            naive_sum,
            exact_sum
        )
        self.add_result(result)

        # Case 2: Alternating sum (high cancellation risk)
        alt_sum = 0.0
        for i in range(1, 1000):
            if i % 2 == 0:
                alt_sum -= 1.0 / i
            else:
                alt_sum += 1.0 / i

        # Exact summation as rational
        exact_alt = Fraction(0)
        for i in range(1, 1000):
            if i % 2 == 0:
                exact_alt -= Fraction(1, i)
            else:
                exact_alt += Fraction(1, i)

        result = self.auditor.audit(
            "alternating_sum: sum((-1)^i / i) for i=1..999",
            alt_sum,
            exact_alt
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


class SqrtAccuracyProbe(NumericProbe):
    """Detects errors in square root computation."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Case 1: sqrt(2)
        x = 2.0
        float_sqrt = math.sqrt(x)
        exact_sqrt = Decimal('2').sqrt()

        result = self.auditor.audit(
            "sqrt_precision: sqrt(2)",
            float_sqrt,
            exact_sqrt
        )
        self.add_result(result)

        # Case 2: sqrt of very small number
        x = 1e-200
        float_sqrt = math.sqrt(x)
        exact_sqrt = Decimal('1e-200').sqrt()

        result = self.auditor.audit(
            "sqrt_tiny: sqrt(1e-200)",
            float_sqrt,
            exact_sqrt
        )
        self.add_result(result)

        # Case 3: sqrt after accumulation
        x = 1.0
        for _ in range(100):
            x = math.sqrt(x)

        # After 100 square roots, x should be very close to 1
        exact = Decimal('1.0')
        result = self.auditor.audit(
            "sqrt_chain_100: (sqrt(sqrt(...(sqrt(1.0)))))",
            x,
            exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 3,
            'passed': self.passed(),
            'results': self.results
        }


class QuadraticFormulaProbe(NumericProbe):
    """Detects errors in solving quadratic equations."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # ax^2 + bx + c = 0
        # Case 1: Standard form with close roots
        a = 1.0
        b = -1e8
        c = 1.0

        discriminant = b * b - 4 * a * c
        sqrt_disc = math.sqrt(discriminant)

        # One root (standard formula)
        x1_naive = (-b + sqrt_disc) / (2 * a)

        # Exact value
        b_exact = Decimal('-1e8')
        disc_exact = b_exact * b_exact - 4
        sqrt_disc_exact = disc_exact.sqrt()
        x1_exact = (-b_exact + sqrt_disc_exact) / 2

        result = self.auditor.audit(
            "quadratic_formula: x1 = (-b + sqrt(disc))/(2a)",
            x1_naive,
            x1_exact
        )
        self.add_result(result)

        # Case 2: Alternative formula (more stable)
        # x2 = 2c / (-b - sqrt(disc))
        x2_alt = 2 * c / (-b - sqrt_disc)
        x2_exact = 2 / (-b_exact - sqrt_disc_exact)

        result = self.auditor.audit(
            "quadratic_formula_alt: x2 = 2c / (-b - sqrt(disc))",
            x2_alt,
            x2_exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


class ExponentAccuracyProbe(NumericProbe):
    """Detects errors in exponential and power operations."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        # Case 1: Large exponent
        x = 1.0001
        float_result = x ** 100

        exact = Decimal('1.0001') ** 100

        result = self.auditor.audit(
            "power_large_exp: (1.0001)^100",
            float_result,
            exact
        )
        self.add_result(result)

        # Case 2: Fractional exponent
        x = 2.0
        float_result = x ** 0.5

        exact = Decimal('2').sqrt()

        result = self.auditor.audit(
            "power_sqrt: 2^0.5",
            float_result,
            exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


class PolynomialEvaluationProbe(NumericProbe):
    """Detects errors in polynomial evaluation using Horner's method vs naive."""

    def run(self) -> Dict[str, Any]:
        self.results = []

        x = 1.1
        # p(x) = x^5 - 5x^4 + 10x^3 - 10x^2 + 5x - 1
        # This is (x-1)^5 which should be 0.00001 at x=1.1

        # Naive evaluation
        naive = x**5 - 5*x**4 + 10*x**3 - 10*x**2 + 5*x - 1

        # Horner's method: ((((x-5)*x+10)*x-10)*x+5)*x-1
        horner = ((((x - 5)*x + 10)*x - 10)*x + 5)*x - 1

        # Exact
        x_exact = Decimal('1.1')
        exact = (x_exact - 1)**5

        result = self.auditor.audit(
            "polynomial_naive: (x-1)^5 naive expansion",
            naive,
            exact
        )
        self.add_result(result)

        result = self.auditor.audit(
            "polynomial_horner: (x-1)^5 Horner's method",
            horner,
            exact
        )
        self.add_result(result)

        return {
            'probe': self.name,
            'operations_tested': 2,
            'passed': self.passed(),
            'results': self.results
        }


def run_all_probes() -> Dict[str, Any]:
    """Run all numeric probes and return aggregated results."""
    auditor = FloatAuditor(ulp_threshold=2.0, rel_error_threshold=1e-14)

    probes = [
        CatastrophicCancellationProbe("catastrophic_cancellation", auditor),
        SignFlipProbe("sign_flip", auditor),
        InversionErrorProbe("inversion_error", auditor),
        SummationErrorProbe("summation_error", auditor),
        SqrtAccuracyProbe("sqrt_accuracy", auditor),
        QuadraticFormulaProbe("quadratic_formula", auditor),
        ExponentAccuracyProbe("exponent_accuracy", auditor),
        PolynomialEvaluationProbe("polynomial_evaluation", auditor),
    ]

    results = {
        'probes': {},
        'total_operations': 0,
        'total_passed': 0,
        'total_failed': 0
    }

    for probe in probes:
        probe_result = probe.run()
        results['probes'][probe.name] = probe_result
        results['total_operations'] += len(probe.results)
        results['total_passed'] += sum(1 for r in probe.results if r.passed())
        results['total_failed'] += sum(1 for r in probe.results if not r.passed())

    results['pass_rate'] = results['total_passed'] / results['total_operations'] if results['total_operations'] > 0 else 0.0
    results['auditor_summary'] = auditor.summary()

    return results
