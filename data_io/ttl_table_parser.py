"""
ttl_table_parser.py

Convert the raw behavioral TTL table into the standardized trial table used
throughout the analysis pipeline.

Design principles
-----------------
- Preserve raw experimental metadata.
- Support both the legacy TTL export and the newer refined clip table.
- Use frameOn / frameOff as the canonical timing source when available,
  because they are the closest shared representation between the formats.
- Keep derived analysis columns separate from raw provenance columns.
- Separate parsing, filtering, derivation, and saving into small functions.
- Keep the module runnable by itself for debugging.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

DEFAULT_MOVIE_FPS = 29.97


def _apply_alias(df: pd.DataFrame, target: str, sources: list[str]) -> None:
    """Copy the first available source column into a canonical alias."""
    if target in df.columns:
        return
    for source in sources:
        if source in df.columns:
            df[target] = df[source]
            return


def _is_truthy_exclude(value: object) -> bool:
    """Interpret a refined-format exclude value as a boolean flag."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def _normalize_input_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Add canonical aliases for either legacy TTL or refined clip tables."""
    df = df.copy()

    if "experimentPhase" not in df.columns:
        df["experimentPhase"] = "recog_task"

    # Canonical legacy names.
    _apply_alias(df, "trialNumber", ["trialNumber", "trial_num"])
    _apply_alias(df, "movieID", ["movieID", "effective_movie_ID", "ttl_movie_ID", "movie_ID"])
    _apply_alias(df, "clipID", ["clipID", "clip_ID"])
    _apply_alias(df, "response", ["response", "resp_answer"])
    _apply_alias(df, "reactionTimePTB", ["reactionTimePTB", "reaction_time_sec"])
    _apply_alias(df, "trialStartTimePTB", ["trialStartTimePTB", "mat_trial_start_sec"])
    _apply_alias(df, "frameOn", ["frameOn", "frame_on"])
    _apply_alias(df, "frameOff", ["frameOff", "frame_off"])
    _apply_alias(df, "Accurate", ["Accurate", "correct"])

    return df


def load_ttl_table(ttl_csv: str | Path) -> pd.DataFrame:
    """
    Load the raw TTL / behavioral table.

    Parameters
    ----------
    ttl_csv:
        Path to the raw CSV file.

    Returns
    -------
    pd.DataFrame
        Raw table with column names stripped of whitespace and aliases added
        for the canonical downstream schema.
    """
    ttl_csv = Path(ttl_csv)
    df = pd.read_csv(ttl_csv)
    df.columns = [str(c).strip() for c in df.columns]
    return _normalize_input_schema(df)


def filter_trials(
    df: pd.DataFrame,
    phase: str = "recog_task",
    movie_id: Optional[int] = 1,
) -> pd.DataFrame:
    """
    Select the subset of trials used for analysis.

    Parameters
    ----------
    df:
        Raw TTL table.
    phase:
        Experiment phase to keep (default: recog_task).
    movie_id:
        Optional movieID to keep. If None, keep all movieIDs.

    Returns
    -------
    pd.DataFrame
        Filtered trial table.
    """
    df = df.copy()

    if "experimentPhase" in df.columns:
        df = df[df["experimentPhase"].astype(str) == phase].copy()

    if movie_id is not None and "movieID" in df.columns:
        movie_ids = pd.to_numeric(df["movieID"], errors="coerce")
        df = df[movie_ids == movie_id].copy()

    return df.reset_index(drop=True)


