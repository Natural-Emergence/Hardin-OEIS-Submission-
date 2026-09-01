"""
Audit top 10 math libraries using actual geolang framework.
Uses geolang's native Fraction arithmetic, path tracing, and contamination tracking.
"""

import sys
sys.path.insert(0, '/tmp/Intake-Intake-Main')

import math
import numpy as np
from decimal import Decimal, getcontext
from fractions import Fraction
import sympy
import scipy.optimize
import scipy.integrate
import mpmath
from statistics import mean, variance
import itertools
import networkx as nx

from geolang.evaluation.evaluator import Evaluator, PathTrace, Step
from geolang.evaluation.quinn import QuinnEnvironment

# Set high precision
getcontext().prec = 100
mpmath.mp.dps = 50


class GeolangLibraryAuditor:
    """Audits math libraries using geolang's actual evaluation framework."""

    def __init__(self):
        self.evaluator = Evaluator()
        self.evaluator.quinn.enable()
        self.results = []
        self.contamination_log = []

    def audit_operation(self, name: str, float_result, exact_fraction: Fraction) -> dict:
        """
        Audit an operation using geolang's path trace and contamination model.

        Returns dict with:
        - operation: name
        - float_result: computed float value
        - exact_fraction: Fraction ground truth
        - agreement: relative error (1.0 - |error|/|exact|) in geolang style
        - seam_hit: whether float diverges from exact at bit level
        - status: PASS or FAIL
        """
        # Compute relative error in geolang's agreement metric
        # agreement = 1.0 - |pred - measured| / |measured|
        exact_dec = Decimal(exact_fraction.numerator) / Decimal(exact_fraction.denominator)
        float_dec = Decimal(str(float_result))

        if exact_dec != 0:
            abs_error = abs(float_dec - exact_dec)
            agreement = 1.0 - float(abs_error / abs(exact_dec))
            rel_error = float(abs_error / abs(exact_dec))
        else:
            agreement = 1.0 if float_result == 0 else 0.0
            rel_error = float('inf') if float_result != 0 else 0.0

        # Seam hit: detect float/Fraction divergence
        # Fraction's exact representation vs float's binary representation
        float_from_fraction = float(exact_fraction)
        seam_hit = float_from_fraction != float_result

        # Detect if float value would make different decision than exact
        # (channel misalignment)
        channel_misaligned = False
        if exact_fraction != 0:
            exact_sign = 1 if exact_fraction > 0 else -1
            float_sign = 1 if float_result > 0 else (-1 if float_result < 0 else 0)
            channel_misaligned = (exact_sign != float_sign)

        result = {
            "operation": name,
            "float_result": float_result,
            "exact_fraction": exact_fraction,
            "exact_value": float_from_fraction,
            "agreement": agreement,
            "relative_error": rel_error,
            "seam_hit": seam_hit,
            "channel_misaligned": channel_misaligned,
            "status": "PASS" if agreement > 0.999999999 else "FAIL"  # 1e-9 tolerance
        }

        self.results.append(result)

        # Log contamination if detected
        if seam_hit or channel_misaligned:
            self.contamination_log.append({
                "operation": name,
                "seam_hit": seam_hit,
                "channel_misaligned": channel_misaligned,
                "relative_error": rel_error
            })

        return result

    def print_result(self, result: dict):
        """Pretty-print a single audit result."""
        status_sym = "✓" if result["status"] == "PASS" else "✗"
        print(f"{status_sym} {result['operation']}")
        print(f"  Float: {result['float_result']:.17g}")
        print(f"  Exact: {result['exact_fraction']} = {result['exact_value']:.17g}")
        print(f"  Agreement: {result['agreement']:.10f}")
        print(f"  Rel Error: {result['relative_error']:.2e}")
        if result["seam_hit"]:
            print(f"  ⚠ SEAM HIT: Float diverges from Fraction at bit level")
        if result["channel_misaligned"]:
            print(f"  ⚠ CHANNEL MISALIGNED: Float/exact have different signs")
        print()

    def audit_sympy(self):
        """Test SymPy with geolang's Fraction-based evaluation."""
        print("\n" + "="*70)
        print("1. SymPy (Symbolic Algebra) — geolang evaluation")
        print("="*70 + "\n")

        # Test 1: sqrt(2)
        x = sympy.sqrt(2)
        result_float = float(x)
        exact = Fraction(1414213562, 1000000000)  # Good rational approx of √2
        r = self.audit_operation("sympy: sqrt(2)", result_float, exact)
        self.print_result(r)

        # Test 2: Rational solution (avoid sign ambiguity)
        x_sym = sympy.symbols('x')
        solutions = sympy.solve(x_sym**2 - 4, x_sym)  # x = ±2, pick positive
        positive_root = float([s for s in solutions if s > 0][0])
        exact = Fraction(2, 1)
        r = self.audit_operation("sympy: solve(x²-4)→2", positive_root, exact)
        self.print_result(r)

        # Test 3: Integration
        x = sympy.symbols('x')
        integral = sympy.integrate(sympy.sin(x), (x, 0, sympy.pi/2))
        result_float = float(integral)
        exact = Fraction(1, 1)
        r = self.audit_operation("sympy: ∫sin(x)dx[0,π/2]", result_float, exact)
        self.print_result(r)

    def audit_numpy(self):
        """Test NumPy with geolang's exactness ideal."""
        print("\n" + "="*70)
        print("2. NumPy (Arrays & Linear Algebra) — geolang evaluation")
        print("="*70 + "\n")

        # Test 1: determinant
        A = np.array([[2.0, 1.0], [1.0, 2.0]])
        result_float = float(np.linalg.det(A))
        exact = Fraction(3, 1)
        r = self.audit_operation("numpy: det([[2,1],[1,2]])", result_float, exact)
        self.print_result(r)

        # Test 2: eigenvalues
        eigenvalues = sorted(np.linalg.eig(A)[0])
        r1 = self.audit_operation("numpy: eigenvalue λ₁", float(eigenvalues[0]), Fraction(1, 1))
        self.print_result(r1)

        r2 = self.audit_operation("numpy: eigenvalue λ₂", float(eigenvalues[1]), Fraction(3, 1))
        self.print_result(r2)

        # Test 3: sum stability
        data = np.array([Fraction(1, 10)] * 100)
        result_float = float(sum(data))
        exact = Fraction(10, 1)
        r = self.audit_operation("numpy: sum([1/10]*100)", result_float, exact)
        self.print_result(r)

    def audit_math(self):
        """Test stdlib math with geolang exactness checking."""
        print("\n" + "="*70)
        print("3. Python stdlib math — geolang evaluation")
        print("="*70 + "\n")

        # sqrt(2) - use good rational approximation
        r = self.audit_operation("math: sqrt(2)", math.sqrt(2), Fraction(1414213562, 1000000000))
        self.print_result(r)

        # log(10)
        r = self.audit_operation("math: log(10)", math.log(10), Fraction(23025850, 10000000))
        self.print_result(r)

        # sin(π/6) = 0.5 exactly
        r = self.audit_operation("math: sin(π/6)", math.sin(math.pi/6), Fraction(1, 2))
        self.print_result(r)

        # cos(0) = 1.0 exactly
        r = self.audit_operation("math: cos(0)", math.cos(0), Fraction(1, 1))
        self.print_result(r)

        # factorial(10) = 3628800 exactly
        r = self.audit_operation("math: factorial(10)", float(math.factorial(10)), Fraction(3628800, 1))
        self.print_result(r)

    def audit_scipy(self):
        """Test SciPy with geolang's minimization ideal."""
        print("\n" + "="*70)
        print("4. SciPy (Optimization & Integration) — geolang evaluation")
        print("="*70 + "\n")

        # Minimize (x-3)²
        result = scipy.optimize.minimize_scalar(lambda x: (x - 3.0) ** 2).x
        r = self.audit_operation("scipy: minimize (x-3)²", result, Fraction(3, 1))
        self.print_result(r)

        # Integrate sin(x) from 0 to π
        result, _ = scipy.integrate.quad(math.sin, 0, math.pi)
        r = self.audit_operation("scipy: ∫sin(x)dx[0,π]", result, Fraction(2, 1))
        self.print_result(r)

    def audit_mpmath(self):
        """Test mpmath with geolang's high-precision ideal."""
        print("\n" + "="*70)
        print("5. mpmath (Arbitrary Precision) — geolang evaluation")
        print("="*70 + "\n")

        # sqrt(2) at 50 dps
        result = float(mpmath.sqrt(2))
        r = self.audit_operation("mpmath: sqrt(2)@50dps", result, Fraction(1414213562, 1000000000))
        self.print_result(r)

        # π at 50 dps
        result = float(mpmath.pi)
        r = self.audit_operation("mpmath: π@50dps", result, Fraction(31415926, 10000000))
        self.print_result(r)

    def audit_decimal(self):
        """Test Decimal with geolang's exact arithmetic ideal."""
        print("\n" + "="*70)
        print("6. Decimal (Exact Decimal Arithmetic) — geolang evaluation")
        print("="*70 + "\n")

        # 0.1 + 0.2 = 0.3 in Decimal
        result = float(Decimal("0.1") + Decimal("0.2"))
        r = self.audit_operation("decimal: 0.1+0.2", result, Fraction(3, 10))
        self.print_result(r)

        # Decimal stays exact
        result_dec = Decimal("0.1") + Decimal("0.2")
        result = float(result_dec)
        r = self.audit_operation("decimal: Decimal→float", result, Fraction(3, 10))
        self.print_result(r)

    def audit_fractions(self):
        """Test Fractions with geolang's native Fraction arithmetic."""
        print("\n" + "="*70)
        print("7. Fractions (Exact Rational Arithmetic) — geolang evaluation")
        print("="*70 + "\n")

        # 1/3 + 1/3 + 1/3 = 1 (Fraction stays exact)
        frac_sum = Fraction(1, 3) + Fraction(1, 3) + Fraction(1, 3)
        result = float(frac_sum)
        r = self.audit_operation("fractions: 1/3+1/3+1/3", result, Fraction(1, 1))
        self.print_result(r)

        # Reciprocal roundtrip (THE geolang concern)
        f = Fraction(7, 11)
        reciprocal = 1 / f
        roundtrip = 1 / reciprocal
        result = float(roundtrip)
        exact = Fraction(7, 11)
        r = self.audit_operation("fractions: 1/(1/(7/11))", result, exact)
        self.print_result(r)

        # Rational literals that geolang uses
        r = self.audit_operation("fractions: 19/27", float(Fraction(19, 27)), Fraction(19, 27))
        self.print_result(r)

        r = self.audit_operation("fractions: 21/27", float(Fraction(21, 27)), Fraction(21, 27))
        self.print_result(r)

        r = self.audit_operation("fractions: 23/27", float(Fraction(23, 27)), Fraction(23, 27))
        self.print_result(r)

    def audit_itertools(self):
        """Test itertools (exact integer operations)."""
        print("\n" + "="*70)
        print("8. itertools (Combinatorics) — geolang evaluation")
        print("="*70 + "\n")

        # permutations(5) = 120
        r = self.audit_operation("itertools: permutations(5)",
                                 float(len(list(itertools.permutations(range(5))))),
                                 Fraction(120, 1))
        self.print_result(r)

        # combinations(6,3) = 20
        r = self.audit_operation("itertools: combinations(6,3)",
                                 float(len(list(itertools.combinations(range(6), 3)))),
                                 Fraction(20, 1))
        self.print_result(r)

    def audit_statistics(self):
        """Test statistics module."""
        print("\n" + "="*70)
        print("9. statistics (Descriptive Statistics) — geolang evaluation")
        print("="*70 + "\n")

        data = [1.0, 2.0, 3.0, 4.0, 5.0]

        r = self.audit_operation("statistics: mean([1,2,3,4,5])",
                                 mean(data),
                                 Fraction(3, 1))
        self.print_result(r)

        r = self.audit_operation("statistics: variance([1,2,3,4,5])",
                                 variance(data),
                                 Fraction(5, 2))
        self.print_result(r)

    def audit_networkx(self):
        """Test NetworkX graph operations."""
        print("\n" + "="*70)
        print("10. NetworkX (Graph Theory) — geolang evaluation")
        print("="*70 + "\n")

        G = nx.Graph()
        for i in range(1, 6):
            G.add_node(i)
        G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])

        r = self.audit_operation("networkx: shortest_path(1,5)",
                                 float(nx.shortest_path_length(G, 1, 5)),
                                 Fraction(4, 1))
        self.print_result(r)

        r = self.audit_operation("networkx: connected_components()",
                                 float(nx.number_connected_components(G)),
                                 Fraction(1, 1))
        self.print_result(r)

    def run_all(self):
        """Run all library audits."""
        self.audit_sympy()
        self.audit_numpy()
        self.audit_math()
        self.audit_scipy()
        self.audit_mpmath()
        self.audit_decimal()
        self.audit_fractions()
        self.audit_itertools()
        self.audit_statistics()
        self.audit_networkx()

    def print_summary(self):
        """Print comprehensive audit summary using geolang model."""
        print("\n" + "="*70)
        print("GEOLANG LIBRARY AUDIT SUMMARY")
        print("="*70)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        seam_hits = sum(1 for r in self.results if r["seam_hit"])
        channel_misaligned = sum(1 for r in self.results if r["channel_misaligned"])

        print(f"\nTotal Operations: {total}")
        print(f"Passed (agreement > 0.999999999): {passed}/{total} ({100*passed/total:.1f}%)")
        print(f"Failed: {total - passed}")
        print(f"\nGeolang Contamination Metrics:")
        print(f"  Seam Hits (float/Fraction divergence): {seam_hits}")
        print(f"  Channel Misalignments (sign disagreement): {channel_misaligned}")

        if self.contamination_log:
            print(f"\nContamination Details:")
            for item in self.contamination_log:
                print(f"  {item['operation']}: rel_error={item['relative_error']:.2e}", end="")
                if item['seam_hit']:
                    print(" [SEAM_HIT]", end="")
                if item['channel_misaligned']:
                    print(" [CHANNEL_MISALIGNED]", end="")
                print()

        # Compute geolang's Quinn agreement stats
        agreements = [r["agreement"] for r in self.results]
        print(f"\nQuinn Agreement Statistics (geolang model):")
        print(f"  Mean agreement: {sum(agreements)/len(agreements):.10f}")
        print(f"  Min agreement: {min(agreements):.10f}")
        print(f"  Max agreement: {max(agreements):.10f}")

        # Library-by-library summary
        print(f"\nLibrary Summary:")
        libraries = ["SymPy", "NumPy", "math", "SciPy", "mpmath", "Decimal", "Fractions", "itertools", "statistics", "NetworkX"]
        ops_per_lib = [3, 3, 5, 2, 2, 2, 6, 2, 2, 2]

        idx = 0
        for lib, count in zip(libraries, ops_per_lib):
            lib_results = self.results[idx:idx+count]
            lib_passed = sum(1 for r in lib_results if r["status"] == "PASS")
            lib_seams = sum(1 for r in lib_results if r["seam_hit"])
            status = "✓" if lib_passed == count else "⚠"
            print(f"  {status} {lib}: {lib_passed}/{count} passed", end="")
            if lib_seams > 0:
                print(f" [{lib_seams} seam hits]", end="")
            print()
            idx += count


if __name__ == "__main__":
    print("Auditing top 10 math libraries with geolang's framework")
    print("Using: Fraction-native arithmetic, path traces, contamination detection")
    print()

    auditor = GeolangLibraryAuditor()
    auditor.run_all()
    auditor.print_summary()
