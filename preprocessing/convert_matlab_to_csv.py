"""convert_mat.py

Stage 0 of the Movie SME pipeline.

Purpose
-------
Convert Wave_Clus MATLAB files (times_manual*.mat) into one CSV per unit.

This replaces BOTH of the original MATLAB scripts:

    times_manual_csv_conversion.m
    delete_unit0_csvs.m

Pipeline
--------
times_manual*.mat
        ↓
cluster_class
        ↓
split by unit
        ↓
skip unit 0
        ↓
times_manual_*_unit_#.csv

Assumptions
-----------
Input files are MATLAB v7.3 (HDF5) files.

cluster_class is stored as

    (3, N)

and after transpose becomes

    (N, 3)

where

column 0 = unit number
column 1 = spike time (seconds)
column 2 = unused metadata (ignored)

Output CSV format
-----------------
units,s
"""

from __future__ import annotations

import argparse
from pathlib import Path

import h5py
import numpy as np
import pandas as pd


def convert_mat_file(
    mat_file: Path,
    output_dir: Path | None = None,
    skip_unit0: bool = True,
) -> list[Path]:
    """
    Convert ONE times_manual*.mat file into one CSV per unit.

    Parameters
    ----------
    mat_file
        MATLAB file to convert.

    output_dir
        Where CSVs should be written.
        Defaults to the same directory as the MAT file.

    skip_unit0
        Ignore unit 0 during conversion.

    Returns
    -------
    list[Path]
        Paths to every CSV that was written.
    """
    mat_file = Path(mat_file)

    if output_dir is None:
        output_dir = mat_file.parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    with h5py.File(mat_file, "r") as f:
        if "cluster_class" not in f:
            raise KeyError(f"{mat_file.name} does not contain 'cluster_class'.")
        cluster = np.array(f["cluster_class"]).T

    if cluster.ndim != 2:
        raise ValueError(f"{mat_file.name}: cluster_class should be 2D.")

    if cluster.shape[1] < 2:
        raise ValueError(
            f"{mat_file.name}: cluster_class should have at least two columns."
        )

    base_name = mat_file.stem
    written_files: list[Path] = []

    units = np.unique(cluster[:, 0].astype(int))

    for unit in units:
        if skip_unit0 and unit == 0:
            continue

        rows = cluster[cluster[:, 0].astype(int) == unit]

        df = pd.DataFrame(
            {
                "units": rows[:, 0].astype(int),
                "s": rows[:, 1],
            }
        )

        outfile = output_dir / f"{base_name}_unit_{unit}.csv"
        df.to_csv(outfile, index=False)
        written_files.append(outfile)

        print(f"Created {outfile.name}")

    return written_files


def convert_folder(folder: Path, skip_unit0: bool = True) -> list[Path]:
    """
    Convert every times_manual*.mat file inside one folder.
    """
    folder = Path(folder)
    written: list[Path] = []

    mat_files = sorted(folder.glob("times_manual*.mat"))

    if not mat_files:
        print(f"No MAT files found in {folder}")
        return written

    print(f"\nProcessing {folder}")

    for mat_file in mat_files:
        written.extend(
            convert_mat_file(
                mat_file,
                output_dir=folder,
                skip_unit0=skip_unit0,
            )
        )

    print(f"Finished {folder}")
    return written


def convert_folders(folders: list[str | Path], skip_unit0: bool = True) -> list[Path]:
    """
    Convert multiple patient folders.
    """
    written: list[Path] = []

    for folder in folders:
        written.extend(convert_folder(Path(folder), skip_unit0=skip_unit0))

    print(f"\nCreated {len(written)} CSV files.")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert times_manual*.mat files into per-unit CSVs."
    )
    parser.add_argument(
        "folders",
        nargs="*",
        help="Folders to process. If omitted, an interactive picker opens.",
    )
    parser.add_argument(
        "--keep-unit-0",
        action="store_true",
        help="Write unit 0 CSVs instead of skipping them.",
    )
    args = parser.parse_args()

    if not args.folders:
        raise SystemExit(
            "Please provide one or more folders containing times_manual*.mat files."
        )

    convert_folders(args.folders, skip_unit0=not args.keep_unit_0)


if __name__ == "__main__":
    main()