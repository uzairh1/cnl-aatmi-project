import pandas as pd
import pytest

from data_io.ttl_table_parser import build_trial_table


def make_fake_ttl_like_real_data() -> pd.DataFrame:
    """
    Create a synthetic TTL table that mirrors the structure of the sample file.

    Real sample characteristics we mimic:
    - 159 total rows
    - 150 recog_task rows
    - 75 recog_task rows with movieID == 1
    - 75 recog_task rows with movieID == 2
    - a handful of non-recognition rows
    - the same key TTL columns used by the parser
    """
    rows = []
    trial_number = 1

    def add_row(
        experiment_phase: str,
        movie_id: int,
        clip_id: int,
        response: int,
        clip_start_s: float,
        clip_end_s: float,
    ) -> None:
        nonlocal trial_number

        frame_on = int(round(clip_start_s * 29.97))
        frame_off = int(round(clip_end_s * 29.97))

        rows.append(
            {
                "experimentPhase": experiment_phase,
                "trialNumber": trial_number,
                "movieID": movie_id,
                "clipID": clip_id,
                "response": response,
                "reactionTimePTB": 1.234 + trial_number * 0.01,
                "trialStartTimePTB": clip_start_s - 0.25,
                "trialEndTimePTB": clip_end_s + 0.25,
                "clipStartTime": clip_start_s,
                "clipEndTime": clip_end_s,
                "frameOn": frame_on,
                "frameOff": frame_off,
                "startTag": f"start_{trial_number}",
                "cueEndTag": f"cue_{trial_number}",
                "endTag": f"end_{trial_number}",
                "startTimeUnixSec": 1700000000.0 + trial_number,
                "cueEndTimeUnixSec": 1700000000.5 + trial_number,
                "endTimeUnixSec": 1700000001.0 + trial_number,
                "startTimeMat": 1000.0 + trial_number,
                "cueEndTimeMat": 1000.5 + trial_number,
                "endTimeMat": 1001.0 + trial_number,
                "trialNumberMat": trial_number + 1000,
            }
        )
        trial_number += 1

    # 150 recognition trials: 75 movieID 1, 75 movieID 2.
    for i in range(75):
        add_row(
            experiment_phase="recog_task",
            movie_id=1,
            clip_id=1000 + i,
            response=2 if i % 3 != 0 else 1,  # mix of accurate/inaccurate
            clip_start_s=10.0 + i * 3.5,
            clip_end_s=12.0 + i * 3.5,
        )

    for i in range(75):
        add_row(
            experiment_phase="recog_task",
            movie_id=2,
            clip_id=2000 + i,
            response=2 if i % 4 != 0 else 1,
            clip_start_s=300.0 + i * 3.5,
            clip_end_s=302.5 + i * 3.5,
        )

    # Non-recognition rows seen in the real sample.
    add_row("cued_recall", 1, 9001, 2, 600.0, 603.0)
    add_row("cued_recall", 1, 9002, 1, 604.0, 607.0)
    add_row("cued_recall", 1, 9003, 2, 608.0, 611.0)
    add_row("cued_recall", 1, 9004, 1, 612.0, 615.0)
    add_row("cued_recall", 1, 9005, 2, 616.0, 619.0)
    add_row("cued_recall", 1, 9006, 1, 620.0, 623.0)

    add_row("spontaneous", 1, 9100, 2, 700.0, 701.0)
    add_row("free_recall", 1, 9200, 1, 702.0, 703.0)
    add_row("movie_watch", 1, 9300, 2, 0.0, 3600.0)

    return pd.DataFrame(rows)


