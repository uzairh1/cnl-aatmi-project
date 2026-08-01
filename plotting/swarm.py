"""swarm.py

Population swarm plots and legacy-style summary statistics.

This version restores the legacy region folder structure and optionally
reconstructs localization labels from the localization workbook.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import chisquare

from data_io.localization import BIPOLAR_REGIONS, infer_neuron_localization, load_localization_map


TARGET_FOLDERS: Dict[str, List[str]] = {
    "HPC": ["HPC"],
    "ERC": ["ERC"],
    "FC": ["FC"],
    "LTC": ["LTC"],
    "MTL": ["AMY", "ERC", "HPC", "PHC"],
}


def load_summary_table(summary_csv: str | Path) -> pd.DataFrame:
    """Load the neuron summary CSV used by the swarm plots."""
    summary_csv = Path(summary_csv)
    df = pd.read_csv(summary_csv)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_patient_root(output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    if output_dir.name == "swarm" and len(output_dir.parents) >= 2:
        return output_dir.parents[1]
    return output_dir


def _aggregate_root(output_dir: str | Path) -> Path:
    return _resolve_patient_root(output_dir) / "Aggregate Patients outputs"


def _select_region_dataframe(df: pd.DataFrame, region_name: str, abbreviations: Optional[List[str]]) -> pd.DataFrame:
    """Filter the summary table to one region or return the full table."""
    if region_name == "Global" or abbreviations is None:
        return df.copy()

    if "Localization - Bipolar" not in df.columns:
        return pd.DataFrame()

    pattern = "^(?:" + "|".join(abbreviations) + ") -"
    return df[df["Localization - Bipolar"].astype(str).str.contains(pattern, case=False, na=False)].copy()


def _enrich_localization_columns(df: pd.DataFrame, localization_file: str = "") -> pd.DataFrame:
    """Add Localization and Localization - Bipolar columns if they are missing."""
    out = df.copy()
    if "Neuron Name" not in out.columns:
        return out

    if "Localization" in out.columns and "Localization - Bipolar" in out.columns and not localization_file:
        return out

    if not localization_file:
        if "Localization" not in out.columns:
            out["Localization"] = "Unknown"
        if "Localization - Bipolar" not in out.columns:
            out["Localization - Bipolar"] = "UNKNOWN - Unknown"
        return out

    loc_df = load_localization_map(localization_file)
    if loc_df.empty:
        if "Localization" not in out.columns:
            out["Localization"] = "Unknown"
        if "Localization - Bipolar" not in out.columns:
            out["Localization - Bipolar"] = "UNKNOWN - Unknown"
        return out

    loc_values = []
    bipolar_values = []
    for neuron_name in out["Neuron Name"].astype(str):
        electrode_code, full_location, region_abbr = infer_neuron_localization(neuron_name, loc_df)
        loc_values.append(full_location)
        bipolar_values.append(f"{region_abbr} - {BIPOLAR_REGIONS.get(region_abbr, 'Unknown')}")

    out["Localization"] = loc_values
    out["Localization - Bipolar"] = bipolar_values
    return out


def _create_swarm_and_stats(
    df: pd.DataFrame,
    metric_col: str,
    plot_id: str,
    title_label: str,
    thresh: Optional[float],
    out_dir: Path,
    stats_rows: List[Dict],
    test_type: str,
    sig_col: Optional[str] = None,
) -> None:
    """Create one swarm plot and append one statistics row."""
    df_clean = df.dropna(subset=[metric_col]).copy()
    if df_clean.empty:
        return

    n_total = len(df_clean)
    mean_val = df_clean[metric_col].mean()
    sem_val = df_clean[metric_col].sem()

    stat_dict = {
        "Plot ID": plot_id,
        "Metric": metric_col,
        "N Total": n_total,
        "Mean": mean_val,
        "SEM": sem_val,
    }

    if test_type == "chisq_vs_chance":
        if sig_col and sig_col in df_clean.columns:
            sig_mask = df_clean[sig_col] == True
            n_sig_pos = int((sig_mask & (df_clean[metric_col] > 0)).sum())
            n_sig_neg = int((sig_mask & (df_clean[metric_col] < 0)).sum())
        elif thresh is not None:
            n_sig_pos = int((df_clean[metric_col] >= thresh).sum())
            n_sig_neg = int((df_clean[metric_col] <= -thresh).sum())
        else:
            n_sig_pos = 0
            n_sig_neg = 0

        n_sig = n_sig_pos + n_sig_neg
        n_nonsig = n_total - n_sig
        expected_sig = n_total * 0.05
        expected_nonsig = n_total * 0.95

        if expected_sig > 0:
            chi2, p_val = chisquare([n_sig, n_nonsig], f_exp=[expected_sig, expected_nonsig])
        else:
            chi2, p_val = None, None

        stat_dict.update(
            {
                "Sig Positive": n_sig_pos,
                "Sig Negative": n_sig_neg,
                "Total Sig": n_sig,
                "Expected Sig (5%)": expected_sig,
                "Chi2 Stat": chi2,
                "P-Value": p_val,
            }
        )

    elif test_type == "chisq_vs_5050":
        n_pre_driven = int((df_clean[metric_col] > 0).sum())
        n_post_driven = int((df_clean[metric_col] < 0).sum())
        n_exact_zero = int((df_clean[metric_col] == 0).sum())

        valid_n = n_pre_driven + n_post_driven
        expected = valid_n / 2.0

        if expected > 0:
            chi2, p_val = chisquare([n_pre_driven, n_post_driven], f_exp=[expected, expected])
        else:
            chi2, p_val = None, None

        stat_dict.update(
            {
                "Pre-Driven (>0)": n_pre_driven,
                "Post-Driven (<0)": n_post_driven,
                "Exact Zero": n_exact_zero,
                "Valid N (excluding 0)": valid_n,
                "Expected (50/50)": expected,
                "Chi2 Stat": chi2,
                "P-Value": p_val,
            }
        )
    else:
        raise ValueError(f"Unknown test_type: {test_type}")

    stats_rows.append(stat_dict)

    fig = plt.figure(figsize=(7, 8))
    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1.5], wspace=0.05)
    ax_swarm = fig.add_subplot(gs[0])
    ax_hist = fig.add_subplot(gs[1], sharey=ax_swarm)

    df_clean = df_clean.copy()
    df_clean["Group"] = "Neurons"

    sns.stripplot(
        x="Group",
        y=metric_col,
        data=df_clean,
        color="#2c3e50",
        size=4.0,
        alpha=0.6,
        jitter=0.25,
        edgecolor="white",
        linewidth=0.3,
        zorder=2,
        ax=ax_swarm,
    )

    ax_swarm.errorbar(
        x=0,
        y=mean_val,
        yerr=sem_val,
        color="#e74c3c",
        capsize=6,
        elinewidth=2.5,
        capthick=2.5,
        marker="_",
        markersize=18,
        label="Mean ± SEM",
        zorder=4,
    )

    ax_hist.hist(df_clean[metric_col], bins=30, orientation="horizontal", color="gray", alpha=0.7)
    ax_hist.tick_params(axis="y", left=False, labelleft=False)
    ax_hist.set_xlabel("Count")

    if thresh is not None:
        ax_swarm.axhline(thresh, color="#3498db", linestyle="--", alpha=0.6, label=f"Significance Guide (+/- {thresh})")
        ax_swarm.axhline(-thresh, color="#3498db", linestyle="--", alpha=0.6)
        ax_hist.axhline(thresh, color="#3498db", linestyle="--", alpha=0.6)
        ax_hist.axhline(-thresh, color="#3498db", linestyle="--", alpha=0.6)

    ax_swarm.axhline(0, color="gray", linestyle="-", alpha=0.3)
    ax_hist.axhline(0, color="gray", linestyle="-", alpha=0.3)

    ax_swarm.set_title(title_label, fontsize=13, pad=20)
    ax_swarm.set_ylabel(metric_col, fontsize=12)
    ax_swarm.set_xlabel("")
    ax_swarm.set_xticks([])

    sns.despine(ax=ax_swarm, bottom=True)
    sns.despine(ax=ax_hist, left=True, bottom=False)

    ax_swarm.legend(frameon=True, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=2)
    ax_swarm.grid(axis="y", linestyle="-", alpha=0.15)

    out_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_dir / f"{plot_id}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def _copy_tree_contents(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def generate_population_swarm_plot(
    summary_csv: str | Path,
    output_dir: str | Path,
    localization_file: str = "",
) -> None:
    """Generate global and region-specific swarm plots from a summary CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    patient_root = _resolve_patient_root(output_dir)
    agg_root = _aggregate_root(output_dir)
    agg_root.mkdir(parents=True, exist_ok=True)

    if not Path(summary_csv).exists():
        raise FileNotFoundError(f"Summary CSV not found: {summary_csv}")

    df = load_summary_table(summary_csv)
    if df.empty:
        print("Summary table is empty. Cannot generate swarm plots.")
        return

    df = _enrich_localization_columns(df, localization_file)

    # Mirror the global summary sheet used by the monolithic pipeline.
    df.to_csv(output_dir / "Aggregate T score sheet across patients.csv", index=False)
    df.to_csv(agg_root / "Aggregate T score sheet across patients.csv", index=False)

    global_sig_dir = _ensure_output_dir(output_dir / "All significant plots")
    global_non_sig_dir = _ensure_output_dir(output_dir / "All Non significant plots")
    agg_global_sig_dir = _ensure_output_dir(agg_root / "All significant plots")
    agg_global_non_sig_dir = _ensure_output_dir(agg_root / "All Non significant plots")

    summary_overview_data = []
    regions = {"Global": None, **TARGET_FOLDERS}

    for region_name, abbr_list in regions.items():
        if region_name == "Global":
            df_sub = df.copy()
        else:
            df_sub = _select_region_dataframe(df, region_name, abbr_list)

        if df_sub.empty:
            continue

        base_region_dir = _ensure_output_dir(output_dir / f"{region_name} plots")
        agg_region_dir = _ensure_output_dir(agg_root / f"{region_name} plots")

        stats_rows: list[dict] = []

        _create_swarm_and_stats(
            df_sub,
            "Post-Stim T-Score",
            "P1_Post-Stim_T-Scores",
            f"[{region_name}] Stim-Locked Post-Clip (200-1200ms)\nT-Scores",
            1.96,
            base_region_dir,
            stats_rows,
            test_type="chisq_vs_chance",
            sig_col="Post-Stim Significant",
        )

        _create_swarm_and_stats(
            df_sub,
            "Pre-Stim T-Score",
            "P2_Pre-Stim_T-Scores",
            f"[{region_name}] Pre-Stimulus (-1000 to 0ms)\nT-Scores",
            1.96,
            base_region_dir,
            stats_rows,
            test_type="chisq_vs_chance",
            sig_col="Pre-Stim Significant",
        )

        df_p3 = df_sub[(df_sub["Pre-Stim Significant"] == True) | (df_sub["Post-Stim Significant"] == True)]
        _create_swarm_and_stats(
            df_p3,
            "T-Score Diff (Pre - Post)",
            "P3_Diff_SigOnly",
            f"[{region_name}] T-Score Diff (Pre - Post)\n[Significant Pre OR Post Neurons]",
            None,
            base_region_dir,
            stats_rows,
            test_type="chisq_vs_5050",
        )

        _create_swarm_and_stats(
            df_sub,
            "T-Score Diff (Pre - Post)",
            "P4_Diff_All",
            f"[{region_name}] T-Score Diff (Pre - Post)\n[All Active Neurons]",
            None,
            base_region_dir,
            stats_rows,
            test_type="chisq_vs_5050",
        )

        df_p5 = df_sub[df_sub["Post-Stim T-Score"] >= 1.0]
        _create_swarm_and_stats(
            df_p5,
            "T-Score Diff (Pre - Post)",
            "P5_Diff_Post_GTE_1",
            f"[{region_name}] T-Score Diff (Pre - Post)\n[Post-Stim T-Score >= +1.0]",
            None,
            base_region_dir,
            stats_rows,
            test_type="chisq_vs_5050",
        )

        if stats_rows:
            region_stats = pd.DataFrame(stats_rows)
            region_stats.to_csv(base_region_dir / f"Swarm_Statistics_{region_name}.csv", index=False)
            print(f"Generated {region_name} swarm plots and statistics in {base_region_dir}")

        sig_pre_count = int(df_sub["Pre-Stim Significant"].sum()) if "Pre-Stim Significant" in df_sub.columns else 0
        sig_post_count = int(df_sub["Post-Stim Significant"].sum()) if "Post-Stim Significant" in df_sub.columns else 0
        region_summary = {
            "Scope": region_name,
            "Total Patients": int(df_sub["Patient"].nunique()) if "Patient" in df_sub.columns else 0,
            "Total Neurons": int(len(df_sub)),
            "Significant Pre (-1000 to 0)": sig_pre_count,
            "Significant Post (200-1200)": sig_post_count,
        }
        summary_overview_data.append(region_summary)

        if region_name != "Global":
            pd.DataFrame([region_summary]).to_csv(base_region_dir / f"Summary_Overview_{region_name}.csv", index=False)

        _copy_tree_contents(base_region_dir, agg_region_dir)

    if summary_overview_data:
        summary_overview_df = pd.DataFrame(summary_overview_data)
        summary_overview_df.to_csv(output_dir / "Summary_Global_and_Regional.csv", index=False)
        summary_overview_df.to_csv(agg_root / "Summary_Global_and_Regional.csv", index=False)
        print("Generated Master Overview Summary (Summary_Global_and_Regional.csv).")

    if "Patient" in df.columns and "Localization - Bipolar" in df.columns:
        breakdown_df = (
            df.groupby(["Patient", "Localization - Bipolar"])
            .agg(
                Num_Neurons=("Neuron Name", "count"),
                Sig_Pre=("Pre-Stim Significant", "sum"),
                Sig_Post=("Post-Stim Significant", "sum"),
            )
            .reset_index()
        )

        breakdown_df.rename(
            columns={
                "Num_Neurons": "Total Neurons",
                "Sig_Pre": "Significant Pre",
                "Sig_Post": "Significant Post",
            },
            inplace=True,
        )
        breakdown_df.to_csv(output_dir / "Summary_Patient_Bipolar_Breakdown.csv", index=False)
        breakdown_df.to_csv(agg_root / "Summary_Patient_Bipolar_Breakdown.csv", index=False)
        print("Generated Detailed Patient/Bipolar Breakdown (Summary_Patient_Bipolar_Breakdown.csv).")

    # Copy global sig / nonsig directories into the aggregate mirror to match the legacy layout.
    _copy_tree_contents(global_sig_dir, agg_global_sig_dir)
    _copy_tree_contents(global_non_sig_dir, agg_global_non_sig_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate population swarm plots from a neuron summary CSV.")
    parser.add_argument("--summary-csv", required=True, help="Path to the neuron summary CSV.")
    parser.add_argument("--output-dir", required=True, help="Folder where swarm plots and summary CSVs will be written.")
    parser.add_argument("--localization-file", default="", help="Optional localization workbook.")
    args = parser.parse_args()

    generate_population_swarm_plot(
        summary_csv=args.summary_csv,
        output_dir=args.output_dir,
        localization_file=args.localization_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())