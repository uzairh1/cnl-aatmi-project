# running

> Interactive pipeline setup, object conversion, and execution.

---

# Files

| File | Purpose |
| --- | --- |
| `setup_and_run.py` | Prompt for the monolithic hardcoded patient values |
| `pipeline_executor.py` | Convert raw dictionaries into objects and run the pipeline |
| `config.py` | Configuration schema, region mappings, and validation |
| `models.py` | Shared data models passed between stages |

---

# Running

```bash
python running/setup_and_run.py
```

The script prompts for the same field names used by the monolithic script, then launches the pipeline.

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

# Data Flow

```text
setup_and_run.py
    -> raw dictionaries
    -> pipeline_executor.py
    -> PatientConfig / PIPELINE_ANALYSIS_CONFIG
    -> full pipeline execution
```

---

# Summary

The `running` folder is the interactive launch point for the pipeline.

`setup_and_run.py` collects the values that were hardcoded in the monolithic script, and `pipeline_executor.py` converts them into the objects used by the rest of the repository.
