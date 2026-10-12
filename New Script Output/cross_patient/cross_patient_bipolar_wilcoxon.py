"""Cross-patient aggregation using the source localization workbook BIPOLAR column only.

This is a READ-ONLY post-processing step with respect to the per-patient
pipeline. It does not rerun alignment, statistics, or rasters.

Key guarantees
--------------
1. Region assignment comes ONLY from the exact BIPOLAR column in each
   participant's localization workbook.
2. The electrode/contact name is used only to locate the correct workbook row;
   it is never used as the region label.
3. aparc+aseg/full-location text is not used to infer or repair regions.
4. A localization_qc.csv is written so every neuron-to-BIPOLAR assignment is
   auditable. Ambiguous/unmatched assignments stop the analysis.
5. Existing neuron_summary.csv files are reused; no patient pipeline rerun is
   required.
6. Participant-level one-sample Wilcoxon signed-rank tests versus 0 are
   calculated separately for PRE and POST t-scores.
7. Patients with missing workbooks or no BIPOLAR column are excluded and
   recorded in excluded_patients.csv. Workbooks are never moved or deleted.

Outputs
-------
By default:
<outputs_root>/cross_patient/

If --output-dir is supplied, outputs are written directly there instead.

    combined_neuron_summary.csv
    localization_qc.csv
    excluded_patients.csv
    region_counts.csv
    participant_wilcoxon_pre_post.csv
    patient_color_key.csv
    neutral/
        poster_HPC_MTL_FC.png
        <scope>_post_pre_diff.png
    colored/
        poster_HPC_MTL_FC.png
        <scope>_post_pre_diff.png

Usage
-----
Convenient discovery of localization workbooks:

    python cross_patient_bipolar_wilcoxon.py \
        --outputs-root "New Script Output" \
        --localizations-root "C:/Users/Uzair/Desktop/CNL/patients"

Writing the cross-patient results somewhere else:

    python cross_patient_bipolar_wilcoxon.py \
        --outputs-root "New Script Output" \
        --output-dir "12-oct-bipolar-wilcoxon" \
        --localizations-root "C:/Users/Uzair/Desktop/CNL/patients"

If more than one localization workbook exists for a patient, use an explicit
mapping CSV instead. The CSV must contain columns:

    Patient ID,Localization File

Example:

    python cross_patient_bipolar_wilcoxon.py \
        --outputs-root "New Script Output" \
        --output-dir "12-oct-bipolar-wilcoxon" \
        --localization-map-csv "localization_files.csv"

To set a patient aside for inspection, add --exclude-patient P574 (repeatable).
Removing a workbook from discovery or the mapping CSV also excludes its patient.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from scipy.stats import rankdata, wilcoxon


METRICS = [
    ("Post-Stim T-Score", "POST"),
    ("Pre-Stim T-Score", "PRE"),
    ("T-Score Diff (Pre - Post)", "PRE - POST"),
]

WILCOXON_METRICS = [
    ("Pre-Stim T-Score", "PRE"),
    ("Post-Stim T-Score", "POST"),
]

MTL_REGIONS = {"AMY", "ERC", "HPC", "PHC"}
POSTER_SCOPES = ["HPC", "MTL", "FC"]


# -----------------------------------------------------------------------------
# Patient/output discovery
# -----------------------------------------------------------------------------

def _patient_id_from_output_path(path: Path) -> str:
    patient_dir = path.parent.parent.name

    m = re.search(
        r"P(\d+)",
        patient_dir,
        flags=re.IGNORECASE,
    )

    if m:
        return f"P{m.group(1)}"

    return patient_dir


def _patient_id_from_localization_filename(path: Path) -> str | None:
    # Expected form:
    # sub-574_localizations.xlsx

    m = re.search(
        r"sub[-_](\d+).*localizations",
        path.stem,
        flags=re.IGNORECASE,
    )

    if m:
        return f"P{m.group(1)}"

    return None


def discover_summary_files(
    outputs_root: Path,
    exclude_substrings: Iterable[str],
) -> list[Path]:

    excludes = [
        s.lower()
        for s in exclude_substrings
        if s
    ]

    paths = sorted(
        outputs_root.glob(
            "P*/statistics/neuron_summary.csv"
        )
    )

    kept: list[Path] = []

    for path in paths:

        low = str(path).lower()

        if any(
            token in low
            for token in excludes
        ):
            continue

        kept.append(path)

    if not kept:
        raise FileNotFoundError(
            "No P*/statistics/neuron_summary.csv files found "
            f"under {outputs_root}"
        )

    return kept


def discover_localization_files(
    localizations_root: Path,
    needed_patients: set[str] | None = None,
) -> dict[str, Path]:

    """
    Recursively discover one
    sub-###_localizations workbook per patient.
    """

    candidates = [
        p
        for p in localizations_root.rglob("*")
        if (
            p.is_file()
            and p.suffix.lower() in {".xlsx", ".xls"}
            and "localizations" in p.stem.lower()
            and p.stem.lower().startswith("sub-")
        )
    ]

    grouped: dict[str, list[Path]] = {}

    for path in candidates:

        patient = _patient_id_from_localization_filename(
            path
        )

        if patient and (needed_patients is None or patient in needed_patients):
            grouped.setdefault(
                patient,
                [],
            ).append(path)

    duplicates = {
        p: xs
        for p, xs in grouped.items()
        if len(xs) > 1
    }

    if duplicates:

        lines = [
            "Multiple localization workbooks were found "
            "for one or more patients.",
            "Use --localization-map-csv so the intended "
            "file is explicit.",
        ]

        for patient, paths in sorted(
            duplicates.items()
        ):

            lines.append(
                f"  {patient}:"
            )

            lines.extend(
                f"    {x}"
                for x in paths
            )

        raise ValueError(
            "\n".join(lines)
        )

    return {
        p: xs[0]
        for p, xs in grouped.items()
    }


def load_localization_map_csv(
    path: Path,
) -> dict[str, Path]:

    df = pd.read_csv(path)

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    required = {
        "Patient ID",
        "Localization File",
    }

    missing = required - set(
        df.columns
    )

    if missing:
        raise ValueError(
            f"{path} is missing columns: "
            f"{sorted(missing)}"
        )

    out: dict[str, Path] = {}

    for _, row in df.iterrows():

        patient = str(
            row["Patient ID"]
        ).strip()

        if (
            patient
            and not patient.upper().startswith("P")
        ):
            patient = f"P{patient}"

        patient = patient.upper()

        loc_path = Path(
            str(
                row["Localization File"]
            ).strip()
        ).expanduser()

        if patient in out:
            raise ValueError(
                "Duplicate localization mapping "
                f"for {patient} in {path}"
            )

        out[patient] = loc_path

    return out


# -----------------------------------------------------------------------------
# BIPOLAR-only localization
# -----------------------------------------------------------------------------

class MissingBipolarColumnError(ValueError):
    """The workbook cannot supply BIPOLAR-only region assignments."""

def _exact_column(
    df: pd.DataFrame,
    wanted: str,
) -> str:

    """
    Find a column by exact name after
    stripping whitespace and ignoring case.
    """

    matches = [
        c
        for c in df.columns
        if (
            str(c).strip().upper()
            == wanted.upper()
        )
    ]

    if len(matches) != 1:

        raise ValueError(
            f"Expected exactly one column named "
            f"{wanted!r}; found "
            f"{matches or 'none'}. "
            f"Columns were: {list(df.columns)}"
        )

    return str(
        matches[0]
    )


def _load_source_localization(
    path: Path,
) -> tuple[
    pd.DataFrame,
    str,
    str,
]:

    if not path.exists():
        raise FileNotFoundError(
            "Localization workbook "
            f"not found: {path}"
        )

    df = pd.read_excel(path)

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    if not any(c.upper() == "BIPOLAR" for c in df.columns):
        raise MissingBipolarColumnError(
            f"No BIPOLAR column in {path}. Columns were: {list(df.columns)}"
        )

    electrode_col = _exact_column(
        df,
        "electrode",
    )

    bipolar_col = _exact_column(
        df,
        "BIPOLAR",
    )

    # Match the behavior of the existing pipeline where
    # possible: prefer microelectrode rows if the workbook
    # contains them.
    micro_mask = (
        df[electrode_col]
        .astype(str)
        .str.contains(
            "micro",
            case=False,
            na=False,
        )
    )

    if micro_mask.any():
        df = df[
            micro_mask
        ].copy()

    return (
        df,
        electrode_col,
        bipolar_col,
    )


def _contact_token_from_neuron_name(
    neuron_name: str,
) -> tuple[
    str | None,
    str | None,
]:

    """
    Return:
        (contact_token, letter_prefix)

    Example:
        RA2 -> ("RA2", "RA")

    Typical neuron:
        times_manual_GA1-RA2_unit_5
    """

    m = re.search(
        r"-([A-Za-z]+\d+)",
        neuron_name,
    )

    if m:

        token = (
            m.group(1)
            .upper()
        )

        prefix_m = re.match(
            r"([A-Za-z]+)",
            token,
        )

        prefix = (
            prefix_m.group(1).upper()
            if prefix_m
            else None
        )

        return (
            token,
            prefix,
        )

    # Fallback for names that may omit
    # a contact number.
    m = re.search(
        r"-([A-Za-z]+)",
        neuron_name,
    )

    if m:

        prefix = (
            m.group(1)
            .upper()
        )

        return (
            None,
            prefix,
        )

    return (
        None,
        None,
    )


def _token_mask(
    series: pd.Series,
    token: str,
) -> pd.Series:

    """
    Match token as a delimited
    electrode/contact component.
    """

    s = (
        series
        .astype(str)
        .str.upper()
    )

    # Treat underscore, hyphen, whitespace,
    # and string edges as boundaries.
    pattern = (
        rf"(?:^|[_\-\s])"
        rf"{re.escape(token)}"
        rf"(?:[_\-\s]|$)"
    )

    return s.str.contains(
        pattern,
        regex=True,
        na=False,
    )


def _clean_bipolar_value(
    value: object,
) -> str:

    if pd.isna(value):
        return "UNKNOWN"

    text = (
        str(value)
        .strip()
        .upper()
    )

    if text in {
        "",
        "NAN",
        "NONE",
        "<NA>",
    }:
        return "UNKNOWN"

    return text


def _lookup_bipolar_for_neuron(
    neuron_name: str,
    loc_df: pd.DataFrame,
    electrode_col: str,
    bipolar_col: str,
) -> dict[str, object]:

    """
    Assign region using ONLY BIPOLAR.

    Electrode is only the row key.

    Matching order
    --------------
    1. Exact contact token, e.g. RA2, if available.
    2. Electrode-letter prefix, e.g. RA, only when
       every candidate row has the same BIPOLAR value.

    This avoids silently taking the first ambiguous row.
    """

    contact, prefix = (
        _contact_token_from_neuron_name(
            neuron_name
        )
    )

    electrode_series = (
        loc_df[
            electrode_col
        ]
    )

    # -------------------------------------------------------------------------
    # Exact contact match
    # -------------------------------------------------------------------------

    if contact:

        exact = loc_df[
            _token_mask(
                electrode_series,
                contact,
            )
        ]

        if len(exact) == 1:

            row = exact.iloc[0]

            return {
                "Electrode Contact": contact,
                "BIPOLAR": _clean_bipolar_value(
                    row[bipolar_col]
                ),
                "Localization Match Status":
                    "OK_EXACT_CONTACT",
                "Localization Match Count": 1,
                "Matched Electrode":
                    str(
                        row[electrode_col]
                    ),
            }

        if len(exact) > 1:

            values = sorted({
                _clean_bipolar_value(v)
                for v in exact[bipolar_col]
            })

            if len(values) == 1:

                return {
                    "Electrode Contact":
                        contact,

                    "BIPOLAR":
                        values[0],

                    "Localization Match Status":
                        "OK_MULTIPLE_EXACT_SAME_BIPOLAR",

                    "Localization Match Count":
                        len(exact),

                    "Matched Electrode":
                        " | ".join(
                            exact[
                                electrode_col
                            ].astype(str).tolist()
                        ),
                }

            return {
                "Electrode Contact":
                    contact,

                "BIPOLAR":
                    "UNKNOWN",

                "Localization Match Status":
                    "ERROR_EXACT_CONTACT_CONFLICT",

                "Localization Match Count":
                    len(exact),

                "Matched Electrode":
                    " | ".join(
                        exact[
                            electrode_col
                        ].astype(str).tolist()
                    ),
            }

    # -------------------------------------------------------------------------
    # Prefix match
    # -------------------------------------------------------------------------

    if prefix:

        prefix_matches = loc_df[
            _token_mask(
                electrode_series,
                prefix,
            )
        ]

        # Some workbooks may contain something like:
        #
        #   GA2_RA1_micro1
        #
        # so a simple contains on the letter prefix
        # is used only as a final candidate finder.
        if prefix_matches.empty:

            prefix_matches = loc_df[
                electrode_series
                .astype(str)
                .str.upper()
                .str.contains(
                    prefix,
                    regex=False,
                    na=False,
                )
            ]

        if not prefix_matches.empty:

            values = sorted({
                _clean_bipolar_value(v)
                for v in prefix_matches[
                    bipolar_col
                ]
            })

            if len(values) == 1:

                return {
                    "Electrode Contact":
                        contact or prefix,

                    "BIPOLAR":
                        values[0],

                    "Localization Match Status":
                        "OK_PREFIX_SAME_BIPOLAR",

                    "Localization Match Count":
                        len(prefix_matches),

                    "Matched Electrode":
                        " | ".join(
                            prefix_matches[
                                electrode_col
                            ].astype(str).tolist()
                        ),
                }

            return {
                "Electrode Contact":
                    contact or prefix,

                "BIPOLAR":
                    "UNKNOWN",

                "Localization Match Status":
                    "ERROR_PREFIX_AMBIGUOUS_BIPOLAR",

                "Localization Match Count":
                    len(prefix_matches),

                "Matched Electrode":
                    " | ".join(
                        prefix_matches[
                            electrode_col
                        ].astype(str).tolist()
                    ),
            }

    return {
        "Electrode Contact":
            contact or prefix or "UNKNOWN",

        "BIPOLAR":
            "UNKNOWN",

        "Localization Match Status":
            "ERROR_NO_MATCH",

        "Localization Match Count":
            0,

        "Matched Electrode":
            "",
    }


def build_combined_table(
    summary_paths: list[Path],
    localization_files: dict[str, Path],
    *,
    excluded_rows: list[dict[str, object]] | None = None,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:

    frames: list[
        pd.DataFrame
    ] = []

    qc_rows: list[
        dict[str, object]
    ] = []

    patient_sources: dict[
        str,
        Path,
    ] = {}

    if excluded_rows is None:
        excluded_rows = []

    for summary_path in summary_paths:

        patient_id = (
            _patient_id_from_output_path(
                summary_path
            )
        )

        if patient_id in patient_sources:

            raise ValueError(
                "Duplicate patient outputs would "
                "double-count neurons:\n"
                f"  {patient_id}: "
                f"{patient_sources[patient_id]}\n"
                f"  {patient_id}: "
                f"{summary_path}"
            )

        patient_sources[
            patient_id
        ] = summary_path

        loc_path = localization_files.get(patient_id)
        if loc_path is None or not loc_path.exists():
            reason = "Missing source localization workbook"
            excluded_rows.append({
                "Patient ID": patient_id,
                "Source Summary CSV": str(summary_path),
                "Localization File": str(loc_path) if loc_path else "",
                "Exclusion Reason": reason,
            })
            print(f"Skipping {patient_id}: {reason} ({loc_path or 'not found/mapped'})")
            continue

        loc_path = (
            localization_files[
                patient_id
            ]
        )

        try:
            (
                loc_df,
                electrode_col,
                bipolar_col,
            ) = _load_source_localization(
                loc_path
            )
        except MissingBipolarColumnError as exc:
            excluded_rows.append({
                "Patient ID": patient_id,
                "Source Summary CSV": str(summary_path),
                "Localization File": str(loc_path),
                "Exclusion Reason": "Missing BIPOLAR column",
            })
            print(f"Skipping {patient_id}: {exc}")
            continue
        except Exception as exc:
            raise ValueError(
                f"Localization loading failed for {patient_id}\n"
                f"File: {loc_path}\n"
                f"Original error: {exc}"
            ) from exc

        df = pd.read_csv(
            summary_path
        )

        df.columns = [
            str(c).strip()
            for c in df.columns
        ]

        required = {
            "Neuron Name",
            *(
                m[0]
                for m in METRICS
            ),
        }

        missing = sorted(
            required
            - set(df.columns)
        )

        if missing:

            raise ValueError(
                f"{summary_path} "
                f"is missing columns: "
                f"{missing}"
            )

        assignments: list[
            dict[str, object]
        ] = []

        for neuron_name in (
            df[
                "Neuron Name"
            ].astype(str)
        ):

            lookup = (
                _lookup_bipolar_for_neuron(
                    neuron_name,
                    loc_df,
                    electrode_col,
                    bipolar_col,
                )
            )

            lookup.update({
                "Patient ID":
                    patient_id,

                "Neuron Name":
                    neuron_name,

                "Localization File":
                    str(loc_path),

                "Region Source Column":
                    bipolar_col,
            })

            assignments.append(
                lookup
            )

            qc_rows.append(
                dict(lookup)
            )

        assign_df = pd.DataFrame(
            assignments
        )

        merged = df.merge(
            assign_df[
                [
                    "Neuron Name",
                    "Electrode Contact",
                    "BIPOLAR",
                ]
            ],
            on="Neuron Name",
            how="left",
            validate="one_to_one",
        )

        merged.insert(
            0,
            "Patient ID",
            patient_id,
        )

        merged.insert(
            1,
            "Patient Output Folder",
            summary_path.parent.parent.name,
        )

        merged[
            "Is MTL"
        ] = merged[
            "BIPOLAR"
        ].isin(
            MTL_REGIONS
        )

        merged[
            "Source Summary CSV"
        ] = str(
            summary_path
        )

        merged[
            "Source Localization File"
        ] = str(
            loc_path
        )

        frames.append(
            merged
        )

    if not frames:
        raise ValueError(
            "No eligible patients remain after localization exclusions. "
            "Inspect excluded_patients.csv in the output directory."
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    qc = pd.DataFrame(
        qc_rows
    )

    return (
        combined,
        qc,
    )


# -----------------------------------------------------------------------------
# Region selection and counts
# -----------------------------------------------------------------------------

def _scope_df(
    df: pd.DataFrame,
    scope: str,
) -> pd.DataFrame:

    if scope.lower() == "global":
        return df.copy()

    scope_u = (
        scope.upper()
    )

    if scope_u == "MTL":

        return df[
            df["BIPOLAR"].isin(
                MTL_REGIONS
            )
        ].copy()

    return df[
        df["BIPOLAR"]
        == scope_u
    ].copy()


def write_region_counts(
    combined: pd.DataFrame,
    scopes: list[str],
    out_path: Path,
) -> None:

    rows = []

    for scope in scopes:

        d = _scope_df(
            combined,
            scope,
        )

        rows.append({
            "Scope":
                scope,

            "Region Source":
                "exact BIPOLAR column",

            "Patients":
                int(
                    d[
                        "Patient ID"
                    ].nunique()
                ),

            "Neurons":
                int(
                    len(d)
                ),

            "Pre Significant":
                (
                    int(
                        d[
                            "Pre-Stim Significant"
                        ]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    )
                    if "Pre-Stim Significant"
                    in d.columns
                    else np.nan
                ),

            "Post Significant":
                (
                    int(
                        d[
                            "Post-Stim Significant"
                        ]
                        .fillna(False)
                        .astype(bool)
                        .sum()
                    )
                    if "Post-Stim Significant"
                    in d.columns
                    else np.nan
                ),
        })

    pd.DataFrame(
        rows
    ).to_csv(
        out_path,
        index=False,
    )


# -----------------------------------------------------------------------------
# Participant-level Wilcoxon signed-rank tests versus zero
# -----------------------------------------------------------------------------

def _wilcoxon_summary(
    values: pd.Series,
) -> dict[str, object]:

    x = (
        pd.to_numeric(
            values,
            errors="coerce",
        )
        .to_numpy(
            dtype=float
        )
    )

    x = x[
        np.isfinite(x)
    ]

    n_total = int(
        len(x)
    )

    if n_total == 0:

        return {
            "N Neurons":
                0,

            "N Nonzero":
                0,

            "Mean T-Score":
                np.nan,

            "Median T-Score":
                np.nan,

            "W Plus":
                np.nan,

            "W Minus":
                np.nan,

            "Signed Rank Score (W+ - W-)":
                np.nan,

            "Rank-Biserial Effect":
                np.nan,

            "Wilcoxon W":
                np.nan,

            "Wilcoxon P":
                np.nan,

            "P < 0.05 (uncorrected)":
                False,

            "Small-N Note":
                "NO_DATA",
        }

    nonzero = x[
        x != 0
    ]

    n_nonzero = int(
        len(nonzero)
    )

    mean_t = float(
        np.mean(x)
    )

    median_t = float(
        np.median(x)
    )

    if n_nonzero == 0:

        return {
            "N Neurons":
                n_total,

            "N Nonzero":
                0,

            "Mean T-Score":
                mean_t,

            "Median T-Score":
                median_t,

            "W Plus":
                0.0,

            "W Minus":
                0.0,

            "Signed Rank Score (W+ - W-)":
                0.0,

            "Rank-Biserial Effect":
                0.0,

            "Wilcoxon W":
                0.0,

            "Wilcoxon P":
                1.0,

            "P < 0.05 (uncorrected)":
                False,

            "Small-N Note":
                "ALL_ZERO",
        }

    ranks = rankdata(
        np.abs(nonzero),
        method="average",
    )

    w_plus = float(
        ranks[
            nonzero > 0
        ].sum()
    )

    w_minus = float(
        ranks[
            nonzero < 0
        ].sum()
    )

    signed_rank = (
        w_plus
        - w_minus
    )

    denom = (
        w_plus
        + w_minus
    )

    rank_biserial = (
        float(
            signed_rank
            / denom
        )
        if denom
        else 0.0
    )

    # method="auto" lets SciPy choose an appropriate
    # exact/approximate method based on N, zeros, and ties.
    result = wilcoxon(
        x,
        zero_method="wilcox",
        correction=False,
        alternative="two-sided",
        method="auto",
    )

    p = float(
        result.pvalue
    )

    stat = float(
        result.statistic
    )

    # With no ties/zeros, a two-sided exact Wilcoxon
    # with <6 nonzero values cannot achieve p<0.05.
    # Ties/zeros can make the attainable p-grid differ,
    # so this is a warning rather than an exclusion rule.
    small_n_note = (
        "LOW_POWER_N<6"
        if n_nonzero < 6
        else ""
    )

    return {
        "N Neurons":
            n_total,

        "N Nonzero":
            n_nonzero,

        "Mean T-Score":
            mean_t,

        "Median T-Score":
            median_t,

        "W Plus":
            w_plus,

        "W Minus":
            w_minus,

        "Signed Rank Score (W+ - W-)":
            signed_rank,

        "Rank-Biserial Effect":
            rank_biserial,

        "Wilcoxon W":
            stat,

        "Wilcoxon P":
            p,

        "P < 0.05 (uncorrected)":
            bool(
                p < 0.05
            ),

        "Small-N Note":
            small_n_note,
    }


def write_participant_wilcoxon(
    combined: pd.DataFrame,
    scopes: list[str],
    out_path: Path,
) -> None:

    patients = sorted(
        combined[
            "Patient ID"
        ]
        .astype(str)
        .unique()
    )

    rows: list[
        dict[str, object]
    ] = []

    for scope in scopes:

        scope_df = _scope_df(
            combined,
            scope,
        )

        for patient in patients:

            patient_df = scope_df[
                scope_df[
                    "Patient ID"
                ].astype(str)
                == patient
            ]

            for (
                metric_col,
                window,
            ) in WILCOXON_METRICS:

                if metric_col in patient_df:
                    values = patient_df[
                        metric_col
                    ]
                else:
                    values = pd.Series(
                        dtype=float
                    )

                summary = (
                    _wilcoxon_summary(
                        values
                    )
                )

                rows.append({
                    "Patient ID":
                        patient,

                    "Scope":
                        scope,

                    "Window":
                        window,

                    "Metric":
                        metric_col,

                    **summary,
                })

    pd.DataFrame(
        rows
    ).to_csv(
        out_path,
        index=False,
    )


# -----------------------------------------------------------------------------
# Plotting
# -----------------------------------------------------------------------------

def _load_or_make_patient_colors(
    cross_root: Path,
    patients: list[str],
) -> dict[str, str]:

    key_path = (
        cross_root
        / "patient_color_key.csv"
    )

    if key_path.exists():

        old = pd.read_csv(
            key_path
        )

        if {
            "Patient ID",
            "Color",
        }.issubset(
            old.columns
        ):

            old_map = dict(
                zip(
                    old[
                        "Patient ID"
                    ].astype(str),

                    old[
                        "Color"
                    ].astype(str),
                )
            )

            if all(
                p in old_map
                for p in patients
            ):

                return {
                    p: old_map[p]
                    for p in patients
                }

    cmap = plt.get_cmap(
        "tab20"
    )

    colors: dict[
        str,
        str,
    ] = {}

    for i, patient in enumerate(
        sorted(patients)
    ):

        colors[
            patient
        ] = matplotlib.colors.to_hex(
            cmap(
                i % cmap.N
            )
        )

    pd.DataFrame(
        [
            {
                "Patient ID": p,
                "Color": colors[p],
            }
            for p in sorted(
                colors
            )
        ]
    ).to_csv(
        key_path,
        index=False,
    )

    return colors


def _finite_values(
    df: pd.DataFrame,
) -> np.ndarray:

    chunks = []

    for (
        metric,
        _,
    ) in METRICS:

        vals = pd.to_numeric(
            df[metric],
            errors="coerce",
        ).to_numpy(
            dtype=float
        )

        vals = vals[
            np.isfinite(vals)
        ]

        if len(vals):
            chunks.append(
                vals
            )

    if chunks:

        return np.concatenate(
            chunks
        )

    return np.array(
        [0.0]
    )


def _ylims_for(
    df: pd.DataFrame,
) -> tuple[
    float,
    float,
]:

    vals = (
        _finite_values(
            df
        )
    )

    lo = float(
        np.min(vals)
    )

    hi = float(
        np.max(vals)
    )

    if lo == hi:

        lo -= 1.0
        hi += 1.0

    pad = max(
        0.25,
        0.08 * (
            hi - lo
        ),
    )

    return (
        lo - pad,
        hi + pad,
    )


def _legend_handles(
    patient_colors: dict[str, str],
    patients: list[str],
) -> list[Line2D]:

    return [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=patient_colors[p],
            markeredgecolor="white",
            markersize=7,
            label=p,
        )
        for p in patients
    ]


def _draw_panel(
    fig: plt.Figure,
    spec,
    df: pd.DataFrame,
    metric: str,
    metric_short: str,
    *,
    colored: bool,
    patient_colors: dict[str, str],
    ylims: tuple[float, float],
    seed: int,
) -> None:

    sub = spec.subgridspec(
        1,
        2,
        width_ratios=[
            4.0,
            1.35,
        ],
        wspace=0.04,
    )

    ax = fig.add_subplot(
        sub[
            0,
            0,
        ]
    )

    hist = fig.add_subplot(
        sub[
            0,
            1,
        ],
        sharey=ax,
    )

    clean = df.copy()

    clean[
        metric
    ] = pd.to_numeric(
        clean[
            metric
        ],
        errors="coerce",
    )

    clean = clean[
        np.isfinite(
            clean[
                metric
            ]
        )
    ]

    if clean.empty:

        ax.text(
            0.5,
            0.5,
            "No data",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )

        hist.axis(
            "off"
        )

        ax.set_title(
            metric_short
        )

        ax.set_ylim(
            *ylims
        )

        return

    rng = np.random.default_rng(
        seed
    )

    jitter = rng.uniform(
        -0.26,
        0.26,
        size=len(clean),
    )

    y = clean[
        metric
    ].to_numpy(
        float
    )

    if colored:

        colors = [
            patient_colors[
                str(p)
            ]
            for p in clean[
                "Patient ID"
            ]
        ]

    else:

        colors = [
            "#2c3e50"
        ] * len(clean)

    ax.scatter(
        jitter,
        y,
        s=18,
        c=colors,
        alpha=0.72,
        edgecolors="white",
        linewidths=0.25,
        zorder=2,
    )

    mean = float(
        clean[
            metric
        ].mean()
    )

    sem = (
        float(
            clean[
                metric
            ].sem()
        )
        if len(clean) > 1
        else 0.0
    )

    ax.errorbar(
        0,
        mean,
        yerr=sem,
        color="#d62728",
        capsize=5,
        elinewidth=2.1,
        capthick=2.1,
        marker="_",
        markersize=16,
        zorder=4,
    )

    hist.hist(
        y,
        bins=20,
        orientation="horizontal",
        color="0.55",
        alpha=0.70,
    )

    for a in (
        ax,
        hist,
    ):

        a.axhline(
            0,
            color="0.55",
            linewidth=0.9,
            alpha=0.65,
            zorder=1,
        )

        a.set_ylim(
            *ylims
        )

        a.grid(
            axis="y",
            alpha=0.12,
            linewidth=0.7,
        )

    ax.set_xlim(
        -0.45,
        0.45,
    )

    ax.set_xticks(
        []
    )

    ax.set_title(
        f"{metric_short}\n"
        f"N={len(clean)} neurons, "
        f"{clean['Patient ID'].nunique()} patients",
        fontsize=10,
    )

    ax.set_ylabel(
        metric,
        fontsize=9,
    )

    hist.set_xlabel(
        "Count",
        fontsize=8,
    )

    hist.tick_params(
        axis="y",
        left=False,
        labelleft=False,
    )

    hist.tick_params(
        axis="x",
        labelsize=7,
    )

    ax.spines[
        [
            "top",
            "right",
            "bottom",
        ]
    ].set_visible(
        False
    )

    hist.spines[
        [
            "top",
            "right",
            "left",
        ]
    ].set_visible(
        False
    )


def make_scope_figure(
    combined: pd.DataFrame,
    scope: str,
    out_path: Path,
    *,
    colored: bool,
    patient_colors: dict[str, str],
    all_patients: list[str],
) -> None:

    df = _scope_df(
        combined,
        scope,
    )

    if df.empty:
        return

    fig = plt.figure(
        figsize=(
            14.5,
            5.2,
        )
    )

    outer = fig.add_gridspec(
        1,
        3,
        wspace=0.32,
    )

    ylims = _ylims_for(
        df
    )

    for j, (
        metric,
        short,
    ) in enumerate(
        METRICS
    ):

        _draw_panel(
            fig,
            outer[
                0,
                j,
            ],
            df,
            metric,
            short,
            colored=colored,
            patient_colors=patient_colors,
            ylims=ylims,
            seed=1000 + j,
        )

    fig.suptitle(
        f"{scope} — cross-patient neuron t-scores "
        "(BIPOLAR only)",
        fontsize=14,
        y=1.01,
    )

    if colored:

        # Show all cohort colors consistently,
        # even when a patient contributes no neurons
        # to this particular region.
        handles = _legend_handles(
            patient_colors,
            all_patients,
        )

        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(
                0.5,
                -0.055,
            ),
            ncol=min(
                6,
                max(
                    1,
                    len(handles),
                ),
            ),
            frameon=False,
            fontsize=8,
        )

        fig.subplots_adjust(
            bottom=0.17
        )

    else:

        fig.subplots_adjust(
            bottom=0.12
        )

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        out_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


def make_poster_grid(
    combined: pd.DataFrame,
    out_path: Path,
    *,
    colored: bool,
    patient_colors: dict[str, str],
    all_patients: list[str],
) -> None:

    available = [
        _scope_df(
            combined,
            scope,
        )
        for scope in POSTER_SCOPES
    ]

    union = pd.concat(
        [
            x
            for x in available
            if not x.empty
        ],
        ignore_index=True,
    )

    if union.empty:
        return

    fig = plt.figure(
        figsize=(
            14.5,
            13.5,
        )
    )

    outer = fig.add_gridspec(
        3,
        3,
        hspace=0.44,
        wspace=0.30,
    )

    ylims = _ylims_for(
        union
    )

    for i, scope in enumerate(
        POSTER_SCOPES
    ):

        df = _scope_df(
            combined,
            scope,
        )

        for j, (
            metric,
            short,
        ) in enumerate(
            METRICS
        ):

            _draw_panel(
                fig,
                outer[
                    i,
                    j,
                ],
                df,
                metric,
                short,
                colored=colored,
                patient_colors=patient_colors,
                ylims=ylims,
                seed=(
                    2000
                    + i * 10
                    + j
                ),
            )

        fig.text(
            0.005,
            0.825
            - i * 0.305,
            scope,
            rotation=90,
            va="center",
            ha="left",
            fontsize=14,
            fontweight="bold",
        )

    fig.suptitle(
        "Poster-style cross-patient t-score distributions "
        "(BIPOLAR only)",
        fontsize=16,
        y=0.995,
    )

    if colored:

        handles = _legend_handles(
            patient_colors,
            all_patients,
        )

        fig.legend(
            handles=handles,
            loc="lower center",
            bbox_to_anchor=(
                0.5,
                0.005,
            ),
            ncol=min(
                6,
                max(
                    1,
                    len(handles),
                ),
            ),
            frameon=False,
            fontsize=8,
        )

        fig.subplots_adjust(
            bottom=0.07,
            top=0.95,
        )

    else:

        fig.subplots_adjust(
            bottom=0.04,
            top=0.95,
        )

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        out_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )


# -----------------------------------------------------------------------------
# Main generation
# -----------------------------------------------------------------------------

def generate_cross_patient_plots(
    outputs_root: str | Path,
    *,
    output_dir: str | Path | None = None,
    localizations_root: str | Path | None = None,
    localization_map_csv: str | Path | None = None,
    exclude_substrings: Iterable[str] = ("_box",),
    exclude_patients: Iterable[str] = (),
    min_neurons: int = 1,
    min_patients: int = 1,
) -> Path:

    outputs_root = Path(
        outputs_root
    )

    # NEW:
    # Read patient outputs from outputs_root,
    # but optionally write the cross-patient results
    # somewhere completely separate.
    cross_root = (
        Path(output_dir)
        if output_dir is not None
        else outputs_root
        / "cross_patient"
    )

    neutral_dir = (
        cross_root
        / "neutral"
    )

    colored_dir = (
        cross_root
        / "colored"
    )

    neutral_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    colored_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # Discover existing patient summaries
    # -------------------------------------------------------------------------

    summary_paths = discover_summary_files(
        outputs_root,
        exclude_substrings,
    )

    excluded_ids = {
        "P" + str(patient).strip().upper().removeprefix("P")
        for patient in exclude_patients
    }
    excluded_rows: list[dict[str, object]] = []
    kept_paths = []
    for path in summary_paths:
        patient = _patient_id_from_output_path(path)
        if patient in excluded_ids:
            excluded_rows.append({
                "Patient ID": patient,
                "Source Summary CSV": str(path),
                "Localization File": "",
                "Exclusion Reason": "Explicitly excluded by --exclude-patient",
            })
            print(f"Skipping {patient}: explicitly excluded")
        else:
            kept_paths.append(path)
    summary_paths = kept_paths
    needed_patients = {_patient_id_from_output_path(p) for p in summary_paths}

    # -------------------------------------------------------------------------
    # Discover source localization workbooks
    # -------------------------------------------------------------------------

    if localization_map_csv:

        localization_files = (
            load_localization_map_csv(
                Path(
                    localization_map_csv
                )
            )
        )

    elif localizations_root:

        localization_files = (
            discover_localization_files(
                Path(
                    localizations_root
                ),
                needed_patients=needed_patients,
            )
        )

    else:

        raise ValueError(
            "BIPOLAR-only analysis requires either "
            "--localizations-root or "
            "--localization-map-csv so the source "
            "localization workbooks can be read directly."
        )

    # -------------------------------------------------------------------------
    # Build BIPOLAR-only combined table
    # -------------------------------------------------------------------------

    try:
        combined, qc = build_combined_table(
            summary_paths,
            localization_files,
            excluded_rows=excluded_rows,
        )
    finally:
        pd.DataFrame(excluded_rows, columns=[
            "Patient ID", "Source Summary CSV", "Localization File", "Exclusion Reason",
        ]).to_csv(cross_root / "excluded_patients.csv", index=False)

    qc.to_csv(
        cross_root
        / "localization_qc.csv",
        index=False,
    )

    # -------------------------------------------------------------------------
    # Stop if any localization assignment was ambiguous/unmatched
    # -------------------------------------------------------------------------

    error_mask = (
        qc[
            "Localization Match Status"
        ]
        .astype(str)
        .str.startswith(
            "ERROR"
        )
    )

    if error_mask.any():

        bad = qc[
            error_mask
        ]

        counts = bad.groupby(
            [
                "Patient ID",
                "Localization Match Status",
            ]
        ).size()

        raise ValueError(
            "BIPOLAR localization QC failed. "
            "No plots/statistics were generated.\n"
            f"Inspect: "
            f"{cross_root / 'localization_qc.csv'}"
            "\n\n"
            + counts.to_string()
        )

    # -------------------------------------------------------------------------
    # Authoritative combined table
    # -------------------------------------------------------------------------

    combined.to_csv(
        cross_root
        / "combined_neuron_summary.csv",
        index=False,
    )

    patients = sorted(
        combined[
            "Patient ID"
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    patient_colors = (
        _load_or_make_patient_colors(
            cross_root,
            patients,
        )
    )

    # -------------------------------------------------------------------------
    # Region/scopes
    # -------------------------------------------------------------------------

    atomic_regions = sorted(
        r
        for r in (
            combined[
                "BIPOLAR"
            ]
            .dropna()
            .astype(str)
            .unique()
        )
        if r not in {
            "",
            "UNKNOWN",
            "NAN",
        }
    )

    scopes = (
        ["global"]
        + atomic_regions
    )

    if "MTL" not in scopes:
        scopes.append(
            "MTL"
        )

    # -------------------------------------------------------------------------
    # Counts + participant Wilcoxon outputs
    # -------------------------------------------------------------------------

    write_region_counts(
        combined,
        scopes,
        cross_root
        / "region_counts.csv",
    )

    write_participant_wilcoxon(
        combined,
        scopes,
        cross_root
        / "participant_wilcoxon_pre_post.csv",
    )

    # -------------------------------------------------------------------------
    # Determine which scopes qualify for plotting
    # -------------------------------------------------------------------------

    plot_scopes = []

    for scope in scopes:

        d = _scope_df(
            combined,
            scope,
        )

        if (
            len(d) >= min_neurons
            and d[
                "Patient ID"
            ].nunique() >= min_patients
        ):

            plot_scopes.append(
                scope
            )

    # -------------------------------------------------------------------------
    # Poster-style HPC / MTL / FC figures
    # -------------------------------------------------------------------------

    make_poster_grid(
        combined,
        neutral_dir
        / "poster_HPC_MTL_FC.png",
        colored=False,
        patient_colors=patient_colors,
        all_patients=patients,
    )

    make_poster_grid(
        combined,
        colored_dir
        / "poster_HPC_MTL_FC.png",
        colored=True,
        patient_colors=patient_colors,
        all_patients=patients,
    )

    # -------------------------------------------------------------------------
    # Individual scope figures
    # -------------------------------------------------------------------------

    for scope in plot_scopes:

        safe = scope.replace(
            "/",
            "-",
        )

        make_scope_figure(
            combined,
            scope,
            neutral_dir
            / f"{safe}_post_pre_diff.png",
            colored=False,
            patient_colors=patient_colors,
            all_patients=patients,
        )

        make_scope_figure(
            combined,
            scope,
            colored_dir
            / f"{safe}_post_pre_diff.png",
            colored=True,
            patient_colors=patient_colors,
            all_patients=patients,
        )

    # -------------------------------------------------------------------------
    # Console summary
    # -------------------------------------------------------------------------

    print(
        "Cross-patient aggregation complete: "
        f"{cross_root}"
    )

    print(
        f"Patients: {len(patients)} "
        f"| Neurons: {len(combined)}"
    )

    print(
        "Region source: exact BIPOLAR column "
        "from source localization workbooks"
    )

    print(
        "Wilcoxon output: "
        f"{cross_root / 'participant_wilcoxon_pre_post.csv'}"
    )

    print(
        "Plotted scopes: "
        f"{', '.join(plot_scopes)}"
    )

    return cross_root


def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Aggregate existing patient neuron summaries "
            "using ONLY the source localization BIPOLAR "
            "column, and compute participant PRE/POST "
            "Wilcoxon signed-rank tests versus zero."
        )
    )

    parser.add_argument(
        "--outputs-root",
        required=True,
        help=(
            "Folder containing "
            "P*/statistics/neuron_summary.csv "
            "patient outputs."
        ),
    )

    # NEW:
    # Allows reading the existing patient data from one location
    # while writing all cross-patient results somewhere else.
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Folder where cross-patient outputs will be "
            "written. Default: "
            "<outputs-root>/cross_patient."
        ),
    )

    loc_group = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    loc_group.add_argument(
        "--localizations-root",
        help=(
            "Root to recursively search for "
            "sub-*_localizations.xlsx workbooks."
        ),
    )

    loc_group.add_argument(
        "--localization-map-csv",
        help=(
            "CSV with columns "
            "'Patient ID' and "
            "'Localization File'."
        ),
    )

    parser.add_argument(
        "--exclude-substring",
        action="append",
        default=[
            "_box"
        ],
        help=(
            "Ignore output paths containing this "
            "substring. Repeatable. Default: _box."
        ),
    )

    parser.add_argument(
        "--exclude-patient",
        action="append",
        default=[],
        help="Exclude an entire patient for inspection, e.g. P574 or 574. Repeatable.",
    )

    parser.add_argument(
        "--min-neurons",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--min-patients",
        type=int,
        default=1,
    )

    args = (
        parser.parse_args()
    )

    generate_cross_patient_plots(
        args.outputs_root,
        output_dir=args.output_dir,
        localizations_root=args.localizations_root,
        localization_map_csv=args.localization_map_csv,
        exclude_substrings=args.exclude_substring,
        exclude_patients=args.exclude_patient,
        min_neurons=args.min_neurons,
        min_patients=args.min_patients,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
