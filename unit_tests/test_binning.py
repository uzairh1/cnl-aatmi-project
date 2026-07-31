from pathlib import Path
import pandas as pd

from analysis.binning import bin_firing_rate, bin_align1_file, bin_align1_folder

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_binning_matches_exact_counts():
    csv_path = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    out = bin_firing_rate(csv_path, bin_size_s=1)
    assert list(out.columns) == ['bin_1s', 'spike_count', 'firing_rate_hz']
    assert out['spike_count'].tolist() == [2, 2]
    assert out['firing_rate_hz'].tolist() == [2.0, 2.0]


def test_binning_writes_file(tmp_path):
    csv_path = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    out_path = tmp_path / 'binned.csv'
    written = bin_align1_file(csv_path, out_path, bin_size_s=1)
    assert written.exists()
    df = pd.read_csv(written)
    assert not df.empty


def test_binning_folder(tmp_path):
    align1_dir = tmp_path / 'align1'
    align1_dir.mkdir()
    src = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    (align1_dir / src.name).write_text(src.read_text())
    outputs = bin_align1_folder(align1_dir, tmp_path / 'out', bin_size_s=1)
    assert len(outputs) == 1
    assert outputs[0].exists()
