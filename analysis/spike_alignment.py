"""
spike_alignment.py

Align per-unit spike CSVs to:
1. the movie/session timebase
2. individual trial windows

This module keeps the historical align1/align2 file naming if desired,
but uses descriptive column names inside the code.

Input files
-----------
- Per-unit spike CSVs from preprocessing/
    columns: units, s

- Standardized trial table from data_io/
    columns include:
    clipStartTimeMs, clipEndTimeMs, clipWindowId, trialOrder,
    movieID, clipID, isAccurate, plotOrder, includeInPlots

Session timing metadata
-----------------------
- start_unix_0
- matLab
- duration

These are used to compute the movie/session window:
    session_start_seconds = start_unix_0 - matLab
    session_end_seconds = session_start_seconds + duration
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def load_spike_csv(spike_csv_path: str | Path) -> pd.DataFrame:
    """
    Load one per-unit spike CSV produced by preprocessing.

    Expected input columns:
    - units
    - s

    Returns a standardized DataFrame with:
    - units
    - spikeTimeRawS
    """
    spike_csv_path = Path(spike_csv_path)
    df = pd.read_csv(spike_csv_path)

    required = {"units", "s"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{spike_csv_path.name} is missing required columns: {sorted(missing)}"
        )

    out = df.copy()
    out["units"] = pd.to_numeric(out["units"], errors="raise").astype(int)
    out["spikeTimeRawS"] = pd.to_numeric(out["s"], errors="coerce")
    out = out.dropna(subset=["spikeTimeRawS"]).copy()

    return out[["units", "spikeTimeRawS"]]


def align_spikes_to_movie_window(
    spike_df: pd.DataFrame,
    session_start_seconds: float,
    session_duration_seconds: float,
) -> pd.DataFrame:
    """
    Filter spikes to the movie/session window and shift time so movie onset is 0.

    Input
    -----
    spike_df:
        DataFrame from load_spike_csv()

    session_start_seconds:
        The movie-alignment zero point.
        In the old script this was:
            start_unix_0 - matLab

    session_duration_seconds:
        Length of the movie/session window.

    Output
    ------
    A DataFrame with:
    - units
    - spikeTimeRawS
    - movieAlignedTimeS
    - movieAlignedTimeMs
    """
    if spike_df.empty:
        return pd.DataFrame(
            columns=["units", "spikeTimeRawS", "movieAlignedTimeS", "movieAlignedTimeMs"]
        )

    session_end_seconds = session_start_seconds + session_duration_seconds

    filtered = spike_df[
        (spike_df["spikeTimeRawS"] >= session_start_seconds)
        & (spike_df["spikeTimeRawS"] <= session_end_seconds)
    ].copy()

    filtered["movieAlignedTimeS"] = filtered["spikeTimeRawS"] - session_start_seconds
    filtered["movieAlignedTimeMs"] = filtered["movieAlignedTimeS"] * 1000.0

    return filtered[["units", "spikeTimeRawS", "movieAlignedTimeS", "movieAlignedTimeMs"]]


def align_spikes_to_trials(
    movie_aligned_spikes: pd.DataFrame,
    trial_table: pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign each movie-aligned spike to trial windows.

    A spike belongs to a trial if:
        clipStartTimeMs <= movieAlignedTimeMs <= clipEndTimeMs

    Input
    -----
    movie_aligned_spikes:
        Output from align_spikes_to_movie_window()

    trial_table:
        Standardized trial table from data_io/ttl_table_parser.py

    Output
    ------
    Long-form DataFrame with one row per spike per trial.
    """
    if movie_aligned_spikes.empty or trial_table.empty:
        return pd.DataFrame(
            columns=[
                "units",
                "spikeTimeRawS",
                "movieAlignedTimeS",
                "movieAlignedTimeMs",
                "trialOrder",
                "clipWindowId",
                "clipID",
                "movieID",
                "isAccurate",
                "plotOrder",
                "includeInPlots",
                "clipStartTimeMs",
                "clipEndTimeMs",
                "spikeTimeRelativeToClipStartMs",
                "spikeTimeRelativeToClipStartS",
            ]
        )

    required_trial_columns = {"clipStartTimeMs", "clipEndTimeMs", "clipWindowId"}
    missing = required_trial_columns - set(trial_table.columns)
    if missing:
        raise ValueError(
            f"trial_table is missing required columns: {sorted(missing)}"
        )

    rows: list[dict] = []

    for _, trial in trial_table.iterrows():
        clip_start_ms = float(trial["clipStartTimeMs"])
        clip_end_ms = float(trial["clipEndTimeMs"])

        in_trial = movie_aligned_spikes[
            (movie_aligned_spikes["movieAlignedTimeMs"] >= clip_start_ms)
            & (movie_aligned_spikes["movieAlignedTimeMs"] <= clip_end_ms)
        ]

        if in_trial.empty:
            continue

        for _, spike in in_trial.iterrows():
            spike_time_relative_ms = spike["movieAlignedTimeMs"] - clip_start_ms

            rows.append(
                {
                    "units": int(spike["units"]),
                    "spikeTimeRawS": float(spike["spikeTimeRawS"]),
                    "movieAlignedTimeS": float(spike["movieAlignedTimeS"]),
                    "movieAlignedTimeMs": float(spike["movieAlignedTimeMs"]),
                    "trialOrder": int(trial["trialOrder"]) if "trialOrder" in trial else None,
                    "clipWindowId": trial["clipWindowId"],
                    "clipID": trial["clipID"] if "clipID" in trial else None,
                    "movieID": trial["movieID"] if "movieID" in trial else None,
                    "isAccurate": trial["isAccurate"] if "isAccurate" in trial else None,
                    "plotOrder": trial["plotOrder"] if "plotOrder" in trial else None,
                    "includeInPlots": trial["includeInPlots"] if "includeInPlots" in trial else None,
                    "clipStartTimeMs": clip_start_ms,
                    "clipEndTimeMs": clip_end_ms,
                    "spikeTimeRelativeToClipStartMs": spike_time_relative_ms,
                    "spikeTimeRelativeToClipStartS": spike_time_relative_ms / 1000.0,
                }
            )

    return pd.DataFrame(rows)


