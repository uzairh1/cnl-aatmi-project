from pathlib import Path
import pandas as pd

from analysis.statistics import (
    load_clip_table,
    compute_rate_hz_in_window,
    compute_correct_vs_wrong_ttest,
    build_neuron_summary_row,
    analyze_align1_folder,
    population_chisq_vs_chance,
    population_chisq_vs_5050,
    population_one_sample_ttest,
)

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_clip_table_normalization():
    clips = load_clip_table(FIXTURES / 'data_io' / 'trial_table.csv')
    assert 'ms start' in clips.columns
    assert 'ms end' in clips.columns
    assert 'Accurate' in clips.columns


def test_rate_and_ttest_helpers():
    align1 = pd.read_csv(FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv')
    spikes_ms = align1['movieAlignedTimeMs'].to_numpy()
    clips = load_clip_table(FIXTURES / 'data_io' / 'trial_table.csv')

    rate = compute_rate_hz_in_window(spikes_ms, clips, 0, 1000)
    assert rate is not None
    assert rate >= 0

    ttest = compute_correct_vs_wrong_ttest(spikes_ms, clips, -1000, 0)
    assert 'ok' in ttest and 'p_value' in ttest and 't_stat' in ttest


def test_build_neuron_summary_row():
    align1 = pd.read_csv(FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv')
    clips = load_clip_table(FIXTURES / 'data_io' / 'trial_table.csv')
    row = build_neuron_summary_row(
        align1_df=align1,
        clips_df=clips,
        neuron_name='times_manual_GA1-REC3_unit_1',
        patient_id='570',
    )
    assert row is not None
    assert row['Patient'] == 'P570'
    assert 'Pre-Stim T-Score' in row
    assert 'Post-Stim T-Score' in row


def test_analyze_align1_folder(tmp_path):
    align1_dir = tmp_path / 'align1'
    align1_dir.mkdir()
    src = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    (align1_dir / src.name).write_text(src.read_text())
    clips = load_clip_table(FIXTURES / 'data_io' / 'trial_table.csv')
    out_csv = tmp_path / 'summary.csv'
    df = analyze_align1_folder(align1_dir, clips, '570', out_csv)
    assert out_csv.exists()
    assert df.shape[0] == 1


def test_population_helpers():
    df = pd.read_csv(FIXTURES / 'analysis' / 'neuron_summary.csv')
    out1 = population_chisq_vs_chance(df, 'Post-Stim T-Score', thresh=1.96, sig_col='Post-Stim Significant')
    out2 = population_chisq_vs_5050(df, 'T-Score Diff (Pre - Post)')
    out3 = population_one_sample_ttest(df, 'T-Score Diff (Pre - Post)', popmean=0.0)
    assert 'Chi2 Stat' in out1
    assert 'Chi2 Stat' in out2
    assert 'T Stat' in out3
