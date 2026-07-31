#!/usr/bin/env python3
"""run_pipeline.py

Set-and-forget driver for the refactored pipeline.

This driver reads patient and analysis objects directly from config.py.
No JSON manifests, no external config files.

Expected config.py convention:
    PATIENTS = [PatientConfig(...), ...]
    ANALYSIS_CONFIG = AnalysisConfig(...)

If PATIENTS / ANALYSIS_CONFIG are not defined, the driver raises a clear
error telling you what to add to config.py.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Iterable, List, Sequence

import pandas as pd

import config as cfg_mod
from analysis.binning import bin_align1_folder
from analysis.statistics import analyze_align1_folder, load_clip_table
from analysis.session_alignment_align1 import align_session_folder as align_session_folder_align1
from analysis.trial_alignment_align2 import align_session_folder as align_session_folder_align2
from data_io.localization import infer_neuron_localization, load_localization_map
from data_io.ttl_table_parser import build_trial_table
from models import PipelineArtifact
from plotting.rasters import plot_align1_folder
from plotting.swarm import generate_population_swarm_plot
from plotting.summary_figures import generate_summary_figures


def _get_patients() -> list:
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


def _patient_root(output_root: Path, patient_cfg) -> Path:
    suffix = f"_{patient_cfg.output_tag}" if getattr(patient_cfg, "output_tag", "") else ""
    return output_root / f"P{patient_cfg.patient_id}{suffix}"


def _add_artifacts_from_paths(paths: Sequence[Path], artifact_type: str) -> list[PipelineArtifact]:
    return [PipelineArtifact(name=p.name, path=p, artifact_type=artifact_type) for p in paths]


def _load_trial_table(ttl_csv: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trial_df, written_path = build_trial_table(ttl_csv=ttl_csv, output_csv=output_path)
    return trial_df, Path(written_path) if written_path is not None else output_path


def _write_localization_trace(align1_dir: Path, loc_df: pd.DataFrame, output_path: Path) -> Path | None:
    if loc_df.empty:
        return None

    align1_files = sorted(align1_dir.glob("align1_*.csv"))
    if not align1_files:
        return None

    rows = []
    for align1_file in align1_files:
        neuron_name = align1_file.name.removeprefix("align1_").removesuffix(".csv")
        try:
            electrode_code, full_location, region_abbr = infer_neuron_localization(neuron_name, loc_df)
        except Exception:
            electrode_code, full_location, region_abbr = ("UNKNOWN", "Unknown", "UNKNOWN")

        rows.append(
            {
                "neuron_name": neuron_name,
                "electrode_code": electrode_code,
                "full_location": full_location,
                "region_abbr": region_abbr,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def run_patient_pipeline(
    patient_cfg,
    analysis_cfg,
    output_root: Path,
    *,
    bin_size_s: int = 10,
) -> list[PipelineArtifact]:
    from config import validate_analysis_config, validate_patient_config

    validate_patient_config(patient_cfg)
    validate_analysis_config(analysis_cfg)

    patient_root = _patient_root(output_root, patient_cfg)
    patient_root.mkdir(parents=True, exist_ok=True)

    data_dir = patient_root / "data"
    align1_dir = patient_root / "align1"
    align2_dir = patient_root / "align2"
    binning_dir = patient_root / "binning"
    stats_dir = patient_root / "statistics"
    rasters_dir = patient_root / "plots" / "rasters"
    swarm_dir = patient_root / "plots" / "swarm"

    for d in (data_dir, align1_dir, align2_dir, binning_dir, stats_dir, rasters_dir, swarm_dir):
        d.mkdir(parents=True, exist_ok=True)

    artifacts: list[PipelineArtifact] = []

    # Stage 1: TTL -> trial_table.csv
    trial_table_path = data_dir / "trial_table.csv"
    trial_df, trial_table_path = _load_trial_table(patient_cfg.clip_ttl_csv, trial_table_path)
    artifacts.append(PipelineArtifact(name=trial_table_path.name, path=trial_table_path, artifact_type="trial_table"))

    # Stage 2: Align 1
    session_start_seconds = patient_cfg.start_unix_0 - patient_cfg.matLab + (getattr(patient_cfg, "event_time_offset_ms", 0.0) / 1000.0)
    align1_files = align_session_folder_align1(
        spike_csv_dir=patient_cfg.signal_path,
        session_start_seconds=session_start_seconds,
        session_duration_seconds=patient_cfg.duration,
        align1_output_dir=align1_dir,
    )
    artifacts.extend(_add_artifacts_from_paths(align1_files, "align1_csv"))

    # Stage 3: Align 2
    align2_files = align_session_folder_align2(
        align1_input_dir=align1_dir,
        trial_table=trial_df,
        align2_output_dir=align2_dir,
    )
    artifacts.extend(_add_artifacts_from_paths(align2_files, "align2_csv"))

    # Stage 4: Bin movie-aligned spikes
    binned_files = bin_align1_folder(align1_dir=align1_dir, output_dir=binning_dir, bin_size_s=bin_size_s)
    artifacts.extend(_add_artifacts_from_paths(binned_files, "binned_csv"))

    # Stage 5: Statistics
    clips_df = load_clip_table(trial_table_path)
    stats_csv = stats_dir / "neuron_summary.csv"
    stats_df = analyze_align1_folder(
        align1_dir=align1_dir,
        clips_df=clips_df,
        patient_id=patient_cfg.patient_id,
        output_csv=stats_csv,
        output_tag=getattr(patient_cfg, "output_tag", ""),
        min_rate_hz=analysis_cfg.min_rate_hz,
        pre_window_ms=analysis_cfg.pre_window_ms,
        post_window_ms=analysis_cfg.post_window_ms,
        alpha=analysis_cfg.alpha,
        significance_method="p_value",
    )
    artifacts.append(PipelineArtifact(name=stats_csv.name, path=stats_csv, artifact_type="neuron_summary_csv"))

    # Stage 6: Raster plots
    raster_pngs = plot_align1_folder(
        align1_dir=align1_dir,
        clips_table=trial_table_path,
        output_dir=rasters_dir,
        patient_id=patient_cfg.patient_id,
        localization_file=getattr(patient_cfg, "localization_file", ""),
        summary_csv=stats_csv,
        output_tag=getattr(patient_cfg, "output_tag", ""),
        window_start_ms=analysis_cfg.raster_window_ms[0],
        window_end_ms=analysis_cfg.raster_window_ms[1],
        split_by_accuracy=True,
        show_clip_end_marker=True,
        smooth_type=analysis_cfg.smoothing,
        min_rate_hz=analysis_cfg.min_rate_hz,
    )
    artifacts.extend(_add_artifacts_from_paths(raster_pngs, "raster_png"))

    # Optional localization trace
    localization_file = getattr(patient_cfg, "localization_file", "")
    if localization_file:
        loc_df = load_localization_map(localization_file)
        trace_path = _write_localization_trace(align1_dir, loc_df, patient_root / "localization_trace.csv")
        if trace_path is not None:
            artifacts.append(PipelineArtifact(name=trace_path.name, path=trace_path, artifact_type="localization_trace"))

    # Stage 7: Swarm plots
    generate_population_swarm_plot(summary_csv=stats_csv, output_dir=swarm_dir)
    artifacts.append(PipelineArtifact(name=swarm_dir.name, path=swarm_dir, artifact_type="swarm_output_dir"))

    # Stage 8: Final summary dashboards
    run_summary_df, dashboard_pngs = generate_summary_figures(output_root=swarm_dir, summary_csv=stats_csv)
    if not run_summary_df.empty:
        run_summary_csv = swarm_dir / "Run_Summary.csv"
        artifacts.append(PipelineArtifact(name=run_summary_csv.name, path=run_summary_csv, artifact_type="run_summary_csv"))
    artifacts.extend(_add_artifacts_from_paths(dashboard_pngs, "dashboard_png"))

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the end-to-end pipeline using config.py objects.")
    parser.add_argument("--output-root", required=True, help="Root folder where per-patient outputs will be written.")
    parser.add_argument("--bin-size-s", type=int, default=10, help="Movie-level bin size in seconds.")
    args = parser.parse_args()

    patients = _get_patients()
    analysis_cfg = _get_analysis_cfg()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    all_artifacts: list[PipelineArtifact] = []
    for patient_cfg in patients:
        print(f"Running patient {patient_cfg.patient_id}...")
        artifacts = run_patient_pipeline(patient_cfg, analysis_cfg, output_root, bin_size_s=args.bin_size_s)
        all_artifacts.extend(artifacts)
        print(f"  Wrote {len(artifacts)} artifacts.")

    manifest = output_root / "pipeline_artifacts.json"
    import json
    manifest.write_text(
        json.dumps([a.to_dict() for a in all_artifacts], indent=2),
        encoding="utf-8",
    )
    print(f"Saved artifact manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())