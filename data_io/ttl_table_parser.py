"""
ttl_table_parser.py

Convert the raw behavioral TTL table into the standardized trial table used
throughout the analysis pipeline.

Design principles
-----------------
- Preserve raw experimental metadata.
- Use clipStartTime / clipEndTime as canonical timing.
- Keep frameOn / frameOff intact as raw provenance.
- Use descriptive names for derived analysis columns.
- Separate parsing, filtering, derivation, and saving into small functions.
- Keep the module runnable by itself for debugging.

Pipeline
--------
Raw TTL CSV
    -> load_ttl_table()
    -> filter_trials()
    -> derive_timing_columns()
    -> derive_analysis_columns()
    -> restore_plot_preferences()
    -> save_trial_table()

Column mapping
--------------
Raw TTL columns (preserved)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
experimentPhase
trialNumber
movieID
clipID
response
reactionTimePTB
trialStartTimePTB
trialEndTimePTB
clipStartTime
clipEndTime
frameOn
frameOff
startTag
cueEndTag
endTag
startTimeUnixSec
cueEndTimeUnixSec
endTimeUnixSec
startTimeMat
cueEndTimeMat
endTimeMat
trialNumberMat

Derived analysis columns
~~~~~~~~~~~~~~~~~~~~~~~
Legacy name           -> New name
ms start              -> clipStartTimeMs
ms end                -> clipEndTimeMs
clip duration ms      -> clipDurationMs
clip duration s       -> clipDurationSec
frame range           -> clipFrameRange
ms range              -> clipTimeRangeMs
ms ID                 -> clipWindowId
Chronological Index   -> trialOrder
Plot Y-Axis           -> plotOrder
Plot Toggle           -> includeInPlots
Accurate              -> isAccurate

Notes
-----
- The parser defaults to experimentPhase == "recog_task" and movieID == 1,
  mirroring the original monolithic behavior.
- The canonical time source is clipStartTime / clipEndTime (seconds).
- Raw frameOn / frameOff values are retained for provenance and debugging.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd


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
        Raw table with column names stripped of whitespace.
    """
    ttl_csv = Path(ttl_csv)
    df = pd.read_csv(ttl_csv)
    df.columns = [str(c).strip() for c in df.columns]
    return df


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


def derive_timing_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add canonical timing columns from clipStartTime / clipEndTime.

    Creates:
    - clipStartTimeMs
    - clipEndTimeMs
    - clipDurationMs
    - clipDurationSec
    - clipFrameRange (if frameOn/frameOff exist)
    - clipTimeRangeMs
    - clipWindowId

    Notes
    -----
    frameOn / frameOff are preserved as raw metadata. They are not used as the
    primary timing source in this refactor.
    """
    df = df.copy()

    required_time_cols = {"clipStartTime", "clipEndTime"}
    missing = sorted(required_time_cols - set(df.columns))
    if missing:
        raise ValueError(
            f"TTL table is missing required timing columns: {missing}. "
            "This parser expects clipStartTime and clipEndTime."
        )

    df["clipStartTime"] = pd.to_numeric(df["clipStartTime"], errors="coerce")
    df["clipEndTime"] = pd.to_numeric(df["clipEndTime"], errors="coerce")
    df = df.dropna(subset=["clipStartTime", "clipEndTime"]).copy()

    if df.empty:
        raise ValueError(
            "All rows were dropped because clipStartTime / clipEndTime were missing."
        )

    df["clipStartTimeMs"] = (df["clipStartTime"] * 1000.0).round().astype(int)
    df["clipEndTimeMs"] = (df["clipEndTime"] * 1000.0).round().astype(int)
    df["clipDurationMs"] = df["clipEndTimeMs"] - df["clipStartTimeMs"]
    df["clipDurationSec"] = df["clipEndTime"] - df["clipStartTime"]

    if {"frameOn", "frameOff"}.issubset(df.columns):
        df["frameOn"] = pd.to_numeric(df["frameOn"], errors="coerce")
        df["frameOff"] = pd.to_numeric(df["frameOff"], errors="coerce")
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
    df = derive_timing_columns(df)
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
    args = parser.parse_args()

    movie_id = None if args.movie_id == -1 else args.movie_id

    table, out_path = build_trial_table(
        ttl_csv=args.ttl_csv,
        output_csv=args.output_csv,
        phase=args.phase,
        movie_id=movie_id,
        previous_table=args.previous_table,
    )
    print(f"Wrote {len(table)} rows to {out_path}")


if __name__ == "__main__":
    main()