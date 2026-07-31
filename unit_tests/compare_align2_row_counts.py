#!/usr/bin/env python3
"""
Compare row counts between old and new Align 2 outputs, using normalized
filenames so the legacy and refactored naming conventions can be compared.

Usage:
    python compare_align2_row_counts_normalized.py \
        --old-dir "path/to/p570 Align 2" \
        --new-dir "path/to/align2" \
        --ignore-unit-0
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def normalize_name(filename: str) -> str:
    """
    Normalize legacy and refactored Align 2 filenames to the underlying neuron ID.

    Examples:
        align2_align1_times_manual_GA1-REC3_unit_1.csv -> times_manual_GA1-REC3_unit_1.csv
        align2_times_manual_GA1-REC3_unit_1.csv        -> times_manual_GA1-REC3_unit_1.csv
    """
    name = filename

    # Remove the leading Align 2 wrapper.
    name = re.sub(r"^align2_", "", name)

    # Remove the legacy Align 1 wrapper if present.
    name = re.sub(r"^align1_", "", name)

    return name


def row_count(csv_path: Path) -> int:
    try:
        return len(pd.read_csv(csv_path))
    except pd.errors.EmptyDataError:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare old vs new Align 2 row counts.")
    parser.add_argument("--old-dir", required=True, help="Folder containing old Align 2 CSVs.")
    parser.add_argument("--new-dir", required=True, help="Folder containing new Align 2 CSVs.")
    parser.add_argument(
        "--ignore-unit-0",
        action="store_true",
        help="Ignore files whose name contains unit_0.csv",
    )
    args = parser.parse_args()

    old_dir = Path(args.old_dir)
    new_dir = Path(args.new_dir)

    old_files = {normalize_name(p.name): p for p in old_dir.glob("*.csv")}
    new_files = {normalize_name(p.name): p for p in new_dir.glob("*.csv")}

    if args.ignore_unit_0:
        old_files = {k: v for k, v in old_files.items() if "unit_0.csv" not in k}
        new_files = {k: v for k, v in new_files.items() if "unit_0.csv" not in k}

    common = sorted(set(old_files) & set(new_files))
    only_old = sorted(set(old_files) - set(new_files))
    only_new = sorted(set(new_files) - set(old_files))

    rows = []
    for name in common:
        old_n = row_count(old_files[name])
        new_n = row_count(new_files[name])
        delta = new_n - old_n
        rows.append((name, old_n, new_n, delta, old_files[name].name, new_files[name].name))

    rows.sort(key=lambda x: abs(x[3]), reverse=True)

    print("Largest row-count differences")
    print("-" * 100)
    print(f"{'Neuron file':45s} {'Old':>6s} {'New':>6s} {'Δ':>6s}")
    print("-" * 100)
    for name, old_n, new_n, delta, _, _ in rows:
        print(f"{name:45.45s} {old_n:6d} {new_n:6d} {delta:6d}")

    print()
    print(f"Matched files: {len(common)}")
    print(f"Files only in old: {len(only_old)}")
    for name in only_old[:10]:
        print(f"  - {name}  ({old_files[name].name})")
    if len(only_old) > 10:
        print("  ...")

    print(f"Files only in new: {len(only_new)}")
    for name in only_new[:10]:
        print(f"  - {name}  ({new_files[name].name})")
    if len(only_new) > 10:
        print("  ...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())