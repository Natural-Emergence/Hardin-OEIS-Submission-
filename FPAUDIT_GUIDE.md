# Floating-Point Audit Framework

A comprehensive testing framework for detecting numeric errors in OEIS solutions and mathematical code. Audits computations for floating-point debt, catastrophic cancellation, sign flips, precision loss, and other numeric pathologies.

## Overview

This framework addresses a critical problem: code that claims "zero floating-point error" often accumulates subtle numeric failures that manifest under specific conditions. The fpaudit framework provides:

1. **Core Auditing Engine** (`fpaudit.py`) - Metrics and error detection
2. **Backend Adapters** (`backends.py`) - Compare across float, Decimal, Fraction, SymPy, mpmath
3. **Numeric Probes** (`probes.py`) - Pre-built tests for common error patterns
4. **Test Runner** (`test_runner.py`) - Harness for coordinating tests and reporting

## Files

| File | Purpose |
|------|---------|
| `fpaudit.py` | Core auditing engine with error detection and metrics |
| `backends.py` | Numeric backend adapters for comparative testing |
| `probes.py` | Pre-built probe tests for common floating-point errors |
| `test_runner.py` | Test orchestration and reporting |
| `example_audit.py` | Example usage patterns and demonstration |

## Quick Start

### Run Standard Probes

```bash
python test_runner.py --probes --verbose
```

### Run All Tests

```bash
python test_runner.py --all --output report.txt
```

### Generate JSON Report

```bash
python test_runner.py --all --format json --output report.json
```

### Run Example Audit

```bash
python example_audit.py
```

## Key Concepts

### Error Types

The framework detects:

- **ULP Overflow** - Precision loss exceeds representable range
- **Catastrophic Cancellation** - (a+b) - a ≈ 0 when b is tiny
- **Sign Flip** - Rounding flips the sign of the result
- **Inversion Error** - Reciprocal operations with wrong sign/magnitude
- **Accumulated Rounding** - Sum of small rounding errors
- **Underflow** - Loss of precision near zero
- **Overflow** - Overflow to infinity
- **Precision Loss** - Relative error exceeds threshold

### Core Metrics

**Relative Error** = |float - exact| / |exact|
- Measures magnitude of error relative to answer
- Threshold default: 1e-14

**ULP Distance** = error / ULP
- Units in Last Place distance
- How many floating-point representable numbers away from exact
- Survives total precision loss (clamped to 1e16)

**Shadow Computation**
- Optional higher-precision computation alongside float
- Enables detection of precision loss
- Useful for comparing float vs Decimal/Fraction/mpmath

## Using the Framework

### Basic Audit

```python
from fpaudit import FloatAuditor
from decimal import Decimal

auditor = FloatAuditor(ulp_threshold=2.0, rel_error_threshold=1e-14)

# Audit a single operation
float_result = math.sqrt(2.0)
exact_result = Decimal('2').sqrt()

result = auditor.audit(
    "sqrt(2)",
    float_result,
    exact_result
)

print(auditor.report())
```

### Custom Probe

```python
from test_runner import FloatAuditTestRunner

runner = FloatAuditTestRunner(verbose=True)

# Test a custom operation
runner.run_custom_probe(
    "my_operation",
    [
        ("op1", 0.1 + 0.2, Decimal('0.3')),
        ("op2", 1e16 + 1 - 1e16, Decimal('1')),
    ]
)

runner.print_report()
```

### Audit User Function

```python
from test_runner import FloatAuditTestRunner

def my_sqrt(x):
    return math.sqrt(x)

runner = FloatAuditTestRunner()

test_cases = [
    (2.0, Decimal('2').sqrt()),
    (3.0, Decimal('3').sqrt()),
]

runner.test_user_function("my_sqrt", my_sqrt, test_cases)
runner.print_report()
```

### Compare Backends

```python
from backends import BackendComparison
from decimal import Decimal

comp = BackendComparison()

# Compare sqrt across all backends
result = comp.compare_results(
    "sqrt(2)",
    lambda backend, inputs: backend.sqrt(inputs['x']),
    {'x': 2.0},
    reference_backend='decimal'
)

print(comp.report_comparison([result]))
```

## Built-in Probes

### CatastrophicCancellationProbe
Tests for catastrophic cancellation:
- `(1e16 + 1.0) - 1e16` should equal 1.0 but computes 0.0
- Nearly equal subtraction

### SignFlipProbe
Tests for sign flips due to rounding:
- Subtraction near zero boundaries
- Accumulated subtraction crossing zero

