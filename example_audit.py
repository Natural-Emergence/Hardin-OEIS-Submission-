"""
Example: Using fpaudit framework to audit user functions.
Demonstrates how to integrate floating-point auditing into existing solutions.
"""

import math
from decimal import Decimal
from fractions import Fraction

from test_runner import FloatAuditTestRunner


# ============================================================================
# Example Functions (simulating OEIS solutions with float operations)
# ============================================================================

def quadratic_roots_naive(a: float, b: float, c: float) -> tuple:
    """
    Naive quadratic formula - prone to catastrophic cancellation.
    Returns both roots using standard formula.
    """
    disc = b * b - 4 * a * c
    sqrt_disc = math.sqrt(disc)
    x1 = (-b + sqrt_disc) / (2 * a)
    x2 = (-b - sqrt_disc) / (2 * a)
    return (x1, x2)


def quadratic_roots_stable(a: float, b: float, c: float) -> tuple:
    """
    Stable quadratic formula - uses alternative form for one root.
    Better numerical stability.
    """
    disc = b * b - 4 * a * c
    sqrt_disc = math.sqrt(disc)

    if b >= 0:
        x1 = (-b - sqrt_disc) / (2 * a)
        x2 = 2 * c / (-b - sqrt_disc)
    else:
        x1 = (-b + sqrt_disc) / (2 * a)
        x2 = 2 * c / (-b + sqrt_disc)

    return (x1, x2)


def sum_reciprocals_naive(n: int) -> float:
    """
    Naive summation of reciprocals - accumulates rounding error.
    sum(1/i) for i=1..n
    """
    total = 0.0
    for i in range(1, n + 1):
        total += 1.0 / i
    return total


def sum_reciprocals_kahan(n: int) -> float:
    """
    Kahan summation - reduces accumulated rounding error.
    """
    total = 0.0
    c = 0.0  # Correction term
    for i in range(1, n + 1):
        y = 1.0 / i - c
        t = total + y
        c = (t - total) - y
        total = t
    return total


def geometric_mean_naive(values: list) -> float:
    """
    Naive geometric mean - product then nth root.
    Can overflow for large n or large values.
    """
    product = 1.0
    for v in values:
        product *= v
    return product ** (1.0 / len(values))


def geometric_mean_stable(values: list) -> float:
    """
    Stable geometric mean - use logarithms.
    Avoids overflow/underflow.
    """
    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / len(values))


