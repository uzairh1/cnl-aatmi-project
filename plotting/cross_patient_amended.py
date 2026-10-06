"""Cross-patient aggregation of existing neuron_summary.csv outputs.

This is intentionally a READ-ONLY post-processing step with respect to the
per-patient pipeline. It does not rerun alignment, statistics, or rasters.

Outputs
-------
<outputs_root>/cross_patient/
    combined_neuron_summary.csv
    region_counts.csv                    # canonical/expanded region counts
    poster_region_counts_strict.csv      # strict poster-era HPC/MTL/FC counts
    patient_color_key.csv
    neutral/
        poster_HPC_MTL_FC.png
        <scope>_post_pre_diff.png
    colored/
        poster_HPC_MTL_FC.png
        <scope>_post_pre_diff.png
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


METRICS = [
    ("Post-Stim T-Score", "POST"),
    ("Pre-Stim T-Score", "PRE"),
    ("T-Score Diff (Pre - Post)", "PRE - POST"),
]

# Canonical region vocabulary already used by the project.
CANONICAL_REGIONS = {
    "AMY", "BAS", "CC", "CENT", "ERC", "FC", "FUS", "HPC", "INS",
    "LTC", "MCC", "PARS", "PC", "PHC", "VIS", "WM", "UNKNOWN",
}

# MTL definition used by the existing pipeline/poster.
MTL_REGIONS = {"AMY", "ERC", "HPC", "PHC"}

POSTER_SCOPES = ["HPC", "MTL", "FC"]


def _patient_id_from_path(path: Path) -> str:
    """Extract P### from the patient output folder name."""
    # .../<patient_output>/statistics/neuron_summary.csv
    patient_dir = path.parent.parent.name
    m = re.search(r"P(\d+)", patient_dir, flags=re.IGNORECASE)
    if m:
        return f"P{m.group(1)}"
    return patient_dir


def _canonicalize_region(raw_abbr: object, full_location: object) -> str:
    """Normalize localization into a shared cross-patient region vocabulary.

    Existing canonical abbreviations are kept unchanged. Noncanonical labels
    (notably lateralized labels in some localization sheets) are mapped using
    the anatomical full_location string while preserving the raw label in a
    separate output column.
    """
    raw = str(raw_abbr).strip().upper() if pd.notna(raw_abbr) else "UNKNOWN"
    loc = str(full_location).strip().lower() if pd.notna(full_location) else ""

    if raw in CANONICAL_REGIONS and raw != "UNKNOWN":
        return raw

    # White matter first so e.g. wm-lh-rostralanteriorcingulate stays WM.
    if loc.startswith("wm-") or "white matter" in loc:
        return "WM"
    if "amygdala" in loc:
        return "AMY"
    if "hippocamp" in loc:
        return "HPC"
    if "entorhinal" in loc:
        return "ERC"
    if "parahippocamp" in loc or "perirhinal" in loc:
        return "PHC"
    if "orbitofrontal" in loc or "frontal" in loc:
        return "FC"
    if "cingulate" in loc:
        if "posterior" in loc or "midcingulate" in loc:
            return "MCC"
        return "CC"
    if "insula" in loc:
        return "INS"
    if "fusiform" in loc:
        return "FUS"
    if any(k in loc for k in ("superiortemporal", "middletemporal", "inferiortemporal", "temporalpole", "bankssts")):
        return "LTC"
    if any(k in loc for k in ("precuneus", "inferiorparietal", "supramarginal", "postcentral", "parietal")):
        return "PC"
    if any(k in loc for k in ("lingual", "pericalcarine", "cuneus")):
        return "VIS"

    # Keep a noncanonical raw code visible rather than silently discarding it.
    if raw and raw not in {"NAN", "NONE", "<NA>", "UNKNOWN"}:
        return f"UNMAPPED_{raw}"
    return "UNKNOWN"


