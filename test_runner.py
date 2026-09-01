"""
Test runner and harness for floating-point auditing framework.
Coordinates probe execution, result aggregation, and report generation.
"""

import sys
import json
import time
from typing import Callable, Dict, Any, List, Optional
from datetime import datetime

from fpaudit import FloatAuditor, FloatAuditResult
from backends import BackendComparison, get_available_backends
from probes import (
    CatastrophicCancellationProbe,
    SignFlipProbe,
    InversionErrorProbe,
    SummationErrorProbe,
    SqrtAccuracyProbe,
    QuadraticFormulaProbe,
    ExponentAccuracyProbe,
    PolynomialEvaluationProbe,
    run_all_probes
)


class FloatAuditTestRunner:
    """Orchestrates floating-point audit testing."""

    def __init__(self, verbose: bool = False, output_format: str = 'text'):
        self.verbose = verbose
        self.output_format = output_format
        self.auditor = FloatAuditor()
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_probes(self) -> Dict[str, Any]:
        """Run all built-in probes."""
        self.start_time = time.time()

        if self.verbose:
            print("Running floating-point error probes...")

        results = run_all_probes()

        self.end_time = time.time()
        self.results['probes'] = results

        return results

    def run_custom_probe(self, name: str, operations: List[tuple]) -> Dict[str, Any]:
        """
        Run custom audit operations.

        Args:
            name: Probe name
            operations: List of (op_name, float_result, exact_result) tuples

        Returns:
            Probe results
        """
        if self.verbose:
            print(f"Running custom probe: {name}")

        probe_results = {
            'probe': name,
            'operations_tested': len(operations),
            'results': []
        }

        for op_name, float_result, exact_result in operations:
            result = self.auditor.audit(op_name, float_result, exact_result)
            probe_results['results'].append(result)

        probe_results['passed'] = all(r.passed() for r in probe_results['results'])
        self.results[name] = probe_results

        return probe_results

    def compare_backends(self, name: str, fn: Callable, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run computation across all backends and compare.

        Args:
            name: Operation name
            fn: Function to compute (receives backend and cast inputs)
            inputs: Input values

        Returns:
            Comparison results
        """
        if self.verbose:
            print(f"Running backend comparison: {name}")

        comp = BackendComparison()
        comparison = comp.compare_results(name, fn, inputs)

        self.results[f'backend_cmp_{name}'] = comparison

        return comparison

    def test_user_function(self, func_name: str, func: Callable, test_cases: List[tuple]) -> Dict[str, Any]:
        """
        Audit a user-provided function.

        Args:
            func_name: Name of function
            func: The function to audit
            test_cases: List of (inputs, expected_output) tuples

        Returns:
            Audit results for function
        """
        if self.verbose:
            print(f"Auditing user function: {func_name}")

        results = {
            'function': func_name,
            'test_cases': len(test_cases),
            'operations': []
        }

        for inputs, expected in test_cases:
            try:
                if isinstance(inputs, (list, tuple)):
                    output = func(*inputs)
                else:
                    output = func(inputs)

                audit_result = self.auditor.audit(
                    f"{func_name}({inputs})",
                    output,
                    expected
                )
                results['operations'].append(audit_result)
            except Exception as e:
                results['operations'].append({
                    'error': str(e),
                    'inputs': inputs
                })

        results['passed'] = all(isinstance(r, FloatAuditResult) and r.passed() for r in results['operations'])

        return results

    def generate_report(self, include_details: bool = True) -> str:
        """Generate comprehensive audit report."""
        lines = []

        lines.append("=" * 80)
        lines.append("FLOATING-POINT AUDIT TEST REPORT")
        lines.append("=" * 80)
        lines.append(f"Timestamp: {datetime.now().isoformat()}")

        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            lines.append(f"Duration: {duration:.2f}s")

        lines.append("")
        lines.append("SUMMARY")
        lines.append("-" * 80)

        # Aggregate statistics
        total_ops = 0
        total_passed = 0
        total_failed = 0

        for result_name, result_data in self.results.items():
            if 'operations_tested' in result_data:
                total_ops += result_data['operations_tested']
                passed = sum(1 for r in result_data.get('results', []) if hasattr(r, 'passed') and r.passed())
                total_passed += passed
                total_failed += result_data['operations_tested'] - passed

        pass_rate = (total_passed / total_ops * 100) if total_ops > 0 else 0

        lines.append(f"Total Operations Tested: {total_ops}")
        lines.append(f"Passed: {total_passed}")
        lines.append(f"Failed: {total_failed}")
        lines.append(f"Pass Rate: {pass_rate:.1f}%")

        # Auditor summary
        if hasattr(self.auditor, 'summary'):
            summary = self.auditor.summary()
            lines.append(f"Max Relative Error: {summary['max_relative_error']:.2e}")
            lines.append(f"Max ULP Distance: {summary['max_ulp_distance']:.2e}")

        if include_details and self.results:
            lines.append("")
            lines.append("DETAILED RESULTS")
            lines.append("-" * 80)

            for result_name, result_data in self.results.items():
                lines.append(f"\n{result_name}:")
                if 'error' in result_data:
                    lines.append(f"  ERROR: {result_data['error']}")
                elif 'operations_tested' in result_data:
                    lines.append(f"  Operations: {result_data['operations_tested']}")
                    lines.append(f"  Status: {'PASSED' if result_data.get('passed', False) else 'FAILED'}")

                    if 'results' in result_data:
                        failed_ops = [r for r in result_data['results'] if hasattr(r, 'passed') and not r.passed()]
                        if failed_ops:
                            lines.append("  Failed operations:")
                            for op in failed_ops[:5]:  # Limit output
                                lines.append(f"    - {op.operation}")
                                for error in op.errors:
                                    lines.append(f"      {error}")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_json_report(self) -> str:
        """Generate JSON format report."""
        # Convert audit results to JSON-serializable format
        json_results = {}

        for key, value in self.results.items():
            if isinstance(value, dict):
                json_results[key] = self._serialize_result(value)

        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': (self.end_time - self.start_time) if (self.start_time and self.end_time) else None,
            'available_backends': get_available_backends(),
            'results': json_results
        }

        return json.dumps(report, indent=2, default=str)

    def _serialize_result(self, obj: Any) -> Any:
        """Recursively serialize result objects."""
        if isinstance(obj, dict):
            return {k: self._serialize_result(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_result(item) for item in obj]
        elif isinstance(obj, FloatAuditResult):
            return {
                'operation': obj.operation,
                'result_float': obj.result_float,
                'relative_error': obj.relative_error,
                'ulp_distance': obj.ulp_distance,
                'passed': obj.passed(),
                'errors': [str(e) for e in obj.errors]
            }
        elif isinstance(obj, float) and (obj == float('inf') or obj == float('-inf') or obj != obj):
            return str(obj)
        else:
            return obj

    def print_report(self):
        """Print formatted text report to stdout."""
        print(self.generate_report(include_details=True))

    def save_report(self, filepath: str, format: str = 'text'):
        """Save report to file."""
        with open(filepath, 'w') as f:
            if format == 'json':
                f.write(self.generate_json_report())
            else:
                f.write(self.generate_report(include_details=True))

        if self.verbose:
            print(f"Report saved to {filepath}")


def main():
    """Command-line interface for test runner."""
    import argparse

    parser = argparse.ArgumentParser(description='Floating-point audit test runner')
    parser.add_argument('--probes', action='store_true', help='Run standard probes')
    parser.add_argument('--backends', action='store_true', help='Compare backends')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output', '-o', type=str, help='Output file')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='Output format')
    parser.add_argument('--all', action='store_true', help='Run all tests')

    args = parser.parse_args()

    runner = FloatAuditTestRunner(verbose=args.verbose, output_format=args.format)

    # Default: run probes if nothing specified
    if args.all or not (args.probes or args.backends):
        runner.run_probes()

    if args.backends:
        # Run some backend comparisons
        comp_fn = lambda backend, inputs: backend.sqrt(inputs['x'])
        runner.compare_backends('sqrt_2', comp_fn, {'x': 2.0})

    if args.output:
        runner.save_report(args.output, format=args.format)
    else:
        runner.print_report()


if __name__ == '__main__':
    main()