def derive_timing_columns(
    df: pd.DataFrame,
    drift_rate_slope: float = 0.0,
) -> pd.DataFrame:
    """
    Add canonical timing columns.

    Prefer frameOn / frameOff when available because they are shared by both the
    legacy TTL export and the refined clip table. If frame timing is not
    available, fall back to clipStartTime / clipEndTime.

    A small optional drift correction can be applied by passing a
    drift_rate_slope value. The correction factor is 1 + drift_rate_slope.

    Creates:
    - clipStartTimeMs
    - clipEndTimeMs
    - clipDurationMs
    - clipDurationSec
    - clipFrameRange (if frameOn/frameOff exist)
    - clipTimeRangeMs
    - clipWindowId
    """
    df = df.copy()

    has_frame_timing = {"frameOn", "frameOff"}.issubset(df.columns)
    has_clip_timing = {"clipStartTime", "clipEndTime"}.issubset(df.columns)

    if not has_frame_timing and not has_clip_timing:
        raise ValueError(
            "TTL table is missing usable timing columns. Expected frameOn / "
            "frameOff or clipStartTime / clipEndTime."
        )

    start_sec = pd.Series(np.nan, index=df.index, dtype="float64")
    end_sec = pd.Series(np.nan, index=df.index, dtype="float64")

    if has_frame_timing:
        df["frameOn"] = pd.to_numeric(df["frameOn"], errors="coerce")
        df["frameOff"] = pd.to_numeric(df["frameOff"], errors="coerce")
        start_sec = df["frameOn"] / DEFAULT_MOVIE_FPS
        end_sec = df["frameOff"] / DEFAULT_MOVIE_FPS

    if has_clip_timing:
        clip_start = pd.to_numeric(df["clipStartTime"], errors="coerce")
        clip_end = pd.to_numeric(df["clipEndTime"], errors="coerce")
        start_sec = start_sec.fillna(clip_start)
        end_sec = end_sec.fillna(clip_end)

    df["clipStartTime"] = start_sec
    df["clipEndTime"] = end_sec
    df = df.dropna(subset=["clipStartTime", "clipEndTime"]).copy()

    if df.empty:
        raise ValueError(
            "All rows were dropped because usable timing columns were missing or invalid."
        )

    correction_factor = 1.0 + float(drift_rate_slope)
    df["clipStartTime"] = df["clipStartTime"] * correction_factor
    df["clipEndTime"] = df["clipEndTime"] * correction_factor

    df["clipStartTimeMs"] = (df["clipStartTime"] * 1000.0).round().astype(int)
    df["clipEndTimeMs"] = (df["clipEndTime"] * 1000.0).round().astype(int)
    df["clipDurationMs"] = df["clipEndTimeMs"] - df["clipStartTimeMs"]
    df["clipDurationSec"] = df["clipEndTime"] - df["clipStartTime"]

    if has_frame_timing:
        df["clipFrameRange"] = (
            df["frameOn"].round().astype("Int64").astype(str)
            + "-"
            + df["frameOff"].round().astype("Int64").astype(str)
        )

    df["clipTimeRangeMs"] = (
        df["clipStartTimeMs"].astype(str)
        + "-"
        + df["clipEndTimeMs"].astype(str)
    )

    if "movieID" in df.columns:
        df["clipWindowId"] = (
            df["movieID"].astype(str)
            + "-"
            + df["clipTimeRangeMs"]
        )
    else:
        df["clipWindowId"] = df["clipTimeRangeMs"]

    return df


