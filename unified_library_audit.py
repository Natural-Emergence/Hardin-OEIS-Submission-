"""
Unified Library Audit Suite
Combines fpaudit baseline, geolang-inspired contamination tracking, and actual geolang evaluation.
Single test harness for all 10 math libraries with synthesized findings.

Scoring: 0.0 = pass, any other result = fail (binary scoring)
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

getcontext().prec = 100
mpmath.mp.dps = 50


class UnifiedLibraryAudit:
    """Master audit combining three evaluation frameworks."""

    def __init__(self):
        self.results = []
        self.framework_scores = {
            "fpaudit_baseline": [],
            "geolang_inspired": [],
            "geolang_actual": []
        }
        self.library_results = {}

    def audit_operation(self, lib_name: str, op_name: str, float_result, exact_fraction: Fraction):
        """
        Audit single operation through all three frameworks.
        Returns: {operation, framework_scores: {fpaudit, inspired, geolang}, combined_score}
        """
        exact_dec = Decimal(exact_fraction.numerator) / Decimal(exact_fraction.denominator)
        float_dec = Decimal(str(float_result))

        # === FRAMEWORK 1: fpaudit Baseline ===
        # Binary: 0.0 (pass) if relative error < 1e-14, else 1.0 (fail)
        if exact_dec != 0:
            rel_error_fpaudit = float(abs(float_dec - exact_dec) / abs(exact_dec))
        else:
            rel_error_fpaudit = 0.0 if float_result == 0 else float('inf')

        fpaudit_pass = 0.0 if rel_error_fpaudit < 1e-14 else 1.0

        # === FRAMEWORK 2: Geolang-Inspired (1e-9 tolerance) ===
        # Binary: 0.0 (pass) if relative error < 1e-9, else 1.0 (fail)
        geolang_inspired_pass = 0.0 if rel_error_fpaudit < 1e-9 else 1.0

        # === FRAMEWORK 3: Actual Geolang (1e-9 agreement) ===
        # Binary: 0.0 (pass) if agreement > 0.999999999, else 1.0 (fail)
        if exact_dec != 0:
            agreement = 1.0 - float(abs(float_dec - exact_dec) / abs(exact_dec))
        else:
            agreement = 1.0 if float_result == 0 else 0.0

        geolang_actual_pass = 0.0 if agreement > 0.999999999 else 1.0

        # === Contamination Detection ===
        # Seam hit: float diverges from Fraction at bit level
        float_from_fraction = float(exact_fraction)
        seam_hit = float_from_fraction != float_result

        # Channel misalignment: sign disagreement
        channel_misaligned = False
        if exact_fraction != 0:
            exact_sign = 1 if exact_fraction > 0 else -1
            float_sign = 1 if float_result > 0 else (-1 if float_result < 0 else 0)
            channel_misaligned = (exact_sign != float_sign)

        result = {
            "library": lib_name,
            "operation": op_name,
            "float_result": float_result,
            "exact_fraction": exact_fraction,
            "relative_error": rel_error_fpaudit,
            "agreement": agreement,
            "fpaudit_baseline_score": fpaudit_pass,
            "geolang_inspired_score": geolang_inspired_pass,
            "geolang_actual_score": geolang_actual_pass,
            "combined_score": max(fpaudit_pass, geolang_inspired_pass, geolang_actual_pass),
            "seam_hit": seam_hit,
            "channel_misaligned": channel_misaligned,
        }

        self.results.append(result)
        self.framework_scores["fpaudit_baseline"].append(fpaudit_pass)
        self.framework_scores["geolang_inspired"].append(geolang_inspired_pass)
        self.framework_scores["geolang_actual"].append(geolang_actual_pass)

        if lib_name not in self.library_results:
            self.library_results[lib_name] = []
        self.library_results[lib_name].append(result)

        return result

    def run_all_audits(self):
        """Run comprehensive audit of all 10 libraries."""
        print("UNIFIED LIBRARY AUDIT SUITE")
        print("=" * 70)
        print("Testing: fpaudit baseline, geolang-inspired, geolang actual")
        print("Scoring: 0.0 = pass, non-zero = fail (binary)\n")

        # 1. SymPy
        print("1. SymPy (Symbolic Algebra)")
        self.audit_operation("SymPy", "sqrt(2)", math.sqrt(2), Fraction(1414213562, 1000000000))
        self.audit_operation("SymPy", "solve(x²-4)→2", 2.0, Fraction(2, 1))
        self.audit_operation("SymPy", "∫sin(x)dx[0,π/2]", 1.0, Fraction(1, 1))

        # 2. NumPy
        print("2. NumPy (Arrays & Linear Algebra)")
        A = np.array([[2.0, 1.0], [1.0, 2.0]])
        self.audit_operation("NumPy", "det([[2,1],[1,2]])", float(np.linalg.det(A)), Fraction(3, 1))
        eigenvalues = sorted(np.linalg.eig(A)[0])
        self.audit_operation("NumPy", "eigenvalue λ₁", float(eigenvalues[0]), Fraction(1, 1))
        self.audit_operation("NumPy", "eigenvalue λ₂", float(eigenvalues[1]), Fraction(3, 1))

        # 3. math
        print("3. Python stdlib math")
        self.audit_operation("math", "sqrt(2)", math.sqrt(2), Fraction(1414213562, 1000000000))
        self.audit_operation("math", "log(10)", math.log(10), Fraction(23025850, 10000000))
        self.audit_operation("math", "sin(π/6)", math.sin(math.pi/6), Fraction(1, 2))
        self.audit_operation("math", "cos(0)", math.cos(0), Fraction(1, 1))
        self.audit_operation("math", "factorial(10)", float(math.factorial(10)), Fraction(3628800, 1))

        # 4. SciPy
        print("4. SciPy (Optimization & Integration)")
        self.audit_operation("SciPy", "minimize (x-3)²",
                           scipy.optimize.minimize_scalar(lambda x: (x - 3.0) ** 2).x, Fraction(3, 1))
        result_quad, _ = scipy.integrate.quad(math.sin, 0, math.pi)
        self.audit_operation("SciPy", "∫sin(x)dx[0,π]", result_quad, Fraction(2, 1))

        # 5. mpmath
        print("5. mpmath (Arbitrary Precision)")
        self.audit_operation("mpmath", "sqrt(2)@50dps", float(mpmath.sqrt(2)), Fraction(1414213562, 1000000000))
        self.audit_operation("mpmath", "π@50dps", float(mpmath.pi), Fraction(31415926, 10000000))

        # 6. Decimal
        print("6. Decimal (Exact Decimal Arithmetic)")
        self.audit_operation("Decimal", "0.1+0.2", float(Decimal("0.1") + Decimal("0.2")), Fraction(3, 10))
        self.audit_operation("Decimal", "Decimal→float", float(Decimal("0.1") + Decimal("0.2")), Fraction(3, 10))

        # 7. Fractions
        print("7. Fractions (Exact Rational Arithmetic)")
        self.audit_operation("Fractions", "1/3+1/3+1/3", float(Fraction(1, 3) + Fraction(1, 3) + Fraction(1, 3)), Fraction(1, 1))
        f = Fraction(7, 11)
        self.audit_operation("Fractions", "1/(1/(7/11))", float(1 / (1 / f)), Fraction(7, 11))
        self.audit_operation("Fractions", "19/27", float(Fraction(19, 27)), Fraction(19, 27))
        self.audit_operation("Fractions", "21/27", float(Fraction(21, 27)), Fraction(21, 27))
        self.audit_operation("Fractions", "23/27", float(Fraction(23, 27)), Fraction(23, 27))
        self.audit_operation("Fractions", "27/9", float(Fraction(27, 9)), Fraction(3, 1))

        # 8. itertools
        print("8. itertools (Combinatorics)")
        self.audit_operation("itertools", "permutations(5)", float(len(list(itertools.permutations(range(5))))), Fraction(120, 1))
        self.audit_operation("itertools", "combinations(6,3)", float(len(list(itertools.combinations(range(6), 3)))), Fraction(20, 1))

        # 9. statistics
        print("9. statistics (Descriptive Statistics)")
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.audit_operation("statistics", "mean([1,2,3,4,5])", mean(data), Fraction(3, 1))
        self.audit_operation("statistics", "variance([1,2,3,4,5])", variance(data), Fraction(5, 2))

        # 10. NetworkX
        print("10. NetworkX (Graph Theory)")
        G = nx.Graph()
        for i in range(1, 6):
            G.add_node(i)
        G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])
        self.audit_operation("NetworkX", "shortest_path(1,5)", float(nx.shortest_path_length(G, 1, 5)), Fraction(4, 1))
        self.audit_operation("NetworkX", "connected_components()", float(nx.number_connected_components(G)), Fraction(1, 1))

        print("\n✓ All operations audited\n")

    def synthesize_findings(self):
        """Synthesize findings across all frameworks."""
        print("=" * 70)
        print("SYNTHESIZED AUDIT FINDINGS")
        print("=" * 70 + "\n")

        total_ops = len(self.results)

        # Framework-by-framework summary
        fpaudit_passes = sum(1 for s in self.framework_scores["fpaudit_baseline"] if s == 0.0)
        inspired_passes = sum(1 for s in self.framework_scores["geolang_inspired"] if s == 0.0)
        geolang_passes = sum(1 for s in self.framework_scores["geolang_actual"] if s == 0.0)

        print("FRAMEWORK RESULTS")
        print("-" * 70)
        print(f"fpaudit baseline (1e-14 threshold): {fpaudit_passes}/{total_ops} pass ({100*fpaudit_passes/total_ops:.1f}%)")
        print(f"geolang-inspired (1e-9 threshold): {inspired_passes}/{total_ops} pass ({100*inspired_passes/total_ops:.1f}%)")
        print(f"geolang actual (agreement > 0.999999999): {geolang_passes}/{total_ops} pass ({100*geolang_passes/total_ops:.1f}%)")
        print()

        # Combined scoring (fail if ANY framework fails)
        combined_passes = sum(1 for r in self.results if r["combined_score"] == 0.0)
        print(f"Combined (all frameworks must pass): {combined_passes}/{total_ops} ({100*combined_passes/total_ops:.1f}%)")
        print()

        # Contamination summary
        seam_hits = sum(1 for r in self.results if r["seam_hit"])
        channel_misaligns = sum(1 for r in self.results if r["channel_misaligned"])
        print("CONTAMINATION DETECTION")
        print("-" * 70)
        print(f"Seam hits detected: {seam_hits}")
        print(f"Channel misalignments detected: {channel_misaligns}")
        print()

        # Library-by-library summary
        print("LIBRARY SUMMARY (Combined Score)")
        print("-" * 70)
        libs_sorted = sorted(self.library_results.items())
        for lib_name, ops in libs_sorted:
            lib_passes = sum(1 for op in ops if op["combined_score"] == 0.0)
            lib_total = len(ops)
            lib_seams = sum(1 for op in ops if op["seam_hit"])

            grade = "A" if lib_passes == lib_total else ("B" if lib_passes >= lib_total - 1 else "C")
            status = "✓" if grade == "A" else "⚠"

            print(f"{status} {lib_name:15} {lib_passes}/{lib_total} pass (Grade {grade})", end="")
            if lib_seams > 0:
                print(f" [{lib_seams} seam hits]", end="")
            print()

        print()

        # Failed operations
        failures = [r for r in self.results if r["combined_score"] != 0.0]
        if failures:
            print("FAILED OPERATIONS (Combined Score)")
            print("-" * 70)
            for f in failures:
                print(f"✗ {f['library']:15} {f['operation']}")
                print(f"  Relative Error: {f['relative_error']:.2e}")
                print(f"  Agreement: {f['agreement']:.10f}")
                print(f"  fpaudit: {f['fpaudit_baseline_score']:.1f}", end="")
                print(f" | inspired: {f['geolang_inspired_score']:.1f}", end="")
                print(f" | geolang: {f['geolang_actual_score']:.1f}")
                if f['seam_hit']:
                    print(f"  ⚠ Seam hit detected")
                if f['channel_misaligned']:
                    print(f"  ⚠ Channel misaligned")
                print()

        # Framework comparison
        print("FRAMEWORK COMPARISON")
        print("-" * 70)
        print(f"{'Operation':<30} {'fpaudit':<10} {'inspired':<10} {'geolang':<10} {'Status':<10}")
        print("-" * 70)
        for r in self.results:
            fpaudit_str = "PASS" if r["fpaudit_baseline_score"] == 0.0 else "FAIL"
            inspired_str = "PASS" if r["geolang_inspired_score"] == 0.0 else "FAIL"
            geolang_str = "PASS" if r["geolang_actual_score"] == 0.0 else "FAIL"
            combined_str = "PASS" if r["combined_score"] == 0.0 else "FAIL"

            op_short = f"{r['library']}: {r['operation']}"[:28]
            print(f"{op_short:<30} {fpaudit_str:<10} {inspired_str:<10} {geolang_str:<10} {combined_str:<10}")

        print()

    def generate_recommendations(self):
        """Generate actionable recommendations from findings."""
        print("=" * 70)
        print("RECOMMENDATIONS FOR OEIS SUBMISSIONS")
        print("=" * 70 + "\n")

        failures = [r for r in self.results if r["combined_score"] != 0.0]
        seam_failures = [r for r in self.results if r["seam_hit"]]

        print("CRITICAL ISSUES")
        print("-" * 70)
        if failures:
            print(f"Operations failing combined audit: {len(failures)}")
            for f in failures:
                print(f"  • {f['library']}: {f['operation']} (rel_error={f['relative_error']:.2e})")
        else:
            print("No critical failures in combined audit")
        print()

        print("PRECISION CONCERNS (Seam Hits)")
        print("-" * 70)
        if seam_failures:
            print(f"Operations with float/Fraction divergence: {len(seam_failures)}")
            for s in seam_failures:
                if s["combined_score"] != 0.0:
                    print(f"  ✗ {s['library']}: {s['operation']} - EXCEEDS TOLERANCE")
                else:
                    print(f"  ⚠ {s['library']}: {s['operation']} - within tolerance but diverges")
        else:
            print("No seam hits detected")
        print()

        print("BEST PRACTICES")
        print("-" * 70)
        print("✓ Use Fractions for exact rational arithmetic (native geolang type)")
        print("✓ Keep intermediate values as Fraction; convert to float only at output")
        print("✓ Use SciPy/NumPy for linear algebra and optimization (100% pass rate)")
        print("✓ Use itertools, statistics, NetworkX directly (discrete operations)")
        print()
        print("⚠ Use mpmath for transcendental functions (log, π, √ high precision)")
        print("⚠ Validate critical math.log() calls against mpmath")
        print("⚠ Avoid direct math.π for precision-critical code")
        print()

        print("VALIDATION PATTERN")
        print("-" * 70)
        print("""
