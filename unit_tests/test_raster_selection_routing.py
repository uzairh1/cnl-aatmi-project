from __future__ import annotations

from pathlib import Path

import pandas as pd

from plotting import rasters


def test_load_align1_csv_accepts_movie_aligned_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "align1_times_manual_unit_1.csv"
    pd.DataFrame(
        {
            "units": [1, 1, 1],
            "spikeTimeRawS": [10.1, 10.2, 10.3],
            "movieAlignedTimeS": [0.1, 0.2, 0.3],
            "movieAlignedTimeMs": [100.0, 200.0, 300.0],
        }
    ).to_csv(csv_path, index=False)

    df = rasters.load_align1_csv(csv_path)

    assert "movieAlignedTimeMs" in df.columns
    assert "movieAlignedTimeS" in df.columns
    assert df["movieAlignedTimeMs"].tolist() == [100.0, 200.0, 300.0]
    assert df["ms"].tolist() == [100.0, 200.0, 300.0]


def test_save_and_mirror_keeps_sig_and_nonsig_separate(tmp_path: Path) -> None:
    import matplotlib.pyplot as plt

    fig = plt.figure()
    out_path = tmp_path / "plots" / "rasters" / "all" / "demo.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rasters._save_and_mirror(fig, out_path, tmp_path / "plots" / "rasters", "HPC", "nonsig")
    assert (tmp_path / "plots" / "rasters" / "all" / "demo.png").exists()
    assert (tmp_path / "plots" / "rasters" / "nonsig" / "demo.png").exists()
    assert not (tmp_path / "plots" / "rasters" / "sig" / "demo.png").exists()


def test_plot_align1_folder_filters_to_summary_neurons(tmp_path: Path, monkeypatch) -> None:
    align1_dir = tmp_path / "align1"
    align1_dir.mkdir(parents=True)

    pd.DataFrame(
        {
            "units": [1, 1, 1, 1],
            "spikeTimeRawS": [10.1, 10.2, 10.3, 10.4],
            "movieAlignedTimeS": [0.1, 0.2, 0.3, 0.4],
            "movieAlignedTimeMs": [100.0, 200.0, 300.0, 400.0],
        }
    ).to_csv(align1_dir / "align1_neuron_a.csv", index=False)

    pd.DataFrame(
        {
            "units": [1, 1, 1, 1],
            "spikeTimeRawS": [11.1, 11.2, 11.3, 11.4],
            "movieAlignedTimeS": [0.5, 0.6, 0.7, 0.8],
            "movieAlignedTimeMs": [500.0, 600.0, 700.0, 800.0],
        }
    ).to_csv(align1_dir / "align1_neuron_b.csv", index=False)

    clips_table = tmp_path / "clips.csv"
    pd.DataFrame(
        {
            "clipID": [1],
            "ms start": [0.0],
            "ms end": [500.0],
            "Accurate": [1],
            "Plot Y-Axis": [1],
        }
    ).to_csv(clips_table, index=False)

    summary_csv = tmp_path / "summary.csv"
    pd.DataFrame(
        {
            "Neuron Name": ["neuron_a"],
            "Post-Stim Mean Rate (Hz)": [1.0],
            "Pre-Stim Significant": [False],
            "Post-Stim Significant": [False],
            "Localization - Bipolar": ["ERC - entorhinal cortex"],
        }
    ).to_csv(summary_csv, index=False)

    monkeypatch.setattr(
        rasters,
        "infer_neuron_localization",
        lambda neuron_name, loc_df: ("REC3", "Region", "ERC"),
    )

    out_dir = tmp_path / "plots" / "rasters"
    outputs = rasters.plot_align1_folder(
        align1_dir=align1_dir,
        clips_table=clips_table,
        output_dir=out_dir,
        patient_id="570",
        localization_file="",
        summary_csv=summary_csv,
        output_tag="",
        window_start_ms=-3000,
        window_end_ms=5000,
        split_by_accuracy=True,
        show_clip_end_marker=True,
        smooth_type="triangle",
        min_rate_hz=0.25,
    )

    assert len(outputs) == 1
    assert (out_dir / "all" / "P570_REC3_neuron_a.png").exists()
    assert not (out_dir / "all" / "P570_REC3_neuron_b.png").exists()


def test_plot_neuron_from_align1_skips_below_rate_threshold(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "align1_times_manual_unit_1.csv"
    pd.DataFrame(
        {
            "units": [1, 1, 1, 1],
            "spikeTimeRawS": [10.1, 10.2, 10.3, 10.4],
            "movieAlignedTimeS": [0.1, 0.2, 0.3, 0.4],
            "movieAlignedTimeMs": [100.0, 200.0, 300.0, 400.0],
        }
    ).to_csv(csv_path, index=False)

    clips_df = pd.DataFrame(
        {
            "clipID": [1],
            "ms start": [0.0],
            "ms end": [500.0],
            "Accurate": [1],
            "Plot Y-Axis": [1],
        }
    )

    monkeypatch.setattr(
        rasters,
        "infer_neuron_localization",
        lambda neuron_name, loc_df: ("REC3", "Region", "ERC"),
    )

    # Summary row below threshold should cause skip.
    result = rasters.plot_neuron_from_align1(
        align1_csv_path=csv_path,
        clips_df=clips_df,
        output_dir=tmp_path / "plots" / "rasters",
        patient_id="570",
        loc_df=pd.DataFrame(),
        summary_row={"Post-Stim Mean Rate (Hz)": 0.1, "Pre-Stim Significant": False, "Post-Stim Significant": False},
        output_tag="",
        window_start_ms=-3000,
        window_end_ms=5000,
        split_by_accuracy=True,
        show_clip_end_marker=True,
        smooth_type="triangle",
        min_rate_hz=0.25,
    )
    assert result is None