def save_aligned_spikes(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Save an aligned spike table to disk.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.4f")
    return output_path


def align_one_neuron(
    spike_csv_path: str | Path,
    trial_table: pd.DataFrame,
    session_start_seconds: float,
    session_duration_seconds: float,
    align1_output_dir: str | Path,
    align2_output_dir: str | Path,
) -> tuple[Path, Path]:
    """
    Create align1 and align2 outputs for one neuron.
    """
    spike_csv_path = Path(spike_csv_path)
    align1_output_dir = Path(align1_output_dir)
    align2_output_dir = Path(align2_output_dir)

    spike_df = load_spike_csv(spike_csv_path)

    movie_aligned = align_spikes_to_movie_window(
        spike_df=spike_df,
        session_start_seconds=session_start_seconds,
        session_duration_seconds=session_duration_seconds,
    )

    align1_path = align1_output_dir / f"align1_{spike_csv_path.name}"
    save_aligned_spikes(movie_aligned, align1_path)

    trial_aligned = align_spikes_to_trials(
        movie_aligned_spikes=movie_aligned,
        trial_table=trial_table,
    )

    align2_path = align2_output_dir / f"align2_{spike_csv_path.name}"
    save_aligned_spikes(trial_aligned, align2_path)

    return align1_path, align2_path


def align_session_folder(
    spike_csv_dir: str | Path,
    trial_table: pd.DataFrame,
    session_start_seconds: float,
    session_duration_seconds: float,
    align1_output_dir: str | Path,
    align2_output_dir: str | Path,
) -> list[tuple[Path, Path]]:
    """
    Align every per-unit CSV in one folder.
    """
    spike_csv_dir = Path(spike_csv_dir)
    results: list[tuple[Path, Path]] = []

    for spike_csv_path in sorted(spike_csv_dir.glob("times_manual*_unit_*.csv")):
        if not spike_csv_path.name.lower().endswith(".csv"):
            continue

        results.append(
            align_one_neuron(
                spike_csv_path=spike_csv_path,
                trial_table=trial_table,
                session_start_seconds=session_start_seconds,
                session_duration_seconds=session_duration_seconds,
                align1_output_dir=align1_output_dir,
                align2_output_dir=align2_output_dir,
            )
        )

    return results