import importlib.util
from pathlib import Path

import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "New Script Output/cross_patient/cross_patient_bipolar_wilcoxon.py"
spec = importlib.util.spec_from_file_location("cross_patient_bipolar_wilcoxon", SCRIPT)
cross = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cross)


def summary(root, patient):
    path = root / f"{patient}_exp1/statistics/neuron_summary.csv"
    path.parent.mkdir(parents=True)
    pd.DataFrame({
        "Neuron Name": ["times_manual_GA1-RA2_unit_5"],
        "Pre-Stim T-Score": [1.0],
        "Post-Stim T-Score": [2.0],
        "T-Score Diff (Pre - Post)": [-1.0],
    }).to_csv(path, index=False)
    return path


def workbook(root, patient, *, bipolar=True, electrode="GA1_RA2_micro1"):
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"sub-{patient}_localizations.xlsx"
    data = {"electrode": [electrode]}
    if bipolar:
        data["BIPOLAR"] = ["HPC"]
    pd.DataFrame(data).to_excel(path, index=False)
    return path


@pytest.fixture
def no_plots(monkeypatch):
    monkeypatch.setattr(cross, "make_poster_grid", lambda *a, **kw: None)
    monkeypatch.setattr(cross, "make_scope_figure", lambda *a, **kw: None)


def test_missing_and_no_bipolar_patients_are_excluded(tmp_path, no_plots):
    outputs, locs, results = (tmp_path / name for name in ["outputs", "locs", "results"])
    for patient in ["P570", "P571", "P572", "P573"]:
        summary(outputs, patient)
    good = workbook(locs, "570")
    bad = workbook(locs, "571", bipolar=False)
    missing = locs / "sub-573_localizations.xlsx"
    mapping = tmp_path / "mapping.csv"
    pd.DataFrame({
        "Patient ID": ["P570", "P571", "P573"],
        "Localization File": [str(good), str(bad), str(missing)],
    }).to_csv(mapping, index=False)

    cross.generate_cross_patient_plots(outputs, output_dir=results, localization_map_csv=mapping)

    combined = pd.read_csv(results / "combined_neuron_summary.csv")
    assert combined["Patient ID"].tolist() == ["P570"]
    assert combined["BIPOLAR"].tolist() == ["HPC"]
    excluded = pd.read_csv(results / "excluded_patients.csv").set_index("Patient ID")
    assert excluded.loc["P571", "Exclusion Reason"] == "Missing BIPOLAR column"
    assert set(excluded.index) == {"P571", "P572", "P573"}
    for name in ["localization_qc.csv", "participant_wilcoxon_pre_post.csv"]:
        assert set(pd.read_csv(results / name)["Patient ID"]) == {"P570"}
    counts = pd.read_csv(results / "region_counts.csv").set_index("Scope")
    assert counts.loc["global", "Patients"] == 1
    assert counts.loc["global", "Neurons"] == 1
    assert bad.exists()


def test_explicit_exclusion_ignores_duplicate_workbooks(tmp_path, no_plots):
    outputs, locs = tmp_path / "outputs", tmp_path / "locs"
    summary(outputs, "P570")
    summary(outputs, "P571")
    workbook(locs, "570")
    workbook(locs, "571")
    workbook(locs / "inspection", "571", bipolar=False)
    results = cross.generate_cross_patient_plots(
        outputs, localizations_root=locs, exclude_patients=["571"],
    )
    assert pd.read_csv(results / "combined_neuron_summary.csv")["Patient ID"].tolist() == ["P570"]
    excluded = pd.read_csv(results / "excluded_patients.csv")
    assert excluded["Patient ID"].tolist() == ["P571"]


def test_removed_workbook_does_not_block_discovery(tmp_path, no_plots):
    outputs, locs = tmp_path / "outputs", tmp_path / "locs"
    summary(outputs, "P570")
    summary(outputs, "P571")
    workbook(locs, "570")
    results = cross.generate_cross_patient_plots(outputs, localizations_root=locs)
    assert pd.read_csv(results / "excluded_patients.csv")["Patient ID"].tolist() == ["P571"]


def test_all_excluded_writes_report_and_stops(tmp_path, no_plots):
    outputs, locs = tmp_path / "outputs", tmp_path / "locs"
    summary(outputs, "P570")
    workbook(locs, "570", bipolar=False)
    with pytest.raises(ValueError, match="No eligible patients remain"):
        cross.generate_cross_patient_plots(outputs, localizations_root=locs)
    assert pd.read_csv(outputs / "cross_patient/excluded_patients.csv")["Patient ID"].tolist() == ["P570"]
    assert not (outputs / "cross_patient/combined_neuron_summary.csv").exists()


def test_unmatched_neuron_still_fails_qc(tmp_path, no_plots):
    outputs, locs = tmp_path / "outputs", tmp_path / "locs"
    summary(outputs, "P570")
    workbook(locs, "570", electrode="GA1_LH1_micro1")
    with pytest.raises(ValueError, match="localization QC failed"):
        cross.generate_cross_patient_plots(outputs, localizations_root=locs)
    qc = pd.read_csv(outputs / "cross_patient/localization_qc.csv")
    assert qc["Localization Match Status"].tolist() == ["ERROR_NO_MATCH"]
    assert not (outputs / "cross_patient/combined_neuron_summary.csv").exists()
