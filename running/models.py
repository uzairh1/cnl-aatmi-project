"""models.py

Small containers for data moving between modules.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class TrialRecord:
    trial_index: int
    clip_id: Any
    ms_start: float
    ms_end: float
    accurate: int
    plot_y_axis: int
    plot_toggle: int = 1
    movie_id: Optional[int] = None
    response: Optional[Any] = None
    reaction_time_ptb: Optional[float] = None

    @property
    def duration_ms(self) -> float:
        return float(self.ms_end - self.ms_start)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpikeTrain:
    neuron_name: str
    spike_times_s: Tuple[float, ...]
    spike_times_ms: Tuple[float, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AlignedSpike:
    neuron_name: str
    trial_index: int
    clip_id: Any
    accurate: int
    spike_ms_global: float
    spike_ms_from_trial_start: float
    trial_ms_start: float
    trial_ms_end: float
    trial_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WindowStats:
    t_stat: Optional[float]
    p_value: Optional[float]
    n_correct: int
    n_incorrect: int
    significant: bool
    method: str = "welch"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NeuronResult:
    patient_id: str
    neuron_name: str
    localization: str
    bipolar_region: str
    pre: WindowStats
    post: WindowStats
    t_score_diff_pre_minus_post: Optional[float]
    mean_post_rate_hz: Optional[float]
    output_tag: str = ""
    raster_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        row = asdict(self)
        row["raster_path"] = str(self.raster_path) if self.raster_path is not None else None

        pre = row.pop("pre")
        post = row.pop("post")

        row["Pre-Stim T-Score"] = pre["t_stat"]
        row["Pre-Stim P-Value"] = pre["p_value"]
        row["Pre-Stim Significant"] = pre["significant"]

        row["Post-Stim T-Score"] = post["t_stat"]
        row["Post-Stim P-Value"] = post["p_value"]
        row["Post-Stim Significant"] = post["significant"]

        row["T-Score Diff (Pre - Post)"] = row.pop("t_score_diff_pre_minus_post")
        row["Post-Stim Mean Rate (Hz)"] = row.pop("mean_post_rate_hz")
        return row


@dataclass(frozen=True)
class PipelineArtifact:
    name: str
    path: Path
    artifact_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "path": str(self.path), "artifact_type": self.artifact_type}