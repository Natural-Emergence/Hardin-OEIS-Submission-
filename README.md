# Hardin OEIS Submission — Floating-Point Audit Framework

A comprehensive testing framework for detecting numeric errors in OEIS solutions. Audits computations for floating-point debt, catastrophic cancellation, sign flips, precision loss, inversion errors, and fractional misrepresentation.

## What This Does

This framework systematically uncovers *hidden* floating-point failures that silently creep into numeric code:

- **Catastrophic Cancellation**: `(1e16 + 1.0) - 1e16` computes to `0.0`, not `1.0`
- **Precision Loss**: Loop accumulation where error grows as √n, n, or n²
- **Sign Flips**: Rounding near zero can flip the sign of a result
- **Inversion Errors**: `1/(1/x) ≠ x` for many values; reciprocal storage fails
- **Fractional Mismatch**: `0.1` in binary isn't the decimal `0.1` you typed
- **Range Collapse**: Softmax overflow, underflow in product chains, norm computation failures

The framework tests claims like "zero floating-point error (discrete integer arithmetic only)" by actually running code through comprehensive probes.

## Quick Start

### Run All Audits

```bash
python test_runner.py --all --verbose
```

### Run Example Demonstrations

```bash
python example_audit.py
```

### Test a Custom Function

```python
from test_runner import FloatAuditTestRunner
from decimal import Decimal

runner = FloatAuditTestRunner()
result = my_function(x)
exact = Decimal('reference_value')

runner.run_custom_probe("my_test", [
    ("my_operation", result, exact)
])
runner.print_report()
```

## Files

| File | Purpose |
|------|---------|
| `fpaudit.py` | Core auditing engine: metrics, error detection, result tracking |
| `backends.py` | Numeric backend adapters (float, Decimal, Fraction, SymPy, mpmath) |
| `probes.py` | Pre-built probe tests for common error patterns |
| `test_runner.py` | Test orchestration, result aggregation, report generation |
| `example_audit.py` | Demonstrations of framework usage patterns |
| `FPAUDIT_GUIDE.md` | Detailed reference for the framework API |
| `INTEGRATION_GUIDE.md` | How to integrate into OEIS solution code |

## Key Concepts

### Error Detection

The framework detects:

- **ULP Overflow** — Precision loss > representable range
- **Catastrophic Cancellation** — Near-equal subtraction with massive relative error
- **Sign Flip** — Rounding changes the sign of the result
- **Inversion Error** — Reciprocal/division operations fail roundtrip tests
- **Accumulated Rounding** — Loop errors grow linearly or quadratically
- **Underflow** → Collapse to zero for nonzero values
- **Overflow** → Escape to infinity for representable answers

### Metrics

**Relative Error** = |float - exact| / |exact|
- Threshold: 1e-14 (16 significant digits)

**ULP Distance** = error / ULP
- How many floating-point representable numbers away from correct answer
- Threshold: 2.0 (survives total precision loss by clamping to 1e16)

**Backend Comparison**
- Run the same operation across float64, Decimal, Fraction, SymPy, mpmath
- Spot precision loss by comparing results

## Example: Detecting a Variance Bug

```python
data = [1e9, 1e9+1, 1e9+2, 1e9+3, 1e9+4]
n = len(data)

# The textbook (wrong) formula
mean_sq = sum(x*x for x in data) / n
mean = sum(data) / n
variance = mean_sq - mean**2  # Can be negative!

# Exact answer via rationals
exact_variance = Fraction('2.5')  # Proven by hand calculation

# Audit
from test_runner import FloatAuditTestRunner
runner = FloatAuditTestRunner()
runner.run_custom_probe("variance", [("variance", variance, exact_variance)])
runner.print_report()

# Output: SIGN_FLIP violation — variance is negative!
```

## Example: Quadratic Roots (Numerically Unstable)

