"""Configuration layer for the naturalistic SME pipeline.

This module keeps definitions and defaults only.
Patient-specific metadata (paths, timestamps, FPS, etc.) should live in an
external JSON manifest that is loaded at runtime.

Keep this file stable and boring: it should define the vocabulary and
analysis settings used everywhere else in the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Union
import json


# =============================================================================
# REGION / LABEL MAPPINGS
# =============================================================================

# Short abbreviations used in the localization spreadsheet -> readable labels.
# These are stable analysis vocabulary, so keeping them here is appropriate.
BIPOLAR_REGIONS: Dict[str, str] = {
    "AMY": "amygdala",
    "BAS": "basal ganglia (putamen, pallidum)",
    "CC": "anterior cingulate cortex",
    "CENT": "pre-/para/POST-central (motor) cortex",
    "ERC": "entorhinal cortex",
    "FC": "frontal cortex (includes SFG, MFG, IFG, OFC)",
    "FUS": "fusiform cortex",
    "HPC": "hippocampus",
    "INS": "insula",
    "LTC": "lateral temporal cortex (includes STG, MTG, IFG, banksSTS and TP)",
    "MCC": "to differentiate from ACC (includes MCC and PCC)",
    "PARS": "pars orbitalis/triangularis/opercularis",
    "PC": "parietal cortex (precuneus, inferiorparietal, somatosensory, supramarginal)",
    "PHC": "parahippocampal gyrus (parahippocampal, perirhinal)",
    "UNKNOWN": "Unknown",
    "VIS": "visual cortex (includes lingual, pericalcarine, cuneus)",
    "WM": "white matter",
}

# Folder-routing rules for aggregate outputs.
TARGET_FOLDERS: Dict[str, List[str]] = {
    "HPC": ["HPC"],
    "ERC": ["ERC"],
    "FC": ["FC"],
    "LTC": ["LTC"],
    "MTL": ["AMY", "ERC", "HPC", "PHC"],
}


# =============================================================================
# CONFIG OBJECTS
# =============================================================================

@dataclass(frozen=True)
class PatientConfig:
    """Patient-specific run metadata.

    This class is only a schema. Values should come from an external manifest,
    e.g. a patients.json file.
    """

    patient_id: str
    movie_label: str
    signal_path: str
    clip_ttl_csv: str
    localization_file: str = ""
    output_tag: str = ""
    matLab: float = 0.0
    start_unix_0: float = 0.0
    duration: float = 0.0
    fps: float = 29.97
    event_time_offset_ms: float = 0.0


@dataclass(frozen=True)
class AnalysisConfig:
    """Analysis-wide parameters that define the methodology.

    These are not patient-specific. They are the reusable scientific choices:
    windows, thresholds, permutation count, smoothing choice, etc.
    """

    pre_window_ms: Tuple[int, int] = (-1000, 0)
    post_window_ms: Tuple[int, int] = (200, 1200)
    raster_window_ms: Tuple[int, int] = (-3000, 5000)
    min_rate_hz: float = 0.25
    alpha: float = 0.05
    stat_style: str = "permutation"  # "permutation" or "welch"
    n_permutations: int = 1000
    smoothing: str = "triangle"  # "none", "triangle", "gaussian_kde", "bin_resize_trial_1"
    psth_bin_ms: int = 100
    raster_figsize: Tuple[float, float] = (12.0, 8.0)
    raster_dpi: int = 200
    line_length: float = 0.8
    line_width: float = 0.6
    clip_end_marker_half_height: float = 0.32


# =============================================================================
# DEFAULTS / CONSTANTS
# =============================================================================

DEFAULT_ANALYSIS_CONFIG = AnalysisConfig()
DEFAULT_BASE_OUTPUT_DIR = Path.cwd()


# =============================================================================
# EXTERNAL MANIFEST LOADERS
# =============================================================================

ManifestPath = Union[str, Path]


def load_patient_configs(manifest_path: ManifestPath) -> List[PatientConfig]:
    """Load one or more patient configs from JSON.

    Expected JSON format:
    [
      {
        "patient_id": "570",
        "movie_label": "24",
        "signal_path": "...",
        "clip_ttl_csv": "...",
        "localization_file": "...",
        "output_tag": "exp4presleep",
        "matLab": 1706304396.2999392,
        "start_unix_0": 1706308502.2209392,
        "duration": 2476.867,
        "fps": 29.97,
        "event_time_offset_ms": 0.0
      }
    ]

    A single JSON object is also accepted and will be wrapped into a list.
    """

    path = Path(manifest_path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        raw = [raw]

    configs: List[PatientConfig] = []
    for item in raw:
        configs.append(
            PatientConfig(
                patient_id=str(item["patient_id"]),
                movie_label=str(item.get("movie_label", "")),
                signal_path=str(item["signal_path"]),
                clip_ttl_csv=str(item["clip_ttl_csv"]),
                localization_file=str(item.get("localization_file", "")),
                output_tag=str(item.get("output_tag", "")),
                matLab=float(item.get("matLab", 0.0)),
                start_unix_0=float(item.get("start_unix_0", 0.0)),
                duration=float(item.get("duration", 0.0)),
                fps=float(item.get("fps", 29.97)),
                event_time_offset_ms=float(item.get("event_time_offset_ms", 0.0)),
            )
        )

    return configs


def load_analysis_config(manifest_path: ManifestPath) -> AnalysisConfig:
    """Load analysis-wide settings from JSON.

    Expected JSON format:
    {
      "pre_window_ms": [-1000, 0],
      "post_window_ms": [200, 1200],
      "raster_window_ms": [-3000, 5000],
      "min_rate_hz": 0.25,
      "alpha": 0.05,
      "stat_style": "permutation",
      "n_permutations": 1000,
      "smoothing": "triangle",
      "psth_bin_ms": 100
    }
    """

    path = Path(manifest_path)
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    return AnalysisConfig(
        pre_window_ms=tuple(raw.get("pre_window_ms", (-1000, 0))),
        post_window_ms=tuple(raw.get("post_window_ms", (200, 1200))),
        raster_window_ms=tuple(raw.get("raster_window_ms", (-3000, 5000))),
        min_rate_hz=float(raw.get("min_rate_hz", 0.25)),
        alpha=float(raw.get("alpha", 0.05)),
        stat_style=str(raw.get("stat_style", "permutation")),
        n_permutations=int(raw.get("n_permutations", 1000)),
        smoothing=str(raw.get("smoothing", "triangle")),
        psth_bin_ms=int(raw.get("psth_bin_ms", 100)),
        raster_figsize=tuple(raw.get("raster_figsize", (12.0, 8.0))),
        raster_dpi=int(raw.get("raster_dpi", 200)),
        line_length=float(raw.get("line_length", 0.8)),
        line_width=float(raw.get("line_width", 0.6)),
        clip_end_marker_half_height=float(raw.get("clip_end_marker_half_height", 0.32)),
    )


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_patient_config(cfg: PatientConfig) -> None:
    """Lightweight guardrail to catch obvious missing fields early."""

    missing: List[str] = []
    if not cfg.patient_id:
        missing.append("patient_id")
    if not cfg.signal_path:
        missing.append("signal_path")
    if not cfg.clip_ttl_csv:
        missing.append("clip_ttl_csv")
    if missing:
        raise ValueError(f"PatientConfig missing required fields: {', '.join(missing)}")


def validate_analysis_config(cfg: AnalysisConfig) -> None:
    """Lightweight guardrail for analysis settings."""

    if cfg.pre_window_ms[0] >= cfg.pre_window_ms[1]:
        raise ValueError("pre_window_ms must be an increasing interval")
    if cfg.post_window_ms[0] >= cfg.post_window_ms[1]:
        raise ValueError("post_window_ms must be an increasing interval")
    if cfg.raster_window_ms[0] >= cfg.raster_window_ms[1]:
        raise ValueError("raster_window_ms must be an increasing interval")
    if cfg.min_rate_hz < 0:
        raise ValueError("min_rate_hz must be non-negative")
    if cfg.n_permutations <= 0:
        raise ValueError("n_permutations must be positive")
    if cfg.alpha <= 0 or cfg.alpha >= 1:
        raise ValueError("alpha must be between 0 and 1")