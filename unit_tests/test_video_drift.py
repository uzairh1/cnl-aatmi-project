from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_io.ttl_table_parser import build_trial_table
from running.config import AnalysisConfig, PatientConfig
from running import pipeline_executor


def _make_ttl_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "experimentPhase": ["recog_task", "recog_task"],
            "movieID": [1, 1],
            "trialNumber": [1, 2],
            "clipID": [101, 102],
            "response": [2, 1],
            "reactionTimePTB": [1.0, 1.2],
            "clipStartTime": [10.0, 20.0],
            "clipEndTime": [12.0, 24.0],
            "frameOn": [300, 600],
            "frameOff": [360, 720],
        }
    )


def test_build_trial_table_applies_drift_slope(tmp_path: Path) -> None:
    ttl_path = tmp_path / "TTL_table.csv"
    _make_ttl_df().to_csv(ttl_path, index=False)

    out_path = tmp_path / "trial_table.csv"
    table, written_path = build_trial_table(
        ttl_csv=ttl_path,
        output_csv=out_path,
        drift_rate_slope=0.001,
    )

    assert written_path == out_path
    factor = 1.001
    first = table.iloc[0]
    assert first["clipStartTime"] == pytest.approx(10.0 * factor)
    assert first["clipEndTime"] == pytest.approx(12.0 * factor)
    assert first["clipStartTimeMs"] == int(round(10.0 * factor * 1000.0))
    assert first["clipEndTimeMs"] == int(round(12.0 * factor * 1000.0))
    assert first["clipDurationSec"] == pytest.approx(2.0 * factor)
    assert first["clipDurationMs"] == int(round(2.0 * factor * 1000.0))


def test_run_patient_pipeline_passes_drift_to_trial_table_and_align1(tmp_path: Path, monkeypatch) -> None:
    ttl_path = tmp_path / "TTL_table.csv"
    _make_ttl_df().to_csv(ttl_path, index=False)

    patient = PatientConfig(
        patient_id="570",
        movie_label="24",
        signal_path=str(tmp_path / "signals"),
        clip_ttl_csv=str(ttl_path),
        localization_file="",
        output_tag="",
        matLab=100.0,
        start_unix_0=110.0,
        duration=20.0,
        fps=29.97,
        drift_rate_slope=0.001,
    )
    analysis = AnalysisConfig()

    captured = {}

    def fake_load_trial_table(ttl_csv: str, output_path: Path, *, drift_rate_slope: float = 0.0):
        captured["drift_rate_slope"] = drift_rate_slope
        df = _make_ttl_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        return df, output_path

    def fake_align_session_folder_align1(*, spike_csv_dir, session_start_seconds, session_duration_seconds, align1_output_dir):
        captured["session_start_seconds"] = session_start_seconds
        captured["session_duration_seconds"] = session_duration_seconds
        align1_output_dir.mkdir(parents=True, exist_ok=True)
        out = align1_output_dir / "align1_times_manual_unit_1.csv"
        pd.DataFrame({"units": [1], "spikeTimeRawS": [110.0], "movieAlignedTimeS": [10.0], "movieAlignedTimeMs": [10000.0]}).to_csv(out, index=False)
        return [out]

    monkeypatch.setattr(pipeline_executor, "_load_trial_table", fake_load_trial_table)
    monkeypatch.setattr(pipeline_executor, "align_session_folder_align1", fake_align_session_folder_align1)
    monkeypatch.setattr(pipeline_executor, "align_session_folder_align2", lambda **kwargs: [])
    monkeypatch.setattr(pipeline_executor, "bin_align1_folder", lambda **kwargs: [])
    monkeypatch.setattr(pipeline_executor, "analyze_align1_folder", lambda **kwargs: None)
    monkeypatch.setattr(pipeline_executor, "plot_align1_folder", lambda **kwargs: [])
    monkeypatch.setattr(pipeline_executor, "generate_population_swarm_plot", lambda **kwargs: None)
    monkeypatch.setattr(pipeline_executor, "generate_summary_figures", lambda **kwargs: (pd.DataFrame(), []))
    monkeypatch.setattr(pipeline_executor, "load_clip_table", lambda path: _make_ttl_df())
    monkeypatch.setattr(pipeline_executor, "load_localization_map", lambda path: pd.DataFrame())

    artifacts = pipeline_executor.run_patient_pipeline(patient, analysis, tmp_path)

    assert captured["drift_rate_slope"] == pytest.approx(0.001)
    assert captured["session_start_seconds"] == pytest.approx(10.0)
    assert captured["session_duration_seconds"] == pytest.approx(20.0)
    assert artifacts