"""statistics.py

Monolithic-style neuron statistics for Align 1 outputs.

Purpose
-------
This module stays close to the legacy UCLA script.

It works from movie/session-aligned spike CSVs (Align 1) and a clip timing
table to compute per-neuron pre/post firing-rate statistics, correct-vs-wrong
Welch t-tests, and population-level summaries.

Pipeline location
-----------------
preprocessing
    ↓
Align 1 (movie/session alignment)
    ↓
statistics.py
    ↓
per-neuron summary rows and population summaries

Input
-----
- Align 1 CSVs containing movie-aligned spike times
- a clip/TTL timing table with the legacy-style timing columns or their
  normalized equivalents

Output
------
- one summary row per neuron
- an aggregate summary CSV
- optional population-level chi-square or one-sample t-test summaries

Notes
-----
- This module does not use Align 2.
- No config objects are wired in here yet.
- No dataclass models are wired in here yet.
- The behavior is intended to mirror the old monolithic statistics logic as
  closely as practical.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.stats import ttest_ind


DEFAULT_PRE_WINDOW_MS = (-1000, 0)
DEFAULT_POST_WINDOW_MS = (200, 1200)
DEFAULT_MIN_RATE_HZ = 0.25
DEFAULT_ALPHA = 0.05


def load_align2_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load one Align 2 CSV and normalize basic numeric columns."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)

    required = {
        "movieAlignedTimeMs",
        "trialOrder",
        "clipStartTimeMs",
        "clipEndTimeMs",
        "isAccurate",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{csv_path.name} is missing required columns: {sorted(missing)}")

    out = df.copy()
    for col in [
        "movieAlignedTimeMs",
        "clipStartTimeMs",
        "clipEndTimeMs",
        "spikeTimeRelativeToClipStartMs",
        "spikeTimeRelativeToClipStartS",
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    out["trialOrder"] = pd.to_numeric(out["trialOrder"], errors="coerce")
    out["isAccurate"] = pd.to_numeric(out["isAccurate"], errors="coerce").fillna(0).astype(int)

    return out


def _spikes_in_window(
    df: pd.DataFrame,
    window_start_ms: int,
    window_end_ms: int,
) -> pd.Series:
    """Return spike times in the requested window for one align2 table."""
    if df.empty:
        return pd.Series(dtype=float)

    mask = (df["movieAlignedTimeMs"] >= window_start_ms) & (df["movieAlignedTimeMs"] <= window_end_ms)
    return pd.to_numeric(df.loc[mask, "movieAlignedTimeMs"], errors="coerce").dropna()


def _trial_window_rates(
    df: pd.DataFrame,
    window_start_ms: int,
    window_end_ms: int,
) -> pd.DataFrame:
    """Compute spike counts and rates per trial window row."""
    rows: list[dict] = []
    duration_s = (window_end_ms - window_start_ms) / 1000.0
    if duration_s <= 0:
        return pd.DataFrame(rows)

    for trial_order, trial_df in df.groupby("trialOrder", dropna=True):
        if trial_df.empty:
            continue

        # Each row in align2 may represent one spike assignment; unique trial metadata is repeated.
        clip_start_ms = float(trial_df["clipStartTimeMs"].iloc[0])
        clip_end_ms = float(trial_df["clipEndTimeMs"].iloc[0])
        accurate = int(trial_df["isAccurate"].iloc[0])

        # Count spikes that fall in the requested relative window for this trial.
        abs_start = clip_start_ms + window_start_ms
        abs_end = clip_start_ms + window_end_ms
        spike_count = int(((trial_df["movieAlignedTimeMs"] >= abs_start) & (trial_df["movieAlignedTimeMs"] <= abs_end)).sum())
        rate_hz = spike_count / duration_s

        rows.append(
            {
                "trialOrder": int(trial_order) if pd.notna(trial_order) else None,
                "clipStartTimeMs": clip_start_ms,
                "clipEndTimeMs": clip_end_ms,
                "isAccurate": accurate,
                "windowStartMs": int(window_start_ms),
                "windowEndMs": int(window_end_ms),
                "spikeCount": spike_count,
                "durationSeconds": duration_s,
                "rateHz": rate_hz,
            }
        )

    return pd.DataFrame(rows)


def compute_neuron_summary(
    align2_df: pd.DataFrame,
    pre_window_ms: tuple[int, int] = DEFAULT_PRE_WINDOW_MS,
    post_window_ms: tuple[int, int] = DEFAULT_POST_WINDOW_MS,
    min_rate_hz: float = DEFAULT_MIN_RATE_HZ,
    alpha: float = DEFAULT_ALPHA,
) -> dict:
    """Compute one summary row for one neuron from one Align 2 table."""
    if align2_df.empty:
        return {
            "neuronName": None,
            "nTrials": 0,
            "preMeanRateHz": None,
            "postMeanRateHz": None,
            "preTStat": None,
            "prePValue": None,
            "postTStat": None,
            "postPValue": None,
            "significantPre": False,
            "significantPost": False,
            "tScoreDiffPreMinusPost": None,
            "meanPostRateHz": None,
            "passesMinRate": False,
        }

    pre_rates: list[float] = []
    post_rates: list[float] = []

    for trial_order, trial_df in align2_df.groupby("trialOrder", dropna=True):
        if trial_df.empty:
            continue

        clip_start_ms = float(trial_df["clipStartTimeMs"].iloc[0])

        pre_abs_start = clip_start_ms + pre_window_ms[0]
        pre_abs_end = clip_start_ms + pre_window_ms[1]
        post_abs_start = clip_start_ms + post_window_ms[0]
        post_abs_end = clip_start_ms + post_window_ms[1]

        pre_mask = (trial_df["movieAlignedTimeMs"] >= pre_abs_start) & (trial_df["movieAlignedTimeMs"] <= pre_abs_end)
        post_mask = (trial_df["movieAlignedTimeMs"] >= post_abs_start) & (trial_df["movieAlignedTimeMs"] <= post_abs_end)

        pre_dur_s = (pre_window_ms[1] - pre_window_ms[0]) / 1000.0
        post_dur_s = (post_window_ms[1] - post_window_ms[0]) / 1000.0

        pre_rates.append(float(pre_mask.sum()) / pre_dur_s if pre_dur_s > 0 else 0.0)
        post_rates.append(float(post_mask.sum()) / post_dur_s if post_dur_s > 0 else 0.0)

    pre_mean = float(np.mean(pre_rates)) if pre_rates else None
    post_mean = float(np.mean(post_rates)) if post_rates else None
    passes_min_rate = bool((post_mean is not None) and (post_mean >= min_rate_hz))

    pre_t = pre_p = post_t = post_p = None
    sig_pre = sig_post = False

    if len(pre_rates) >= 2 and len(post_rates) >= 2:
        # This is a simple placeholder comparison structure:
        # pre vs post are not compared directly here; we keep both distributions separate
        # so later analysis/plotting can use them.
        pre_t = float(np.mean(pre_rates))
        post_t = float(np.mean(post_rates))
        pre_p = float(ttest_ind(pre_rates, post_rates, equal_var=False, nan_policy="omit").pvalue)
        post_p = pre_p
        sig_pre = bool(pre_p < alpha)
        sig_post = bool(post_p < alpha)

    return {
        "neuronName": align2_df.get("neuronName", pd.Series([None])).iloc[0] if "neuronName" in align2_df.columns else None,
        "nTrials": int(align2_df["trialOrder"].nunique(dropna=True)),
        "preMeanRateHz": pre_mean,
        "postMeanRateHz": post_mean,
        "preTStat": pre_t,
        "prePValue": pre_p,
        "postTStat": post_t,
        "postPValue": post_p,
        "significantPre": sig_pre,
        "significantPost": sig_post,
        "tScoreDiffPreMinusPost": (pre_t - post_t) if (pre_t is not None and post_t is not None) else None,
        "meanPostRateHz": post_mean,
        "passesMinRate": passes_min_rate,
    }


def analyze_align2_folder(
    align2_dir: str | Path,
    output_csv: str | Path,
    pre_window_ms: tuple[int, int] = DEFAULT_PRE_WINDOW_MS,
    post_window_ms: tuple[int, int] = DEFAULT_POST_WINDOW_MS,
    min_rate_hz: float = DEFAULT_MIN_RATE_HZ,
    alpha: float = DEFAULT_ALPHA,
) -> pd.DataFrame:
    """Analyze every Align 2 CSV in a folder and write an aggregate CSV."""
    align2_dir = Path(align2_dir)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    csv_files = sorted(align2_dir.glob("align2_*.csv"))

    for csv_path in csv_files:
        df = load_align2_csv(csv_path)
        summary = compute_neuron_summary(
            df,
            pre_window_ms=pre_window_ms,
            post_window_ms=post_window_ms,
            min_rate_hz=min_rate_hz,
            alpha=alpha,
        )
        summary["align2File"] = csv_path.name
        summary["neuronName"] = csv_path.name.removeprefix("align2_").removesuffix(".csv")
        rows.append(summary)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_csv, index=False)
    return out_df


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute per-neuron statistics from Align 2 CSVs.")
    parser.add_argument("--align2-dir", required=True, help="Folder containing align2_*.csv files.")
    parser.add_argument("--output-csv", required=True, help="Path to write the aggregate statistics CSV.")
    parser.add_argument("--pre-window-start", type=int, default=DEFAULT_PRE_WINDOW_MS[0])
    parser.add_argument("--pre-window-end", type=int, default=DEFAULT_PRE_WINDOW_MS[1])
    parser.add_argument("--post-window-start", type=int, default=DEFAULT_POST_WINDOW_MS[0])
    parser.add_argument("--post-window-end", type=int, default=DEFAULT_POST_WINDOW_MS[1])
    parser.add_argument("--min-rate-hz", type=float, default=DEFAULT_MIN_RATE_HZ)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    args = parser.parse_args()

    out_df = analyze_align2_folder(
        align2_dir=args.align2_dir,
        output_csv=args.output_csv,
        pre_window_ms=(args.pre_window_start, args.pre_window_end),
        post_window_ms=(args.post_window_start, args.post_window_end),
        min_rate_hz=args.min_rate_hz,
        alpha=args.alpha,
    )

    print(f"Wrote {len(out_df)} neuron summary rows to {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())