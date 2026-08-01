# running

> Interactive pipeline setup, output planning, and execution.

---

# Files

| File | Purpose |
| --- | --- |
| `setup_and_run.py` | Prompt for the monolithic hardcoded patient values |
| `pipeline_executor.py` | Convert raw dictionaries into objects, plan outputs, and run the pipeline |
| `config.py` | Configuration schema, region mappings, and validation |

---

# Running

Run the pipeline interactively

```bash
python running/setup_and_run.py
```

Show the planned output tree without running the pipeline

```bash
python running/setup_and_run.py --dry-run
```

---

# Prompted fields

Patient prompts:

- `patient_id`
- `movie_label`
- `signal_path`
- `clip_ttl_csv`
- `localization_file`
- `output_tag`
- `matLab`
- `start_unix_0`
- `duration`
- `fps`

Runtime prompts:

- `output_root`
- `movie_bin_size_s`

The movie bin size defaults to the project standard from `PIPELINE_ANALYSIS_CONFIG`.

---

# Planned output structure

```text
P570/

    data/
        trial_table.csv

    align1/
    align2/
    binning/

    statistics/
        neuron_summary.csv

    plots/

        rasters/
            all/
                *.png
                T_score_sheet.csv
            sig/
                *.png
                T_score_sheet.csv
            nonsig/
                *.png
                T_score_sheet.csv
            by_region/
                HPC/
                    *.png
                    T_score_sheet.csv
                ERC/
                    ...
                FC/
                    ...
                LTC/
                    ...
                MTL/
                    ...

        swarm/
            global/
                P1_Post-Stim_T-Scores.png
                P2_Pre-Stim_T-Scores.png
                P3_Diff_SigOnly.png
                P4_Diff_All.png
                P5_Diff_Post_GTE_1.png
                Swarm_Statistics_global.csv
                Summary_Overview_global.csv
            HPC/
                ...
            ERC/
                ...
            FC/
                ...
            LTC/
                ...
            MTL/
                ...

        dashboards/
            global_dashboard.png
            HPC_dashboard.png
            ERC_dashboard.png
            FC_dashboard.png
            LTC_dashboard.png
            MTL_dashboard.png
            Run_Summary.csv

    localization_trace.csv
    pipeline_artifacts.json
```

---

# Summary

The `running` folder is the interactive launch point for the pipeline.

`setup_and_run.py` collects the values that were hardcoded in the monolithic script, and `pipeline_executor.py` converts them into the objects used by the rest of the repository.
