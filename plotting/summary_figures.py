"""summary_figures.py

Final summary dashboards and report assembly for the plotting layer.

This version prefers the legacy aggregate output directory when it exists,
so the same code can read both the new and old folder layouts.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import List, Optional, Sequence

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_SWARM_PLOTS = [
    "P1_Post-Stim_T-Scores.png",
    "P2_Pre-Stim_T-Scores.png",
    "P3_Diff_SigOnly.png",
    "P4_Diff_All.png",
    "P5_Diff_Post_GTE_1.png",
]


def _preferred_root(output_root: str | Path) -> Path:
    """Prefer Aggregate Patients outputs if it exists anywhere above output_root."""
    output_root = Path(output_root)
    candidates = [output_root, *output_root.parents]
    for candidate in candidates:
        agg = candidate / "Aggregate Patients outputs"
        if agg.exists():
            return agg
    return output_root


def load_summary_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load a summary CSV produced by the statistics or swarm stage."""
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_region_summary_tables(output_root: str | Path) -> list[Path]:
    """Find swarm summary CSVs in an output tree."""
    root = _preferred_root(output_root)
    return sorted(root.rglob("Swarm_Statistics_*.csv"))


def find_region_overview_tables(output_root: str | Path) -> list[Path]:
    """Find region overview CSVs in an output tree."""
    root = _preferred_root(output_root)
    return sorted(root.rglob("Summary_Overview_*.csv"))


def find_global_summary_tables(output_root: str | Path) -> list[Path]:
    """Find run-level summary CSVs in an output tree."""
    root = _preferred_root(output_root)
    candidates = [
        root / "Summary_Global_and_Regional.csv",
        root / "Summary_Patient_Bipolar_Breakdown.csv",
        root / "Aggregate T score sheet across patients.csv",
    ]
    return [p for p in candidates if p.exists()]


def build_run_summary(
    output_root: str | Path,
    summary_csv: str | Path | None = None,
) -> pd.DataFrame:
    """Build a compact run summary from existing summary tables."""
    root = _preferred_root(output_root)
    rows: list[dict] = []

    if summary_csv is not None:
        df = load_summary_csv(summary_csv)
        rows.append(
            {
                "scope": "neuron_summary",
                "rows": int(len(df)),
                "patients": int(df["Patient"].nunique()) if "Patient" in df.columns else None,
                "neurons": int(df["Neuron Name"].nunique()) if "Neuron Name" in df.columns else None,
                "sig_pre": int(df["Pre-Stim Significant"].sum()) if "Pre-Stim Significant" in df.columns else None,
                "sig_post": int(df["Post-Stim Significant"].sum()) if "Post-Stim Significant" in df.columns else None,
            }
        )

    for path in find_region_summary_tables(root):
        try:
            df = load_summary_csv(path)
        except Exception:
            continue
        rows.append(
            {
                "scope": path.stem,
                "rows": int(len(df)),
                "patients": int(df["Patient"].nunique()) if "Patient" in df.columns else None,
                "neurons": int(df["Neuron Name"].nunique()) if "Neuron Name" in df.columns else None,
                "sig_pre": int(df["Pre-Stim Significant"].sum()) if "Pre-Stim Significant" in df.columns else None,
                "sig_post": int(df["Post-Stim Significant"].sum()) if "Post-Stim Significant" in df.columns else None,
            }
        )

    for path in find_global_summary_tables(root):
        try:
            df = load_summary_csv(path)
        except Exception:
            continue
        rows.append(
            {
                "scope": path.stem,
                "rows": int(len(df)),
                "patients": int(df["Total Patients"].iloc[0]) if "Total Patients" in df.columns and not df.empty else None,
                "neurons": int(df["Total Neurons"].iloc[0]) if "Total Neurons" in df.columns and not df.empty else None,
                "sig_pre": int(df["Significant Pre (-1000 to 0)"].iloc[0]) if "Significant Pre (-1000 to 0)" in df.columns and not df.empty else None,
                "sig_post": int(df["Significant Post (200-1200)"].iloc[0]) if "Significant Post (200-1200)" in df.columns and not df.empty else None,
            }
        )

    out_df = pd.DataFrame(rows)
    if not out_df.empty:
        out_df = out_df.sort_values(["scope"]).reset_index(drop=True)
    return out_df


