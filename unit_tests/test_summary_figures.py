from pathlib import Path

from plotting.swarm import generate_population_swarm_plot
from plotting.summary_figures import generate_summary_figures

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def test_summary_figures(tmp_path):
    summary_csv = FIXTURES / 'analysis' / 'neuron_summary.csv'
    out_dir = tmp_path / 'pipeline_output'
    generate_population_swarm_plot(summary_csv=summary_csv, output_dir=out_dir)
    run_summary, dashboards = generate_summary_figures(output_root=out_dir, summary_csv=summary_csv)

    assert (out_dir / 'Run_Summary.csv').exists()
    assert not run_summary.empty
    assert len(dashboards) >= 1
