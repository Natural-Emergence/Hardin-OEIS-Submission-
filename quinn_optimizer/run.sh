#!/bin/bash
# One-command runner for the QUINN optimizer training benchmark.
# Usage:
#   ./run.sh                  # full run (20 epochs)
#   ./run.sh --quick          # quick test (~5 min, 3 epochs)
#   DEVICE=cuda ./run.sh      # GPU if available
set -e

DEVICE=${DEVICE:-cpu}
ARGS="$@"

echo "=== Installing dependencies ==="
pip install torch datasets tiktoken --break-system-packages -q 2>/dev/null \
  || pip install torch datasets tiktoken -q 2>/dev/null \
  || echo "Warning: some packages may not have installed cleanly"

echo ""
echo "=== Running QUINN training benchmark ==="
python train/protocol.py --device "$DEVICE" --epochs 20 $ARGS

echo ""
echo "=== Generating plots (if matplotlib available) ==="
python train/plot.py 2>/dev/null || echo "Skipping plots (matplotlib not available)"

echo ""
echo "=== Summary ==="
cat results/summary.txt
