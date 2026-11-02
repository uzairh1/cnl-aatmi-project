"""
Create a black-and-white 3x3 participant swarm figure from
combined_neuron_summary.csv.

Rows:
    HPC
    Non-HPC MTL = AMY + ERC + PHC
    FC

Columns:
    POST
    PRE
    PRE - POST

Within each participant:
    - each dot = one neuron-level t-score
    - black marker/errorbar = mean +/- SEM
    - annotation = Signed Wilcoxon Z versus 0

No upstream analysis is rerun.

Example
-------
python participant_swarm_nonHPC_MTL_wilcoxon_3x3.py \
    --combined-csv "C:/Users/Uzair/Desktop/CNL/cnl_aatmi_project/12-oct-bipolar-wilcoxon/combined_neuron_summary.csv" \
    --output-dir "C:/Users/Uzair/Desktop/CNL/cnl_aatmi_project/01-nov-nonHPC-MTL-swarm-plots"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon


# ============================================================
# Region definitions
# ============================================================

# IMPORTANT:
# MTL here means NON-HIPPOCAMPAL MTL.
#
# HPC is intentionally excluded because HPC is plotted
# separately as its own row.
NON_HPC_MTL_REGIONS = {
    "AMY",
    "ERC",
    "PHC",
}

REGIONS = [
    "HPC",
    "MTL",
    "FC",
]


# ============================================================
# Plot columns
# ============================================================

METRICS = [
    (
        "Post-Stim T-Score",
        "POST",
    ),
    (
        "Pre-Stim T-Score",
        "PRE",
    ),
    (
        "T-Score Diff (Pre - Post)",
        "PRE - POST",
    ),
]


# ============================================================
# Helpers
# ============================================================

def patient_sort_key(patient: str):
    """
    Sort P566, P567, ... numerically.
    """
    match = re.search(
        r"(\d+)",
        str(patient),
    )

    if match:
        return int(
            match.group(1)
        )

    return str(patient)


def region_subset(
    df: pd.DataFrame,
    region: str,
) -> pd.DataFrame:
    """
    Return neurons belonging to the requested analysis region.

    HPC:
        BIPOLAR == HPC

    MTL:
        NON-HIPPOCAMPAL MTL ONLY
        AMY + ERC + PHC

    FC:
        BIPOLAR == FC
    """

    if region == "MTL":

        return df[
            df["BIPOLAR"].isin(
                NON_HPC_MTL_REGIONS
            )
        ].copy()

    return df[
        df["BIPOLAR"] == region
    ].copy()


def region_display_name(
    region: str,
) -> str:
    """
    Labels used on the figure and stats output.
    """

    if region == "MTL":
        return "Non-HPC MTL"

    return region


# ============================================================
# Signed Wilcoxon Z
# ============================================================

def signed_wilcoxon_z(
    values,
) -> dict:
    """
    One-sample Wilcoxon signed-rank test versus 0.

    SciPy's two-sided Z does not preserve the desired
    biological direction, so direction is restored using:

        sign(W+ - W-) * abs(Z)

    Returns:
        n
        n_nonzero
        z
        p
        w_plus
        w_minus
        signed_rank_score
        rank_biserial
        direction
    """

    x = pd.to_numeric(
        pd.Series(values),
        errors="coerce",
    ).to_numpy(
        dtype=float
    )

    x = x[
        np.isfinite(x)
    ]

    n_total = len(x)

    if n_total == 0:

        return {
            "n": 0,
            "n_nonzero": 0,
            "z": np.nan,
            "p": np.nan,
            "w_plus": np.nan,
            "w_minus": np.nan,
            "signed_rank_score": np.nan,
            "rank_biserial": np.nan,
            "direction": "NO_DATA",
        }

    # Wilcoxon with zero_method="wilcox"
    # discards exact zero observations.
    nonzero = x[
        x != 0
    ]

    n_nonzero = len(
        nonzero
    )

    # Every value exactly zero.
    if n_nonzero == 0:

        return {
            "n": n_total,
            "n_nonzero": 0,
            "z": 0.0,
            "p": 1.0,
            "w_plus": 0.0,
            "w_minus": 0.0,
            "signed_rank_score": 0.0,
            "rank_biserial": 0.0,
            "direction": "BALANCED",
        }

    # --------------------------------------------------------
    # Signed-rank direction
    # --------------------------------------------------------

    ranks = rankdata(
        np.abs(
            nonzero
        ),
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

    signed_rank_score = (
        w_plus - w_minus
    )

    rank_sum_total = (
        w_plus + w_minus
    )

    if rank_sum_total > 0:

        rank_biserial = (
            signed_rank_score
            / rank_sum_total
        )

    else:

        rank_biserial = 0.0

    direction_sign = np.sign(
        signed_rank_score
    )

    # --------------------------------------------------------
    # Wilcoxon test
    # --------------------------------------------------------

    # Newer SciPy:
    # method="asymptotic"
    #
    # Older SciPy:
    # method="approx"
    try:

        result = wilcoxon(
            x,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="asymptotic",
        )

    except ValueError:

        result = wilcoxon(
            x,
            zero_method="wilcox",
            correction=False,
            alternative="two-sided",
            method="approx",
        )

    p_value = float(
        result.pvalue
    )

    raw_z = getattr(
        result,
        "zstatistic",
        np.nan,
    )

    if np.isfinite(
        raw_z
    ):

        signed_z = (
            float(
                abs(raw_z)
            )
            * float(
                direction_sign
            )
        )

    else:

        signed_z = np.nan

    if direction_sign > 0:

        direction = "POSITIVE"

    elif direction_sign < 0:

        direction = "NEGATIVE"

    else:

        direction = "BALANCED"

    return {
        "n":
            int(
                n_total
            ),

        "n_nonzero":
            int(
                n_nonzero
            ),

        "z":
            signed_z,

        "p":
            p_value,

        "w_plus":
            w_plus,

        "w_minus":
            w_minus,

        "signed_rank_score":
            signed_rank_score,

        "rank_biserial":
            rank_biserial,

        "direction":
            direction,
    }


# ============================================================
# Main figure
# ============================================================

def make_figure(
    combined: pd.DataFrame,
    output_path: Path,
    stats_output_path: Path,
) -> None:

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required = {
        "Patient ID",
        "BIPOLAR",
        "Post-Stim T-Score",
        "Pre-Stim T-Score",
    }

    missing = (
        required
        - set(
            combined.columns
        )
    )

    if missing:

        raise ValueError(
            "combined_neuron_summary.csv is missing "
            f"required columns: {sorted(missing)}"
        )

    # --------------------------------------------------------
    # Standardize BIPOLAR labels
    # --------------------------------------------------------

    combined[
        "BIPOLAR"
    ] = (
        combined[
            "BIPOLAR"
        ]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # PRE - POST
    # --------------------------------------------------------

    # Prefer the existing pipeline value.
    #
    # If absent, reconstruct:
    #
    # PRE - POST
    if (
        "T-Score Diff (Pre - Post)"
        not in combined.columns
    ):

        combined[
            "T-Score Diff (Pre - Post)"
        ] = (
            pd.to_numeric(
                combined[
                    "Pre-Stim T-Score"
                ],
                errors="coerce",
            )
            -
            pd.to_numeric(
                combined[
                    "Post-Stim T-Score"
                ],
                errors="coerce",
            )
        )

    # --------------------------------------------------------
    # Patient order
    # --------------------------------------------------------

    patients = sorted(
        combined[
            "Patient ID"
        ]
        .dropna()
        .astype(str)
        .unique(),
        key=patient_sort_key,
    )

    print(
        "\nParticipants in figure:"
    )

    print(
        ", ".join(
            patients
        )
    )

    # --------------------------------------------------------
    # Print regional neuron counts for QC
    # --------------------------------------------------------

    print(
        "\nRegional neuron counts:"
    )

    for region in REGIONS:

        rdf = region_subset(
            combined,
            region,
        )

        print(
            f"  {region_display_name(region)}: "
            f"{len(rdf)} neurons"
        )

    # --------------------------------------------------------
    # Common y-axis across all 9 panels
    # --------------------------------------------------------

    all_values = []

    for region in REGIONS:

        rdf = region_subset(
            combined,
            region,
        )

        for metric, _ in METRICS:

            vals = pd.to_numeric(
                rdf[
                    metric
                ],
                errors="coerce",
            ).to_numpy(
                dtype=float
            )

            vals = vals[
                np.isfinite(
                    vals
                )
            ]

            all_values.extend(
                vals.tolist()
            )

    if not all_values:

        raise ValueError(
            "No finite t-score values found."
        )

    ymin = float(
        np.min(
            all_values
        )
    )

    ymax = float(
        np.max(
            all_values
        )
    )

    span = (
        ymax - ymin
    )

    if span == 0:
        span = 1.0

    # Room around data
    data_pad = max(
        0.5,
        0.08 * span,
    )

    # Extra room specifically for Z labels
    annotation_pad = max(
        1.0,
        0.20 * span,
    )

    plot_ymin = (
        ymin
        - data_pad
    )

    plot_ymax = (
        ymax
        + data_pad
        + annotation_pad
    )

    annotation_y = (
        ymax
        + data_pad
        + 0.55
        * annotation_pad
    )

    # --------------------------------------------------------
    # Create 3 x 3 figure
    # --------------------------------------------------------

    fig, axes = plt.subplots(
        nrows=3,
        ncols=3,
        figsize=(
            24,
            16,
        ),

        # Keep common x/y scales,
        # but force labels to show below every panel.
        sharex=True,
        sharey=True,
    )

    rng = np.random.default_rng(
        20261101
    )

    stats_rows = []

    # --------------------------------------------------------
    # Loop through panels
    # --------------------------------------------------------

    for row_idx, region in enumerate(
        REGIONS
    ):

        rdf = region_subset(
            combined,
            region,
        )

        display_region = (
            region_display_name(
                region
            )
        )

        for col_idx, (
            metric,
            metric_label,
        ) in enumerate(
            METRICS
        ):

            ax = axes[
                row_idx,
                col_idx,
            ]

            # ------------------------------------------------
            # Zero reference
            # ------------------------------------------------

            ax.axhline(
                0,
                linestyle="--",
                linewidth=1.1,
                color="0.45",
                alpha=0.8,
                zorder=0,
            )

            # ------------------------------------------------
            # Participants
            # ------------------------------------------------

            for x_idx, patient in enumerate(
                patients
            ):

                pdf = rdf[
                    rdf[
                        "Patient ID"
                    ].astype(str)
                    == patient
                ]

                values = pd.to_numeric(
                    pdf[
                        metric
                    ],
                    errors="coerce",
                )

                values = values[
                    np.isfinite(
                        values
                    )
                ].to_numpy(
                    dtype=float
                )

                # No neurons for this patient-region:
                # leave the x-axis position blank.
                if len(values) == 0:
                    continue

                # --------------------------------------------
                # Individual neuron swarm
                # --------------------------------------------

                jitter = rng.uniform(
                    -0.22,
                    0.22,
                    size=len(
                        values
                    ),
                )

                ax.scatter(
                    x_idx
                    + jitter,

                    values,

                    s=27,

                    # grayscale / B&W
                    color="0.35",

                    alpha=0.60,

                    edgecolors="white",

                    linewidths=0.35,

                    zorder=2,
                )

                # --------------------------------------------
                # Mean +/- SEM
                # --------------------------------------------

                mean_value = float(
                    np.mean(
                        values
                    )
                )

                if len(values) > 1:

                    sem_value = float(
                        np.std(
                            values,
                            ddof=1,
                        )
                        /
                        np.sqrt(
                            len(
                                values
                            )
                        )
                    )

                else:

                    sem_value = 0.0

                ax.errorbar(
                    x_idx,
                    mean_value,
                    yerr=sem_value,

                    # horizontal mean marker
                    fmt="_",

                    markersize=22,
                    markeredgewidth=2.5,

                    color="black",
                    ecolor="black",

                    elinewidth=2,
                    capsize=5,
                    capthick=1.8,

                    zorder=5,
                )

                # --------------------------------------------
                # Signed Wilcoxon Z vs 0
                # --------------------------------------------

                result = (
                    signed_wilcoxon_z(
                        values
                    )
                )

                z = result[
                    "z"
                ]

                p = result[
                    "p"
                ]

                n = result[
                    "n"
                ]

                # --------------------------------------------
                # Save exact plotted statistics
                # --------------------------------------------

                stats_rows.append({
                    "Patient ID":
                        patient,

                    "Region":
                        display_region,

                    "Region Code":
                        region,

                    "Window":
                        metric_label,

                    "Metric Column":
                        metric,

                    "N Neurons":
                        n,

                    "N Nonzero":
                        result[
                            "n_nonzero"
                        ],

                    "Mean T-Score":
                        mean_value,

                    "SEM T-Score":
                        sem_value,

                    "Signed Wilcoxon Z":
                        z,

                    "Wilcoxon P":
                        p,

                    "W Plus":
                        result[
                            "w_plus"
                        ],

                    "W Minus":
                        result[
                            "w_minus"
                        ],

                    "Signed Rank Score":
                        result[
                            "signed_rank_score"
                        ],

                    "Rank-Biserial Effect":
                        result[
                            "rank_biserial"
                        ],

                    "Direction":
                        result[
                            "direction"
                        ],
                })

                # --------------------------------------------
                # Horizontal Z annotation
                # --------------------------------------------

                if np.isfinite(
                    z
                ):

                    label = (
                        f"Z={z:+.2f}"
                    )

                    ax.text(
                        x_idx,
                        annotation_y,
                        label,

                        # horizontal
                        rotation=0,

                        ha="center",
                        va="center",

                        fontsize=7.5,

                        color="black",
                    )

            # ------------------------------------------------
            # Panel formatting
            # ------------------------------------------------

            ax.set_xlim(
                -0.55,
                len(patients)
                - 0.45,
            )

            ax.set_ylim(
                plot_ymin,
                plot_ymax,
            )

            ax.set_xticks(
                np.arange(
                    len(
                        patients
                    )
                )
            )

            ax.set_xticklabels(
                patients,
                rotation=45,
                ha="right",
                fontsize=9,
            )

            # IMPORTANT:
            # show patient labels on every subplot,
            # despite sharex=True
            ax.tick_params(
                axis="x",
                labelbottom=True,
            )

            ax.grid(
                axis="y",
                alpha=0.13,
                linewidth=0.8,
            )

            ax.spines[
                "top"
            ].set_visible(
                False
            )

            ax.spines[
                "right"
            ].set_visible(
                False
            )

            # Column headings
            if row_idx == 0:

                ax.set_title(
                    metric_label,
                    fontsize=15,
                    fontweight="bold",
                    pad=12,
                )

            # Row headings
            if col_idx == 0:

                ax.set_ylabel(
                    f"{display_region}\nNeuron t-score",
                    fontsize=12,
                    fontweight="bold",
                )

            # Participant label beneath EVERY panel
            ax.set_xlabel(
                "Participant",
                fontsize=10,
            )

    # ========================================================
    # Figure title
    # ========================================================

    fig.suptitle(
        (
            "Neuron t-score distributions by participant\n"
            "HPC vs Non-Hippocampal MTL vs FC"
        ),
        fontsize=17,
        y=0.995,
    )

    # ========================================================
    # Figure note
    # ========================================================

    fig.text(
        0.5,
        0.008,
        (
            "Each dot = one neuron. "
            "Black marker/error bar = mean ± SEM. "
            "Z = signed Wilcoxon signed-rank Z vs 0. "
            "Non-HPC MTL = AMY + ERC + PHC. "
            "Blank participant positions indicate no neurons "
            "for that region."
        ),
        ha="center",
        fontsize=10,
    )

    fig.tight_layout(
        rect=[
            0.02,
            0.045,
            1.0,
            0.96,
        ]
    )

    # ========================================================
    # Save
    # ========================================================

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # PNG
    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    # Vector PDF
    pdf_path = (
        output_path.with_suffix(
            ".pdf"
        )
    )

    fig.savefig(
        pdf_path,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    # ========================================================
    # Save statistics
    # ========================================================

    stats_df = pd.DataFrame(
        stats_rows
    )

    stats_df.to_csv(
        stats_output_path,
        index=False,
    )

    print(
        f"\nSaved PNG:\n  {output_path}"
    )

    print(
        f"\nSaved PDF:\n  {pdf_path}"
    )

    print(
        f"\nSaved statistics:\n  {stats_output_path}"
    )


# ============================================================
# Command line
# ============================================================

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Generate black-and-white participant swarm plots "
            "for HPC, non-HPC MTL, and FC from an existing "
            "combined_neuron_summary.csv."
        )
    )

    parser.add_argument(
        "--combined-csv",
        required=True,
        help=(
            "Path to combined_neuron_summary.csv "
            "from the BIPOLAR-only cross-patient analysis."
        ),
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Destination folder for PNG, PDF, "
            "and statistics CSV."
        ),
    )

    args = parser.parse_args()

    combined_path = Path(
        args.combined_csv
    )

    output_dir = Path(
        args.output_dir
    )

    if not combined_path.exists():

        raise FileNotFoundError(
            "Combined CSV not found:\n"
            f"{combined_path}"
        )

    combined = pd.read_csv(
        combined_path
    )

    make_figure(
        combined=combined,

        output_path=(
            output_dir
            / "participant_swarm_nonHPC_MTL_wilcoxon_3x3.png"
        ),

        stats_output_path=(
            output_dir
            / "participant_swarm_nonHPC_MTL_wilcoxon_3x3_stats.csv"
        ),
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )