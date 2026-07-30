"""session_alignment.py

Align per-unit spike CSVs to the movie/session timebase.

This is the Align 1 stage:
- load per-unit spike CSVs from preprocessing/
- compute the session window from matLab, start_unix_0, and duration
- filter spikes to the movie window
- re-zero spike times at movie onset
- write one aligned CSV per neuron

Expected input columns in the raw spike CSV:
- units
- s

Output columns:
- units
- spikeTimeRawS
- movieAlignedTimeS
- movieAlignedTimeMs
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def compute_session_window(
    start_unix_0: float,
    matLab: float,
    duration: float,
) -> tuple[float, float]:
    """Return the movie/session start and end times in seconds."""
    session_start_seconds = start_unix_0 - matLab
    session_end_seconds = session_start_seconds + duration
    return session_start_seconds, session_end_seconds


def load_spike_csv(spike_csv_path: str | Path) -> pd.DataFrame:
    """Load one per-unit spike CSV produced by preprocessing."""
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
    """Filter spikes to the movie/session window and re-zero onset to 0 s."""
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


def save_aligned_spikes(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Save an aligned spike table to disk."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.4f")
    return output_path


def align_one_neuron(
    spike_csv_path: str | Path,
    session_start_seconds: float,
    session_duration_seconds: float,
    align1_output_dir: str | Path,
) -> Path:
    """Create one Align 1 file for a single neuron."""
    spike_csv_path = Path(spike_csv_path)
    align1_output_dir = Path(align1_output_dir)

    spike_df = load_spike_csv(spike_csv_path)
    movie_aligned = align_spikes_to_movie_window(
        spike_df=spike_df,
        session_start_seconds=session_start_seconds,
        session_duration_seconds=session_duration_seconds,
    )

    align1_path = align1_output_dir / f"align1_{spike_csv_path.name}"
    save_aligned_spikes(movie_aligned, align1_path)
    return align1_path


def align_session_folder(
    spike_csv_dir: str | Path,
    session_start_seconds: float,
    session_duration_seconds: float,
    align1_output_dir: str | Path,
) -> list[Path]:
    """Create Align 1 files for every per-unit CSV in one folder."""
    spike_csv_dir = Path(spike_csv_dir)
    results: list[Path] = []

    for spike_csv_path in sorted(spike_csv_dir.glob("times_manual*_unit_*.csv")):
        if not spike_csv_path.name.lower().endswith(".csv"):
            continue

        results.append(
            align_one_neuron(
                spike_csv_path=spike_csv_path,
                session_start_seconds=session_start_seconds,
                session_duration_seconds=session_duration_seconds,
                align1_output_dir=align1_output_dir,
            )
        )

    return results

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Create Align 1 session-aligned spike CSVs.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--start-unix-0", type=float, required=True)
    parser.add_argument("--matlab", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    args = parser.parse_args()

    session_start_seconds = args.start_unix_0 - args.matlab

    results = align_session_folder(
        spike_csv_dir=args.input_dir,
        session_start_seconds=session_start_seconds,
        session_duration_seconds=args.duration,
        align1_output_dir=args.output_dir,
    )

    print(f"Found {len(results)} input files; wrote {len(results)} align1 files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())