def test_build_trial_table_filters_like_real_data(tmp_path):
    ttl_df = make_fake_ttl_like_real_data()
    ttl_path = tmp_path / "TTL_table.csv"
    ttl_df.to_csv(ttl_path, index=False)

    out_path = tmp_path / "trial_table.csv"
    table, written_path = build_trial_table(
        ttl_csv=ttl_path,
        output_csv=out_path,
        phase="recog_task",
        movie_id=1,
    )

    assert written_path == out_path
    assert out_path.exists()

    # Real sample behavior: keep 75 movieID==1 recog_task rows.
    assert len(table) == 75
    assert set(table["experimentPhase"].unique()) == {"recog_task"}
    assert set(table["movieID"].unique()) == {1}

    # Raw metadata preserved.
    assert "frameOn" in table.columns
    assert "frameOff" in table.columns
    assert "clipStartTime" in table.columns
    assert "clipEndTime" in table.columns

    # Derived columns present.
    for col in [
        "clipStartTimeMs",
        "clipEndTimeMs",
        "clipDurationMs",
        "clipDurationSec",
        "clipTimeRangeMs",
        "clipWindowId",
        "isAccurate",
        "trialOrder",
        "plotOrder",
        "includeInPlots",
    ]:
        assert col in table.columns

    # Spot-check timing conversion.
    first = table.iloc[0]
    assert first["clipStartTimeMs"] == int(round(first["clipStartTime"] * 1000.0))
    assert first["clipEndTimeMs"] == int(round(first["clipEndTime"] * 1000.0))
    assert first["clipDurationMs"] == first["clipEndTimeMs"] - first["clipStartTimeMs"]
    assert first["clipDurationSec"] == pytest.approx(first["clipEndTime"] - first["clipStartTime"])

    # response == 2 should become isAccurate == 1.
    expected_first_accuracy = 1 if first["response"] == 2 else 0
    assert first["isAccurate"] == expected_first_accuracy

    # Plot order should be a 1..75 permutation.
    assert sorted(table["trialOrder"].tolist()) == list(range(1, 76))
    assert sorted(table["plotOrder"].tolist()) == list(range(1, 76))

    # All rows default to inclusion.
    assert table["includeInPlots"].dtype == bool
    assert table["includeInPlots"].all()


def test_build_trial_table_can_keep_all_recog_trials(tmp_path):
    ttl_df = make_fake_ttl_like_real_data()
    ttl_path = tmp_path / "TTL_table.csv"
    ttl_df.to_csv(ttl_path, index=False)

    out_path = tmp_path / "trial_table_all_movies.csv"
    table, _ = build_trial_table(
        ttl_csv=ttl_path,
        output_csv=out_path,
        phase="recog_task",
        movie_id=None,
    )

    # Real sample behavior: 150 recognition rows total.
    assert len(table) == 150
    assert set(table["movieID"].unique()) == {1, 2}
    assert set(table["experimentPhase"].unique()) == {"recog_task"}

    # The derived trial identifier should encode the time window.
    assert table["clipWindowId"].str.contains(r"^\d+-\d+-\d+$").all()


def test_restore_plot_preferences_from_previous_table(tmp_path):
    ttl_df = make_fake_ttl_like_real_data()
    ttl_path = tmp_path / "TTL_table.csv"
    ttl_df.to_csv(ttl_path, index=False)

    base_out = tmp_path / "base_trial_table.csv"
    table, _ = build_trial_table(
        ttl_csv=ttl_path,
        output_csv=base_out,
        phase="recog_task",
        movie_id=1,
    )

    # Mark the first two clip windows as excluded.
    prev = table.copy()
    prev.loc[prev.index[:2], "includeInPlots"] = False
    prev_path = tmp_path / "previous_trial_table.csv"
    prev.to_csv(prev_path, index=False)

    rerun_out = tmp_path / "rerun_trial_table.csv"
    rerun_table, _ = build_trial_table(
        ttl_csv=ttl_path,
        output_csv=rerun_out,
        phase="recog_task",
        movie_id=1,
        previous_table=prev_path,
    )

    assert not bool(rerun_table.loc[rerun_table.index[0], "includeInPlots"])
    assert not bool(rerun_table.loc[rerun_table.index[1], "includeInPlots"])
    assert bool(rerun_table.loc[rerun_table.index[2], "includeInPlots"])