def discover_summary_files(outputs_root: Path, exclude_substrings: Iterable[str]) -> list[Path]:
    """Find existing per-patient summary CSVs without running the pipeline."""
    excludes = [s.lower() for s in exclude_substrings if s]
    paths = sorted(outputs_root.glob("P*/statistics/neuron_summary.csv"))
    kept = []
    for path in paths:
        path_lower = str(path).lower()
        if any(token in path_lower for token in excludes):
            continue
        kept.append(path)
    if not kept:
        raise FileNotFoundError(
            f"No */statistics/neuron_summary.csv files found under {outputs_root}"
        )
    return kept


def build_combined_table(summary_paths: list[Path]) -> pd.DataFrame:
    """Combine patient summaries and join each with its localization_trace.csv."""
    frames: list[pd.DataFrame] = []
    patient_sources: dict[str, Path] = {}

    for summary_path in summary_paths:
        patient_id = _patient_id_from_path(summary_path)
        if patient_id in patient_sources:
            raise ValueError(
                "Duplicate patient outputs would double-count neurons:\n"
                f"  {patient_id}: {patient_sources[patient_id]}\n"
                f"  {patient_id}: {summary_path}\n"
                "Exclude one copy (for example old *_box outputs) before aggregating."
            )
        patient_sources[patient_id] = summary_path

        df = pd.read_csv(summary_path)
        df.columns = [str(c).strip() for c in df.columns]

        required = {"Neuron Name", *(m[0] for m in METRICS)}
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"{summary_path} is missing columns: {missing}")

        trace_path = summary_path.parent.parent / "localization_trace.csv"
        if not trace_path.exists():
            raise FileNotFoundError(
                f"Missing localization trace for {patient_id}: {trace_path}\n"
                "Cross-patient regional plots need this existing pipeline artifact."
            )

        trace = pd.read_csv(trace_path)
        trace.columns = [str(c).strip() for c in trace.columns]
        required_trace = {"neuron_name", "region_abbr", "full_location"}
        missing_trace = sorted(required_trace - set(trace.columns))
        if missing_trace:
            raise ValueError(f"{trace_path} is missing columns: {missing_trace}")

        trace = trace[["neuron_name", "region_abbr", "full_location"]].rename(
            columns={
                "neuron_name": "Neuron Name",
                "region_abbr": "Region Raw",
                "full_location": "Full Location",
            }
        )

        merged = df.merge(trace, on="Neuron Name", how="left", validate="one_to_one")
        merged.insert(0, "Patient ID", patient_id)
        merged.insert(1, "Patient Output Folder", summary_path.parent.parent.name)
        merged["Region Canonical"] = [
            _canonicalize_region(raw, loc)
            for raw, loc in zip(merged["Region Raw"], merged["Full Location"])
        ]
        merged["Source Summary CSV"] = str(summary_path)
        frames.append(merged)

    out = pd.concat(frames, ignore_index=True)
    out["Is MTL"] = out["Region Canonical"].isin(MTL_REGIONS)
    return out


def _scope_df(
    df: pd.DataFrame,
    scope: str,
    *,
    region_mode: str = "canonical",
) -> pd.DataFrame:
    """Select neurons for a plotting scope.

    region_mode="canonical" is the expanded/new analysis: it uses the
    harmonized Region Canonical column so lateralized/nonstandard raw labels
    can contribute to their anatomical group.

    region_mode="strict_raw" reproduces the poster-era selection logic:
      HPC = Region Raw == "HPC"
      FC  = Region Raw == "FC"
      MTL = Region Raw in {AMY, ERC, HPC, PHC}
    No heuristic anatomical remapping is used in strict_raw mode.
    """
    if scope.lower() == "global":
        return df.copy()

    scope_u = scope.upper()
    if region_mode == "strict_raw":
        raw = df["Region Raw"].astype("string").str.strip().str.upper()
        if scope_u == "MTL":
            return df[raw.isin(MTL_REGIONS)].copy()
        return df[raw == scope_u].copy()

    if region_mode != "canonical":
        raise ValueError(f"Unknown region_mode: {region_mode}")

    if scope_u == "MTL":
        return df[df["Region Canonical"].isin(MTL_REGIONS)].copy()
    return df[df["Region Canonical"] == scope].copy()


