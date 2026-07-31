from pathlib import Path

from plotting.rasters import plot_neuron_from_align1, plot_align1_folder
from analysis.statistics import load_clip_table

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_plot_single_neuron(tmp_path):
    align1 = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    clips = load_clip_table(FIXTURES / 'data_io' / 'trial_table.csv')
    out = plot_neuron_from_align1(
        align1_csv_path=align1,
        clips_df=clips,
        output_dir=tmp_path,
        patient_id='570',
        summary_row=None,
        output_tag='test',
    )
    assert out is not None
    assert out.exists()


def test_plot_folder(tmp_path):
    align1_dir = tmp_path / 'align1'
    align1_dir.mkdir()
    src = FIXTURES / 'alignment' / 'align1_times_manual_GA1-REC3_unit_1.csv'
    (align1_dir / src.name).write_text(src.read_text())

    out_dir = tmp_path / 'plots'
    outputs = plot_align1_folder(
        align1_dir=align1_dir,
        clips_table=FIXTURES / 'data_io' / 'trial_table.csv',
        output_dir=out_dir,
        patient_id='570',
    )
    assert len(outputs) == 1
    assert outputs[0].exists()
