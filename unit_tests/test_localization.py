import pandas as pd

from data_io.localization import infer_neuron_localization, region_description


def test_infer_neuron_localization_returns_strings():
    fake_loc_df = pd.DataFrame(
        {
            "electrode": ["RA_micro_1", "LA_micro_2"],
            "aparc+aseg": ["right amygdala", "left hippocampus"],
            "bipolar_region": ["AMY", "HPC"],
        }
    )

    electrode_code, full_location, region_abbr = infer_neuron_localization(
        "align1_times_manual_GA1-RA2_unit_5.csv",
        fake_loc_df,
    )

    assert isinstance(electrode_code, str)
    assert isinstance(full_location, str)
    assert isinstance(region_abbr, str)


def test_region_description_known_region():
    assert region_description("HPC") == "hippocampus"


def test_region_description_unknown_region():
    assert region_description("XYZ") == "Unknown"