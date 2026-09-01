"""
Comprehensive fpaudit of the top 10 math libraries used by Claude Code.

Audits each library's core operations against high-precision references
to quantify floating-point debt and identify best practices.
"""

import sys
import math
from decimal import Decimal, getcontext
from fractions import Fraction
import traceback

getcontext().prec = 100

from test_runner import FloatAuditTestRunner
from fpaudit import FloatAuditor

# Try to import all 10 libraries
libraries = {}
try:
    import numpy as np
    libraries['numpy'] = np
except ImportError:
    print("⚠ numpy not installed")

try:
    from scipy import optimize, integrate, linalg
    libraries['scipy'] = {'optimize': optimize, 'integrate': integrate, 'linalg': linalg}
except ImportError:
    print("⚠ scipy not installed")

try:
    import sympy as sp
    libraries['sympy'] = sp
except ImportError:
    print("⚠ sympy not installed")

try:
    import mpmath as mp
    mp.dps = 50
    libraries['mpmath'] = mp
except ImportError:
    print("⚠ mpmath not installed")

try:
    import matplotlib.pyplot as plt
    libraries['matplotlib'] = plt
except ImportError:
    print("⚠ matplotlib not installed")

try:
    import networkx as nx
    libraries['networkx'] = nx
except ImportError:
    print("⚠ networkx not installed")

try:
    from scipy import stats
    libraries['scipy.stats'] = stats
except ImportError:
    print("⚠ scipy.stats not installed")

# Stdlib modules are always available
libraries['math'] = math
libraries['fractions'] = Fraction
libraries['decimal'] = Decimal

print("=" * 90)
print("FPAUDIT: TOP 10 MATH LIBRARIES")
print("=" * 90)

runner = FloatAuditTestRunner(verbose=False)
results = {}

# ============================================================================
# 1. SYMPY - Symbolic Algebra
# ============================================================================

print("\n1. SymPy (Symbolic Algebra)")
print("-" * 90)

