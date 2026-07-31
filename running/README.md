# running

> Interactive pipeline setup, configuration, and execution.

---

# Table of Contents

- [Purpose](#purpose)
- [Files](#files)
- [Running](#running)
- [Prompting](#prompting)
- [Data Flow](#data-flow)
- [Summary](#summary)

---

# Purpose

The `running` folder contains the scripts that collect the pipeline
inputs, convert them into objects, and launch the full pipeline.

The field names match the monolithic script so the values can be copied
over directly.

---

# Files

| File | Purpose |
| --- | --- |
| `setup_and_run.py` | Prompt for the hardcoded values and launch the pipeline |
| `pipeline_executor.py` | Convert raw inputs into objects and execute the pipeline |
| `config.py` | Configuration schema, region mappings, and validation |
| `models.py` | Shared data models passed between stages |

---

# Running

```bash
python running/setup_and_run.py
```

The script will prompt for the same field names used by the monolithic
script and then launch the pipeline.

---

# Prompting

Patient prompts use the monolithic field names:

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
- `event_time_offset_ms`

Analysis prompts use the pipeline-wide names:

- `pre_window_start_ms`
- `pre_window_end_ms`
- `post_window_start_ms`
- `post_window_end_ms`
- `raster_window_start_ms`
- `raster_window_end_ms`
- `min_rate_hz`
- `alpha`
- `stat_style`
- `n_permutations`
- `smoothing`
- `psth_bin_ms`

---

# Data Flow

```text
setup_and_run.py
    ↓
raw dictionaries
    ↓
pipeline_executor.py
    ↓
PatientConfig / AnalysisConfig
    ↓
trial table
    ↓
Align 1
    ↓
Align 2
    ↓
binning
    ↓
statistics
    ↓
rasters
    ↓
swarm
    ↓
summary figures
```

---

# Summary

The `running` folder is the interactive entry point for the pipeline.

`setup_and_run.py` prompts for the same values that were hardcoded in the
monolithic script, and `pipeline_executor.py` converts those values into
the objects used by the rest of the repository.
