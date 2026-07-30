from pathlib import Path

import pandas as pd
import pytest

from analysis.session_alignment_align1 import (
    align_one_neuron as align_session_one_neuron,
    align_spikes_to_movie_window,
    load_spike_csv,
)
from analysis.trial_alignment_align2 import (
    align_one_neuron as align_trial_one_neuron,
    align_spikes_to_trials,
)


def make_fake_spike_csv(tmp_path: Path) -> Path:
    """
    Create a realistic per-unit spike CSV like the preprocessing output.

    The file mirrors the current preprocessing schema:
    - units
    - s
    """
    spike_df = pd.DataFrame(
        {
            "units": [5, 5, 5, 5, 5, 5],
            "s": [9.5, 10.0, 10.5234, 11.2, 12.4999, 13.1],
        }
    )
    spike_path = tmp_path / "times_manual_GA1-RA2_unit_5.csv"
    spike_df.to_csv(spike_path, index=False)
    return spike_path


def make_fake_trial_table() -> pd.DataFrame:
    """
    Create a trial table close to the current refactored schema.

    These trial windows are movie-relative (Align 2 compares against
    movieAlignedTimeMs):
    - trial 1: 0-1000 ms
    - trial 2: 2000-3500 ms
    """
    return pd.DataFrame(
        {
            "experimentPhase": ["recog_task", "recog_task"],
            "trialNumber": [1, 2],
            "movieID": [1, 1],
            "clipID": [101, 102],
            "response": [2, 1],
            "clipStartTime": [0.0, 2.0],
            "clipEndTime": [1.0, 3.5],
            "frameOn": [300, 360],
            "frameOff": [330, 405],
            "clipStartTimeMs": [0, 2000],
            "clipEndTimeMs": [1000, 3500],
            "clipDurationMs": [1000, 1500],
            "clipDurationSec": [1.0, 1.5],
            "clipFrameRange": ["300-330", "360-405"],
            "clipTimeRangeMs": ["0-1000", "2000-3500"],
            "clipWindowId": ["1-0-1000", "1-2000-3500"],
            "isAccurate": [1, 0],
            "trialOrder": [1, 2],
            "plotOrder": [1, 2],
            "includeInPlots": [True, True],
        }
    )


def test_load_spike_csv_reads_expected_columns(tmp_path):
    spike_path = make_fake_spike_csv(tmp_path)

    df = load_spike_csv(spike_path)

    assert list(df.columns) == ["units", "spikeTimeRawS"]
    assert df["units"].tolist() == [5, 5, 5, 5, 5, 5]
    assert df["spikeTimeRawS"].tolist() == [9.5, 10.0, 10.5234, 11.2, 12.4999, 13.1]


def test_align_spikes_to_movie_window_filters_and_rezeros_times(tmp_path):
    spike_path = make_fake_spike_csv(tmp_path)
    spike_df = load_spike_csv(spike_path)

    aligned = align_spikes_to_movie_window(
        spike_df=spike_df,
        session_start_seconds=10.0,
        session_duration_seconds=2.0,
    )

    # Only spikes inside [10.0, 12.0] should remain.
    assert aligned["spikeTimeRawS"].tolist() == [10.0, 10.5234, 11.2]
    assert aligned["movieAlignedTimeS"].tolist() == pytest.approx([0.0, 0.5234, 1.2], abs=1e-9)
    assert aligned["movieAlignedTimeMs"].tolist() == pytest.approx([0.0, 523.4, 1200.0], abs=1e-9)


def test_align_spikes_to_trials_assigns_spikes_to_trial_windows(tmp_path):
    spike_path = make_fake_spike_csv(tmp_path)
    spike_df = load_spike_csv(spike_path)

    movie_aligned = align_spikes_to_movie_window(
        spike_df=spike_df,
        session_start_seconds=10.0,
        session_duration_seconds=4.0,
    )
    trial_table = make_fake_trial_table()

    trial_aligned = align_spikes_to_trials(
        movie_aligned_spikes=movie_aligned,
        trial_table=trial_table,
    )

    assert sorted(trial_aligned["trialOrder"].dropna().unique().tolist()) == [1, 2]

    first_trial_rows = trial_aligned[trial_aligned["trialOrder"] == 1]
    second_trial_rows = trial_aligned[trial_aligned["trialOrder"] == 2]

    assert len(first_trial_rows) == 2
    assert len(second_trial_rows) == 2

    # Spike at 10.0 s should belong to first trial with zero relative offset.
    assert first_trial_rows.iloc[0]["spikeTimeRelativeToClipStartMs"] == pytest.approx(0.0, abs=1e-9)


def test_align_one_neuron_writes_align1_and_align2_outputs(tmp_path):
    spike_path = make_fake_spike_csv(tmp_path)
    trial_table = make_fake_trial_table()

    align1_dir = tmp_path / "align_24"
    align2_dir = tmp_path / "align_24_trial"

    align1_path = align_session_one_neuron(
        spike_csv_path=spike_path,
        session_start_seconds=10.0,
        session_duration_seconds=4.0,
        align1_output_dir=align1_dir,
    )

    align2_path = align_trial_one_neuron(
        align1_csv_path=align1_path,
        trial_table=trial_table,
        align2_output_dir=align2_dir,
    )

    assert align1_path.exists()
    assert align2_path.exists()
    assert align1_path.name.startswith("align1_")
    assert align2_path.name.startswith("align2_")

    align1_df = pd.read_csv(align1_path)
    align2_df = pd.read_csv(align2_path)

    assert "movieAlignedTimeMs" in align1_df.columns
    assert "trialOrder" in align2_df.columns
    assert "spikeTimeRelativeToClipStartMs" in align2_df.columns