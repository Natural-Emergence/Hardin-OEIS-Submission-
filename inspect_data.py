#!/usr/bin/env python3
"""
Inspect K3 triangulation computational data files.
Loads and summarizes the contents of .npz archives from the runs.

Usage:
  python3 inspect_data.py [--all | --hodge | --seam | --projector]
  python3 inspect_data.py --key <filename> <keyname>
"""

import numpy as np
import os
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

FILES = {
    "hodge": DATA_DIR / "k3_16_hodge_matrices.npz",
    "seam": DATA_DIR / "quinn_k3_fundamental_class_orientation_seam_matrices.npz",
    "projector": DATA_DIR / "quinn_seam_projector_matrices.npz",
}


def summarize_array(key: str, arr) -> str:
    """Format array summary."""
    if arr.dtype in (object, bool):
        return f"{arr.dtype}"
    return f"{arr.dtype} shape={arr.shape} min={arr.min():.3e} max={arr.max():.3e} norm={np.linalg.norm(arr):.3e}"


def inspect_file(name: str, verbose: bool = False):
    """Inspect one .npz file."""
    fpath = FILES.get(name)
    if not fpath or not fpath.exists():
        print(f"File not found: {name} -> {fpath}")
        return

    print(f"\n{'='*70}")
    print(f"  {name.upper()}: {fpath.name}")
    print('='*70)

    data = np.load(fpath, allow_pickle=True)
    keys = sorted(data.keys())

    print(f"Arrays ({len(keys)}):")
    for key in keys:
        arr = data[key]
        summary = summarize_array(key, arr)
        print(f"  {key:35s}  {summary}")

    if verbose:
        print("\nDetailed inspection:")
        for key in keys:
            arr = data[key]
            print(f"\n  {key}:")
            print(f"    dtype: {arr.dtype}, shape: {arr.shape}")
            if arr.size < 50:
                print(f"    {arr}")
            elif arr.ndim == 1:
                print(f"    head: {arr[:5]}")
                print(f"    tail: {arr[-5:]}")
            elif arr.ndim == 2:
                print(f"    head:\n{arr[:3, :5]}")

    data.close()


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "--all":
        for name in FILES:
            inspect_file(name, verbose=False)
    elif sys.argv[1] == "--key" and len(sys.argv) >= 4:
        fname = sys.argv[2]
        keyname = sys.argv[3]
        fpath = FILES.get(fname) or Path(fname)
        if not fpath.exists():
            print(f"File not found: {fpath}")
            return
        data = np.load(fpath, allow_pickle=True)
        if keyname not in data:
            print(f"Key not found: {keyname}")
            print(f"Available keys: {list(data.keys())}")
            return
        arr = data[keyname]
        print(f"{keyname} ({fname}):")
        print(f"  dtype: {arr.dtype}, shape: {arr.shape}")
        if arr.size <= 100:
            print(f"  {arr}")
        else:
            print(f"  norm: {np.linalg.norm(arr):.3e}")
            if arr.ndim >= 1:
                print(f"  head: {arr.flat[:20]}")
    elif sys.argv[1] in ("--hodge", "--seam", "--projector"):
        inspect_file(sys.argv[1][2:], verbose="--verbose" in sys.argv)
    elif sys.argv[1] == "--verbose" and len(sys.argv) >= 3:
        inspect_file(sys.argv[2], verbose=True)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
