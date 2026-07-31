"""config.py

Shared configuration and schema objects for the pipeline.

This file defines the stable vocabulary used by the rest of the repo:
- region mappings
- patient configuration schema
- analysis configuration schema
- validation helpers
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

# =============================================================================
# REGION / LABEL MAPPINGS
# =============================================================================

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

    The values in this schema correspond to the fields that were hardcoded
    in the monolithic pipeline.
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
    """Analysis-wide parameters.

    These settings define the shared windows, thresholds, and plotting
    behavior used across patients.
    """

    pre_window_ms: Tuple[int, int] = (-1000, 0)
    post_window_ms: Tuple[int, int] = (200, 1200)
    raster_window_ms: Tuple[int, int] = (-3000, 5000)
    min_rate_hz: float = 0.25
    alpha: float = 0.05
    stat_style: str = "welch"
    n_permutations: int = 1000
    smoothing: str = "triangle"
    psth_bin_ms: int = 100
    raster_figsize: Tuple[float, float] = (12.0, 8.0)
    raster_dpi: int = 200
    line_length: float = 0.8
    line_width: float = 0.6
    clip_end_marker_half_height: float = 0.32


DEFAULT_ANALYSIS_CONFIG = AnalysisConfig()


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_patient_config(cfg: PatientConfig) -> None:
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