```python
# Classic formula: (-b + sqrt(b²-4ac)) / 2a
a, b, c = 1.0, 1e8, 1.0
disc = b*b - 4*a*c
sqrt_disc = math.sqrt(disc)
x1_naive = (-b + sqrt_disc) / (2*a)  # Catastrophic cancellation!

# Exact root computed with high precision
exact_x1 = (-Decimal(1e8) + (Decimal('1e8')**2 - 4).sqrt()) / 2

# Audit
runner.run_custom_probe("quadratic", [("root", x1_naive, exact_x1)])
# Output: CATASTROPHIC_CANCELLATION — -b and sqrt(b²-4ac) cancel
```

## Example: Fix with Stable Formula

```python
# Stable form: 2c / (-b - sqrt(b²-4ac))
x1_stable = 2*c / (-b - sqrt_disc)

runner.run_custom_probe("quadratic_stable", [("root", x1_stable, exact_x1)])
runner.print_report()
# Output: PASS — no errors detected
```

## Report Example

```
================================================================================
FLOATING-POINT AUDIT TEST REPORT
================================================================================
Total Operations Tested: 18
Passed: 6
Failed: 12
Pass Rate: 33.3%

Max Relative Error: 1.00e+00
Max ULP Distance: 4.49e+307

Error Breakdown:
  CATASTROPHIC_CANCELLATION: 6
  INVERSION_ERROR: 8
  PRECISION_LOSS: 18
  SIGN_FLIP: 4

Failed Operations:
  catastrophic_cancellation: (1e16 + 1.0) - 1e16
    → Catastrophic cancellation detected | severity=1.00e+00
  quadratic_naive_x2
    → Precision loss > threshold | severity=7.71e+14
  sum_reciprocals_naive
    → Inversion error: 1/x has wrong sign or magnitude | severity=9.48e+01
  ...
```

## Probe Families

### Catastrophic Cancellation
- `(1e16 + 1.0) - 1e16` → 0.0 (should be 1.0)
- Nearly equal subtraction with massive loss of significance

### Sign Flip
- Rounding near zero boundaries
- Accumulated errors crossing sign threshold
- Geometric calculations on slivers (Heron's formula)

### Inversion Error
- Reciprocal roundtrips: `1/(1/x) ≠ x`
- Divide vs. reciprocal multiply: `a/b ≠ a*(1/b)`
- Quadratic roots, function roundtrips

### Summation
- Naive sum of small + large numbers
- Alternating sums with high cancellation
- Kahan compensation comparison

### Square Root Accuracy
- sqrt(2) precision
- Tiny numbers (sqrt(1e-200))
- Chain of square roots

### Polynomial Evaluation
- Naive expansion vs. Horner's method
- Stability comparison on polynomials

### Floating-Point Laws
- Associativity violations
- Distributivity failures
- Loop counter off-by-one

## Integration

Add to your OEIS solution:

```python
from test_runner import FloatAuditTestRunner

def solve(n):
    result = compute(n)
    
    # Audit against known values
    runner = FloatAuditTestRunner()
    exact = compute_exact(n)  # High-precision reference
    runner.run_custom_probe("solution", [(f"n={n}", result, exact)])
    
    if not runner.auditor.summary()['passed']:
        print("WARNING: Floating-point errors detected!")
        runner.print_report()
    
    return result
```

## Use in CI/CD

```bash
# GitHub Actions / GitLab CI / etc
python test_runner.py --all --format json --output audit.json
python -c "import json; data = json.load(open('audit.json')); exit(sum(1 for r in data.get('results',{}).values() if 'CRITICAL' in str(r)))"
```

## References

- [What Every Computer Scientist Should Know About Floating-Point Arithmetic](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)
- IEEE 754 Standard (IEEE 754-2019)
- [Numerical Recipes](http://numerical.recipes/)
- [The Art of Computer Programming Vol. 2](https://en.wikipedia.org/wiki/The_Art_of_Computer_Programming) (Seminumerical Algorithms)

## License

Public domain / CC0 — for OEIS submissions