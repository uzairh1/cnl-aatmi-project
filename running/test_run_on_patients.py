#!/usr/bin/env python3
"""smoke_test_pipeline.py

Run a single patient from config.py through the end-to-end pipeline and
assert that the expected stage outputs exist.

No JSON manifests. This reads PATIENTS and ANALYSIS_CONFIG from config.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import config as cfg_mod
from run_pipeline import run_patient_pipeline


def _get_patients():
    patients = getattr(cfg_mod, "PATIENTS", None)
    if not patients:
        raise SystemExit(
            "config.py must define PATIENTS as a non-empty list of PatientConfig objects."
        )
    return list(patients)


def _get_analysis_cfg():
    analysis_cfg = getattr(cfg_mod, "ANALYSIS_CONFIG", None)
    if analysis_cfg is None:
        analysis_cfg = getattr(cfg_mod, "DEFAULT_ANALYSIS_CONFIG", None)
    if analysis_cfg is None:
        raise SystemExit(
            "config.py must define ANALYSIS_CONFIG (or DEFAULT_ANALYSIS_CONFIG) as an AnalysisConfig object."
        )
    return analysis_cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real-data smoke test using config.py objects.")
    parser.add_argument("--output-root", required=True, help="Root folder for smoke-test outputs.")
    parser.add_argument("--patient-id", default="", help="Optional patient_id to run from PATIENTS.")
    parser.add_argument("--bin-size-s", type=int, default=10, help="Movie-level bin size in seconds.")
    args = parser.parse_args()

    patients = _get_patients()
    if args.patient_id:
        patients = [p for p in patients if p.patient_id == args.patient_id]
    if not patients:
        raise SystemExit("No matching patients found in config.py PATIENTS.")

    analysis_cfg = _get_analysis_cfg()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    patient_cfg = patients[0]
    artifacts = run_patient_pipeline(patient_cfg, analysis_cfg, output_root, bin_size_s=args.bin_size_s)
    assert artifacts, "Pipeline produced no artifacts"

    patient_root = output_root / (f"P{patient_cfg.patient_id}" + (f"_{patient_cfg.output_tag}" if getattr(patient_cfg, "output_tag", "") else ""))
    assert (patient_root / "data" / "trial_table.csv").exists()
    assert (patient_root / "align1").exists()
    assert (patient_root / "align2").exists()
    assert (patient_root / "binning").exists()
    assert (patient_root / "statistics" / "neuron_summary.csv").exists()
    assert (patient_root / "plots" / "rasters").exists()
    assert (patient_root / "plots" / "swarm").exists()

    print(f"Smoke test passed for patient {patient_cfg.patient_id}")
    print(f"Artifacts: {len(artifacts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())