def _load_or_make_patient_colors(cross_root: Path, patients: list[str]) -> dict[str, str]:
    """Create a deterministic color map and persist it for future reruns."""
    key_path = cross_root / "patient_color_key.csv"
    if key_path.exists():
        old = pd.read_csv(key_path)
        if {"Patient ID", "Color"}.issubset(old.columns):
            old_map = dict(zip(old["Patient ID"].astype(str), old["Color"].astype(str)))
            if all(p in old_map for p in patients):
                return {p: old_map[p] for p in patients}

    cmap = plt.get_cmap("tab20")
    colors = {}
    for i, patient in enumerate(sorted(patients)):
        rgba = cmap(i % cmap.N)
        colors[patient] = matplotlib.colors.to_hex(rgba)

    pd.DataFrame(
        [{"Patient ID": p, "Color": colors[p]} for p in sorted(colors)]
    ).to_csv(key_path, index=False)
    return colors


def _finite_values(df: pd.DataFrame) -> np.ndarray:
    chunks = []
    for metric, _ in METRICS:
        vals = pd.to_numeric(df[metric], errors="coerce").to_numpy(dtype=float)
        vals = vals[np.isfinite(vals)]
        if len(vals):
            chunks.append(vals)
    return np.concatenate(chunks) if chunks else np.array([0.0])


def _ylims_for(df: pd.DataFrame) -> tuple[float, float]:
    vals = _finite_values(df)
    lo = float(np.min(vals))
    hi = float(np.max(vals))
    if lo == hi:
        lo -= 1.0
        hi += 1.0
    pad = max(0.25, 0.08 * (hi - lo))
    return lo - pad, hi + pad


def _draw_panel(
    fig: plt.Figure,
    spec,
    df: pd.DataFrame,
    metric: str,
    metric_short: str,
    *,
    scope: str,
    colored: bool,
    patient_colors: dict[str, str],
    ylims: tuple[float, float],
    seed: int,
) -> None:
    sub = spec.subgridspec(1, 2, width_ratios=[4.0, 1.35], wspace=0.04)
    ax = fig.add_subplot(sub[0, 0])
    hist = fig.add_subplot(sub[0, 1], sharey=ax)

    clean = df.copy()
    clean[metric] = pd.to_numeric(clean[metric], errors="coerce")
    clean = clean[np.isfinite(clean[metric])]

    if clean.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        hist.axis("off")
        ax.set_title(metric_short)
        ax.set_ylim(*ylims)
        return

    rng = np.random.default_rng(seed)
    jitter = rng.uniform(-0.26, 0.26, size=len(clean))
    y = clean[metric].to_numpy(float)

    if colored:
        colors = [patient_colors[str(p)] for p in clean["Patient ID"]]
    else:
        colors = ["#2c3e50"] * len(clean)

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

    mean = float(clean[metric].mean())
    sem = float(clean[metric].sem()) if len(clean) > 1 else 0.0
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

    hist.hist(y, bins=20, orientation="horizontal", color="0.55", alpha=0.70)

    for a in (ax, hist):
        a.axhline(0, color="0.55", linewidth=0.9, alpha=0.65, zorder=1)
        a.set_ylim(*ylims)
        a.grid(axis="y", alpha=0.12, linewidth=0.7)

    ax.set_xlim(-0.45, 0.45)
    ax.set_xticks([])
    ax.set_xlabel("")
    ax.set_title(
        f"{metric_short}\nN={len(clean)} neurons, {clean['Patient ID'].nunique()} patients",
        fontsize=10,
    )
    ax.set_ylabel(metric, fontsize=9)
    hist.set_xlabel("Count", fontsize=8)
    hist.tick_params(axis="y", left=False, labelleft=False)
    hist.tick_params(axis="x", labelsize=7)

    ax.spines[["top", "right", "bottom"]].set_visible(False)
    hist.spines[["top", "right", "left"]].set_visible(False)


