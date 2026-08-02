"""convert_matlab_to_csv.py

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


def choose_folders() -> list[Path]:
    """
    Repeatedly ask the user to choose folders.

    Cancel finishes the selection.
    """
    try:
        from tkinter import Tk, filedialog
    except Exception as e:
        raise RuntimeError(
            "tkinter is not available, so interactive folder selection cannot run. "
            "Pass folders on the command line instead."
        ) from e

    root = Tk()
    root.withdraw()

    folders: list[Path] = []

    while True:
        folder = filedialog.askdirectory(
            title="Select a folder containing times_manual*.mat (Cancel to finish)"
        )
        if not folder:
            break
        folders.append(Path(folder))

    root.destroy()
    return folders


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
        df.to_csv(outfile, index=False, float_format="%.4f")
        written_files.append(outfile)


    return written_files


def convert_folder(folder: Path, skip_unit0: bool = True) -> list[Path]:
    """
    Convert every times_manual*.mat file inside one folder.
    """
    folder = Path(folder)
    written: list[Path] = []
    skipped_errors: list[tuple[str, str]] = []
    no_csv_files: list[str] = []

    mat_files = sorted(folder.glob("times_manual*.mat"))

    log_path = folder / "skipped_mat_files.txt"

    if not mat_files:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "Movie SME Preprocessing\n"
            "=======================\n\n"
            f"Folder:\n{folder}\n\n"
            "Summary\n"
            "-------\n"
            "MAT files found: 0\n"
            "MAT files read successfully: 0\n"
            "CSV files written: 0\n"
            "Skipped due to errors: 0\n"
            "No CSVs written after filtering: 0\n",
            encoding="utf-8",
        )
        return written

    for mat_file in mat_files:
        try:
            written_this_file = convert_mat_file(
                mat_file,
                output_dir=folder,
                skip_unit0=skip_unit0,
            )
        except Exception as exc:
            skipped_errors.append((mat_file.name, f"{type(exc).__name__}: {exc}"))
            continue

        written.extend(written_this_file)

        if not written_this_file:
            no_csv_files.append(mat_file.name)

    if skipped_errors or no_csv_files:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_lines: list[str] = [
            "Movie SME Preprocessing",
            "=======================",
            "",
            "Folder:",
            f"{folder}",
            "",
            "Summary",
            "-------",
            f"MAT files found: {len(mat_files)}",
            f"MAT files read successfully: {len(mat_files) - len(skipped_errors)}",
            f"CSV files written: {len(written)}",
            f"Skipped due to errors: {len(skipped_errors)}",
            f"No CSVs written after filtering: {len(no_csv_files)}",
            "",
        ]

        if skipped_errors:
            log_lines.extend(
                [
                    "Skipped MAT files",
                    "-----------------",
                    "",
                ]
            )
            for file_name, reason in skipped_errors:
                log_lines.extend(
                    [
                        file_name,
                        f"    Reason: {reason}",
                        "",
                    ]
                )

        if no_csv_files:
            log_lines.extend(
                [
                    "Files that produced no CSV output",
                    "----------------------------------",
                    "",
                ]
            )
            for file_name in no_csv_files:
                log_lines.extend(
                    [
                        file_name,
                        "    Reason: No CSVs were written after filtering out unit 0.",
                        "",
                    ]
                )

        log_path.write_text("\n".join(log_lines).rstrip() + "\n", encoding="utf-8")

    return written


def convert_folders(folders: list[str | Path], skip_unit0: bool = True) -> list[Path]:
    """
    Convert multiple patient folders.
    """
    written: list[Path] = []

    for folder in folders:
        written.extend(convert_folder(Path(folder), skip_unit0=skip_unit0))

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

    if args.folders:
        folders = [Path(f) for f in args.folders]
    else:
        folders = choose_folders()

    if not folders:
        print("Completed preprocessing: 0 CSV files written.")
        return

    written = convert_folders(folders, skip_unit0=not args.keep_unit_0)
    print(f"Completed preprocessing: {len(written)} CSV files written. See skipped_mat_files.txt for details.")


if __name__ == "__main__":
    main()