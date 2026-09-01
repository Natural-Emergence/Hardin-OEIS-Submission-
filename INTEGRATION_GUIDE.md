# Integration Guide: Using fpaudit with OEIS Solutions

This guide explains how to integrate the floating-point auditing framework into OEIS solution code to systematically uncover numeric errors.

## Quick Integration

### Step 1: Add to Solution Entry Point

```python
# In your solution module
import fpaudit_integration as fpa

def sequence(n):
    """Compute the nth term of the sequence."""
    result = compute_term(n)
    
    # Audit the result
    auditor = fpa.get_auditor()
    auditor.audit(f"sequence({n})", result, exact_result)
    
    return result

# At module exit
if __name__ == "__main__":
    import sys
    sequence(int(sys.argv[1]))
    fpa.print_report()
```

### Step 2: Run with Auditing

```bash
python solution.py 100  # Normal execution
python -m fpaudit solution.py 100  # With auditing
```

## Probe Categories

### 1. Debt Probes

Detect where floating-point errors are created and how they compound:

**Catastrophic Cancellation**
```python
# The classic: (1e16 + 1.0) - 1e16 computes to 0.0
# Detected when near-equal numbers are subtracted
```

**Compounding Errors**
```python
# A loop that accumulates rounding error
# sum(0.1) * 100_000 times accumulates debt linearly
```

**Range Collapse**
```python
# Softmax overflow: exp(1000) + exp(1001) becomes inf
# But the result (probabilities) should be finite
```

### 2. Fractional Probes

Detect when decimal representation doesn't match binary storage:

**Decimal Literals**
```python
# 0.1 isn't exactly 0.1 in binary — it's 0.1000000000000000055511151231...
# This is the "principal" on every computation
```

**Sum of Parts**
```python
# 100/3 + 100/3 + 100/3 != 100 due to rounding
# Classic billing system failure
```

**Mediant Drift**
```python
# Farey sequence operations are exact in rational, lose exactness in float
# Comparison can select wrong representative
```

### 3. Inversion Probes

Detect errors in operations that should be their own inverse:

**Reciprocal Roundtrip**
```python
# 1/(1/x) != x for many values of x
# Affects unit conversions, cached scale factors
```

**Divide vs. Multiply**
```python
# a/b != a*(1/b) due to rounding difference
# Why -ffast-math changes results
```

**Function Roundtrips**
```python
# sqrt(x)**2 != x, exp(log(x)) != x, sin(asin(x)) != x
```

### 4. Sign Flip Probes

Detect when rounding changes the sign:

**Near-Zero Subtraction**
```python
# 1e-150 - (1e-150 + 1e-170) should be negative but might flip
```

**Accumulated Rounding**
```python
# Loop: x = 1.0; x = x - 0.001 * 1001 times
# Final x should be slightly negative but might round to zero
```

### 5. Law Violation Probes

Detect violations of mathematical laws:

**Associativity**
```python
# (a + b) + c != a + (b + c) in floating point
```

**Distributivity**
```python
# a*(b + c) != a*b + a*c
```

**Loop Counter**
```python
# while x < 1.0: x += 0.1  runs 11 times, not 10
```

## Example: Testing a Geometric Mean Implementation

### Standard Implementation (Prone to Overflow)

```python
def geometric_mean_naive(values):
    """Naive implementation: multiply then take nth root."""
    product = 1.0
    for v in values:
        product *= v
    return product ** (1.0 / len(values))

# Test
from test_runner import FloatAuditTestRunner
from decimal import Decimal

runner = FloatAuditTestRunner(verbose=True)

values = [1.0, 2.0, 4.0, 8.0]
result = geometric_mean_naive(values)

# Exact: 4th root of (1*2*4*8) = 4th root of 64 = 2.828...
exact = Decimal('64') ** (Decimal('1') / Decimal('4'))

runner.run_custom_probe("geom_mean_naive", [
    ("geometric_mean", result, exact)
])

runner.print_report()
```

### Robust Implementation (Using Logarithms)

```python
import math

def geometric_mean_stable(values):
    """Stable: use logarithms to avoid overflow/underflow."""
    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / len(values))
```

### Comparison

```python
runner.run_custom_probe("geom_mean_stable", [
    ("geometric_mean_stable", geometric_mean_stable(values), exact)
])

# See which passes auditing
runner.print_report()
```

## Real-World Examples from OEIS

### Detecting Variance Bugs

Many analytics solutions compute variance as `E[x²] - E[x]²`, which can be negative:

```python
def test_variance_computation():
    data = [1e9, 1e9+1, 1e9+2, 1e9+3, 1e9+4]
    
    # Naive computation
    n = len(data)
    mean_sq = sum(x*x for x in data) / n
    mean = sum(data) / n
    variance = mean_sq - mean**2  # Can be negative!
    
    if variance < 0:
        print("ERROR: Negative variance from rounding error")
        print(f"  sqrt({variance}) = NaN")
```

The auditing framework detects this automatically:

```python
from test_runner import FloatAuditTestRunner
from decimal import Decimal
from fractions import Fraction

runner = FloatAuditTestRunner()

# Exact computation
exact_data = [Fraction(int(1e9 + k)) for k in range(5)]
exact_mean = sum(exact_data) / len(exact_data)
exact_var = sum((x - exact_mean)**2 for x in exact_data) / len(exact_data)

# Float computation
float_result = variance  # From above

runner.run_custom_probe("variance_bug", [
    ("one_pass_variance", float_result, exact_var)
])

runner.print_report()
# Reports: SIGN_FLIP violation if variance < 0
```