def distance_2d_naive(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Naive Euclidean distance - can overflow.
    """
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


def distance_2d_stable(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Stable Euclidean distance - using hypot.
    Handles underflow/overflow better.
    """
    dx = x2 - x1
    dy = y2 - y1
    return math.hypot(dx, dy)


def polynomial_eval_naive(coeffs: list, x: float) -> float:
    """
    Naive polynomial evaluation.
    p(x) = c0 + c1*x + c2*x^2 + ...
    """
    result = 0.0
    x_power = 1.0
    for coeff in coeffs:
        result += coeff * x_power
        x_power *= x
    return result


def polynomial_eval_horner(coeffs: list, x: float) -> float:
    """
    Horner's method for polynomial evaluation.
    More numerically stable.
    p(x) = (...((cn*x + c(n-1))*x + c(n-2))*x + ... )*x + c0
    """
    result = 0.0
    for coeff in reversed(coeffs):
        result = result * x + coeff
    return result


# ============================================================================
# Exact Reference Functions
# ============================================================================

def quadratic_roots_exact(a, b, c):
    """Exact quadratic roots using Decimal."""
    a_d = Decimal(str(a))
    b_d = Decimal(str(b))
    c_d = Decimal(str(c))

    disc = b_d * b_d - 4 * a_d * c_d
    sqrt_disc = disc.sqrt()

    x1 = (-b_d + sqrt_disc) / (2 * a_d)
    x2 = (-b_d - sqrt_disc) / (2 * a_d)

    return (x1, x2)


def sum_reciprocals_exact(n: int):
    """Exact sum of reciprocals using Fraction."""
    total = Fraction(0)
    for i in range(1, n + 1):
        total += Fraction(1, i)
    return total


def polynomial_eval_exact(coeffs: list, x):
    """Exact polynomial evaluation using Decimal."""
    from decimal import Decimal
    result = Decimal(0)
    x_d = Decimal(str(x))
    x_power = Decimal(1)
    for coeff in coeffs:
        result += Decimal(str(coeff)) * x_power
        x_power *= x_d
    return result


# ============================================================================
# Audit Suite
# ============================================================================

def run_audit_suite():
    """Run comprehensive audit on example functions."""

    runner = FloatAuditTestRunner(verbose=True)

    print("FLOATING-POINT AUDIT: Example Functions")
    print("=" * 80)

    # Test 1: Quadratic Formula
    print("\n[1] Auditing quadratic formula implementations...")
    a, b, c = 1.0, -1e8, 1.0
    x1_naive, x2_naive = quadratic_roots_naive(a, b, c)
    x1_exact, x2_exact = quadratic_roots_exact(a, b, c)

    runner.run_custom_probe(
        "quadratic_naive",
        [
            ("quadratic_naive_x1", x1_naive, x1_exact),
            ("quadratic_naive_x2", x2_naive, x2_exact),
        ]
    )

    x1_stable, x2_stable = quadratic_roots_stable(a, b, c)
    runner.run_custom_probe(
        "quadratic_stable",
        [
            ("quadratic_stable_x1", x1_stable, x1_exact),
            ("quadratic_stable_x2", x2_stable, x2_exact),
        ]
    )

    # Test 2: Summation
    print("[2] Auditing summation implementations...")
    n = 10000
    sum_naive = sum_reciprocals_naive(n)
    sum_kahan = sum_reciprocals_kahan(n)
    sum_exact = sum_reciprocals_exact(n)

    runner.run_custom_probe(
        "summation_naive",
        [("sum_reciprocals_naive", sum_naive, sum_exact)]
    )

    runner.run_custom_probe(
        "summation_kahan",
        [("sum_reciprocals_kahan", sum_kahan, sum_exact)]
    )

    # Test 3: Geometric Mean
    print("[3] Auditing geometric mean implementations...")
    values = [1.0, 2.0, 4.0, 8.0]
    gm_naive = geometric_mean_naive(values)
    gm_stable = geometric_mean_stable(values)
    gm_exact = Decimal('1') * Decimal('2') * Decimal('4') * Decimal('8')
    gm_exact = gm_exact ** (Decimal('1') / Decimal('4'))

    runner.run_custom_probe(
        "geometric_mean_naive",
        [("geom_mean_naive", gm_naive, gm_exact)]
    )

    runner.run_custom_probe(
        "geometric_mean_stable",
        [("geom_mean_stable", gm_stable, gm_exact)]
    )

    # Test 4: Distance Calculation
    print("[4] Auditing distance calculations...")
    x1, y1 = 1e100, 1e100
    x2, y2 = 1e100 + 1.0, 1e100

    # Expected distance is approximately 1.0
    dist_naive = distance_2d_naive(x1, y1, x2, y2)
    dist_stable = distance_2d_stable(x1, y1, x2, y2)

    # Exact should be 1.0
    exact_dist = Decimal('1.0')

    runner.run_custom_probe(
        "distance_naive",
        [("distance_2d_naive", dist_naive, exact_dist)]
    )

    runner.run_custom_probe(
        "distance_stable",
        [("distance_2d_stable", dist_stable, exact_dist)]
    )

    # Test 5: Polynomial Evaluation
    print("[5] Auditing polynomial evaluation...")
    # p(x) = x^4 - 4x^3 + 6x^2 - 4x + 1 = (x-1)^4
    # At x = 1.0001
    coeffs = [1, -4, 6, -4, 1]
    x = 1.0001

    p_naive = polynomial_eval_naive(coeffs, x)
    p_horner = polynomial_eval_horner(coeffs, x)
    p_exact = polynomial_eval_exact(coeffs, x)

    runner.run_custom_probe(
        "polynomial_naive",
        [("poly_naive", p_naive, p_exact)]
    )

    runner.run_custom_probe(
        "polynomial_horner",
        [("poly_horner", p_horner, p_exact)]
    )

    # Generate and print report
    print("\n" + "=" * 80)
    runner.print_report()

    # Optionally save JSON report
    runner.save_report('/tmp/fpaudit_results.json', format='json')
    print("\nJSON report saved to /tmp/fpaudit_results.json")


if __name__ == '__main__':
    run_audit_suite()