def _infer_accuracy(df: pd.DataFrame) -> pd.Series:
    """
    Infer a binary isAccurate column.

    Priority:
    1. existing Accurate / Accuracy column
    2. response == 2
    3. default to 0
    """
    acc_col_candidates = [c for c in df.columns if c.lower() in {"accurate", "accuracy"}]

    if acc_col_candidates:
        return (
            pd.to_numeric(df[acc_col_candidates[0]], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    if "response" in df.columns:
        return (
            df["response"]
            .astype(str)
            .str.replace(".0", "", regex=False)
            .str.strip()
            .eq("2")
            .astype(int)
        )

    return pd.Series(0, index=df.index, dtype=int)


def derive_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add analysis-only columns.

    Creates:
    - isAccurate
    - trialOrder
    - plotOrder
    - includeInPlots
    """
    df = df.copy()

    df["isAccurate"] = _infer_accuracy(df)

    df["trialOrder"] = range(1, len(df) + 1)

    correct_mask = df["isAccurate"] == 1
    incorrect_mask = df["isAccurate"] == 0

    df.loc[correct_mask, "plotOrder"] = range(1, correct_mask.sum() + 1)
    df.loc[incorrect_mask, "plotOrder"] = range(correct_mask.sum() + 1, len(df) + 1)
    df["plotOrder"] = df["plotOrder"].astype(int)

    df["includeInPlots"] = True

    if "exclude" in df.columns:
        exclude_mask = df["exclude"].map(_is_truthy_exclude)
        df.loc[exclude_mask, "includeInPlots"] = False

    return df


def restore_plot_preferences(
    df: pd.DataFrame,
    previous_table: Optional[str | Path],
) -> pd.DataFrame:
    """
    Restore includeInPlots values from a previous derived trial table.

    This preserves manual exclusions across reruns.
    """
    if previous_table is None:
        return df

    previous_table = Path(previous_table)
    if not previous_table.exists():
        return df

    try:
        old = pd.read_csv(previous_table)
        if {"clipWindowId", "includeInPlots"}.issubset(old.columns) and "clipWindowId" in df.columns:
            mapping = dict(zip(old["clipWindowId"], old["includeInPlots"]))
            df = df.copy()
            df["includeInPlots"] = (
                df["clipWindowId"]
                .map(mapping)
                .fillna(df["includeInPlots"])
                .astype(bool)
            )
    except Exception as e:
        print(f"Warning: could not reuse includeInPlots values from {previous_table}: {e}")

    return df


def save_trial_table(df: pd.DataFrame, output_csv: str | Path) -> Path:
    """
    Save the standardized trial table to disk.
    """
    output_csv = Path(output_csv)
    df.to_csv(output_csv, index=False)
    return output_csv


def build_trial_table(
    ttl_csv: str | Path,
    output_csv: str | Path,
    phase: str = "recog_task",
    movie_id: Optional[int] = 1,
    previous_table: Optional[str | Path] = None,
    drift_rate_slope: float = 0.0,
) -> tuple[pd.DataFrame, Path]:
    """
    Build the standardized trial table from the raw TTL CSV.

    Returns
    -------
    (DataFrame, Path)
        The final table and the file it was written to.
    """
    df = load_ttl_table(ttl_csv)
    df = filter_trials(df, phase=phase, movie_id=movie_id)
    df = derive_timing_columns(df, drift_rate_slope=drift_rate_slope)
    df = derive_analysis_columns(df)
    df = restore_plot_preferences(df, previous_table)
    out_path = save_trial_table(df, output_csv)
    return df, out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a standardized trial table from a TTL CSV."
    )
    parser.add_argument("ttl_csv", help="Path to the raw TTL / clip CSV.")
    parser.add_argument(
        "--output-csv",
        default="trial_table.csv",
        help="Output CSV path (default: trial_table.csv in the current folder).",
    )
    parser.add_argument(
        "--phase",
        default="recog_task",
        help="Experiment phase to keep (default: recog_task).",
    )
    parser.add_argument(
        "--movie-id",
        type=int,
        default=1,
        help="MovieID to keep (default: 1). Use --movie-id -1 to keep all movieIDs.",
    )
    parser.add_argument(
        "--previous-table",
        default=None,
        help="Optional existing trial table whose includeInPlots values should be reused.",
    )
    parser.add_argument(
        "--drift-rate-slope",
        type=float,
        default=0.0,
        help="Optional drift-rate slope to apply to timing columns.",
    )
    args = parser.parse_args()

    movie_id = None if args.movie_id == -1 else args.movie_id

    table, out_path = build_trial_table(
        ttl_csv=args.ttl_csv,
        output_csv=args.output_csv,
        phase=args.phase,
        movie_id=movie_id,
        previous_table=args.previous_table,
        drift_rate_slope=args.drift_rate_slope,
    )
    print(f"Wrote {len(table)} rows to {out_path}")


if __name__ == "__main__":
    main()