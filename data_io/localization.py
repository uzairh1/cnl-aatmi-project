"""
localization.py

Load electrode localization metadata and infer a neuron's anatomical label
from its filename.

This module is intentionally small:
- no spike statistics
- no plotting
- no trial logic

It only handles:
1. loading the localization spreadsheet
2. extracting a neuron's region label from that spreadsheet
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

import pandas as pd


# These abbreviations match the existing project vocabulary.
BIPOLAR_REGIONS = {
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


def load_localization_map(file_path: str | Path) -> pd.DataFrame:
    """
    Load the localization spreadsheet and keep only microelectrode rows.

    Parameters
    ----------
    file_path:
        Path to the Excel file.

    Returns
    -------
    pd.DataFrame
        Cleaned localization table.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"Warning: Localization file not found at {file_path}")
        return pd.DataFrame()

    df = pd.read_excel(file_path)
    df.columns = [str(col).strip() for col in df.columns]

    # Keep only rows that look like microelectrode rows when the column exists.
    if "electrode" in df.columns:
        df = df[df["electrode"].astype(str).str.contains("micro", case=False, na=False)].copy()

    return df


def _infer_electrode_abbr_from_filename(neuron_filename: str) -> str:
    """
    Extract the electrode abbreviation from the neuron filename.

    Example patterns this can handle:
    - align1_times_manual_GA1-RA2_unit_5.csv
    - something-HPC12.csv
    """
    match_hyphen = re.search(r"-([a-zA-Z]+)", neuron_filename)
    if match_hyphen:
        return match_hyphen.group(1).upper()

    match_no_hyphen = re.search(r"([a-zA-Z]+)[0-9]*", neuron_filename)
    if match_no_hyphen:
        return match_no_hyphen.group(1).upper()

    return "UNKNOWN"


def _find_matching_row(loc_df: pd.DataFrame, abbr: str) -> pd.DataFrame:
    """
    Find the row in the localization table that matches the inferred abbreviation.
    """
    if loc_df.empty or "electrode" not in loc_df.columns:
        return pd.DataFrame()

    electrode_series = loc_df["electrode"].astype(str).str.upper()

    row = loc_df[electrode_series.str.startswith(abbr + "_")]
    if not row.empty:
        return row

    row = loc_df[electrode_series.str.contains(abbr, na=False)]
    return row


def _pick_region_abbr(row: pd.Series, loc_df: pd.DataFrame) -> str:
    """
    Extract the bipolar region abbreviation from a matched row.

    This prefers a column containing 'bipolar'. If none exists, it falls back
    to any column containing 'region'.
    """
    bipolar_cols = [c for c in loc_df.columns if "bipolar" in str(c).lower()]
    if bipolar_cols:
        val = str(row[bipolar_cols[0]]).strip().upper()
        return val if val else "UNKNOWN"

    for c in loc_df.columns:
        if "region" in str(c).lower():
            val = str(row[c]).strip().upper()
            return val if val else "UNKNOWN"

    return "UNKNOWN"


def infer_neuron_localization(neuron_filename: str, loc_df: pd.DataFrame) -> Tuple[str, str, str]:
    """
    Infer localization for one neuron.

    Parameters
    ----------
    neuron_filename:
        Filename of the neuron CSV or Align 1 file.

    loc_df:
        Localization table loaded by `load_localization_map`.

    Returns
    -------
    tuple[str, str, str]
        (electrode_code, full_location_name, region_abbr)

    Examples
    --------
    ("RA", "right amygdala", "AMY")
    """
    if loc_df.empty:
        return "Unknown", "Unknown Location", "UNKNOWN"

    abbr = _infer_electrode_abbr_from_filename(neuron_filename)
    row = _find_matching_row(loc_df, abbr)

    if row.empty:
        return abbr, "Unknown Location", "UNKNOWN"

    first = row.iloc[0]
    electrode_code = abbr
    full_name = str(first.get("aparc+aseg", "Unknown Location"))
    region_abbr = _pick_region_abbr(first, loc_df)

    return electrode_code, full_name, region_abbr


def region_description(region_abbr: str) -> str:
    """
    Convert a region abbreviation into a readable label.
    """
    return BIPOLAR_REGIONS.get(str(region_abbr).upper(), "Unknown")