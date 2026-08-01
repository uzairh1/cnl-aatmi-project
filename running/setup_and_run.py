#!/usr/bin/env python3
"""Interactive pipeline setup with dry-run planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .config import PIPELINE_ANALYSIS_CONFIG
    from .pipeline_executor import analysis_dict_to_config, plan_patient_pipeline, patient_dict_to_config, run_pipeline
except ImportError:  # pragma: no cover
    from config import PIPELINE_ANALYSIS_CONFIG
    from pipeline_executor import analysis_dict_to_config, plan_patient_pipeline, patient_dict_to_config, run_pipeline


def _prompt_str(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("This value is required.")


def _prompt_optional_str(label: str) -> str:
    return input(f"{label} (press Enter to leave blank): ").strip()


def _prompt_float(label: str) -> float:
    while True:
        value = input(f"{label}: ").strip()
        try:
            return float(value)
        except ValueError:
            print("Enter a number.")


def _prompt_patient() -> Dict[str, object]:
    print("\nPatientConfig")
    return {
        "patient_id": _prompt_str("patient_id"),
        "movie_label": _prompt_str("movie_label"),
        "signal_path": _prompt_str("signal_path"),
        "clip_ttl_csv": _prompt_str("clip_ttl_csv"),
        "localization_file": _prompt_optional_str("localization_file"),
        "output_tag": _prompt_optional_str("output_tag"),
        "matLab": _prompt_float("matLab"),
        "start_unix_0": _prompt_float("start_unix_0"),
        "duration": _prompt_float("duration"),
        "fps": _prompt_float("fps"),
    }


def _prompt_movie_bin_size() -> int:
    default = PIPELINE_ANALYSIS_CONFIG.movie_bin_size_s
    raw = input(f"movie_bin_size_s [{default}]: ").strip()
    if raw == "":
        return default
    try:
        return int(float(raw))
    except ValueError:
        print("Invalid value; using default.")
        return default


def _print_tree(plan: dict) -> None:
    print(f"patient_root: {plan['patient_root']}")
    print("folders:")
    for item in plan["folders"]:
        print(f"  - {item}")
    print("canonical_files:")
    for item in plan["canonical_files"]:
        print(f"  - {item}")
    print("raster_csvs:")
    for item in plan["raster_csvs"]:
        print(f"  - {item}")
    print("raster_region_csvs:")
    for item in plan["raster_region_csvs"]:
        print(f"  - {item}")
    print("swarm_files:")
    for item in plan["swarm_files"]:
        print(f"  - {item}")
    print("dashboards:")
    for item in plan["dashboards"]:
        print(f"  - {item}")
    print(f"movie_bin_size_s: {plan['bin_size_s']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive pipeline setup.")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned output tree without running the pipeline.")
    args = parser.parse_args()

    print("Interactive pipeline setup")
    print("Enter the appropriate values when prompted.\n")

    patients: List[Dict[str, object]] = []
    while True:
        patients.append(_prompt_patient())
        another = input("\nAdd another patient? [y/N]: ").strip().lower()
        if another not in {"y", "yes"}:
            break

    output_root = _prompt_str("\noutput_root")
    bin_size_s = _prompt_movie_bin_size()

    if args.dry_run:
        analysis_cfg = analysis_dict_to_config(None)
        output_root_path = Path(output_root)
        for raw_patient in patients:
            patient_cfg = patient_dict_to_config(raw_patient)
            plan = plan_patient_pipeline(patient_cfg, analysis_cfg, output_root_path, bin_size_s=bin_size_s)
            _print_tree(plan)
        return 0

    run_pipeline(patients, None, output_root, bin_size_s=bin_size_s)
    print(f"Pipeline launched to: {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