def _load_image(path: Path):
    """Load an image for dashboard composition."""
    import matplotlib.image as mpimg

    return mpimg.imread(path)


def build_dashboard_figure(
    plot_dir: str | Path,
    output_png: str | Path,
    title: str = "",
    plot_names: Sequence[str] = DEFAULT_SWARM_PLOTS,
) -> Optional[Path]:
    """Build one dashboard figure from existing P1--P5 swarm plots."""
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
        img = _load_image(img_path)
        ax.imshow(img)
        ax.set_title(img_path.name, fontsize=10)
        ax.axis("off")

    if title:
        fig.suptitle(title, fontsize=14)

    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_png


def build_region_dashboards(
    output_root: str | Path,
    dashboard_dir: str | Path | None = None,
) -> list[Path]:
    """Build dashboard figures for every region folder that contains swarm plots."""
    root = _preferred_root(output_root)
    dashboard_dir = Path(dashboard_dir) if dashboard_dir is not None else (Path(output_root) / "dashboards")
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    seen: set[str] = set()
    for region_dir in sorted(root.rglob("* plots")):
        if not region_dir.is_dir():
            continue
        if region_dir.name in seen:
            continue
        seen.add(region_dir.name)
        out_png = dashboard_dir / f"{region_dir.name.replace(' ', '_')}_dashboard.png"
        result = build_dashboard_figure(
            plot_dir=region_dir,
            output_png=out_png,
            title=region_dir.name,
        )
        if result is not None:
            outputs.append(result)
    return outputs


def _mirror_outputs(src_files: list[Path], src_root: Path, dst_root: Path) -> None:
    for src in src_files:
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def generate_summary_figures(
    output_root: str | Path,
    summary_csv: str | Path | None = None,
) -> tuple[pd.DataFrame, list[Path]]:
    """Generate run summaries and dashboard figures from existing outputs."""
    output_root = Path(output_root)
    preferred_root = _preferred_root(output_root)

    run_summary = build_run_summary(output_root=output_root, summary_csv=summary_csv)
    if not run_summary.empty:
        out_csv = output_root / "Run_Summary.csv"
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        run_summary.to_csv(out_csv, index=False)
        if preferred_root != output_root:
            preferred_csv = preferred_root / "Run_Summary.csv"
            preferred_csv.parent.mkdir(parents=True, exist_ok=True)
            run_summary.to_csv(preferred_csv, index=False)

    dashboards = build_region_dashboards(output_root=output_root)
    if preferred_root != output_root:
        src_dashboard_dir = output_root / "dashboards"
        dst_dashboard_dir = preferred_root / "dashboards"
        if src_dashboard_dir.exists():
            dst_dashboard_dir.mkdir(parents=True, exist_ok=True)
            for png in src_dashboard_dir.glob("*.png"):
                shutil.copy2(png, dst_dashboard_dir / png.name)

    return run_summary, dashboards


def main() -> int:
    parser = argparse.ArgumentParser(description="Assemble summary dashboards from existing swarm/statistics outputs.")
    parser.add_argument("--output-root", required=True, help="Root output folder containing region and global summary tables.")
    parser.add_argument("--summary-csv", default="", help="Optional neuron-level summary CSV from statistics.py.")
    args = parser.parse_args()

    summary_csv = args.summary_csv if args.summary_csv else None
    run_summary, dashboards = generate_summary_figures(
        output_root=args.output_root,
        summary_csv=summary_csv,
    )

    print(f"Wrote run summary rows: {len(run_summary)}")
    print(f"Wrote dashboard figures: {len(dashboards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())