def make_scope_figure(
    combined: pd.DataFrame,
    scope: str,
    out_path: Path,
    *,
    colored: bool,
    patient_colors: dict[str, str],
) -> None:
    df = _scope_df(combined, scope, region_mode="canonical")
    if df.empty:
        return

    fig = plt.figure(figsize=(14.5, 5.2))
    outer = fig.add_gridspec(1, 3, wspace=0.32)
    ylims = _ylims_for(df)

    for j, (metric, short) in enumerate(METRICS):
        _draw_panel(
            fig,
            outer[0, j],
            df,
            metric,
            short,
            scope=scope,
            colored=colored,
            patient_colors=patient_colors,
            ylims=ylims,
            seed=1000 + j,
        )

    fig.suptitle(f"{scope} — cross-patient neuron t-scores", fontsize=14, y=1.01)

    if colored:
        present = sorted(df["Patient ID"].dropna().astype(str).unique())
        handles = [
            Line2D([0], [0], marker="o", color="none", markerfacecolor=patient_colors[p],
                   markeredgecolor="white", markersize=7, label=p)
            for p in present
        ]
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.055),
                   ncol=min(6, max(1, len(handles))), frameon=False, fontsize=8)
        fig.subplots_adjust(bottom=0.17)
    else:
        fig.subplots_adjust(bottom=0.12)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_poster_grid(
    combined: pd.DataFrame,
    out_path: Path,
    *,
    colored: bool,
    patient_colors: dict[str, str],
) -> None:
    """3x3 HPC / MTL / FC by POST / PRE / PRE-POST, matching poster organization."""
    # IMPORTANT: poster replication uses the original strict raw region labels.
    # Expanded per-region figures below continue to use canonicalized regions.
    available = [
        _scope_df(combined, scope, region_mode="strict_raw")
        for scope in POSTER_SCOPES
    ]
    union = pd.concat([x for x in available if not x.empty], ignore_index=True)
    if union.empty:
        return

    fig = plt.figure(figsize=(14.5, 13.5))
    outer = fig.add_gridspec(3, 3, hspace=0.44, wspace=0.30)
    ylims = _ylims_for(union)

    for i, scope in enumerate(POSTER_SCOPES):
        df = _scope_df(combined, scope, region_mode="strict_raw")
        for j, (metric, short) in enumerate(METRICS):
            _draw_panel(
                fig,
                outer[i, j],
                df,
                metric,
                short,
                scope=scope,
                colored=colored,
                patient_colors=patient_colors,
                ylims=ylims,
                seed=2000 + i * 10 + j,
            )
        # Row label placed in the left margin.
        fig.text(0.005, 0.825 - i * 0.305, scope, rotation=90,
                 va="center", ha="left", fontsize=14, fontweight="bold")

    fig.suptitle("Poster-style cross-patient t-score distributions", fontsize=16, y=0.995)

    if colored:
        present = sorted(union["Patient ID"].dropna().astype(str).unique())
        handles = [
            Line2D([0], [0], marker="o", color="none", markerfacecolor=patient_colors[p],
                   markeredgecolor="white", markersize=7, label=p)
            for p in present
        ]
        fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.005),
                   ncol=min(6, max(1, len(handles))), frameon=False, fontsize=8)
        fig.subplots_adjust(bottom=0.07, top=0.95)
    else:
        fig.subplots_adjust(bottom=0.04, top=0.95)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_region_counts(
    combined: pd.DataFrame,
    scopes: list[str],
    out_path: Path,
    *,
    region_mode: str = "canonical",
) -> None:
    rows = []
    for scope in scopes:
        d = _scope_df(combined, scope, region_mode=region_mode)
        rows.append({
            "Scope": scope,
            "Selection Rule": region_mode,
            "Patients": int(d["Patient ID"].nunique()),
            "Neurons": int(len(d)),
            "Pre Significant": int(d["Pre-Stim Significant"].fillna(False).astype(bool).sum())
                if "Pre-Stim Significant" in d.columns else np.nan,
            "Post Significant": int(d["Post-Stim Significant"].fillna(False).astype(bool).sum())
                if "Post-Stim Significant" in d.columns else np.nan,
        })
    pd.DataFrame(rows).to_csv(out_path, index=False)


