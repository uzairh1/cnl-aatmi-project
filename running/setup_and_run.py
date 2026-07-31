#!/usr/bin/env python3
"""setup_and_run.py

Prompt for the monolithic hardcoded values and launch the pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .pipeline_executor import run_pipeline
except ImportError:
    from pipeline_executor import run_pipeline

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

def _prompt_int(label: str) -> int:
    while True:
        value = input(f"{label}: ").strip()
        try:
            return int(float(value))
        except ValueError:
            print("Enter an integer.")

def _prompt_pair(label: str) -> tuple[int, int]:
    while True:
        first = input(f"{label} start: ").strip()
        second = input(f"{label} end: ").strip()
        try:
            return int(float(first)), int(float(second))
        except ValueError:
            print("Enter two numbers.")

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
        "event_time_offset_ms": _prompt_float("event_time_offset_ms"),
    }

def _prompt_analysis() -> Dict[str, object]:
    print("\nAnalysisConfig")
    pre_window_ms = _prompt_pair("pre_window_ms")
    post_window_ms = _prompt_pair("post_window_ms")
    raster_window_ms = _prompt_pair("raster_window_ms")
    return {
        "pre_window_ms": pre_window_ms,
        "post_window_ms": post_window_ms,
        "raster_window_ms": raster_window_ms,
        "min_rate_hz": _prompt_float("min_rate_hz"),
        "alpha": _prompt_float("alpha"),
        "stat_style": _prompt_str("stat_style"),
        "n_permutations": _prompt_int("n_permutations"),
        "smoothing": _prompt_str("smoothing"),
        "psth_bin_ms": _prompt_int("psth_bin_ms"),
        "raster_figsize": _prompt_pair("raster_figsize"),
        "raster_dpi": _prompt_int("raster_dpi"),
        "line_length": _prompt_float("line_length"),
        "line_width": _prompt_float("line_width"),
        "clip_end_marker_half_height": _prompt_float("clip_end_marker_half_height"),
    }

def main() -> int:
    print("Interactive pipeline setup")
    print("Enter the monolithic field names when prompted.\n")

    patients: List[Dict[str, object]] = []
    while True:
        patients.append(_prompt_patient())
        another = input("\nAdd another patient? [y/N]: ").strip().lower()
        if another not in {"y", "yes"}:
            break

    analysis = _prompt_analysis()
    output_root = _prompt_str("\noutput_root")
    bin_size_s = _prompt_int("bin_size_s")

    run_pipeline(patients, analysis, output_root, bin_size_s=bin_size_s)
    print(f"Pipeline launched to: {output_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())