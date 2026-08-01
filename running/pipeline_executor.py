"""Transform prompted dictionaries into pipeline objects and execute stages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from .config import (
        AnalysisConfig,
        PatientConfig,
        PIPELINE_ANALYSIS_CONFIG,
        validate_analysis_config,
        validate_patient_config,
    )
    from .models import PipelineArtifact
except ImportError:  # pragma: no cover
    from config import (
        AnalysisConfig,
        PatientConfig,
        PIPELINE_ANALYSIS_CONFIG,
        validate_analysis_config,
        validate_patient_config,
    )
    from models import PipelineArtifact

from analysis.binning import bin_align1_folder
from analysis.statistics import analyze_align1_folder, load_clip_table
from analysis.session_alignment_align1 import align_session_folder as align_session_folder_align1
from analysis.trial_alignment_align2 import align_session_folder as align_session_folder_align2
from data_io.localization import infer_neuron_localization, load_localization_map
from data_io.ttl_table_parser import build_trial_table
from plotting.rasters import plot_align1_folder
from plotting.swarm import generate_population_swarm_plot
from plotting.summary_figures import generate_summary_figures


def _as_pair(value, default):
    if value is None:
        return tuple(default)
    if isinstance(value, str):
        pieces = [p.strip() for p in value.split(",") if p.strip()]
        if len(pieces) == 2:
            return (float(pieces[0]), float(pieces[1]))
        return tuple(default)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return (float(value[0]), float(value[1]))
    return tuple(default)


def patient_dict_to_config(raw: dict) -> PatientConfig:
    return PatientConfig(
        patient_id=str(raw.get("patient_id", "")),
        movie_label=str(raw.get("movie_label", "")),
        signal_path=str(raw.get("signal_path", "")),
        clip_ttl_csv=str(raw.get("clip_ttl_csv", "")),
        localization_file=str(raw.get("localization_file", "")),
        output_tag=str(raw.get("output_tag", "")),
        matLab=float(raw.get("matLab", 0.0)),
        start_unix_0=float(raw.get("start_unix_0", 0.0)),
        duration=float(raw.get("duration", 0.0)),
        fps=float(raw.get("fps", 29.97)),
        drift_rate_slope=float(raw.get("drift_rate_slope", 0.0)),
        event_time_offset_ms=float(raw.get("event_time_offset_ms", 0.0)),
    )


def analysis_dict_to_config(raw: dict | None) -> AnalysisConfig:
    if raw is None:
        return PIPELINE_ANALYSIS_CONFIG

    default = PIPELINE_ANALYSIS_CONFIG
    return AnalysisConfig(
        pre_window_ms=tuple(raw.get("pre_window_ms", default.pre_window_ms)),
        post_window_ms=tuple(raw.get("post_window_ms", default.post_window_ms)),
        raster_window_ms=tuple(raw.get("raster_window_ms", default.raster_window_ms)),
        min_rate_hz=float(raw.get("min_rate_hz", default.min_rate_hz)),
        alpha=float(raw.get("alpha", default.alpha)),
        stat_style=str(raw.get("stat_style", default.stat_style)),
        n_permutations=int(raw.get("n_permutations", default.n_permutations)),
        smoothing=str(raw.get("smoothing", default.smoothing)),
        psth_bin_ms=int(raw.get("psth_bin_ms", default.psth_bin_ms)),
        movie_bin_size_s=int(raw.get("movie_bin_size_s", default.movie_bin_size_s)),
        raster_figsize=_as_pair(raw.get("raster_figsize", default.raster_figsize), default.raster_figsize),
        raster_dpi=int(raw.get("raster_dpi", default.raster_dpi)),
        line_length=float(raw.get("line_length", default.line_length)),
        line_width=float(raw.get("line_width", default.line_width)),
        clip_end_marker_half_height=float(raw.get("clip_end_marker_half_height", default.clip_end_marker_half_height)),
    )


def _patient_root(output_root: Path, patient_cfg: PatientConfig) -> Path:
    suffix = f"_{patient_cfg.output_tag}" if patient_cfg.output_tag else ""
    return output_root / f"P{patient_cfg.patient_id}{suffix}"


def _add_artifacts_from_paths(paths: Sequence[Path], artifact_type: str) -> list[PipelineArtifact]:
    return [PipelineArtifact(name=p.name, path=p, artifact_type=artifact_type) for p in paths]


def _load_trial_table(ttl_csv: str, output_path: Path, *, drift_rate_slope: float = 0.0):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    trial_df, written_path = build_trial_table(
        ttl_csv=ttl_csv,
        output_csv=output_path,
        drift_rate_slope=drift_rate_slope,
    )
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
        rows.append({"neuron_name": neuron_name, "electrode_code": electrode_code, "full_location": full_location, "region_abbr": region_abbr})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    return output_path


def plan_patient_pipeline(
    patient_cfg: PatientConfig,
    analysis_cfg: AnalysisConfig,
    output_root: Path,
    *,
    bin_size_s: int | None = None,
) -> dict:
    if bin_size_s is None:
        bin_size_s = analysis_cfg.movie_bin_size_s

    patient_root = _patient_root(output_root, patient_cfg)
    plots_root = patient_root / "plots"
    rasters_root = plots_root / "rasters"
    swarm_root = plots_root / "swarm"
    dashboards_root = plots_root / "dashboards"

    folders = [
        patient_root / "data",
        patient_root / "align1",
        patient_root / "align2",
        patient_root / "binning",
        patient_root / "statistics",
        rasters_root / "all",
        rasters_root / "sig",
        rasters_root / "nonsig",
        rasters_root / "by_region",
        swarm_root / "global",
        swarm_root / "HPC",
        swarm_root / "ERC",
        swarm_root / "FC",
        swarm_root / "LTC",
        swarm_root / "MTL",
        dashboards_root,
    ]

    canonical_files = [
        patient_root / "data" / "trial_table.csv",
        patient_root / "statistics" / "neuron_summary.csv",
        patient_root / "localization_trace.csv",
        patient_root / "pipeline_artifacts.json",
        swarm_root / "Summary_Global_and_Regional.csv",
        swarm_root / "Summary_Patient_Bipolar_Breakdown.csv",
        dashboards_root / "Run_Summary.csv",
    ]

    # The actual raster/swarm files are data-dependent and are therefore
    # returned as patterns here.
    raster_csvs = [
        rasters_root / "all" / "T_score_sheet.csv",
        rasters_root / "sig" / "T_score_sheet.csv",
        rasters_root / "nonsig" / "T_score_sheet.csv",
    ]
    raster_region_csvs = [
        rasters_root / "by_region" / region / "T_score_sheet.csv"
        for region in ["HPC", "ERC", "FC", "LTC", "MTL", "AMY", "INS", "PHC", "CC", "BAS", "CENT", "FUS", "PC", "VIS", "WM", "UNKNOWN"]
    ]
    swarm_files = []
    for region in ["global", "HPC", "ERC", "FC", "LTC", "MTL"]:
        out = swarm_root / region
        swarm_files.extend([
            out / "P1_Post-Stim_T-Scores.png",
            out / "P2_Pre-Stim_T-Scores.png",
            out / "P3_Diff_SigOnly.png",
            out / "P4_Diff_All.png",
            out / "P5_Diff_Post_GTE_1.png",
            out / f"Swarm_Statistics_{region}.csv",
            out / f"Summary_Overview_{region}.csv",
        ])
    dashboards = [dashboards_root / f"{region}_dashboard.png" for region in ["global", "HPC", "ERC", "FC", "LTC", "MTL"]]

    return {
        "patient_root": str(patient_root),
        "bin_size_s": bin_size_s,
        "folders": [str(p) for p in folders],
        "canonical_files": [str(p) for p in canonical_files],
        "raster_csvs": [str(p) for p in raster_csvs],
        "raster_region_csvs": [str(p) for p in raster_region_csvs],
        "swarm_files": [str(p) for p in swarm_files],
        "dashboards": [str(p) for p in dashboards],
    }


def run_patient_pipeline(
    patient_cfg: PatientConfig,
    analysis_cfg: AnalysisConfig,
    output_root: Path,
    *,
    bin_size_s: int | None = None,
) -> list[PipelineArtifact]:
    validate_patient_config(patient_cfg)
    validate_analysis_config(analysis_cfg)

    if bin_size_s is None:
        bin_size_s = analysis_cfg.movie_bin_size_s

    patient_root = _patient_root(output_root, patient_cfg)
    patient_root.mkdir(parents=True, exist_ok=True)

    data_dir = patient_root / "data"
    align1_dir = patient_root / "align1"
    align2_dir = patient_root / "align2"
    binning_dir = patient_root / "binning"
    stats_dir = patient_root / "statistics"
    rasters_dir = patient_root / "plots" / "rasters"
    swarm_dir = patient_root / "plots" / "swarm"
    dashboards_dir = patient_root / "plots" / "dashboards"
    for d in (data_dir, align1_dir, align2_dir, binning_dir, stats_dir, rasters_dir, swarm_dir, dashboards_dir):
        d.mkdir(parents=True, exist_ok=True)

    artifacts: list[PipelineArtifact] = []

    trial_table_path = data_dir / "trial_table.csv"
    trial_df, trial_table_path = _load_trial_table(
        patient_cfg.clip_ttl_csv,
        trial_table_path,
        drift_rate_slope=patient_cfg.drift_rate_slope,
    )
    artifacts.append(PipelineArtifact(name=trial_table_path.name, path=trial_table_path, artifact_type="trial_table"))

    session_start_seconds = patient_cfg.start_unix_0 - patient_cfg.matLab + (patient_cfg.event_time_offset_ms / 1000.0)
    align1_files = align_session_folder_align1(
        spike_csv_dir=patient_cfg.signal_path,
        session_start_seconds=session_start_seconds,
        session_duration_seconds=patient_cfg.duration,
        align1_output_dir=align1_dir,
    )
    artifacts.extend(_add_artifacts_from_paths(align1_files, "align1_csv"))

    align2_files = align_session_folder_align2(
        align1_input_dir=align1_dir,
        trial_table=trial_df,
        align2_output_dir=align2_dir,
    )
    artifacts.extend(_add_artifacts_from_paths(align2_files, "align2_csv"))

    binned_files = bin_align1_folder(align1_dir=align1_dir, output_dir=binning_dir, bin_size_s=bin_size_s)
    artifacts.extend(_add_artifacts_from_paths(binned_files, "binned_csv"))

    clips_df = load_clip_table(trial_table_path)
    stats_csv = stats_dir / "neuron_summary.csv"
    analyze_align1_folder(
        align1_dir=align1_dir,
        clips_df=clips_df,
        patient_id=patient_cfg.patient_id,
        output_csv=stats_csv,
        output_tag=patient_cfg.output_tag,
        min_rate_hz=analysis_cfg.min_rate_hz,
        pre_window_ms=analysis_cfg.pre_window_ms,
        post_window_ms=analysis_cfg.post_window_ms,
        alpha=analysis_cfg.alpha,
        significance_method="p_value",
    )
    artifacts.append(PipelineArtifact(name=stats_csv.name, path=stats_csv, artifact_type="neuron_summary_csv"))

    raster_pngs = plot_align1_folder(
        align1_dir=align1_dir,
        clips_table=trial_table_path,
        output_dir=rasters_dir,
        patient_id=patient_cfg.patient_id,
        localization_file=patient_cfg.localization_file,
        summary_csv=stats_csv,
        output_tag=patient_cfg.output_tag,
        window_start_ms=analysis_cfg.raster_window_ms[0],
        window_end_ms=analysis_cfg.raster_window_ms[1],
        split_by_accuracy=True,
        show_clip_end_marker=True,
        smooth_type=analysis_cfg.smoothing,
        min_rate_hz=analysis_cfg.min_rate_hz,
    )
    artifacts.extend(_add_artifacts_from_paths(raster_pngs, "raster_png"))

    if patient_cfg.localization_file:
        loc_df = load_localization_map(patient_cfg.localization_file)
        trace_path = _write_localization_trace(align1_dir, loc_df, patient_root / "localization_trace.csv")
        if trace_path is not None:
            artifacts.append(PipelineArtifact(name=trace_path.name, path=trace_path, artifact_type="localization_trace"))

    generate_population_swarm_plot(
        summary_csv=stats_csv,
        output_dir=swarm_dir,
        localization_file=patient_cfg.localization_file,
    )
    artifacts.append(PipelineArtifact(name=swarm_dir.name, path=swarm_dir, artifact_type="swarm_output_dir"))

    run_summary_df, dashboard_pngs = generate_summary_figures(output_root=swarm_dir, summary_csv=stats_csv)
    if not run_summary_df.empty:
        run_summary_csv = dashboards_dir / "Run_Summary.csv"
        run_summary_df.to_csv(run_summary_csv, index=False)
        artifacts.append(PipelineArtifact(name=run_summary_csv.name, path=run_summary_csv, artifact_type="run_summary_csv"))
    artifacts.extend(_add_artifacts_from_paths(dashboard_pngs, "dashboard_png"))

    manifest = patient_root / "pipeline_artifacts.json"
    manifest.write_text(json.dumps([a.to_dict() for a in artifacts], indent=2), encoding="utf-8")
    artifacts.append(PipelineArtifact(name=manifest.name, path=manifest, artifact_type="pipeline_artifact_manifest"))
    return artifacts


def run_pipeline(
    raw_patient_dicts: Sequence[dict],
    raw_analysis_dict: dict | None,
    output_root: str | Path,
    *,
    bin_size_s: int | None = None,
) -> list[PipelineArtifact]:
    analysis_cfg = analysis_dict_to_config(raw_analysis_dict)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    all_artifacts: list[PipelineArtifact] = []
    for raw_patient in raw_patient_dicts:
        patient_cfg = patient_dict_to_config(raw_patient)
        artifacts = run_patient_pipeline(patient_cfg, analysis_cfg, output_root, bin_size_s=bin_size_s)
        all_artifacts.extend(artifacts)
    return all_artifacts