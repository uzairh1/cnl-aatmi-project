"""trial_alignment.py

Align movie/session-aligned spikes to individual trial windows.

This is the Align 2 stage:
- read Align 1 spike files
- read the standardized trial table from data_io/
- assign each spike to a trial window
- write one Align 2 file per neuron

Trial membership rule
---------------------
A spike belongs to a trial when:

    clipStartTimeMs <= movieAlignedTimeMs <= clipEndTimeMs

Expected input columns for Align 1 files:
- units
- spikeTimeRawS
- movieAlignedTimeS
- movieAlignedTimeMs

Expected input columns for trial_table.csv:
- clipStartTimeMs
- clipEndTimeMs
- clipWindowId
- trialOrder
- clipID
- movieID
- isAccurate
- plotOrder
- includeInPlots

Output columns:
- units
- spikeTimeRawS
- movieAlignedTimeS
- movieAlignedTimeMs
- trialOrder
- clipWindowId
- clipID
- movieID
- isAccurate
- plotOrder
- includeInPlots
- clipStartTimeMs
- clipEndTimeMs
- spikeTimeRelativeToClipStartMs
- spikeTimeRelativeToClipStartS
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
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


def load_align1_spike_csv(spike_csv_path: str | Path) -> pd.DataFrame:
    """Load one Align 1 file produced by session_alignment.py."""
    spike_csv_path = Path(spike_csv_path)
    df = pd.read_csv(spike_csv_path)

    required = {"units", "spikeTimeRawS", "movieAlignedTimeS", "movieAlignedTimeMs"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"{spike_csv_path.name} is missing required columns: {sorted(missing)}"
        )

    out = df.copy()
    out["units"] = pd.to_numeric(out["units"], errors="raise").astype(int)
    out["spikeTimeRawS"] = pd.to_numeric(out["spikeTimeRawS"], errors="coerce")
    out["movieAlignedTimeS"] = pd.to_numeric(out["movieAlignedTimeS"], errors="coerce")
    out["movieAlignedTimeMs"] = pd.to_numeric(out["movieAlignedTimeMs"], errors="coerce")
    out = out.dropna(
        subset=["spikeTimeRawS", "movieAlignedTimeS", "movieAlignedTimeMs"]
    ).copy()

    return out[["units", "spikeTimeRawS", "movieAlignedTimeS", "movieAlignedTimeMs"]]


def align_spikes_to_trials(
    movie_aligned_spikes: pd.DataFrame,
    trial_table: pd.DataFrame,
) -> pd.DataFrame:
    """Assign each movie-aligned spike to every matching trial window."""
    if movie_aligned_spikes.empty or trial_table.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

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
            spike_time_relative_ms = float(spike["movieAlignedTimeMs"]) - clip_start_ms

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

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def save_trial_aligned_spikes(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Save an Align 2 table to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.4f")
    return output_path


def align_one_neuron(
    align1_csv_path: str | Path,
    trial_table: pd.DataFrame,
    align2_output_dir: str | Path,
) -> Path:
    """Create one Align 2 file for a single neuron."""
    align1_csv_path = Path(align1_csv_path)
    align2_output_dir = Path(align2_output_dir)

    movie_aligned = load_align1_spike_csv(align1_csv_path)
    trial_aligned = align_spikes_to_trials(
        movie_aligned_spikes=movie_aligned,
        trial_table=trial_table,
    )

    align2_path = align2_output_dir / f"align2_{align1_csv_path.name.removeprefix('align1_')}"
    save_trial_aligned_spikes(trial_aligned, align2_path)
    return align2_path


def align_session_folder(
    align1_input_dir: str | Path,
    trial_table: pd.DataFrame,
    align2_output_dir: str | Path,
) -> list[Path]:
    """Create Align 2 files for every Align 1 CSV in one folder."""
    align1_input_dir = Path(align1_input_dir)
    results: list[Path] = []

    for align1_csv_path in sorted(align1_input_dir.glob("align1_*.csv")):
        results.append(
            align_one_neuron(
                align1_csv_path=align1_csv_path,
                trial_table=trial_table,
                align2_output_dir=align2_output_dir,
            )
        )

    return results
