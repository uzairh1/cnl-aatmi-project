#!/usr/bin/env python3
"""setup_and_run.py

Interactive prompting for the same field names used in the monolithic script.
This script only collects values and passes them to pipeline_executor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from pipeline_executor import run_pipeline

# -----------------------------------------------------------------------------
# Monolithic-style prompt defaults
# -----------------------------------------------------------------------------

PATIENT_CONFIGS: List[Dict[str, object]] = [
    {
        "patient_id": "566",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/566TMexp7presleep",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/566TMexp7presleep/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-566_localizations.xlsx",
        "output_tag": "exp7presleep",
        "matLab": 1691272807.193047,
        "start_unix_0": 1691273171.2970471,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "567",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/567TMexp8presleep",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/567TMexp8presleep/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-567_localizations.xlsx",
        "output_tag": "exp8presleep",
        "matLab": 1692747794.1907692,
        "start_unix_0": 1692748176.5677693,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "568",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/568TMexp5presleep",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/568TMexp5presleep/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-568_localizations.xlsx",
        "output_tag": "exp5presleep",
        "matLab": 1700603867.2240472,
        "start_unix_0": 1700604469.2170877,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "570",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/570TMexp4presleep",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/570TMexp4presleep/570_TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-570_localizations.xlsx",
        "output_tag": "exp4presleep",
        "matLab": 1706304396.2999392,
        "start_unix_0": 1706308502.2209392,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "572",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/572TMexp9presleepviewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/572TMexp9presleepviewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-572_localizations.xlsx",
        "output_tag": "exp9presleepviewing",
        "matLab": 1711142763.6770148,
        "start_unix_0": 1711143392.781015,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "573",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/573TMexp7presleepviewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/573TMexp7presleepviewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-573_localizations.xlsx",
        "output_tag": "exp7presleepviewing",
        "matLab": 1714775636.2359192,
        "start_unix_0": 1714775660.3849192,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "574",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/574TMexp10viewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/574TMexp10viewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-574_localizations.xlsx",
        "output_tag": "exp10viewing",
        "matLab": 1721747817.881015,
        "start_unix_0": 1721747828.862015,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "576",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/576TMexp14Viewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/576TMexp14Viewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-576_localizations.xlsx",
        "output_tag": "exp14Viewing",
        "matLab": 1726515700.953,
        "start_unix_0": 1726515776.9090002,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "577",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/577TMexp4viewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/577TMexp4viewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-577_localizations.xlsx",
        "output_tag": "exp4viewing",
        "matLab": 1726269951.420004,
        "start_unix_0": 1726269994.518004,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "579",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/579TMexp6viewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/579TMexp6viewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-579_localizations.xlsx",
        "output_tag": "exp6viewing",
        "matLab": 1734025549.335989,
        "start_unix_0": 1734025573.176989,
        "duration": 2476.867,
        "fps": 29.97,
    },
    {
        "patient_id": "582",
        "movie_label": "24",
        "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/582TMexp8viewing",
        "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/582TMexp8viewing/TTL_table.csv",
        "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-582_localizations.xlsx",
        "output_tag": "exp8viewing",
        "matLab": 1742751241.165916,
        "start_unix_0": 1742751270.809916,
        "duration": 2476.867,
        "fps": 29.97,
    },
]

ANALYSIS_TEMPLATE: Dict[str, object] = {
    "pre_window_ms": (-1000, 0),
    "post_window_ms": (200, 1200),
    "raster_window_ms": (-3000, 5000),
    "min_rate_hz": 0.25,
    "alpha": 0.05,
    "stat_style": "welch",
    "n_permutations": 1000,
    "smoothing": "triangle",
    "psth_bin_ms": 100,
    "raster_figsize": (12.0, 8.0),
    "raster_dpi": 200,
    "line_length": 0.8,
    "line_width": 0.6,
    "clip_end_marker_half_height": 0.32,
}

def _prompt_value(label: str, default):
    raw = input(f"{label} [{default}]: ").strip()
    if raw == "":
        return default
    return raw

def _prompt_float(label: str, default: float) -> float:
    while True:
        value = _prompt_value(label, default)
        try:
            return float(value)
        except ValueError:
            print("Enter a number.")

def _prompt_int(label: str, default: int) -> int:
    while True:
        value = _prompt_value(label, default)
        try:
            return int(float(value))
        except ValueError:
            print("Enter an integer.")

def _prompt_patient(template: Dict[str, object]) -> Dict[str, object]:
    print("\nPatientConfig")
    return {
        "patient_id": _prompt_value("patient_id", template["patient_id"]),
        "movie_label": _prompt_value("movie_label", template["movie_label"]),
        "signal_path": _prompt_value("signal_path", template["signal_path"]),
        "clip_ttl_csv": _prompt_value("clip_ttl_csv", template["clip_ttl_csv"]),
        "localization_file": _prompt_value("localization_file", template["localization_file"]),
        "output_tag": _prompt_value("output_tag", template["output_tag"]),
        "matLab": _prompt_float("matLab", float(template["matLab"])),
        "start_unix_0": _prompt_float("start_unix_0", float(template["start_unix_0"])),
        "duration": _prompt_float("duration", float(template["duration"])),
        "fps": _prompt_float("fps", float(template["fps"])),
        "event_time_offset_ms": _prompt_float("event_time_offset_ms", 0.0),
    }

def _prompt_analysis(template: Dict[str, object]) -> Dict[str, object]:
    print("\nAnalysisConfig")
    pre = template["pre_window_ms"]
    post = template["post_window_ms"]
    raster = template["raster_window_ms"]
    return {
        "pre_window_ms": (
            _prompt_int("pre_window_start_ms", pre[0]),
            _prompt_int("pre_window_end_ms", pre[1]),
        ),
        "post_window_ms": (
            _prompt_int("post_window_start_ms", post[0]),
            _prompt_int("post_window_end_ms", post[1]),
        ),
        "raster_window_ms": (
            _prompt_int("raster_window_start_ms", raster[0]),
            _prompt_int("raster_window_end_ms", raster[1]),
        ),
        "min_rate_hz": _prompt_float("min_rate_hz", float(template["min_rate_hz"])),
        "alpha": _prompt_float("alpha", float(template["alpha"])),
        "stat_style": _prompt_value("stat_style", template["stat_style"]),
        "n_permutations": _prompt_int("n_permutations", int(template["n_permutations"])),
        "smoothing": _prompt_value("smoothing", template["smoothing"]),
        "psth_bin_ms": _prompt_int("psth_bin_ms", int(template["psth_bin_ms"])),
        "raster_figsize": (
            float(template["raster_figsize"][0]),
            float(template["raster_figsize"][1]),
        ),
        "raster_dpi": int(template["raster_dpi"]),
        "line_length": float(template["line_length"]),
        "line_width": float(template["line_width"]),
        "clip_end_marker_half_height": float(template["clip_end_marker_half_height"]),
    }

def main() -> int:
    print("Interactive pipeline setup")
    print("Press Enter to keep the default shown in brackets.\n")

    raw_patients = [_prompt_patient(t) for t in PATIENT_CONFIGS]
    raw_analysis = _prompt_analysis(ANALYSIS_TEMPLATE)

    print("\nCollected configuration:")
    print(json.dumps({"PATIENT_CONFIGS": raw_patients, "ANALYSIS_CONFIG": raw_analysis}, indent=2))

    output_root = _prompt_value("output_root", str(Path.cwd() / "outputs"))
    bin_size_s = _prompt_int("bin_size_s", 10)

    run_pipeline(raw_patients, raw_analysis, output_root, bin_size_s=bin_size_s)
    print(f"Pipeline launched to: {output_root}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())