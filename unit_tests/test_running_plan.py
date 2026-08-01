from __future__ import annotations

from pathlib import Path

from running.config import AnalysisConfig, PatientConfig
from running.pipeline_executor import plan_patient_pipeline


def test_plan_patient_pipeline_matches_intended_tree(tmp_path: Path) -> None:
    patient = PatientConfig(
        patient_id="570",
        movie_label="24",
        signal_path=r"C:\Users\Uzair\Desktop\CNL\patients\570 - new",
        clip_ttl_csv=r"C:\Users\Uzair\Desktop\CNL\570 test run\TTL_table.csv",
        localization_file=r"C:\Users\Uzair\Desktop\CNL\570 test run\sub-570_localizations.xlsx",
        output_tag="",
        matLab=1706304396.2999392,
        start_unix_0=1706308502.2209392,
        duration=2476.867,
        fps=29.97,
    )

    analysis = AnalysisConfig()
    plan = plan_patient_pipeline(patient, analysis, tmp_path)

    patient_root = tmp_path / "P570"
    expected_folders = {
        patient_root / "data",
        patient_root / "align1",
        patient_root / "align2",
        patient_root / "binning",
        patient_root / "statistics",
        patient_root / "plots" / "rasters" / "all",
        patient_root / "plots" / "rasters" / "sig",
        patient_root / "plots" / "rasters" / "nonsig",
        patient_root / "plots" / "rasters" / "by_region",
        patient_root / "plots" / "swarm" / "global",
        patient_root / "plots" / "swarm" / "HPC",
        patient_root / "plots" / "swarm" / "ERC",
        patient_root / "plots" / "swarm" / "FC",
        patient_root / "plots" / "swarm" / "LTC",
        patient_root / "plots" / "swarm" / "MTL",
        patient_root / "plots" / "dashboards",
    }

    assert plan["patient_root"] == str(patient_root)
    assert set(map(Path, plan["folders"])) == expected_folders

    expected_files = {
        patient_root / "data" / "trial_table.csv",
        patient_root / "statistics" / "neuron_summary.csv",
        patient_root / "localization_trace.csv",
        patient_root / "pipeline_artifacts.json",
        patient_root / "plots" / "swarm" / "Summary_Global_and_Regional.csv",
        patient_root / "plots" / "swarm" / "Summary_Patient_Bipolar_Breakdown.csv",
        patient_root / "plots" / "dashboards" / "Run_Summary.csv",
    }
    assert set(map(Path, plan["canonical_files"])) == expected_files

    raster_csvs = set(map(Path, plan["raster_csvs"]))
    assert raster_csvs == {
        patient_root / "plots" / "rasters" / "all" / "T_score_sheet.csv",
        patient_root / "plots" / "rasters" / "sig" / "T_score_sheet.csv",
        patient_root / "plots" / "rasters" / "nonsig" / "T_score_sheet.csv",
    }

    expected_regions = {"HPC", "ERC", "FC", "LTC", "MTL", "AMY", "INS", "PHC", "CC", "BAS", "CENT", "FUS", "PC", "VIS", "WM", "UNKNOWN"}
    planned_region_csvs = {Path(p).parent.name for p in plan["raster_region_csvs"]}
    assert expected_regions.issubset(planned_region_csvs)

    expected_swarm = {
        patient_root / "plots" / "swarm" / region / "P1_Post-Stim_T-Scores.png"
        for region in ("global", "HPC", "ERC", "FC", "LTC", "MTL")
    }
    assert all(path in map(Path, plan["swarm_files"]) for path in expected_swarm)

    expected_dashboards = {
        patient_root / "plots" / "dashboards" / f"{region}_dashboard.png"
        for region in ("global", "HPC", "ERC", "FC", "LTC", "MTL")
    }
    assert set(map(Path, plan["dashboards"])) == expected_dashboards

    assert plan["bin_size_s"] == 10


def test_plan_patient_pipeline_uses_overrides(tmp_path: Path) -> None:
    patient = PatientConfig(
        patient_id="570",
        movie_label="24",
        signal_path=r"C:\Users\Uzair\Desktop\CNL\patients\570 - new",
        clip_ttl_csv=r"C:\Users\Uzair\Desktop\CNL\570 test run\TTL_table.csv",
    )
    analysis = AnalysisConfig(movie_bin_size_s=10)
    plan = plan_patient_pipeline(patient, analysis, tmp_path, bin_size_s=25)
    assert plan["bin_size_s"] == 25
    assert Path(plan["patient_root"]) == tmp_path / "P570"