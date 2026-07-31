from pathlib import Path

from plotting.swarm import generate_population_swarm_plot

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_swarm_outputs(tmp_path):
    summary_csv = FIXTURES / 'analysis' / 'neuron_summary.csv'
    out_dir = tmp_path / 'swarm'
    generate_population_swarm_plot(summary_csv=summary_csv, output_dir=out_dir)

    assert out_dir.exists()
    assert (out_dir / 'Summary_Global_and_Regional.csv').exists()
    assert any(p.name.startswith('P1_') for p in out_dir.rglob('*.png'))
