"""Final summary dashboards and report assembly."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_SWARM_PLOTS = [
    "P1_Post-Stim_T-Scores.png",
    "P2_Pre-Stim_T-Scores.png",
    "P3_Diff_SigOnly.png",
    "P4_Diff_All.png",
    "P5_Diff_Post_GTE_1.png",
]


def load_summary_csv(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_region_summary_tables(output_root: str | Path) -> list[Path]:
    return sorted(Path(output_root).rglob("Swarm_Statistics_*.csv"))


def find_region_overview_tables(output_root: str | Path) -> list[Path]:
    return sorted(Path(output_root).rglob("Summary_Overview_*.csv"))


def find_global_summary_tables(output_root: str | Path) -> list[Path]:
    output_root = Path(output_root)
    candidates = [output_root / "Summary_Global_and_Regional.csv", output_root / "Summary_Patient_Bipolar_Breakdown.csv"]
    return [p for p in candidates if p.exists()]


def build_run_summary(output_root: str | Path, summary_csv: str | Path | None = None) -> pd.DataFrame:
    rows: list[dict] = []
    if summary_csv is not None:
        df = load_summary_csv(summary_csv)
        rows.append({
            "scope": "neuron_summary",
            "rows": int(len(df)),
            "patients": int(df["Patient"].nunique()) if "Patient" in df.columns else None,
            "neurons": int(df["Neuron Name"].nunique()) if "Neuron Name" in df.columns else None,
            "sig_pre": int(df["Pre-Stim Significant"].sum()) if "Pre-Stim Significant" in df.columns else None,
            "sig_post": int(df["Post-Stim Significant"].sum()) if "Post-Stim Significant" in df.columns else None,
        })
    for path in find_region_summary_tables(output_root):
        try:
            df = load_summary_csv(path)
        except Exception:
            continue
        rows.append({
            "scope": path.stem,
            "rows": int(len(df)),
            "patients": int(df["Patient"].nunique()) if "Patient" in df.columns else None,
            "neurons": int(df["Neuron Name"].nunique()) if "Neuron Name" in df.columns else None,
            "sig_pre": int(df["Pre-Stim Significant"].sum()) if "Pre-Stim Significant" in df.columns else None,
            "sig_post": int(df["Post-Stim Significant"].sum()) if "Post-Stim Significant" in df.columns else None,
        })
    for path in find_global_summary_tables(output_root):
        try:
            df = load_summary_csv(path)
        except Exception:
            continue
        rows.append({
            "scope": path.stem,
            "rows": int(len(df)),
            "patients": int(df["Total Patients"].iloc[0]) if "Total Patients" in df.columns and not df.empty else None,
            "neurons": int(df["Total Neurons"].iloc[0]) if "Total Neurons" in df.columns and not df.empty else None,
            "sig_pre": int(df["Significant Pre (-1000 to 0)"].iloc[0]) if "Significant Pre (-1000 to 0)" in df.columns and not df.empty else None,
            "sig_post": int(df["Significant Post (200-1200)"].iloc[0]) if "Significant Post (200-1200)" in df.columns and not df.empty else None,
        })
    out_df = pd.DataFrame(rows)
    if not out_df.empty:
        out_df = out_df.sort_values(["scope"]).reset_index(drop=True)
    return out_df


def _load_image(path: Path):
    import matplotlib.image as mpimg
    return mpimg.imread(path)


def build_dashboard_figure(plot_dir: str | Path, output_png: str | Path, title: str = "", plot_names: Sequence[str] = DEFAULT_SWARM_PLOTS) -> Optional[Path]:
    plot_dir = Path(plot_dir)
    output_png = Path(output_png)
    existing = [plot_dir / name for name in plot_names if (plot_dir / name).exists()]
    if not existing:
        return None
    n = len(existing)
    ncols = 2 if n > 1 else 1
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(14, 4.5 * nrows))
    axes_list = axes.ravel().tolist() if hasattr(axes, "ravel") else [axes]
    for ax in axes_list:
        ax.axis("off")
    for ax, img_path in zip(axes_list, existing):
        ax.imshow(_load_image(img_path))
        ax.set_title(img_path.name, fontsize=10)
        ax.axis("off")
    if title:
        fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_png


def build_region_dashboards(output_root: str | Path, dashboard_dir: str | Path | None = None) -> list[Path]:
    output_root = Path(output_root)
    dashboard_dir = Path(dashboard_dir) if dashboard_dir is not None else (output_root.parent / "dashboards")
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for region_dir in sorted(output_root.glob("*")):
        if not region_dir.is_dir():
            continue
        if region_dir.name == "dashboards":
            continue
        result = build_dashboard_figure(region_dir, dashboard_dir / f"{region_dir.name}_dashboard.png", title=region_dir.name)
        if result is not None:
            outputs.append(result)
    return outputs


def generate_summary_figures(output_root: str | Path, summary_csv: str | Path | None = None) -> tuple[pd.DataFrame, list[Path]]:
    output_root = Path(output_root)
    run_summary = build_run_summary(output_root=output_root, summary_csv=summary_csv)
    dashboards = build_region_dashboards(output_root=output_root)
    dashboard_dir = output_root.parent / "dashboards"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    if not run_summary.empty:
        run_summary.to_csv(dashboard_dir / "Run_Summary.csv", index=False)
    return run_summary, dashboards


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble summary dashboards from existing swarm/statistics outputs.")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary-csv", default="")
    args = parser.parse_args()
    summary_csv = args.summary_csv if args.summary_csv else None
    run_summary, dashboards = generate_summary_figures(output_root=args.output_root, summary_csv=summary_csv)
    print(f"Wrote run summary rows: {len(run_summary)}")
    print(f"Wrote dashboard figures: {len(dashboards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())