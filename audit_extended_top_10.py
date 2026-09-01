"""
Extended audit of top 10 math libraries using geolang-inspired contamination tracking.
Combines fpaudit baseline detection with geolang's contamination metrics:
- Seam hits (float/exact divergence)
- Layer anomalies (single-operation precision loss)
- Channel misalignments (decision point disagreement)
"""

import math
import numpy as np
from decimal import Decimal, getcontext
from fractions import Fraction
import sympy
import scipy.special
import scipy.optimize
import scipy.integrate
import mpmath
from statistics import mean, variance
import itertools
import networkx as nx

from fpaudit import FloatAuditor, FloatAuditResult

# Set high precision
getcontext().prec = 100
mpmath.mp.dps = 50


class ExtendedLibraryAuditor:
    """Audits math libraries with geolang-inspired contamination tracking."""

    def __init__(self):
        # Use extended auditor with contamination tracking enabled
        self.auditor = FloatAuditor(
            ulp_threshold=2.0,
            rel_error_threshold=1e-14,
            approx_tolerance=1e-9,  # geolang ~= operator
            enable_contamination_tracking=True
        )
        self.results = {}

    def audit_sympy(self):
        """Test SymPy symbolic algebra → float conversion."""
        print("\n" + "="*70)
        print("1. SymPy (Symbolic Algebra)")
        print("="*70)

        tests = []

        # Test 1: sqrt(2)
        x = sympy.sqrt(2)
        result = float(x)
        exact = Decimal('2').sqrt()
        r = self.auditor.audit("sympy: sqrt(2)", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "sqrt(2) symbolic", result, exact)
        print(f"√2: {result:.17f} | Error: {r.relative_error:.2e}")
        if r.contamination.seam_hits > 0:
            print(f"  ⚠ Seam hit detected!")

        # Test 2: solve for x in x²-2=0
        x_sym = sympy.symbols('x')
        solutions = sympy.solve(x_sym**2 - 2, x_sym)
        result = float(solutions[0])  # Take positive root
        exact = Decimal('2').sqrt()
        r = self.auditor.audit("sympy: solve(x²-2)", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "solve(x²-2)", result, exact)
        print(f"solve(x²-2): {result:.17f} | Error: {r.relative_error:.2e}")
        if r.contamination.channel_misalignments > 0:
            print(f"  ⚠ Channel misalignment!")

        # Test 3: integral of sin(x) from 0 to π/2
        x = sympy.symbols('x')
        integral = sympy.integrate(sympy.sin(x), (x, 0, sympy.pi/2))
        result = float(integral)
        exact = Decimal('1.0')
        r = self.auditor.audit("sympy: ∫sin(x)dx[0,π/2]", result, exact)
        tests.append(r)
        print(f"∫sin(x)dx[0,π/2]: {result:.17f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_numpy(self):
        """Test NumPy linear algebra operations."""
        print("\n" + "="*70)
        print("2. NumPy (Arrays & Linear Algebra)")
        print("="*70)

        tests = []

        # Test 1: determinant of [[2,1],[1,2]]
        A = np.array([[2.0, 1.0], [1.0, 2.0]])
        result = float(np.linalg.det(A))
        exact = Decimal('3.0')
        r = self.auditor.audit("numpy: det([[2,1],[1,2]])", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "det computation", result, exact)
        print(f"det([[2,1],[1,2]]): {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: eigenvalues
        eigenvalues, _ = np.linalg.eig(A)
        eigenvalues_sorted = sorted(eigenvalues)

        # Expected: [1.0, 3.0]
        result_min = float(eigenvalues_sorted[0])
        exact_min = Decimal('1.0')
        r1 = self.auditor.audit("numpy: eigenvalue λ₁", result_min, exact_min)
        tests.append(r1)
        print(f"eigenvalue λ₁: {result_min:.17f} | Error: {r1.relative_error:.2e}")

        result_max = float(eigenvalues_sorted[1])
        exact_max = Decimal('3.0')
        r2 = self.auditor.audit("numpy: eigenvalue λ₂", result_max, exact_max)
        tests.append(r2)
        print(f"eigenvalue λ₂: {result_max:.17f} | Error: {r2.relative_error:.2e}")

        # Test 3: sum of small numbers (accumulation test)
        data = np.array([0.1] * 100)
        result = float(np.sum(data))
        exact = Decimal('10.0')
        r = self.auditor.audit("numpy: sum([0.1]*100)", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "sum accumulation", result, exact)
        print(f"sum([0.1]*100): {result:.17f} | Error: {r.relative_error:.2e}")
        if r.contamination.layer_anomalies > 0:
            print(f"  ⚠ Layer anomaly (accumulation error)")

        return tests

    def audit_math(self):
        """Test Python stdlib math functions."""
        print("\n" + "="*70)
        print("3. Python stdlib math")
        print("="*70)

        tests = []

        # Test 1: sqrt(2)
        result = math.sqrt(2.0)
        exact = Decimal('2').sqrt()
        r = self.auditor.audit("math: sqrt(2)", result, exact)
        tests.append(r)
        print(f"sqrt(2): {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: log(10)
        result = math.log(10.0)
        exact = Decimal('10').ln()
        r = self.auditor.audit("math: log(10)", result, exact)
        tests.append(r)
        print(f"log(10): {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 3: sin(π/6) = 0.5
        result = math.sin(math.pi / 6.0)
        exact = Decimal('0.5')
        r = self.auditor.audit("math: sin(π/6)", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "sin(π/6)", result, exact)
        print(f"sin(π/6): {result:.17f} | Error: {r.relative_error:.2e}")
        if r.approx_equal_to_exact:
            print(f"  ✓ Approx equal (geolang ~=)")

        # Test 4: cos(0) = 1.0
        result = math.cos(0.0)
        exact = Decimal('1.0')
        r = self.auditor.audit("math: cos(0)", result, exact)
        tests.append(r)
        print(f"cos(0): {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 5: factorial(10)
        result = float(math.factorial(10))
        exact = Decimal('3628800')
        r = self.auditor.audit("math: factorial(10)", result, exact)
        tests.append(r)
        print(f"factorial(10): {result:.1f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_scipy(self):
        """Test SciPy optimization and integration."""
        print("\n" + "="*70)
        print("4. SciPy (Optimization & Integration)")
        print("="*70)

        tests = []

        # Test 1: minimize (x-3)²
        def f(x):
            return (x - 3.0) ** 2

        result = scipy.optimize.minimize_scalar(f).x
        exact = Decimal('3.0')
        r = self.auditor.audit("scipy: minimize (x-3)²", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "optimization result", result, exact)
        print(f"minimize (x-3)²: x = {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: integrate sin(x) from 0 to π
        def integrand(x):
            return math.sin(x)

        result, _ = scipy.integrate.quad(integrand, 0, math.pi)
        exact = Decimal('2.0')
        r = self.auditor.audit("scipy: ∫sin(x)dx[0,π]", result, exact)
        tests.append(r)
        print(f"∫sin(x)dx[0,π]: {result:.17f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_mpmath(self):
        """Test mpmath arbitrary precision arithmetic."""
        print("\n" + "="*70)
        print("5. mpmath (Arbitrary Precision)")
        print("="*70)

        tests = []

        # Test 1: sqrt(2) at 50 dps
        result_mp = mpmath.sqrt(2)
        result = float(result_mp)
        exact = Decimal('2').sqrt()
        r = self.auditor.audit("mpmath: sqrt(2) @ 50dps", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "mp sqrt(2) → float", result, exact)
        print(f"sqrt(2) @ 50dps: {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: π at 50 dps
        result_mp = mpmath.pi
        result = float(result_mp)
        exact = Decimal('3.1415926535897932384626433832795')
        r = self.auditor.audit("mpmath: π @ 50dps", result, exact)
        tests.append(r)
        print(f"π @ 50dps: {result:.17f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_decimal(self):
        """Test Decimal exact decimal arithmetic."""
        print("\n" + "="*70)
        print("6. Decimal (Exact Decimal Arithmetic)")
        print("="*70)

        tests = []

        # Test 1: 0.1 + 0.2 = 0.3 (exact in Decimal)
        result = float(Decimal("0.1") + Decimal("0.2"))
        exact = Decimal('0.3')
        r = self.auditor.audit("decimal: 0.1 + 0.2", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "decimal add → float", result, exact)
        print(f"0.1 + 0.2: {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: Decimal("0.1") + Decimal("0.2") (stays Decimal)
        result_dec = Decimal("0.1") + Decimal("0.2")
        result = float(result_dec)
        exact = Decimal('0.3')
        r = self.auditor.audit("decimal: Decimal(0.1+0.2)→float", result, exact)
        tests.append(r)
        print(f"Decimal(0.1+0.2)→float: {result:.17f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_fractions(self):
        """Test Fractions exact rational arithmetic (with geolang's precision concern)."""
        print("\n" + "="*70)
        print("7. Fractions (Exact Rational Arithmetic)")
        print("="*70)

        tests = []

        # Test 1: 1/3 + 1/3 + 1/3 = 1 (exact in Fractions)
        result = float(Fraction(1, 3) + Fraction(1, 3) + Fraction(1, 3))
        exact = Decimal('1.0')
        r = self.auditor.audit("fractions: 1/3+1/3+1/3", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "fraction sum → float", result, exact)
        print(f"1/3+1/3+1/3: {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: reciprocal roundtrip (the known failure case)
        f = Fraction(7, 11)
        reciprocal = 1 / f
        roundtrip = 1 / reciprocal
        result = float(roundtrip)
        exact = Decimal('7') / Decimal('11')
        r = self.auditor.audit("fractions: 1/(1/(7/11))→float", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "reciprocal roundtrip", result, exact)
        print(f"1/(1/(7/11))→float: {result:.17f} | Error: {r.relative_error:.2e}")
        if r.contamination.seam_hits > 0:
            print(f"  ⚠ Seam hit in reciprocal roundtrip (geolang detects float divergence)")
        if r.contamination.channel_misalignments > 0:
            print(f"  ⚠ Channel misalignment in rational operations")

        # Test 3: rational literals that exhibit geolang concern (19/27, 21/27, 23/27)
        result = float(Fraction(19, 27))
        exact = Decimal('19') / Decimal('27')
        r = self.auditor.audit("fractions: 19/27", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "fraction 19/27 → float", result, exact)
        print(f"19/27: {result:.17f} | Error: {r.relative_error:.2e}")

        result = float(Fraction(21, 27))
        exact = Decimal('21') / Decimal('27')
        r = self.auditor.audit("fractions: 21/27", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "fraction 21/27 → float", result, exact)
        print(f"21/27: {result:.17f} | Error: {r.relative_error:.2e}")
        if r.contamination.seam_hits > 0:
            print(f"  ⚠ Seam hit (float ≠ exact at bit level)")

        result = float(Fraction(23, 27))
        exact = Decimal('23') / Decimal('27')
        r = self.auditor.audit("fractions: 23/27", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "fraction 23/27 → float", result, exact)
        print(f"23/27: {result:.17f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_itertools(self):
        """Test itertools combinatorics (exact integer operations)."""
        print("\n" + "="*70)
        print("8. itertools (Combinatorics)")
        print("="*70)

        tests = []

        # Test 1: permutations(5)
        result = float(len(list(itertools.permutations(range(5)))))
        exact = Decimal('120')
        r = self.auditor.audit("itertools: permutations(5)", result, exact)
        tests.append(r)
        print(f"permutations(5): {result:.1f} | Error: {r.relative_error:.2e}")

        # Test 2: combinations(6,3)
        result = float(len(list(itertools.combinations(range(6), 3))))
        exact = Decimal('20')
        r = self.auditor.audit("itertools: combinations(6,3)", result, exact)
        tests.append(r)
        print(f"combinations(6,3): {result:.1f} | Error: {r.relative_error:.2e}")

        return tests

    def audit_statistics(self):
        """Test statistics module (descriptive statistics)."""
        print("\n" + "="*70)
        print("9. statistics (Descriptive Statistics)")
        print("="*70)

        tests = []

        # Test 1: mean
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = mean(data)
        exact = Decimal('3.0')
        r = self.auditor.audit("statistics: mean([1,2,3,4,5])", result, exact)
        tests.append(r)
        print(f"mean([1,2,3,4,5]): {result:.17f} | Error: {r.relative_error:.2e}")

        # Test 2: variance
        result = variance(data)
        exact = Decimal('2.5')
        r = self.auditor.audit("statistics: variance([1,2,3,4,5])", result, exact)
        tests.append(r)
        self.auditor.track_path_step(r, "variance computation", result, exact)
        print(f"variance([1,2,3,4,5]): {result:.17f} | Error: {r.relative_error:.2e}")
        if r.relative_error > 1e-10 and r.relative_error < 1e-7:
            print(f"  ⚠ Layer anomaly in variance computation")

        return tests

    def audit_networkx(self):
        """Test NetworkX graph theory operations."""
        print("\n" + "="*70)
        print("10. NetworkX (Graph Theory)")
        print("="*70)

        tests = []

        # Create simple graph for testing
        G = nx.Graph()
        for i in range(1, 6):
            G.add_node(i)
        G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])

        # Test 1: shortest path length
        result = float(nx.shortest_path_length(G, 1, 5))
        exact = Decimal('4')
        r = self.auditor.audit("networkx: shortest_path_length(1,5)", result, exact)
        tests.append(r)
        print(f"shortest_path_length(1,5): {result:.1f} | Error: {r.relative_error:.2e}")

        # Test 2: number of connected components
        result = float(nx.number_connected_components(G))
        exact = Decimal('1')
        r = self.auditor.audit("networkx: number_connected_components()", result, exact)
        tests.append(r)
        print(f"number_connected_components(): {result:.1f} | Error: {r.relative_error:.2e}")

        return tests

    def run_all(self):
        """Run all audits and generate report."""
        all_tests = []
        all_tests.extend(self.audit_sympy())
        all_tests.extend(self.audit_numpy())
        all_tests.extend(self.audit_math())
        all_tests.extend(self.audit_scipy())
        all_tests.extend(self.audit_mpmath())
        all_tests.extend(self.audit_decimal())
        all_tests.extend(self.audit_fractions())
        all_tests.extend(self.audit_itertools())
        all_tests.extend(self.audit_statistics())
        all_tests.extend(self.audit_networkx())

        return all_tests

    def print_summary(self):
        """Print extended audit summary."""
        print("\n" + "="*70)
        print("EXTENDED AUDIT SUMMARY (geolang-inspired metrics)")
        print("="*70)
        summary = self.auditor.summary()
        print(self.auditor.report())
        print("\n" + "="*70)
        print("GEOLANG CONTAMINATION ANALYSIS")
        print("="*70)
        print(f"Total Seam Hits: {summary['contamination']['total_seam_hits']}")
        print(f"Total Layer Anomalies: {summary['contamination']['total_layer_anomalies']}")
        print(f"Total Channel Misalignments: {summary['contamination']['total_channel_misalignments']}")
        print(f"Max Contamination Level: {summary['contamination']['max_contamination_level']:.2e}")
        print(f"\nApprox Equal (geolang ~=): {summary['approx_equal_count']} operations")


if __name__ == "__main__":
    auditor = ExtendedLibraryAuditor()
    auditor.run_all()
    auditor.print_summary()
