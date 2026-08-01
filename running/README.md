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

The dry run shows the planned filesystem layout without creating files.

Typical top-level structure:

```text
P570_exp4presleep/
    data/
    align1/
    align2/
    binning/
    statistics/
    plots/
        rasters/
            all/
            sig/
            nonsig/
            regions/
        swarm/
            global/
            HPC/
            ERC/
            FC/
            LTC/
            MTL/
        dashboards/
    pipeline_artifacts.json
```

---

# Summary

The `running` folder is the interactive launch point for the pipeline.

`setup_and_run.py` collects the values that were hardcoded in the monolithic script, and `pipeline_executor.py` converts them into the objects used by the rest of the repository.
