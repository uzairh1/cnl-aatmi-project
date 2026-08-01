"""Raster and PSTH plotting for movie/session-aligned spikes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from scipy.stats import gaussian_kde

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.statistics import load_clip_table
from data_io.localization import infer_neuron_localization, load_localization_map
from running.config import BIPOLAR_REGIONS, TARGET_FOLDERS


RASTER_FIGSIZE: Tuple[float, float] = (12, 8)
RASTER_DPI = 200
LINE_LENGTH = 0.8
LINE_WIDTH = 0.6
PSTH_BIN_MS = 100
PSTH_LINE_WIDTH = 2.0
COLOR_ALL = "black"
COLOR_CORRECT = "green"
COLOR_INCORRECT = "red"


def load_align1_csv(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "ms" not in df.columns:
        raise ValueError(f"{csv_path} missing ms column")
    df = df.copy()
    df["ms"] = pd.to_numeric(df["ms"], errors="coerce")
    return df.dropna(subset=["ms"]).copy()


def load_summary_csv(summary_csv: str | Path) -> pd.DataFrame:
    df = pd.read_csv(summary_csv)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def load_summary_map(summary_csv: str | Path) -> dict:
    if not summary_csv:
        return {}
    df = load_summary_csv(summary_csv)
    if "Neuron Name" not in df.columns:
        return {}
    return {str(row["Neuron Name"]): row.to_dict() for _, row in df.iterrows()}


def build_clip_rows_for_window(
    spikes_ms: np.ndarray,
    clips_df: pd.DataFrame,
    window_start_ms: int,
    window_end_ms: int,
) -> List[Dict[str, object]]:
    plot_rows: List[Dict[str, object]] = []
    for clip_index, clip_row in clips_df.reset_index(drop=True).iterrows():
        start_ms = clip_row.get("ms start")
        end_ms = clip_row.get("ms end")
        if pd.isna(start_ms) or pd.isna(end_ms):
            continue
        start_ms = float(start_ms)
        end_ms = float(end_ms)
        abs_window_start = start_ms + window_start_ms
        abs_window_end = start_ms + window_end_ms
        in_window = spikes_ms[(spikes_ms >= abs_window_start) & (spikes_ms <= abs_window_end)]
        aligned_spikes = (in_window - start_ms).tolist()
        plot_rows.append(
            {
                "clip_index": clip_index + 1,
                "clipID": clip_row.get("clipID", clip_index + 1),
                "accurate": int(clip_row.get("Accurate", 0)) if pd.notna(clip_row.get("Accurate")) else 0,
                "clip_end_marker_ms": end_ms - start_ms,
                "aligned_spikes_ms": aligned_spikes,
                "plot_y_axis": int(clip_row.get("Plot Y-Axis", clip_index + 1)),
            }
        )
    return plot_rows


def compute_psth_hz(clip_rows: List[List[float]], x_min: int, x_max: int, bin_ms: int) -> Tuple[np.ndarray, np.ndarray]:
    edges = np.arange(x_min, x_max + bin_ms, bin_ms)
    if len(edges) < 2:
        edges = np.array([x_min, x_max], dtype=float)
    centers = edges[:-1] + (np.diff(edges) / 2.0)
    n_trials = len(clip_rows)
    if n_trials == 0:
        return centers, np.zeros(len(centers), dtype=float)
    counts_per_trial = np.zeros((n_trials, len(edges) - 1), dtype=float)
    for i, row in enumerate(clip_rows):
        if len(row) == 0:
            continue
        counts, _ = np.histogram(np.asarray(row, dtype=float), bins=edges)
        counts_per_trial[i, :] = counts
    return centers, counts_per_trial.mean(axis=0) / (bin_ms / 1000.0)


def compute_smoothed_psth_hz(
    clip_rows: List[List[float]], x_min: int, x_max: int, bin_ms: int = PSTH_BIN_MS, smooth_type: str = "none"
) -> Tuple[np.ndarray, np.ndarray]:
    has_spikes = any(len(r) > 0 for r in clip_rows)
    all_spikes = np.concatenate([r for r in clip_rows if len(r) > 0]) if has_spikes else np.array([])
    n_trials = len(clip_rows)
    if len(all_spikes) < 2 or n_trials == 0:
        edges = np.arange(x_min, x_max + bin_ms, bin_ms)
        if len(edges) < 2:
            edges = np.array([x_min, x_max], dtype=float)
        centers = edges[:-1] + (np.diff(edges) / 2.0)
        return centers, np.zeros(len(centers), dtype=float)

    if smooth_type == "gaussian_kde":
        centers = np.linspace(x_min, x_max, max(200, int((x_max - x_min) / 10)))
        try:
            kde = gaussian_kde(all_spikes, bw_method="scott")
            return centers, kde.evaluate(centers) * 1000.0 * (len(all_spikes) / n_trials)
        except np.linalg.LinAlgError:
            pass

    if smooth_type == "bin_resize_trial_1":
        small_bin = 50
        edges = np.arange(x_min, x_max + small_bin, small_bin)
        if len(edges) < 2:
            edges = np.array([x_min, x_max], dtype=float)
        centers = edges[:-1] + (np.diff(edges) / 2.0)
        counts, _ = np.histogram(all_spikes, bins=edges)
        raw_hz = (counts / n_trials) / (small_bin / 1000.0)
        kernel = np.exp(-0.5 * (np.arange(-2, 3) / 1.5) ** 2)
        kernel /= kernel.sum()
        return centers, np.convolve(raw_hz, kernel, mode="same")

    small_bin = 25
    edges = np.arange(x_min, x_max + small_bin, small_bin)
    if len(edges) < 2:
        edges = np.array([x_min, x_max], dtype=float)
    centers = edges[:-1] + (np.diff(edges) / 2.0)
    counts, _ = np.histogram(all_spikes, bins=edges)
    raw_hz = (counts / n_trials) / (small_bin / 1000.0)
    triangle = np.concatenate([np.arange(1, 7), np.arange(5, 0, -1)])
    triangle = triangle / triangle.sum()
    return centers, np.convolve(raw_hz, triangle, mode="same")


def sort_rows_accuracy_top_bottom(plot_rows: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], int]:
    correct_rows = [row for row in plot_rows if row["accurate"] == 1]
    incorrect_rows = [row for row in plot_rows if row["accurate"] == 0]
    return correct_rows + incorrect_rows, len(correct_rows)


def _region_abbr_from_label(label: str) -> str:
    if not label or " - " not in label:
        return "UNKNOWN"
    return str(label).split(" - ", 1)[0].strip().upper() or "UNKNOWN"


def _make_output_dirs(base_dir: Path) -> dict:
    d = {
        "all": base_dir / "all",
        "sig": base_dir / "sig",
        "nonsig": base_dir / "nonsig",
        "by_region": base_dir / "by_region",
    }
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def _stem_for_neuron(patient_id: str, output_tag: str, clean_loc: str, neuron_name: str) -> str:
    if output_tag:
        return f"P{patient_id}_{output_tag}_{clean_loc}_{neuron_name}"
    return f"P{patient_id}_{clean_loc}_{neuron_name}"


def _save_and_mirror(fig: plt.Figure, final_file_path: Path, base_dir: Path, region_abbr: str, sig_status: str) -> Path:
    dirs = _make_output_dirs(base_dir)
    fig.savefig(final_file_path, dpi=RASTER_DPI, bbox_inches="tight")
    data = final_file_path.read_bytes()

    (dirs["all"] / final_file_path.name).write_bytes(data)
    if "sig" in sig_status:
        (dirs["sig"] / final_file_path.name).write_bytes(data)
    if "nonsig" in sig_status:
        (dirs["nonsig"] / final_file_path.name).write_bytes(data)

    if region_abbr and region_abbr in TARGET_FOLDERS:
        reg = dirs["by_region"] / region_abbr
        reg.mkdir(parents=True, exist_ok=True)
        (reg / final_file_path.name).write_bytes(data)

    plt.close(fig)
    return final_file_path


def _has_any_spikes(plot_rows: List[Dict[str, object]]) -> bool:
    return any(len(row["aligned_spikes_ms"]) > 0 for row in plot_rows)


def _plot_raster_with_optional_split_and_psth(
    plot_rows: List[Dict[str, object]],
    out_path: Path,
    patient_id: str,
    neuron_name: str,
    title_suffix: str,
    x_min: int,
    x_max: int,
    split_by_accuracy: bool,
    show_clip_end_marker: bool,
    ttest_label: str = "",
    loc_df: pd.DataFrame = pd.DataFrame(),
    output_tag: str = "",
    sig_status_str: str = "nonsig",
    smooth_type: str = "none",
) -> Optional[Path]:
    if len(plot_rows) == 0:
        return None

    if split_by_accuracy:
        plot_rows, n_correct = sort_rows_accuracy_top_bottom(plot_rows)
        raster_rows = [row["aligned_spikes_ms"] for row in plot_rows]
        raster_colors = [COLOR_CORRECT if row["accurate"] == 1 else COLOR_INCORRECT for row in plot_rows]
    else:
        n_correct = 0
        raster_rows = [row["aligned_spikes_ms"] for row in plot_rows]
        raster_colors = COLOR_ALL

    if not any(len(row) > 0 for row in raster_rows):
        return None

    y_labels = [str(row.get("plot_y_axis", i + 1)) for i, row in enumerate(plot_rows)]
    electrode_code, full_location, region_abbr = infer_neuron_localization(neuron_name, loc_df)
    clean_loc = str(electrode_code).replace(" ", "_")
    bipolar_desc = BIPOLAR_REGIONS.get(region_abbr, "UNKNOWN")
    loc_bipolar_str = f"{region_abbr} - {bipolar_desc}"
    stem = _stem_for_neuron(patient_id, output_tag, clean_loc, neuron_name)
    final_file_path = out_path.parent.parent / "all" / f"{stem}.png"

    fig = plt.figure(figsize=RASTER_FIGSIZE)
    gs = GridSpec(2, 1, height_ratios=[4.6, 1.4], hspace=0.08)
    ax_raster = fig.add_subplot(gs[0])
    ax_psth = fig.add_subplot(gs[1], sharex=ax_raster)

    ax_raster.eventplot(raster_rows, colors=raster_colors, linelengths=LINE_LENGTH, linewidths=LINE_WIDTH, zorder=3)

    if show_clip_end_marker:
        for row_idx, row in enumerate(plot_rows):
            clip_end_x = float(row.get("clip_end_marker_ms", 0))
            shade_end = min(clip_end_x, x_max)
            if shade_end > 0:
                ax_raster.barh(y=row_idx, width=shade_end, left=0, height=1.0, color="lightgreen", alpha=0.3, zorder=0, edgecolor="none")

    if split_by_accuracy and 0 < n_correct < len(plot_rows):
        ax_raster.axhline(n_correct - 0.5, color="0.5", linestyle="--", linewidth=1, zorder=4)

    ax_raster.axvline(0, color="0.5", linestyle="--", linewidth=1, zorder=4)
    ax_psth.axvline(0, color="0.5", linestyle="--", linewidth=1)

    title_lines = [
        f"Patient {patient_id} | {full_location} ({electrode_code}) | Region: {loc_bipolar_str} | Neuron {neuron_name}",
        title_suffix,
    ]
    if ttest_label:
        title_lines.append(ttest_label)
    ax_raster.set_title(chr(10).join(title_lines), fontsize=14)
    ax_raster.set_ylabel("Clip Plot Y-Axis", fontsize=12)
    ax_raster.set_xlim(x_min, x_max)

    n_rows = len(plot_rows)
    tick_positions = list(range(n_rows)) if n_rows <= 40 else list(range(0, n_rows, max(1, n_rows // 20)))
    ax_raster.set_yticks(tick_positions)
    ax_raster.set_yticklabels([y_labels[i] for i in tick_positions])
    ax_raster.grid(axis="x", linestyle=":", alpha=0.4)

    if split_by_accuracy:
        correct_rows = [row["aligned_spikes_ms"] for row in plot_rows if row["accurate"] == 1]
        incorrect_rows = [row["aligned_spikes_ms"] for row in plot_rows if row["accurate"] == 0]
        if len(correct_rows) > 0:
            x_c, y_c = (compute_psth_hz(correct_rows, x_min, x_max, PSTH_BIN_MS) if smooth_type == "none"
                        else compute_smoothed_psth_hz(correct_rows, x_min, x_max, PSTH_BIN_MS, smooth_type))
            ax_psth.plot(x_c, y_c, linewidth=PSTH_LINE_WIDTH, color=COLOR_CORRECT, label="Correct (Green)")
        if len(incorrect_rows) > 0:
            x_i, y_i = (compute_psth_hz(incorrect_rows, x_min, x_max, PSTH_BIN_MS) if smooth_type == "none"
                        else compute_smoothed_psth_hz(incorrect_rows, x_min, x_max, PSTH_BIN_MS, smooth_type))
            ax_psth.plot(x_i, y_i, linewidth=PSTH_LINE_WIDTH, color=COLOR_INCORRECT, label="Incorrect (Red)")
        ax_psth.legend(frameon=False, fontsize=10, loc="upper right")
    else:
        x_all, y_all = (compute_psth_hz(raster_rows, x_min, x_max, PSTH_BIN_MS) if smooth_type == "none"
                        else compute_smoothed_psth_hz(raster_rows, x_min, x_max, PSTH_BIN_MS, smooth_type))
        ax_psth.plot(x_all, y_all, linewidth=PSTH_LINE_WIDTH, color=COLOR_ALL)

    ax_psth.set_xlabel("Time from clip start (ms)", fontsize=12)
    ax_psth.set_ylabel("Hz", fontsize=12)
    ax_psth.grid(axis="x", linestyle=":", alpha=0.4)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.09, hspace=0.08)

    if not _has_any_spikes(plot_rows):
        plt.close(fig)
        return None

    return _save_and_mirror(fig, final_file_path, out_path.parent.parent, region_abbr, sig_status_str)


def plot_neuron_from_align1(
    align1_csv_path: str | Path,
    clips_df: pd.DataFrame,
    output_dir: str | Path,
    patient_id: str,
    loc_df: pd.DataFrame = pd.DataFrame(),
    summary_row: Optional[dict] = None,
    output_tag: str = "",
    window_start_ms: int = -3000,
    window_end_ms: int = 5000,
    split_by_accuracy: bool = True,
    show_clip_end_marker: bool = True,
    smooth_type: str = "triangle",
    min_rate_hz: float = 0.25,
) -> Optional[Path]:
    align1_csv_path = Path(align1_csv_path)
    output_dir = Path(output_dir)
    neuron_name = align1_csv_path.name.replace("align1_", "").replace(".csv", "")
    try:
        neuron_df = load_align1_csv(align1_csv_path)
        spikes_ms = pd.to_numeric(neuron_df["ms"], errors="coerce").dropna().to_numpy()
    except Exception:
        return None

    if len(spikes_ms) == 0:
        return None

    if summary_row is not None:
        post_rate_hz = summary_row.get("Post-Stim Mean Rate (Hz)")
        if post_rate_hz is not None and pd.notna(post_rate_hz) and float(post_rate_hz) < min_rate_hz:
            return None

    plot_rows = build_clip_rows_for_window(spikes_ms, clips_df, window_start_ms, window_end_ms)

    sig_status = "nonsig"
    ttest_label = ""
    if summary_row is not None:
        pre_sig = bool(summary_row.get("Pre-Stim Significant", False))
        post_sig = bool(summary_row.get("Post-Stim Significant", False))
        if pre_sig or post_sig:
            sig_status = "sig"
            if pre_sig and not post_sig:
                sig_status = "sig_pre"
            elif post_sig and not pre_sig:
                sig_status = "sig_post"
            else:
                sig_status = "sig_both"
        pre_t = summary_row.get("Pre-Stim T-Score")
        pre_p = summary_row.get("Pre-Stim P-Value")
        post_t = summary_row.get("Post-Stim T-Score")
        post_p = summary_row.get("Post-Stim P-Value")
        ttest_label = (
            f"PRE T: {f'{pre_t:.3f}' if pre_t is not None and pd.notna(pre_t) else 'N/A'} "
            f"(p={f'{pre_p:.3f}' if pre_p is not None and pd.notna(pre_p) else 'N/A'}) | "
            f"POST T: {f'{post_t:.3f}' if post_t is not None and pd.notna(post_t) else 'N/A'} "
            f"(p={f'{post_p:.3f}' if post_p is not None and pd.notna(post_p) else 'N/A'})"
        )

    title_suffix = ""
    if summary_row is not None and summary_row.get("Post-Stim Mean Rate (Hz)") is not None:
        title_suffix = f"Average Firing Rate: {float(summary_row['Post-Stim Mean Rate (Hz)']):.2f} Hz"

    out_path = output_dir / "all" / f"{_stem_for_neuron(patient_id, output_tag, infer_neuron_localization(neuron_name, loc_df)[0].replace(' ', '_'), neuron_name)}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return _plot_raster_with_optional_split_and_psth(
        plot_rows=plot_rows,
        out_path=out_path,
        patient_id=patient_id,
        neuron_name=neuron_name,
        title_suffix=title_suffix,
        x_min=window_start_ms,
        x_max=window_end_ms,
        split_by_accuracy=split_by_accuracy,
        show_clip_end_marker=show_clip_end_marker,
        ttest_label=ttest_label,
        loc_df=loc_df,
        output_tag=output_tag,
        sig_status_str=sig_status,
        smooth_type=smooth_type,
    )


def _write_companion_csvs(output_dir: Path, rows: list[dict]) -> None:
    if not rows:
        return
    df = pd.DataFrame(rows)
    all_dir = output_dir / "all"
    sig_dir = output_dir / "sig"
    nonsig_dir = output_dir / "nonsig"
    by_region_dir = output_dir / "by_region"
    all_dir.mkdir(parents=True, exist_ok=True)
    sig_dir.mkdir(parents=True, exist_ok=True)
    nonsig_dir.mkdir(parents=True, exist_ok=True)
    by_region_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(all_dir / "T_score_sheet.csv", index=False)
    if "Sig Status" in df.columns:
        df[df["Sig Status"].str.contains("sig", na=False)].to_csv(sig_dir / "T_score_sheet.csv", index=False)
        df[df["Sig Status"] == "nonsig"].to_csv(nonsig_dir / "T_score_sheet.csv", index=False)
    else:
        df.to_csv(sig_dir / "T_score_sheet.csv", index=False)
        df.to_csv(nonsig_dir / "T_score_sheet.csv", index=False)

    if "Region Abbr" in df.columns:
        for region_abbr, sub in df.groupby("Region Abbr"):
            reg = by_region_dir / str(region_abbr)
            reg.mkdir(parents=True, exist_ok=True)
            sub.to_csv(reg / "T_score_sheet.csv", index=False)


def plot_align1_folder(
    align1_dir: str | Path,
    clips_table: str | Path,
    output_dir: str | Path,
    patient_id: str,
    localization_file: str = "",
    summary_csv: str | Path = "",
    output_tag: str = "",
    window_start_ms: int = -3000,
    window_end_ms: int = 5000,
    split_by_accuracy: bool = True,
    show_clip_end_marker: bool = True,
    smooth_type: str = "triangle",
    min_rate_hz: float = 0.25,
) -> list[Path]:
    align1_dir = Path(align1_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clips_df = load_clip_table(clips_table)
    loc_df = load_localization_map(localization_file) if localization_file else pd.DataFrame()
    summary_map = load_summary_map(summary_csv) if summary_csv else {}

    outputs: list[Path] = []
    rows: list[dict] = []
    for align1_csv_path in sorted(align1_dir.glob("align1_*.csv")):
        neuron_name = align1_csv_path.name.replace("align1_", "").replace(".csv", "")
        summary_row = summary_map.get(neuron_name)
        out_path = plot_neuron_from_align1(
            align1_csv_path=align1_csv_path,
            clips_df=clips_df,
            output_dir=output_dir,
            patient_id=patient_id,
            loc_df=loc_df,
            summary_row=summary_row,
            output_tag=output_tag,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            split_by_accuracy=split_by_accuracy,
            show_clip_end_marker=show_clip_end_marker,
            smooth_type=smooth_type,
            min_rate_hz=min_rate_hz,
        )
        if out_path is not None:
            outputs.append(out_path)

        if summary_row is not None:
            row = dict(summary_row)
            region_label = row.get("Localization - Bipolar", "")
            region_abbr = _region_abbr_from_label(region_label) if region_label else "UNKNOWN"
            row["Region Abbr"] = region_abbr
            row["Sig Status"] = "sig" if bool(row.get("Pre-Stim Significant", False)) or bool(row.get("Post-Stim Significant", False)) else "nonsig"
            row["Raster Path"] = str(out_path) if out_path is not None else ""
            rows.append(row)

    _write_companion_csvs(output_dir, rows)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Create raster/PSTH plots from Align 1 CSVs.")
    parser.add_argument("--align1-dir", required=True)
    parser.add_argument("--clips-table", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--patient-id", required=True)
    parser.add_argument("--localization-file", default="")
    parser.add_argument("--summary-csv", default="")
    parser.add_argument("--output-tag", default="")
    parser.add_argument("--window-start-ms", type=int, default=-3000)
    parser.add_argument("--window-end-ms", type=int, default=5000)
    parser.add_argument("--no-split-by-accuracy", action="store_true")
    parser.add_argument("--no-clip-end-marker", action="store_true")
    parser.add_argument("--smooth-type", default="triangle", choices=["none", "triangle", "gaussian_kde", "bin_resize_trial_1"])
    parser.add_argument("--min-rate-hz", type=float, default=0.25)
    args = parser.parse_args()

    outputs = plot_align1_folder(
        align1_dir=args.align1_dir,
        clips_table=args.clips_table,
        output_dir=args.output_dir,
        patient_id=args.patient_id,
        localization_file=args.localization_file,
        summary_csv=args.summary_csv,
        output_tag=args.output_tag,
        window_start_ms=args.window_start_ms,
        window_end_ms=args.window_end_ms,
        split_by_accuracy=not args.no_split_by_accuracy,
        show_clip_end_marker=not args.no_clip_end_marker,
        smooth_type=args.smooth_type,
        min_rate_hz=args.min_rate_hz,
    )
    print(f"Wrote {len(outputs)} raster plots to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())