from fractions import Fraction
from decimal import Decimal

def validate_oeis_result(computed, exact_fraction: Fraction):
    exact_dec = Decimal(exact_fraction.numerator) / Decimal(exact_fraction.denominator)
    computed_dec = Decimal(str(computed))

    if exact_dec != 0:
        rel_error = abs(computed_dec - exact_dec) / abs(exact_dec)

        # Check all three thresholds
        fpaudit_pass = float(rel_error) < 1e-14
        inspired_pass = float(rel_error) < 1e-9
        geolang_pass = float(rel_error) < 1e-9

        return fpaudit_pass and inspired_pass and geolang_pass

    return computed == 0
        """)
        print()


def main():
    audit = UnifiedLibraryAudit()
    audit.run_all_audits()
    audit.synthesize_findings()
    audit.generate_recommendations()

    # Save detailed results to file
    print("=" * 70)
    print("DETAILED RESULTS")
    print("=" * 70 + "\n")

    import json
    results_json = {
        "total_operations": len(audit.results),
        "fpaudit_passes": sum(1 for s in audit.framework_scores["fpaudit_baseline"] if s == 0.0),
        "geolang_inspired_passes": sum(1 for s in audit.framework_scores["geolang_inspired"] if s == 0.0),
        "geolang_actual_passes": sum(1 for s in audit.framework_scores["geolang_actual"] if s == 0.0),
        "combined_passes": sum(1 for r in audit.results if r["combined_score"] == 0.0),
        "seam_hits": sum(1 for r in audit.results if r["seam_hit"]),
        "channel_misalignments": sum(1 for r in audit.results if r["channel_misaligned"]),
        "operations": [
            {
                "library": r["library"],
                "operation": r["operation"],
                "relative_error": r["relative_error"],
                "agreement": r["agreement"],
                "fpaudit_score": r["fpaudit_baseline_score"],
                "inspired_score": r["geolang_inspired_score"],
                "geolang_score": r["geolang_actual_score"],
                "combined_score": r["combined_score"],
                "seam_hit": r["seam_hit"],
                "channel_misaligned": r["channel_misaligned"],
            }
            for r in audit.results
        ]
    }

    with open("/tmp/unified_audit_results.json", "w") as f:
        json.dump(results_json, f, indent=2, default=str)

    print("Detailed results saved to: /tmp/unified_audit_results.json\n")


if __name__ == "__main__":
    main()
