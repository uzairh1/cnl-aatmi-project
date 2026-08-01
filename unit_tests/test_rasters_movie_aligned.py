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


def test_plot_neuron_from_align1_writes_png_for_movie_aligned_schema(
    tmp_path: Path, monkeypatch
) -> None:
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

    out_dir = tmp_path / "plots" / "rasters"
    result = rasters.plot_neuron_from_align1(
        align1_csv_path=csv_path,
        clips_df=clips_df,
        output_dir=out_dir,
        patient_id="570",
        loc_df=pd.DataFrame(),
        summary_row=None,
        output_tag="",
        window_start_ms=-3000,
        window_end_ms=5000,
        split_by_accuracy=True,
        show_clip_end_marker=True,
        smooth_type="triangle",
        min_rate_hz=0.25,
    )

    assert result is not None
    assert result.exists()
    assert result.parent.name == "all"