if 'sympy' in libraries:
    sp = libraries['sympy']
    sympy_tests = []

    try:
        # sqrt(2)
        sym_sqrt2 = sp.sqrt(2)
        float_sqrt2 = float(sym_sqrt2)
        exact_sqrt2 = Decimal(2).sqrt()

        result = runner.auditor.audit("SymPy: sqrt(2)", float_sqrt2, exact_sqrt2)
        sympy_tests.append(result)
        print(f"  sqrt(2): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # Solve equation
        x = sp.symbols('x')
        solutions = sp.solve(x**2 - 2, x)
        sol_float = float(solutions[1])  # Positive root

        result = runner.auditor.audit("SymPy: solve(x²-2)", sol_float, exact_sqrt2)
        sympy_tests.append(result)
        print(f"  solve(x²-2): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # Integration
        expr = sp.sin(x)
        integral = sp.integrate(expr, (x, 0, sp.pi/2))
        int_float = float(integral)
        exact_int = Decimal(1)  # ∫sin(x)dx from 0 to π/2 = 1

        result = runner.auditor.audit("SymPy: ∫sin(x)dx[0,π/2]", int_float, exact_int)
        sympy_tests.append(result)
        print(f"  ∫sin(x): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        passed = sum(1 for r in sympy_tests if r.passed())
        print(f"  SymPy: {passed}/{len(sympy_tests)} tests passed")
        results['sympy'] = {'passed': passed, 'total': len(sympy_tests), 'tests': sympy_tests}
    except Exception as e:
        print(f"  ✗ Error: {e}")

# ============================================================================
# 2. NUMPY - Arrays and Linear Algebra
# ============================================================================

print("\n2. NumPy (Arrays & Linear Algebra)")
print("-" * 90)

if 'numpy' in libraries:
    np = libraries['numpy']
    numpy_tests = []

    try:
        # Matrix inversion roundtrip
        A = np.array([[2.0, 1.0], [1.0, 2.0]])
        A_inv = np.linalg.inv(A)
        identity = A @ A_inv

        # Exact value
        exact_det = Decimal(3)  # det([[2,1],[1,2]]) = 3
        float_det = float(np.linalg.det(A))

        result = runner.auditor.audit("NumPy: det([[2,1],[1,2]])", float_det, exact_det)
        numpy_tests.append(result)
        print(f"  det([[2,1],[1,2]]): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # Eigenvalues of symmetric matrix
        eigenvals = np.linalg.eigvalsh(A)
        # Exact eigenvalues: 1, 3

        result = runner.auditor.audit("NumPy: eigvalsh([[2,1],[1,2]])[0]", eigenvals[0], Decimal(1))
        numpy_tests.append(result)
        print(f"  eig λ₁: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        result = runner.auditor.audit("NumPy: eigvalsh([[2,1],[1,2]])[1]", eigenvals[1], Decimal(3))
        numpy_tests.append(result)
        print(f"  eig λ₂: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # Sum precision (classic problem)
        vals = np.array([0.1] * 100)
        np_sum = np.sum(vals)
        exact_sum = Decimal('10')  # 0.1 * 100 = 10

        result = runner.auditor.audit("NumPy: sum([0.1]*100)", np_sum, exact_sum)
        numpy_tests.append(result)
        print(f"  sum([0.1]*100): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        passed = sum(1 for r in numpy_tests if r.passed())
        print(f"  NumPy: {passed}/{len(numpy_tests)} tests passed")
        results['numpy'] = {'passed': passed, 'total': len(numpy_tests), 'tests': numpy_tests}
    except Exception as e:
        print(f"  ✗ Error: {e}")

# ============================================================================
# 3. Python stdlib math
# ============================================================================

print("\n3. Python stdlib math")
print("-" * 90)

math_tests = []

try:
    # sqrt
    result = runner.auditor.audit("math.sqrt(2)", math.sqrt(2), Decimal(2).sqrt())
    math_tests.append(result)
    print(f"  sqrt(2): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # log
    result = runner.auditor.audit("math.log(10)", math.log(10), Decimal(10).ln())
    math_tests.append(result)
    print(f"  log(10): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # sin(π/6) = 0.5
    result = runner.auditor.audit("math.sin(π/6)", math.sin(math.pi/6), Decimal('0.5'))
    math_tests.append(result)
    print(f"  sin(π/6): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # cos(0) = 1
    result = runner.auditor.audit("math.cos(0)", math.cos(0), Decimal(1))
    math_tests.append(result)
    print(f"  cos(0): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # factorial
    result = runner.auditor.audit("math.factorial(10)", float(math.factorial(10)), Decimal(3628800))
    math_tests.append(result)
    print(f"  factorial(10): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    passed = sum(1 for r in math_tests if r.passed())
    print(f"  stdlib math: {passed}/{len(math_tests)} tests passed")
    results['math'] = {'passed': passed, 'total': len(math_tests), 'tests': math_tests}
except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# 4. SciPy - Optimization & Integration
# ============================================================================

print("\n4. SciPy (Optimization & Integration)")
print("-" * 90)

if 'scipy' in libraries:
    scipy_tests = []

    try:
        from scipy.optimize import fminbound
        from scipy.integrate import quad

        # Minimize (x-3)^2
        def f(x):
            return (x - 3)**2

        minimum = fminbound(f, 0, 5)
        result = runner.auditor.audit("SciPy: minimize (x-3)²", minimum, Decimal(3))
        scipy_tests.append(result)
        print(f"  minimize(x-3)²: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # Integrate sin(x) from 0 to π
        def integrand(x):
            return math.sin(x)

        integral, error = quad(integrand, 0, math.pi)
        result = runner.auditor.audit("SciPy: ∫sin(x)[0,π]", integral, Decimal(2))
        scipy_tests.append(result)
        print(f"  ∫sin(x)[0,π]: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        passed = sum(1 for r in scipy_tests if r.passed())
        print(f"  SciPy: {passed}/{len(scipy_tests)} tests passed")
        results['scipy'] = {'passed': passed, 'total': len(scipy_tests), 'tests': scipy_tests}
    except Exception as e:
        print(f"  ✗ Error: {e}")

# ============================================================================
# 5. mpmath - Arbitrary Precision
# ============================================================================

print("\n5. mpmath (Arbitrary Precision)")
print("-" * 90)

if 'mpmath' in libraries:
    mp = libraries['mpmath']
    mpmath_tests = []

    try:
        # sqrt(2) to 50 digits
        mp_sqrt2 = mp.sqrt(2)
        float_sqrt2 = float(mp_sqrt2)
        exact_sqrt2 = Decimal(2).sqrt()

        result = runner.auditor.audit("mpmath: sqrt(2) @ 50dps", float_sqrt2, exact_sqrt2)
        mpmath_tests.append(result)
        print(f"  sqrt(2): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        # π
        mp_pi = mp.pi
        float_pi = float(mp_pi)
        exact_pi = Decimal('3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679')

        result = runner.auditor.audit("mpmath: π @ 50dps", float_pi, exact_pi)
        mpmath_tests.append(result)
        print(f"  π: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

        passed = sum(1 for r in mpmath_tests if r.passed())
        print(f"  mpmath: {passed}/{len(mpmath_tests)} tests passed")
        results['mpmath'] = {'passed': passed, 'total': len(mpmath_tests), 'tests': mpmath_tests}
    except Exception as e:
        print(f"  ✗ Error: {e}")

# ============================================================================
# 6. Decimal (Exact Decimal Arithmetic)
# ============================================================================

print("\n6. Python decimal (Exact Decimal Arithmetic)")
print("-" * 90)

decimal_tests = []

try:
    # 0.1 + 0.2 = 0.3?
    d1 = Decimal('0.1') + Decimal('0.2')
    exact = Decimal('0.3')
    float_result = float(d1)

    result = runner.auditor.audit("Decimal: 0.1 + 0.2", float_result, exact)
    decimal_tests.append(result)
    print(f"  0.1 + 0.2: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # Decimal preserves exactness
    d_sum = Decimal('0.1') + Decimal('0.2')
    d_exact = Decimal('0.3')
    result = runner.auditor.audit("Decimal: exact 0.1+0.2", float(d_sum), d_exact)
    decimal_tests.append(result)
    print(f"  Decimal 0.1+0.2: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    passed = sum(1 for r in decimal_tests if r.passed())
    print(f"  Decimal: {passed}/{len(decimal_tests)} tests passed")
    results['decimal'] = {'passed': passed, 'total': len(decimal_tests), 'tests': decimal_tests}
except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# 7. Fractions (Exact Rational Arithmetic)
# ============================================================================

print("\n7. Python fractions (Exact Rational Arithmetic)")
print("-" * 90)

fraction_tests = []

try:
    # 1/3 + 1/3 + 1/3 = 1
    f1 = Fraction(1, 3) + Fraction(1, 3) + Fraction(1, 3)
    exact = Fraction(1, 1)
    float_result = float(f1)

    result = runner.auditor.audit("Fraction: 1/3 + 1/3 + 1/3", float_result, exact)
    fraction_tests.append(result)
    print(f"  1/3 + 1/3 + 1/3: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # Reciprocal roundtrip
    f = Fraction(7, 11)
    reciprocal = 1 / f
    roundtrip = 1 / reciprocal

    result = runner.auditor.audit("Fraction: 1/(1/(7/11))", float(roundtrip), f)
    fraction_tests.append(result)
    print(f"  reciprocal roundtrip: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    passed = sum(1 for r in fraction_tests if r.passed())
    print(f"  Fractions: {passed}/{len(fraction_tests)} tests passed")
    results['fractions'] = {'passed': passed, 'total': len(fraction_tests), 'tests': fraction_tests}
except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# 8. itertools (Combinatorics)
# ============================================================================

print("\n8. itertools (Combinatorics)")
print("-" * 90)

try:
    import itertools
    itertools_tests = []

    # Generate permutations and verify count
    perms = list(itertools.permutations(range(5)))
    exact_count = math.factorial(5)

    result = runner.auditor.audit("itertools: permutations(5)", float(len(perms)), Decimal(exact_count))
    itertools_tests.append(result)
    print(f"  permutations(5): {('✓ PASS' if result.passed() else '✗ FAIL'):8} count={len(perms)} (expected {exact_count})")

    # Combinations
    combos = list(itertools.combinations(range(6), 3))
    exact_count = math.comb(6, 3)

    result = runner.auditor.audit("itertools: combinations(6,3)", float(len(combos)), Decimal(exact_count))
    itertools_tests.append(result)
    print(f"  combinations(6,3): {('✓ PASS' if result.passed() else '✗ FAIL'):8} count={len(combos)} (expected {exact_count})")

    passed = sum(1 for r in itertools_tests if r.passed())
    print(f"  itertools: {passed}/{len(itertools_tests)} tests passed")
    results['itertools'] = {'passed': passed, 'total': len(itertools_tests), 'tests': itertools_tests}
except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# 9. statistics (Descriptive Statistics)
# ============================================================================

print("\n9. statistics (Descriptive Statistics)")
print("-" * 90)

try:
    import statistics
    stats_tests = []

    # Mean of [1, 2, 3, 4, 5] = 3
    data = [1, 2, 3, 4, 5]
    mean_val = statistics.mean(data)

    result = runner.auditor.audit("statistics: mean([1,2,3,4,5])", mean_val, Decimal(3))
    stats_tests.append(result)
    print(f"  mean([1,2,3,4,5]): {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    # Variance (one-pass formula)
    variance = statistics.variance(data)
    exact_var = Decimal('2.5')  # variance of [1,2,3,4,5]

    result = runner.auditor.audit("statistics: variance([1,2,3,4,5])", variance, exact_var)
    stats_tests.append(result)
    print(f"  variance: {('✓ PASS' if result.passed() else '✗ FAIL'):8} rel_err={result.relative_error:.2e}")

    passed = sum(1 for r in stats_tests if r.passed())
    print(f"  statistics: {passed}/{len(stats_tests)} tests passed")
    results['statistics'] = {'passed': passed, 'total': len(stats_tests), 'tests': stats_tests}
except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# 10. NetworkX (Graph Algorithms)
# ============================================================================

print("\n10. NetworkX (Graph Theory)")
print("-" * 90)

if 'networkx' in libraries:
    nx = libraries['networkx']
    nx_tests = []

    try:
        # Create a simple graph and compute shortest path
        G = nx.Graph()
        G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])

        shortest = nx.shortest_path_length(G, 1, 5)
        # Path: 1 -> 2 -> 3 -> 4 -> 5 (length 4)

        result = runner.auditor.audit("NetworkX: shortest_path(1,5)", float(shortest), Decimal(4))
        nx_tests.append(result)
        print(f"  shortest_path(1,5): {('✓ PASS' if result.passed() else '✗ FAIL'):8} length={shortest}")

        # Connected components
        components = len(list(nx.connected_components(G)))
        result = runner.auditor.audit("NetworkX: connected_components", float(components), Decimal(1))
        nx_tests.append(result)
        print(f"  connected_components: {('✓ PASS' if result.passed() else '✗ FAIL'):8} count={components}")

        passed = sum(1 for r in nx_tests if r.passed())
        print(f"  NetworkX: {passed}/{len(nx_tests)} tests passed")
        results['networkx'] = {'passed': passed, 'total': len(nx_tests), 'tests': nx_tests}
    except Exception as e:
        print(f"  ✗ Error: {e}")

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 90)
print("SUMMARY: TOP 10 LIBRARIES FPAUDIT RESULTS")
print("=" * 90)

total_passed = 0
total_tests = 0
library_grades = []

for lib_name in ['sympy', 'numpy', 'math', 'scipy', 'mpmath', 'decimal', 'fractions', 'itertools', 'statistics', 'networkx']:
    if lib_name in results:
        res = results[lib_name]
        passed = res['passed']
        total = res['total']
        pct = (passed / total * 100) if total > 0 else 0

        if pct == 100:
            grade = 'A'
        elif pct >= 95:
            grade = 'A-'
        elif pct >= 80:
            grade = 'B'
        else:
            grade = 'C'

        library_grades.append((lib_name, grade, passed, total, pct))
        total_passed += passed
        total_tests += total

        print(f"{lib_name:20} {grade:3}  {passed:2}/{total:2} tests passed  ({pct:5.1f}%)")

print("\n" + "-" * 90)
print(f"{'OVERALL':20} {'':3}  {total_passed}/{total_tests} tests passed  ({total_passed/total_tests*100:5.1f}%)")
print("=" * 90)

# Rank libraries by reliability
print("\nLIBRARY RELIABILITY RANKING (by fpaudit tests):")
print("-" * 90)
for i, (lib, grade, passed, total, pct) in enumerate(sorted(library_grades, key=lambda x: -x[4]), 1):
    print(f"{i:2}. {lib:20} {grade:3}  {pct:5.1f}%  ({passed}/{total} tests)")

print("\n" + "=" * 90)
print("AUDIT COMPLETE")
print("=" * 90)
