# plotting

> Figure generation layer for rasters, PSTHs, and summary visualizations.

---

# Table of Contents

- [Purpose](#purpose)
- [Responsibilities](#responsibilities)
- [Package Structure](#package-structure)
- [Current Modules](#current-modules)
- [rasters.py](#rasterspy)
- [swarm.py](#swarmpy)

---

# Purpose

The `plotting` package contains the modules that turn standardized analysis
outputs into figures.

This package sits after `analysis` and consumes the outputs of
movie/session alignment, trial assignment, statistics, and, where useful,
binning.

The package is intentionally separate from the scientific calculations so
that plotting remains a presentation layer rather than a computation layer.

---

# Responsibilities

The package is responsible for

- drawing raster figures
- drawing PSTH curves
- applying legacy-style visual formatting
- using summaries from the analysis layer when available
- writing publication-style PNG outputs

The package does **not** own raw metadata parsing, alignment, or the primary
statistical calculations.

---

# Package Structure

```text
plotting/

├── __init__.py

├── rasters.py

└── README.md
```

Each module has exactly one primary responsibility.

---

# Current Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `rasters.py` | Draw raster plots and PSTHs from Align 1 outputs | Complete |

Future modules should follow the same architectural style.

---

# rasters.py

## Running

```bash
python -m plotting.rasters \
    --align1-dir <align1_directory> \
    --clips-table <trial_table.csv> \
    --output-dir <output_directory> \
    --patient-id <patient_id> \
    [--localization-file <localization.xlsx>] \
    [--summary-csv <summary.csv>] \
    [--output-tag <tag>]
```

## Purpose

The `rasters.py` module reproduces the legacy single-neuron raster/PSTH
figures from the monolithic UCLA script.

It works from Align 1 spike CSVs and the clip timing table.

It does **not** require Align 2.

When a neuron summary CSV is available, the plotting module can use it to
add legacy-style pre/post statistics to figure titles and to filter low-rate
neurons in the same general way as the monolithic script.

---

## Inputs

Primary inputs

- `align1_*.csv`
- `trial_table.csv` or legacy clip timing table

Optional inputs

- localization workbook
- neuron summary CSV from `statistics.py`

Expected Align 1 columns

| Column | Description |
| --- | --- |
| `ms` | Movie/session-aligned spike time in milliseconds |

Expected clip table columns

| Column | Description |
| --- | --- |
| `ms start` or `clipStartTimeMs` | Clip start time in milliseconds |
| `ms end` or `clipEndTimeMs` | Clip end time in milliseconds |
| `Accurate` or `isAccurate` | Accuracy flag |
| `Plot Y-Axis` or `plotOrder` | Manual raster ordering |
| `Plot Toggle` or `includeInPlots` | Manual plot inclusion flag |

---

## Outputs

Primary output

One PNG per neuron.

Example output file name

```text
P570_exp4presleep_RA_times_manual_GA1-REC3_unit_1_neg3_to_5_sig.png
```

Typical figure contents

- raster panel
- PSTH panel
- optional split by correct vs incorrect trials
- optional clip-end markers
- optional pre/post title labels

---

## Public API

The public interface of `rasters.py` consists of a small number of
functions that together implement the legacy-style plotting workflow.

The intended execution order is

```text
Align 1 CSV
    ↓
load_align1_csv()
    ↓
load_clip_table()
    ↓
build_clip_rows_for_window()
    ↓
compute_psth_hz() / compute_smoothed_psth_hz()
    ↓
plot_neuron_from_align1()
    ↓
plot_align1_folder()
    ↓
PNG figures
```

Although these functions may be called independently, they are normally
orchestrated through `plot_align1_folder()` or the module CLI.

---

### load_align1_csv()

#### Purpose

Load one Align 1 CSV and validate that it contains the expected movie-aligned
spike-time column.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `csv_path` | `str \| Path` | Yes | Path to one Align 1 CSV |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| DataFrame | `pandas.DataFrame` | Standardized Align 1 spike table |

#### Side Effects

None.

---

### load_summary_csv()

#### Purpose

Load the neuron summary CSV if one is available.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `summary_csv` | `str \| Path` | Yes | Path to the summary CSV |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| DataFrame | `pandas.DataFrame` | Summary table |

---

### load_summary_map()

#### Purpose

Convert the summary CSV into a neuron-name lookup table.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `summary_csv` | `str \| Path` | Yes | Path to the summary CSV |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| dict | `dict[str, dict]` | Summary row keyed by neuron name |

---

### build_clip_rows_for_window()

#### Purpose

Build raster rows for each clip using spikes relative to clip start.

This is the core trial-window construction step used for raster and PSTH
figures.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `spikes_ms` | `numpy.ndarray` | Yes | Movie-aligned spike times in milliseconds |
| `clips_df` | `DataFrame` | Yes | Clip timing table |
| `window_start_ms` | `int` | Yes | Relative start of the figure window |
| `window_end_ms` | `int` | Yes | Relative end of the figure window |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| list[dict] | list of dictionaries | One raster row per clip |

---

### compute_psth_hz()

#### Purpose

Compute a PSTH in Hz from trial-aligned spike rows.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `clip_rows` | `list[list[float]]` | Yes | Per-trial spike rows |
| `x_min` | `int` | Yes | Minimum x value |
| `x_max` | `int` | Yes | Maximum x value |
| `bin_ms` | `int` | Yes | Bin width in milliseconds |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| tuple | `tuple[np.ndarray, np.ndarray]` | PSTH centers and rates |

---

### compute_smoothed_psth_hz()

#### Purpose

Compute a smoothed PSTH using one of the legacy-style smoothing modes.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `clip_rows` | `list[list[float]]` | Yes | Per-trial spike rows |
| `x_min` | `int` | Yes | Minimum x value |
| `x_max` | `int` | Yes | Maximum x value |
| `bin_ms` | `int` | No | Bin width in milliseconds |
| `smooth_type` | `str` | No | Smoothing mode |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| tuple | `tuple[np.ndarray, np.ndarray]` | Smoothed PSTH centers and rates |

---

### sort_rows_accuracy_top_bottom()

#### Purpose

Order clip rows so correct trials appear above incorrect trials.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `plot_rows` | `list[dict]` | Yes | Raster rows |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| tuple | `tuple[list[dict], int]` | Reordered rows and number of correct rows |

---

### draw_clip_end_markers()

#### Purpose

Draw clip-end markers on the raster panel.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `ax` | `matplotlib.axes.Axes` | Yes | Raster axis |
| `plot_rows` | `list[dict]` | Yes | Raster rows |
| `x_max` | `int` | Yes | Maximum x value |

#### Returns

None.

---

### has_any_spikes()

#### Purpose

Return whether any clip row contains at least one spike.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `plot_rows` | `list[dict]` | Yes | Raster rows |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| bool | `bool` | True if any row contains spikes |

---

### plot_neuron_from_align1()

#### Purpose

Plot one neuron from one Align 1 CSV.

This is the single-neuron wrapper around the lower-level loading and
plotting functions.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `align1_csv_path` | `str \| Path` | Yes | Input Align 1 CSV |
| `clips_df` | `DataFrame` | Yes | Clip timing table |
| `output_dir` | `str \| Path` | Yes | Output folder |
| `patient_id` | `str` | Yes | Patient ID used in filenames |
| `loc_df` | `DataFrame` | No | Localization table |
| `summary_row` | `dict \| None` | No | Optional neuron summary row |
| `output_tag` | `str` | No | Optional output tag |
| `window_start_ms` | `int` | No | Figure window start |
| `window_end_ms` | `int` | No | Figure window end |
| `split_by_accuracy` | `bool` | No | Whether to split correct vs incorrect |
| `show_clip_end_marker` | `bool` | No | Whether to draw clip-end markers |
| `smooth_type` | `str` | No | PSTH smoothing mode |
| `min_rate_hz` | `float` | No | Minimum post-stimulus firing rate |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| Path or None | `pathlib.Path \| None` | Written PNG path or `None` |

---

### plot_align1_folder()

#### Purpose

Plot every Align 1 CSV in one folder.

This is the folder-level wrapper for figure generation.

#### Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `align1_dir` | `str \| Path` | Yes | Folder containing Align 1 CSVs |
| `clips_table` | `str \| Path` | Yes | Trial/clip timing table |
| `output_dir` | `str \| Path` | Yes | Folder where PNGs will be written |
| `patient_id` | `str` | Yes | Patient ID used in filenames |
| `localization_file` | `str` | No | Optional localization workbook |
| `summary_csv` | `str \| Path` | No | Optional summary CSV |
| `output_tag` | `str` | No | Optional output tag |
| `window_start_ms` | `int` | No | Figure window start |
| `window_end_ms` | `int` | No | Figure window end |
| `split_by_accuracy` | `bool` | No | Whether to split correct vs incorrect |
| `show_clip_end_marker` | `bool` | No | Whether to draw clip-end markers |
| `smooth_type` | `str` | No | PSTH smoothing mode |
| `min_rate_hz` | `float` | No | Minimum post-stimulus firing rate |

#### Returns

| Name | Type | Description |
| --- | --- | --- |
| list[Path] | list of `pathlib.Path` | Paths to the written PNG files |

---

swarm.py
Running
```bash
python -m plotting.swarm         --summary-csv <neuron_summary.csv>         --output-dir <aggregate_output_directory>
```
Purpose
The `swarm.py` module reproduces the legacy population-level swarm plots
from the monolithic UCLA script.
It works from the neuron summary CSV produced by the statistics layer.
This module does not perform spike alignment.
It does not require Align 2.
It groups neurons by region, draws swarm plots with mean ± SEM, adds a side
histogram, and writes the same family of region-level summary CSVs used by
the old workflow.
---
Inputs
Primary input
`neuron_summary.csv`
Expected columns
Column	Description
`Patient`	Patient label
`Neuron Name`	Neuron identifier
`Localization - Bipolar`	Region label used for region grouping
`Pre-Stim T-Score`	Pre-window t-score
`Pre-Stim Significant`	Pre-window significance flag
`Post-Stim T-Score`	Post-window t-score
`Post-Stim Significant`	Post-window significance flag
`T-Score Diff (Pre - Post)`	Pre minus post t-score difference
If `Localization - Bipolar` is missing, only the global plots are generated.
---
Outputs
Primary outputs
global swarm plots
region swarm plots
`Swarm_Statistics_<region>.csv`
`Summary_Overview_<region>.csv`
`Summary_Global_and_Regional.csv`
`Summary_Patient_Bipolar_Breakdown.csv`
Plot file names follow the legacy naming scheme used by the monolithic script.
---
Public API
The public interface of `swarm.py` consists of a small number of functions
that together implement the legacy population-plot workflow.
The intended execution order is
```text
Neuron summary CSV
    ↓
load_summary_table()
    ↓
generate_population_swarm_plot()
    ↓
regional swarm plots + summary CSVs
```
Although the functions may be called independently, the module is normally
orchestrated through `generate_population_swarm_plot()` or the CLI.
---
load_summary_table()
Purpose
Load the neuron summary CSV into a DataFrame.
Parameters
Parameter	Type	Required	Description
`summary_csv`	`str | Path`	Yes	Path to the neuron summary CSV
Returns
Name	Type	Description
DataFrame	`pandas.DataFrame`	Loaded summary table
---
_select_region_dataframe()
Purpose
Filter the summary table to one region.
This helper is used internally to reproduce the legacy region-grouping
behavior.
Parameters
Parameter	Type	Required	Description
`df`	`DataFrame`	Yes	Summary table
`region_name`	`str`	Yes	Region name
`abbreviations`	`list[str] | None`	Yes	Region abbreviations
Returns
Filtered DataFrame.
---
_create_swarm_and_stats()
Purpose
Create one swarm plot and append one statistics row.
This mirrors the legacy helper that produced the per-metric figure/statistic
pairs.
Parameters
Parameter	Type	Required	Description
`df`	`DataFrame`	Yes	Summary table or region subset
`metric_col`	`str`	Yes	Metric to plot
`plot_id`	`str`	Yes	Output figure ID
`title_label`	`str`	Yes	Plot title
`thresh`	`float | None`	No	Threshold guide line
`out_dir`	`Path`	Yes	Output directory
`stats_rows`	`list[dict]`	Yes	Stats rows accumulator
`test_type`	`str`	Yes	`chisq_vs_chance` or `chisq_vs_5050`
`sig_col`	`str | None`	No	Optional significance column
Returns
None.
Notes
This helper performs the chi-square calculations used by the legacy swarm
plots.
---
generate_population_swarm_plot()
Purpose
Generate global and region-specific swarm plots from a summary CSV.
This is the main public entry point.
Parameters
Parameter	Type	Required	Description
`summary_csv`	`str | Path`	Yes	Path to the neuron summary CSV
`output_dir`	`str | Path`	Yes	Folder where swarm plots will be written
Returns
None.
Side Effects
Creates region-specific output folders and writes PNG/CSV summary outputs.
---


# Summary

The `plotting` package turns aligned spikes and analysis summaries into
legacy-style figures.

`rasters.py` is the first plotting module and reproduces the core
single-neuron raster/PSTH workflow from the monolithic script.

The `swarm.py` module turns the neuron summary table into legacy-style
population figures and summary CSVs.
It mirrors the monolithic script’s region grouping and chi-square workflow.