def generate_cross_patient_plots(
    outputs_root: str | Path,
    *,
    exclude_substrings: Iterable[str] = ("_box",),
    min_neurons: int = 1,
    min_patients: int = 1,
) -> Path:
    outputs_root = Path(outputs_root)
    cross_root = outputs_root / "cross_patient"
    neutral_dir = cross_root / "neutral"
    colored_dir = cross_root / "colored"
    neutral_dir.mkdir(parents=True, exist_ok=True)
    colored_dir.mkdir(parents=True, exist_ok=True)

    summary_paths = discover_summary_files(outputs_root, exclude_substrings)
    combined = build_combined_table(summary_paths)
    combined.to_csv(cross_root / "combined_neuron_summary.csv", index=False)

    patients = sorted(combined["Patient ID"].dropna().astype(str).unique())
    patient_colors = _load_or_make_patient_colors(cross_root, patients)

    atomic_regions = sorted(
        r for r in combined["Region Canonical"].dropna().astype(str).unique()
        if r != "UNKNOWN"
    )
    scopes = ["global"] + atomic_regions
    if "MTL" not in scopes:
        scopes.append("MTL")

    # Expanded/new regional analysis: canonicalized anatomical labels.
    write_region_counts(
        combined, scopes, cross_root / "region_counts.csv", region_mode="canonical"
    )

    # Poster replication audit: exactly the old strict bipolar-label grouping.
    write_region_counts(
        combined,
        ["global", *POSTER_SCOPES],
        cross_root / "poster_region_counts_strict.csv",
        region_mode="strict_raw",
    )

    plot_scopes = []
    for scope in scopes:
        d = _scope_df(combined, scope, region_mode="canonical")
        if len(d) >= min_neurons and d["Patient ID"].nunique() >= min_patients:
            plot_scopes.append(scope)

    make_poster_grid(
        combined,
        neutral_dir / "poster_HPC_MTL_FC.png",
        colored=False,
        patient_colors=patient_colors,
    )
    make_poster_grid(
        combined,
        colored_dir / "poster_HPC_MTL_FC.png",
        colored=True,
        patient_colors=patient_colors,
    )

    for scope in plot_scopes:
        safe = scope.replace("/", "-")
        make_scope_figure(
            combined,
            scope,
            neutral_dir / f"{safe}_post_pre_diff.png",
            colored=False,
            patient_colors=patient_colors,
        )
        make_scope_figure(
            combined,
            scope,
            colored_dir / f"{safe}_post_pre_diff.png",
            colored=True,
            patient_colors=patient_colors,
        )

    print(f"Cross-patient aggregation complete: {cross_root}")
    print(f"Patients: {len(patients)} | Neurons: {len(combined)}")
    print(f"Plotted scopes: {', '.join(plot_scopes)}")
    return cross_root


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate existing per-patient neuron summaries into cross-patient figures."
    )
    parser.add_argument(
        "--outputs-root",
        required=True,
        help="Folder containing P*/statistics/neuron_summary.csv patient outputs.",
    )
    parser.add_argument(
        "--exclude-substring",
        action="append",
        default=["_box"],
        help=(
            "Ignore output paths containing this substring. Can be repeated. "
            "Default: _box, to avoid double-counting old Box/non-Box duplicate outputs."
        ),
    )
    parser.add_argument("--min-neurons", type=int, default=1)
    parser.add_argument("--min-patients", type=int, default=1)
    args = parser.parse_args()

    generate_cross_patient_plots(
        args.outputs_root,
        exclude_substrings=args.exclude_substring,
        min_neurons=args.min_neurons,
        min_patients=args.min_patients,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
