"""binning.py

Legacy-style spike binning for Align 1 outputs.

Purpose
-------
This module reproduces the movie-level spike binning performed by the
legacy UCLA `bin_firing_rate()` helper.

Unlike trial alignment or PSTH generation, this stage does not operate on
individual behavioral trials. Instead, it bins the entire movie-aligned
spike train for one neuron into fixed-width time bins.

Pipeline location
-----------------
preprocessing
    ↓
Align 1 (movie/session alignment)
    ↓
binning.py
    ↓
movie-level firing-rate table

Input
-----
One Align 1 CSV containing movie-aligned spike times.

Required columns:
    - ms

Output
------
One binned firing-rate table containing:

    - bin_{bin_size_s}s
    - spike_count
    - firing_rate_hz

Binning rule
------------
Spike times are converted from milliseconds to seconds and assigned to bins
using the legacy UCLA rule:

    bin_index = floor(time_seconds / bin_size_s)

Bins with no spikes are retained and assigned a spike count of zero.

Design notes
------------
- This module intentionally mirrors the legacy UCLA implementation.
- Binning is performed on Align 1 outputs, not Align 2.
- No trial information is used.
- No config objects are wired in.
- No dataclass models are wired in.
- The output is intended primarily for movie-level firing-rate analyses and
  compatibility with the legacy workflow.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import pandas as pd


DEFAULT_BIN_MS = 100


def load_align2_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load one Align 2 CSV and normalize the columns used by binning."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    required = {
        "trialOrder",
        "clipWindowId",
        "spikeTimeRelativeToClipStartMs",
        "movieAlignedTimeMs",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path.name} is missing required columns: {sorted(missing)}")

    out = df.copy()
    for col in ["trialOrder", "spikeTimeRelativeToClipStartMs", "movieAlignedTimeMs"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def build_bin_edges(window_start_ms: int, window_end_ms: int, bin_ms: int) -> List[int]:
    """Build bin edges covering the requested window."""
    if bin_ms <= 0:
        raise ValueError("bin_ms must be positive")
    if window_start_ms >= window_end_ms:
        raise ValueError("window_start_ms must be < window_end_ms")

    edges = list(range(window_start_ms, window_end_ms, bin_ms))
    if not edges or edges[0] != window_start_ms:
        edges = [window_start_ms] + edges

    if edges[-1] < window_end_ms:
        edges.append(window_end_ms)
    elif edges[-1] > window_end_ms:
        edges[-1] = window_end_ms

    # Ensure the final edge is exactly the end of the window.
    if edges[-1] != window_end_ms:
        edges.append(window_end_ms)

    # Remove any accidental duplicates while preserving order.
    deduped: List[int] = []
    for edge in edges:
        if not deduped or deduped[-1] != edge:
            deduped.append(edge)

    return deduped


def bin_align2_dataframe(
    align2_df: pd.DataFrame,
    bin_ms: int = DEFAULT_BIN_MS,
    window_start_ms: int = -3000,
    window_end_ms: int = 5000,
) -> pd.DataFrame:
    """Convert one Align 2 table into a binned spike-rate table."""
    if align2_df.empty:
        return pd.DataFrame(
            columns=[
                "trialOrder",
                "clipWindowId",
                "binStartMs",
                "binEndMs",
                "binCenterMs",
                "spikeCount",
                "rateHz",
            ]
        )

    if "spikeTimeRelativeToClipStartMs" not in align2_df.columns:
        raise ValueError("align2_df must contain spikeTimeRelativeToClipStartMs")

    edges = build_bin_edges(window_start_ms, window_end_ms, bin_ms)
    rows: list[dict] = []
    bin_width_s = bin_ms / 1000.0

    # Count spikes within each trial separately.
    trial_groups = align2_df.groupby("trialOrder", dropna=True)

    for trial_order, trial_df in trial_groups:
        if trial_df.empty:
            continue

        clip_window_id = trial_df["clipWindowId"].iloc[0] if "clipWindowId" in trial_df.columns else None
        rel_spikes = pd.to_numeric(
            trial_df["spikeTimeRelativeToClipStartMs"], errors="coerce"
        ).dropna().to_numpy()

        # Convert from relative-to-clip spikes to a histogram over the chosen window.
        # We count only spikes that fall inside [window_start_ms, window_end_ms).
        for left, right in zip(edges[:-1], edges[1:]):
            mask = (rel_spikes >= left) & (rel_spikes < right)
            spike_count = int(mask.sum())
            rows.append(
                {
                    "trialOrder": int(trial_order) if pd.notna(trial_order) else None,
                    "clipWindowId": clip_window_id,
                    "binStartMs": int(left),
                    "binEndMs": int(right),
                    "binCenterMs": (left + right) / 2.0,
                    "spikeCount": spike_count,
                    "rateHz": spike_count / bin_width_s,
                }
            )

    return pd.DataFrame(rows)


def bin_align2_file(
    align2_csv_path: str | Path,
    output_csv_path: str | Path,
    bin_ms: int = DEFAULT_BIN_MS,
    window_start_ms: int = -3000,
    window_end_ms: int = 5000,
) -> Path:
    """Bin one Align 2 CSV and write the binned output to disk."""
    align2_csv_path = Path(align2_csv_path)
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    align2_df = load_align2_csv(align2_csv_path)
    binned_df = bin_align2_dataframe(
        align2_df,
        bin_ms=bin_ms,
        window_start_ms=window_start_ms,
        window_end_ms=window_end_ms,
    )
    binned_df.to_csv(output_csv_path, index=False)
    return output_csv_path


def bin_align2_folder(
    align2_dir: str | Path,
    output_dir: str | Path,
    bin_ms: int = DEFAULT_BIN_MS,
    window_start_ms: int = -3000,
    window_end_ms: int = 5000,
) -> list[Path]:
    """Bin every Align 2 CSV in a folder."""
    align2_dir = Path(align2_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for align2_csv_path in sorted(align2_dir.glob("align2_*.csv")):
        out_path = output_dir / align2_csv_path.name.replace(".csv", f"_binned_{bin_ms}ms.csv")
        outputs.append(
            bin_align2_file(
                align2_csv_path=align2_csv_path,
                output_csv_path=out_path,
                bin_ms=bin_ms,
                window_start_ms=window_start_ms,
                window_end_ms=window_end_ms,
            )
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Bin Align 2 spike tables into fixed-width firing-rate tables.")
    parser.add_argument("--align2-dir", required=True, help="Folder containing align2_*.csv files.")
    parser.add_argument("--output-dir", required=True, help="Folder where binned CSVs will be written.")
    parser.add_argument("--bin-ms", type=int, default=DEFAULT_BIN_MS, help="Bin width in milliseconds.")
    parser.add_argument("--window-start-ms", type=int, default=-3000, help="Start of binning window in ms relative to clip start.")
    parser.add_argument("--window-end-ms", type=int, default=5000, help="End of binning window in ms relative to clip start.")
    args = parser.parse_args()

    outputs = bin_align2_folder(
        align2_dir=args.align2_dir,
        output_dir=args.output_dir,
        bin_ms=args.bin_ms,
        window_start_ms=args.window_start_ms,
        window_end_ms=args.window_end_ms,
    )

    print(f"Wrote {len(outputs)} binned CSV files to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())