### InversionErrorProbe
Tests for reciprocal/division errors:
- Simple reciprocals (1/3)
- Reciprocals of tiny numbers (potential underflow)
- Reciprocal chains (accumulated error)

### SummationErrorProbe
Tests for accumulated summation errors:
- Naive summation of small + large values
- Alternating sums (high cancellation)

### SqrtAccuracyProbe
Tests square root accuracy:
- sqrt(2) precision
- sqrt of very small numbers
- Chains of square roots

### QuadraticFormulaProbe
Tests quadratic formula implementations:
- Standard formula
- Alternative formula for stability

### ExponentAccuracyProbe
Tests exponential and power operations:
- Large exponents
- Fractional exponents

### PolynomialEvaluationProbe
Tests polynomial evaluation:
- Naive expansion vs Horner's method
- Comparison of numerical stability

## Interpreting Results

### Pass/Fail

An operation **PASSES** if:
- No sign flips detected
- No cancellation artifacts
- Relative error < 1e-14
- ULP distance < 2.0

An operation **FAILS** if any error is detected.

### Report Structure

```
FLOATING-POINT AUDIT REPORT
├─ Summary
│  ├─ Total Operations
│  ├─ Pass Rate
│  ├─ Max Relative Error
│  └─ Max ULP Distance
├─ Error Breakdown (by ErrorType)
├─ Detailed Results
│  └─ Failed Operations with specific errors
└─ Available Backends
```

### Example Failure

```
catastrophic_cancellation: (1e16 + 1.0) - 1e16
  → Catastrophic cancellation detected | (1e16 + 1.0) - 1e16 | severity=1.00e+00
```

## Common Patterns

### Finding the Best Implementation

```python
runner = FloatAuditTestRunner()

# Test naive version
runner.run_custom_probe("quadratic_naive", [...])

# Test stable version
runner.run_custom_probe("quadratic_stable", [...])

# Compare in report
runner.print_report()
```

### Validating Numerical Claims

```python
# Test claim: "zero floating-point error (discrete integer arithmetic only)"
runner.run_probes()  # Run comprehensive probes

summary = runner.auditor.summary()
if summary['failed'] > 0:
    print("Claim VIOLATED: Found floating-point errors")
else:
    print("Claim HOLDS: No floating-point errors detected")
```

### Benchmarking Approaches

```python
# Compare Kahan summation vs naive
test_cases = [
    (sum_naive(n), exact_sum),
    (sum_kahan(n), exact_sum),
]

runner.run_custom_probe("summation_methods", test_cases)
runner.print_report()
```

## Integration with Existing Code

Add to your solution module:

```python
import fpaudit_integration

# At solution function boundaries:
result = solution_function(x, y, z)
auditor = fpaudit_integration.get_auditor()
auditor.audit(f"solution({x},{y},{z})", result, exact_result)

# At the end:
print(auditor.report())
```

## Advanced: Custom Error Detection

Create custom error detectors by subclassing:

```python
from fpaudit import FloatAuditor, ErrorType, NumericError

class CustomAuditor(FloatAuditor):
    def _detect_custom_error(self, result, exact_val):
        # Your detection logic here
        if condition:
            result.errors.append(NumericError(
                ErrorType.PRECISION_LOSS,
                result.result_float,
                exact_val,
                "Custom error message",
                severity
            ))
```

## Performance Notes

- **Float operations**: Fast (~1ms per audit)
- **Decimal backend**: Slower (~50ms per audit)
- **Fraction backend**: Variable (depends on denominator size)
- **SymPy/mpmath**: Slowest (~500ms+ per audit)

For performance-critical code, use float backend with spot-checks via Decimal.

## Limitations

- Detects *symptoms* of floating-point error, not root causes
- Accuracy detection is heuristic (not exhaustive)
- Some error types only visible with high-precision reference
- No detection of errors in dependencies (external libraries)

## See Also

- [What Every Computer Scientist Should Know About Floating-Point Arithmetic](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)
- IEEE 754 Standard
- [The Art of Computer Programming Vol. 2](https://en.wikipedia.org/wiki/The_Art_of_Computer_Programming)
- [Numerical Recipes](http://numerical.recipes/)

## Future Enhancements

- [ ] Automatic regression detection (comparing runs)
- [ ] Memory-safe auditing (bounds checking)
- [ ] GPU backend (CuPy)
- [ ] Integration with pytest/unittest
- [ ] Interactive visualization of error propagation
- [ ] Automated rewriting suggestions for unstable code