### Detecting Root Finding Errors

Quadratic roots fail on nearly-equal solutions:

```python
def test_quadratic_roots():
    a, b, c = 1.0, 1e8, 1.0
    
    # Standard formula: (-b ± sqrt(b²-4ac)) / 2a
    disc = b*b - 4*a*c
    sqrt_disc = math.sqrt(disc)
    
    x1 = (-b + sqrt_disc) / (2*a)  # Lost to catastrophic cancellation!
    x2 = (-b - sqrt_disc) / (2*a)  # This one is OK
    
    # x1 should be very close to 0 but computes as exact 0
```

The framework detects this:

```python
runner = FloatAuditTestRunner()

# Exact root via rationals
from fractions import Fraction
ea, eb, ec = Fraction(1), Fraction(10**8), Fraction(1)
edisc = eb*eb - 4*ea*ec
e_sqrt_disc = Decimal(edisc).sqrt()
exact_x1 = (-eb + e_sqrt_disc) / (2*ea)

runner.run_custom_probe("quadratic_roots", [
    ("naive_small_root", x1, exact_x1)
])

runner.print_report()
# Reports: CATASTROPHIC_CANCELLATION violation
```

## Interpreting the Report

### Key Metrics

| Metric | Meaning | Threshold |
|--------|---------|-----------|
| **Relative Error** | Error relative to answer | 1e-14 default |
| **ULP Distance** | Units in Last Place away | 2.0 default |
| **Severity** | How bad the error is | CRITICAL > HIGH > MEDIUM > LOW |

### Error Types and Actions

| Error Type | Indicator | Solution |
|-----------|-----------|----------|
| **Catastrophic Cancellation** | `(a+b)-a ≈ 0` | Reorder operations, use `a+b-a` form differently |
| **Sign Flip** | Result has wrong sign | Use stable formula, avoid near-zero subtractions |
| **Precision Loss** | ULP >> 2.0 | Use higher precision for intermediate steps |
| **Inversion Error** | `1/(1/x) ≠ x` | Avoid reciprocal storage, compute directly |
| **Accumulated Rounding** | Error grows with loop count | Use Kahan summation, fsum(), or log-space arithmetic |
| **Underflow** | Result is 0.0 but shouldn't be | Use log-space arithmetic, hypot(), scaled computation |
| **Overflow** | Result is inf but shouldn't be | Subtract max before exp(), use hypot(), scale |

## Testing Against OEIS Specifications

### Example: Sequence A000045 (Fibonacci)

```python
def fibonacci_float(n):
    """Naive float implementation."""
    if n <= 1:
        return float(n)
    a, b = 0.0, 1.0
    for _ in range(n - 1):
        a, b = b, a + b
    return b

def fibonacci_exact(n):
    """Exact implementation for testing."""
    if n <= 1:
        return Fraction(n)
    a, b = Fraction(0), Fraction(1)
    for _ in range(n - 1):
        a, b = b, a + b
    return b

# Test
runner = FloatAuditTestRunner()

test_n = 100
result_float = fibonacci_float(test_n)
result_exact = fibonacci_exact(test_n)

runner.run_custom_probe("fibonacci", [
    (f"fib({test_n})", result_float, float(result_exact))
])

runner.print_report()
```

## Command-Line Usage

### Run All Probes

```bash
python test_runner.py --all --verbose
```

### Run Specific Probe Family

```bash
python test_runner.py --probes --verbose
```

### Compare Backends

```bash
python test_runner.py --backends --output backend_comparison.json --format json
```

### Run Example Suite

```bash
python example_audit.py
```

### Generate JSON Report (for CI Integration)

```bash
python test_runner.py --all --format json --output report.json
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Floating-Point Audit

on: [push, pull_request]

jobs:
  fpaudit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Run floating-point audit
        run: python test_runner.py --all --format json --output audit_report.json
      
      - name: Check for critical errors
        run: |
          python -c "
          import json
          with open('audit_report.json') as f:
              data = json.load(f)
          critical = sum(1 for r in data.get('results', {}).values() 
                        if 'CRITICAL' in str(r))
          if critical > 0:
              print(f'CRITICAL errors found: {critical}')
              exit(1)
          "
      
      - name: Upload report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: floating-point-audit
          path: audit_report.json
```

## Troubleshooting

### "Module not found: SymPy / mpmath"

These backends are optional. The framework falls back to float/Decimal/Fraction.

```bash
pip install sympy mpmath  # To enable
```

### "ULP distance overflows"

This is expected and correct—it means total precision loss. The framework clamps to 1e16 to survive this.

### "False positive: PRECISION_LOSS when I expect accuracy"

Adjust thresholds:

```python
auditor = FloatAuditor(
    ulp_threshold=10.0,  # More lenient
    rel_error_threshold=1e-12  # Allows larger relative error
)
```

## Summary

The floating-point auditing framework lets you:

1. **Detect** where floating-point errors occur in your code
2. **Quantify** the magnitude of errors (ULP distance, relative error)
3. **Compare** implementations to find which is most accurate
4. **Test** against ground truth computed in higher precision
5. **Document** numeric stability in your OEIS solutions

Use it to validate claims like "zero floating-point error" and catch subtle bugs before they reach production.
