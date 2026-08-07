#!/usr/bin/env python3
"""Interactive pipeline launcher with folder discovery and optional dry-run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .config import PIPELINE_ANALYSIS_CONFIG
    from .folder_discovery import (
        build_patient_dict,
        confirm_run,
        discover_patient_folder,
        print_run_summary,
        run_preprocessing_if_needed,
        validate_patient_folder,
    )
    from .pipeline_executor import (
        analysis_dict_to_config,
        patient_dict_to_config,
        plan_patient_pipeline,
        run_pipeline,
    )
except ImportError:  # pragma: no cover
    from config import PIPELINE_ANALYSIS_CONFIG
    from folder_discovery import (
        build_patient_dict,
        confirm_run,
        discover_patient_folder,
        print_run_summary,
        run_preprocessing_if_needed,
        validate_patient_folder,
    )
    from pipeline_executor import (
        analysis_dict_to_config,
        patient_dict_to_config,
        plan_patient_pipeline,
        run_pipeline,
    )


def _choose_patient_folders() -> list[Path]:
    """Select one or more patient folders using a simple Tk directory picker."""
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "tkinter is not available, so interactive folder selection cannot run."
        ) from exc

    folders: list[Path] = []
    try:
        while True:
            folder = filedialog.askdirectory(
                title="Select a patient folder (Cancel when finished)"
            )
            if not folder:
                break
            path = Path(folder)
            if path not in folders:
                folders.append(path)
    finally:
        root.destroy()

    return folders


def _choose_output_root(patient_folders: list[Path]) -> Path:
    """Default outputs beside the selected patient folders."""
    if not patient_folders:
        raise RuntimeError("No patient folders were selected.")

    parents = {p.resolve().parent for p in patient_folders}
    if len(parents) != 1:
        raise RuntimeError(
            "All selected patient folders must share the same parent directory "
            "so a single outputs folder can be used."
        )

    output_root = next(iter(parents)) / "outputs"
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root


def _analysis_override_from_args(raster_window_ms: tuple[int, int] | None) -> dict[str, Any] | None:
    """Build the minimal analysis override dict for the pipeline executor."""
    if raster_window_ms is None:
        return None
    start_ms, end_ms = raster_window_ms
    if start_ms >= end_ms:
        raise ValueError("raster window must be an increasing interval")
    return {"raster_window_ms": [start_ms, end_ms]}


def _movie_bin_size_s_from_config(cfg: Any) -> int:
    """Get the shared movie bin size from the available config object(s)."""
    if hasattr(cfg, "movie_bin_size_s"):
        return int(getattr(cfg, "movie_bin_size_s"))
    fallback = getattr(PIPELINE_ANALYSIS_CONFIG, "movie_bin_size_s", 10)
    return int(fallback)


def _print_tree(plan: dict[str, Any]) -> None:
    print()
    print("=" * 72)
    print("Planned Output")
    print("=" * 72)

    print(f"patient_root: {plan['patient_root']}")

    print()
    print("Folders")
    for item in plan["folders"]:
        print(f"  {item}")

    print()
    print("Canonical files")
    for item in plan["canonical_files"]:
        print(f"  {item}")

    print()
    print("Raster CSVs")
    for item in plan["raster_csvs"]:
        print(f"  {item}")

    print()
    print("Regional raster CSVs")
    for item in plan["raster_region_csvs"]:
        print(f"  {item}")

    print()
    print("Swarm outputs")
    for item in plan["swarm_files"]:
        print(f"  {item}")

    print()
    print("Dashboards")
    for item in plan["dashboards"]:
        print(f"  {item}")

    print()
    print(f"movie_bin_size_s: {plan['bin_size_s']}")
    print("=" * 72)


def _run_one_patient(
    patient_folder: Path,
    output_root: Path,
    analysis_cfg: Any,
    raw_analysis_override: dict[str, Any] | None,
    dry_run: bool,
) -> bool:
    """Validate, preprocess, and launch one patient folder."""
    try:
        print()
        print("=" * 80)
        print(f"Processing {patient_folder.name}")
        print("=" * 80)

        contents = discover_patient_folder(patient_folder)
        report = validate_patient_folder(contents)
        print_run_summary(contents, report)

        if not confirm_run(report):
            print(f"Skipping {patient_folder.name}.")
            return False

        run_preprocessing_if_needed(contents)

        # Refresh after preprocessing so the discovered folder state is current.
        contents = discover_patient_folder(patient_folder)
        raw_patient = build_patient_dict(contents)

        movie_bin_size_s = _movie_bin_size_s_from_config(analysis_cfg)
        raster_window = getattr(analysis_cfg, "raster_window_ms", (-3000, 5000))
        print(
            f"Raster window      : {raster_window[0]} to {raster_window[1]} ms"
        )

        if dry_run:
            patient_cfg = patient_dict_to_config(raw_patient)
            plan = plan_patient_pipeline(
                patient_cfg,
                analysis_cfg,
                output_root,
                bin_size_s=movie_bin_size_s,
            )
            _print_tree(plan)
            return True

        run_pipeline(
            [raw_patient],
            raw_analysis_override,
            output_root,
            bin_size_s=movie_bin_size_s,
        )

        print()
        print(f"SUCCESS: {patient_folder.name}")
        return True

    except Exception as exc:
        print()
        print("=" * 80)
        print(f"FAILED: {patient_folder.name}")
        print(exc)
        print("=" * 80)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Patient folder pipeline launcher."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only display the planned output tree without running the pipeline.",
    )
    parser.add_argument(
        "--raster-window-ms",
        nargs=2,
        type=int,
        metavar=("START_MS", "END_MS"),
        default=None,
        help=(
            "Optional raster window in milliseconds. Example: "
            "--raster-window-ms -5000 5000"
        ),
    )
    args = parser.parse_args()

    patient_folders = _choose_patient_folders()
    if not patient_folders:
        print("No patient folders selected.")
        return 1

    output_root = _choose_output_root(patient_folders)
    raw_analysis_override = _analysis_override_from_args(args.raster_window_ms)
    analysis_cfg = analysis_dict_to_config(raw_analysis_override)

    raster_window = getattr(analysis_cfg, "raster_window_ms", (-3000, 5000))
    print()
    print("=" * 80)
    print("Launcher Settings")
    print("=" * 80)
    print(f"Selected folders   : {len(patient_folders)}")
    print(f"Output root        : {output_root}")
    print(f"Raster window      : {raster_window[0]} to {raster_window[1]} ms")
    print("=" * 80)

    n_success = 0
    n_failed = 0
    for patient_folder in patient_folders:
        ok = _run_one_patient(
            patient_folder=patient_folder,
            output_root=output_root,
            analysis_cfg=analysis_cfg,
            raw_analysis_override=raw_analysis_override,
            dry_run=args.dry_run,
        )
        if ok:
            n_success += 1
        else:
            n_failed += 1

    print()
    print("=" * 80)
    print("Pipeline Summary")
    print("=" * 80)
    print(f"Patient folders selected : {len(patient_folders)}")
    print(f"Successful               : {n_success}")
    print(f"Failed / skipped         : {n_failed}")
    print(f"Outputs written to       : {output_root}")
    print("=" * 80)

    if n_failed == 0:
        print("ALL PATIENTS COMPLETED SUCCESSFULLY")
        return 0

    print("PIPELINE COMPLETED WITH ERRORS")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())