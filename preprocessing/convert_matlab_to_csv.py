# preprocessing/convert_mat.py
"""Convert times_manual*.mat files into per-unit CSVs.

This replaces the MATLAB preprocessing stage and folds unit-0 removal into
the conversion step.

Expected input in the .mat file:
- cluster_class
  - column 0: unit id
  - column 1: spike time in seconds
  - column 2: extra metadata field (ignored for CSV output)

Output per unit:
- <basename>_unit_<unit>.csv
- columns: units, s
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence, Tuple, Union

import numpy as np
import pandas as pd

try:
    from scipy.io import loadmat as scipy_loadmat
except Exception:  # pragma: no cover
    scipy_loadmat = None

try:
    import h5py  # type: ignore
except Exception:  # pragma: no cover
    h5py = None


ManifestPath = Union[str, Path]


def _load_mat_file(mat_path: Path) -> dict:
    """Load a MATLAB file and return a dict-like object with cluster_class."""
    if scipy_loadmat is not None:
        try:
            data = scipy_loadmat(str(mat_path), squeeze_me=True, struct_as_record=False)
            if "cluster_class" in data:
                return data
        except Exception:
            pass

    if h5py is not None:
        try:
            with h5py.File(mat_path, "r") as f:
                if "cluster_class" in f:
                    return {"cluster_class": f["cluster_class"][...]}
        except Exception:
            pass

    raise ValueError(
        f"Could not read {mat_path.name}. "
        "If this is MATLAB v7.3, make sure h5py is installed."
    )


def _normalize_cluster_class(cluster_class: object) -> np.ndarray:
    """
    Convert cluster_class into an Nx3 numeric array:
    [unit_id, spike_time_s, extra_field].
    """
    arr = np.asarray(cluster_class)

    if arr.ndim != 2:
        raise ValueError(f"cluster_class must be 2D; got shape {arr.shape!r}")

    # Your sample file is stored as (3, N), so transpose to (N, 3).
    if arr.shape[0] == 3 and arr.shape[1] != 3:
        arr = arr.T

    if arr.shape[1] < 2:
        raise ValueError(f"cluster_class must have at least 2 columns; got {arr.shape!r}")

    # Keep only the first 3 columns if more exist.
    arr = arr[:, :3]

    rows: List[Tuple[float, float, float]] = []
    for row in arr:
        unit_raw = row[0]
        time_raw = row[1]
        extra_raw = row[2] if len(row) > 2 else np.nan

        try:
            unit = float(unit_raw)
            time_s = float(time_raw)
            extra = float(extra_raw) if extra_raw is not None else np.nan
        except Exception as e:
            raise ValueError(f"Could not parse row {row!r} in cluster_class") from e

        rows.append((unit, time_s, extra))

    return np.asarray(rows, dtype=float)


def convert_times_manual_mat_to_csv(
    mat_path: ManifestPath,
    output_dir: ManifestPath | None = None,
    skip_unit0: bool = True,
    overwrite: bool = True,
) -> List[Path]:
    """
    Convert one times_manual*.mat file into per-unit CSVs.

    Returns a list of written CSV paths.
    """
    mat_path = Path(mat_path)
    if output_dir is None:
        output_dir = mat_path.parent
    else:
        output_dir = Path(output_dir)

    data = _load_mat_file(mat_path)
    if "cluster_class" not in data:
        raise KeyError(f"'cluster_class' not found in {mat_path.name}")

    cluster = _normalize_cluster_class(data["cluster_class"])

    base_name = mat_path.stem
    written: List[Path] = []

    unit_values = np.unique(cluster[:, 0].astype(int))

    for unit in unit_values:
        if skip_unit0 and int(unit) == 0:
            continue

        unit_rows = cluster[cluster[:, 0].astype(int) == int(unit), :2]
        if unit_rows.size == 0:
            continue

        out_path = output_dir / f"{base_name}_unit_{int(unit)}.csv"
        if out_path.exists() and not overwrite:
            continue

        df = pd.DataFrame(unit_rows, columns=["units", "s"])
        df["units"] = df["units"].round().astype(int)
        df["s"] = pd.to_numeric(df["s"], errors="coerce")
        df = df.dropna(subset=["s"])

        df.to_csv(out_path, index=False)
        written.append(out_path)

    return written


def find_times_manual_mat_files(folder: ManifestPath) -> List[Path]:
    """Return all times_manual*.mat files in a folder."""
    folder = Path(folder)
    return sorted(folder.glob("times_manual*.mat"))


def convert_folders(
    folders: Sequence[ManifestPath],
    output_dir_same_as_input: bool = True,
    skip_unit0: bool = True,
    overwrite: bool = True,
) -> List[Path]:
    """Convert all times_manual*.mat files in all selected folders."""
    written_all: List[Path] = []

    for folder in folders:
        folder = Path(folder)
        if not folder.is_dir():
            print(f"Skipping non-existent folder: {folder}")
            continue

        print(f"Processing folder: {folder}")
        mat_files = find_times_manual_mat_files(folder)

        if not mat_files:
            print(f"  No times_manual*.mat files found in {folder}")
            continue

        for mat_file in mat_files:
            try:
                out_dir = folder if output_dir_same_as_input else folder
                written = convert_times_manual_mat_to_csv(
                    mat_file,
                    output_dir=out_dir,
                    skip_unit0=skip_unit0,
                    overwrite=overwrite,
                )
                written_all.extend(written)
                print(f"  Converted {mat_file.name} -> {len(written)} CSVs")
            except Exception as e:
                print(f"  Warning: failed to convert {mat_file.name}: {e}")

    return written_all


def _choose_folders_interactively() -> List[Path]:
    """Optional folder picker, similar to the MATLAB workflow."""
    try:
        from tkinter import Tk, filedialog
    except Exception as e:
        raise RuntimeError(
            "tkinter is not available, so interactive folder selection cannot run. "
            "Pass folders on the command line instead."
        ) from e

    root = Tk()
    root.withdraw()
    root.update()

    folders: List[Path] = []
    while True:
        selected = filedialog.askdirectory(
            title="Select a folder containing times_manual*.mat (Cancel to finish)"
        )
        if not selected:
            break
        folders.append(Path(selected))

    root.destroy()
    return folders


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
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing CSV files.",
    )
    args = parser.parse_args()

    if args.folders:
        folders = [Path(p) for p in args.folders]
    else:
        folders = _choose_folders_interactively()

    if not folders:
        print("No folders selected. Nothing to do.")
        return

    written = convert_folders(
        folders=folders,
        output_dir_same_as_input=True,
        skip_unit0=not args.keep_unit_0,
        overwrite=not args.no_overwrite,
    )
    print(f"Done. Wrote {len(written)} CSV files.")


if __name__ == "__main__":
    main()