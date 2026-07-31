# analysis

> Alignment layer for spike data.

## Purpose

The `analysis` package contains the alignment stages that sit between preprocessing/data_io and later statistical analysis.

## Current Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `session_alignment_align1.py` | Align per-unit spike CSVs to the movie/session timebase | Complete |
| `trial_alignment_align2.py` | Assign movie-aligned spikes to trial windows | Complete |
| `binning.py` | Bins Align 1 data | Complete
| `statistics.py` | Computes summary statistics before plotting | Complete
| `README.md` | Package documentation | Complete |

# session_alignment_align1.py

## Running

```bash
python -m analysis.session_alignment_align1 \
    --input-dir <raw_spike_csv_directory> \
    --output-dir <align1_output_directory> \
    --start-unix-0 <movie_start_unix_seconds> \
    --matlab <matlab_reference_unix_seconds> \
    --duration <movie_duration_seconds>
````

## Purpose

The `session_alignment_align1.py` module aligns raw per-unit spike CSVs to the movie/session time base.

This is the first alignment stage in the analysis pipeline.

It performs the same conceptual job as the legacy UCLA Align 1 step:

* load raw spike CSVs
* compute the movie/session window
* keep only spikes that fall inside that window
* re-zero spike times so movie onset is time 0
* write one aligned CSV per neuron

This module does **not** assign spikes to individual trials.

That belongs to `trial_alignment_align2.py`.

---

## Inputs

Expected input directory

```text
times_manual*_unit_*.csv
```

Expected raw spike columns

| Column  | Description            |
| ------- | ---------------------- |
| `units` | Neuron/unit identifier |
| `s`     | Spike time in seconds  |

The module assumes the input CSVs are already produced by preprocessing.

It does not read the `.mat` file directly.

---

## Outputs

Primary output

One `align1_*.csv` file per neuron.

Example output file name

```text
align1_times_manual_GA1-REC3_unit_1.csv
```

Typical output columns

| Column               | Description                                         |
| -------------------- | --------------------------------------------------- |
| `units`              | Neuron/unit identifier                              |
| `spikeTimeRawS`      | Original spike time in seconds                      |
| `movieAlignedTimeS`  | Spike time relative to movie onset, in seconds      |
| `movieAlignedTimeMs` | Spike time relative to movie onset, in milliseconds |

---

## Public API

The public interface of `session_alignment_align1.py` consists of a small number of functions that together implement Align 1.

The intended execution order is

```text
Raw spike CSVs
    ↓
load_spike_csv()
    ↓
align_spikes_to_movie_window()
    ↓
save_aligned_spikes()
    ↓
align_one_neuron()
    ↓
align_session_folder()
    ↓
align1_*.csv
```

Although these functions may be called independently, they are normally orchestrated through `align_session_folder()` or the module CLI.

---

### compute_session_window()

#### Purpose

Compute the start and end of the movie/session window in seconds.

This function converts the patient/session timing metadata into the
window used for spike filtering.

---

#### Parameters

| Parameter      | Type    | Required | Description                                |
| -------------- | ------- | -------- | ------------------------------------------ |
| `start_unix_0` | `float` | Yes      | Movie start time in Unix seconds           |
| `matLab`       | `float` | Yes      | MATLAB reference timestamp in Unix seconds |
| `duration`     | `float` | Yes      | Movie duration in seconds                  |

---

#### Returns

| Name  | Type                  | Description                            |
| ----- | --------------------- | -------------------------------------- |
| tuple | `tuple[float, float]` | Session start and end times in seconds |

---

#### Notes

The session start is computed as

```text
session_start_seconds = start_unix_0 - matLab
```

and the session end is

```text
session_end_seconds = session_start_seconds + duration
```

---

### load_spike_csv()

#### Purpose

Load one raw spike CSV produced by preprocessing.

This is the lowest-level file loading function in the module.

It performs minimal validation and converts the raw spike time column into
a standardized internal name.

---

#### Parameters

| Parameter        | Type          | Required | Description                        |
| ---------------- | ------------- | -------- | ---------------------------------- |
| `spike_csv_path` | `str \| Path` | Yes      | Path to one raw per-unit spike CSV |

---

#### Returns

| Name      | Type               | Description                                             |
| --------- | ------------------ | ------------------------------------------------------- |
| DataFrame | `pandas.DataFrame` | Standardized DataFrame with `units` and `spikeTimeRawS` |

---

#### Raises

Possible exceptions include

* file not found
* unreadable CSV
* malformed CSV
* missing required columns

These exceptions are intentionally allowed to propagate to the caller.

---

#### Side Effects

None.

The input file is never modified.

---

### align_spikes_to_movie_window()

#### Purpose

Filter spikes to the movie/session window and re-zero spike times so movie
onset becomes 0.

This is the core Align 1 transformation.

---

#### Parameters

| Parameter                  | Type        | Required | Description                             |
| -------------------------- | ----------- | -------- | --------------------------------------- |
| `spike_df`                 | `DataFrame` | Yes      | Raw spike table from `load_spike_csv()` |
| `session_start_seconds`    | `float`     | Yes      | Movie/session start time in seconds     |
| `session_duration_seconds` | `float`     | Yes      | Movie/session duration in seconds       |

---

#### Returns

| Name      | Type               | Description               |
| --------- | ------------------ | ------------------------- |
| DataFrame | `pandas.DataFrame` | Movie-aligned spike table |

---

#### Notes

This function keeps only spikes satisfying

```text
session_start_seconds <= spikeTimeRawS <= session_end_seconds
```

It then subtracts `session_start_seconds` from each retained spike time.

The resulting movie-aligned time is stored both in seconds and
milliseconds.

---

### save_aligned_spikes()

#### Purpose

Write one movie-aligned spike table to disk.

---

#### Parameters

| Parameter     | Type          | Required | Description         |
| ------------- | ------------- | -------- | ------------------- |
| `df`          | `DataFrame`   | Yes      | Aligned spike table |
| `output_path` | `str \| Path` | Yes      | Output CSV path     |

---

#### Returns

| Name | Type           | Description                 |
| ---- | -------------- | --------------------------- |
| Path | `pathlib.Path` | Location of the written CSV |

---

#### Side Effects

Creates or overwrites the output CSV.

---

### align_one_neuron()

#### Purpose

Create one Align 1 output file for a single neuron.

This is the single-neuron wrapper around the lower-level loading and
alignment functions.

---

#### Parameters

| Parameter                  | Type          | Required | Description                            |
| -------------------------- | ------------- | -------- | -------------------------------------- |
| `spike_csv_path`           | `str \| Path` | Yes      | Input raw spike CSV                    |
| `session_start_seconds`    | `float`       | Yes      | Movie/session start time in seconds    |
| `session_duration_seconds` | `float`       | Yes      | Movie/session duration in seconds      |
| `align1_output_dir`        | `str \| Path` | Yes      | Folder where Align 1 files are written |

---

#### Returns

| Name | Type           | Description              |
| ---- | -------------- | ------------------------ |
| Path | `pathlib.Path` | Written Align 1 CSV path |

---

#### Side Effects

Creates the output directory if needed.

Writes one `align1_*.csv` file.

---

### align_session_folder()

#### Purpose

Create Align 1 files for every raw per-unit CSV in one folder.

This is the folder-level wrapper for Align 1.

---

#### Parameters

| Parameter                  | Type          | Required | Description                            |
| -------------------------- | ------------- | -------- | -------------------------------------- |
| `spike_csv_dir`            | `str \| Path` | Yes      | Folder containing raw spike CSVs       |
| `session_start_seconds`    | `float`       | Yes      | Movie/session start time in seconds    |
| `session_duration_seconds` | `float`       | Yes      | Movie/session duration in seconds      |
| `align1_output_dir`        | `str \| Path` | Yes      | Folder where Align 1 files are written |

---

#### Returns

| Name       | Type                   | Description                        |
| ---------- | ---------------------- | ---------------------------------- |
| list[Path] | list of `pathlib.Path` | Paths to the written Align 1 files |

---

#### Side Effects

Creates the output directory if needed.

Writes one Align 1 CSV per input neuron.

---

# trial_alignment_align2.py

## Running

```bash
python -m analysis.trial_alignment_align2 \
    --align1-dir <align1_directory> \
    --trial-table <trial_table.csv> \
    --output-dir <align2_output_directory>
```

## Purpose

The `trial_alignment_align2.py` module assigns movie-aligned spikes to
individual behavioral trial windows.

This is the second alignment stage in the analysis pipeline.

It takes `align1_*.csv` files and the standardized trial table, then writes
one `align2_*.csv` file per neuron.

This module does **not** read raw spike CSVs directly.

That job belongs to `session_alignment_align1.py`.

---

## Inputs

Primary inputs

* `align1_*.csv`
* `trial_table.csv`

Expected Align 1 columns

| Column | Description |
| --- | --- | --- |
| `units` | Neuron/unit identifier |
| `spikeTimeRawS` | Original spike time in seconds |
| `movieAlignedTimeS` | Spike time relative to movie onset, in seconds |
| `movieAlignedTimeMs` | Spike time relative to movie onset, in milliseconds |

Expected trial table columns

| Column            | Description                      |
| ----------------- | -------------------------------- |
| `clipStartTimeMs` | Trial start time in milliseconds |
| `clipEndTimeMs`   | Trial end time in milliseconds   |
| `clipWindowId`    | Unique clip-window identifier    |
| `trialOrder`      | Trial ordering                   |
| `clipID`          | Clip identifier                  |
| `movieID`         | Movie identifier                 |
| `isAccurate`      | Recognition accuracy flag        |
| `plotOrder`       | Plotting order                   |
| `includeInPlots`  | Plot inclusion flag              |

---

## Outputs

Primary output

One `align2_*.csv` file per neuron.

Example output file name

```text
align2_times_manual_GA1-REC3_unit_1.csv
```

Typical output columns

| Column                           | Description                                         |
| -------------------------------- | --------------------------------------------------- |
| `units`                          | Neuron/unit identifier                              |
| `spikeTimeRawS`                  | Original spike time in seconds                      |
| `movieAlignedTimeS`              | Spike time relative to movie onset, in seconds      |
| `movieAlignedTimeMs`             | Spike time relative to movie onset, in milliseconds |
| `trialOrder`                     | Trial ordering                                      |
| `clipWindowId`                   | Unique clip-window identifier                       |
| `clipID`                         | Clip identifier                                     |
| `movieID`                        | Movie identifier                                    |
| `isAccurate`                     | Recognition accuracy flag                           |
| `plotOrder`                      | Plotting order                                      |
| `includeInPlots`                 | Plot inclusion flag                                 |
| `clipStartTimeMs`                | Trial start time in milliseconds                    |
| `clipEndTimeMs`                  | Trial end time in milliseconds                      |
| `spikeTimeRelativeToClipStartMs` | Spike time relative to trial start, in milliseconds |
| `spikeTimeRelativeToClipStartS`  | Spike time relative to trial start, in seconds      |

---

## Public API

The public interface of `trial_alignment_align2.py` consists of a small
number of functions that together implement Align 2.

The intended execution order is

```text
Align 1 CSVs
    ↓
load_align1_spike_csv()
    ↓
align_spikes_to_trials()
    ↓
save_trial_aligned_spikes()
    ↓
align_one_neuron()
    ↓
align_session_folder()
    ↓
align2_*.csv
```

Although these functions may be called independently, they are normally
orchestrated through `align_session_folder()` or the module CLI.

---

### load_align1_spike_csv()

#### Purpose

Load one Align 1 CSV produced by `session_alignment_align1.py`.

This function prepares the movie-aligned spike table for trial assignment.

---

#### Parameters

| Parameter        | Type          | Required | Description             |
| ---------------- | ------------- | -------- | ----------------------- |
| `spike_csv_path` | `str \| Path` | Yes      | Path to one Align 1 CSV |

---

#### Returns

| Name      | Type               | Description                      |
| --------- | ------------------ | -------------------------------- |
| DataFrame | `pandas.DataFrame` | Standardized Align 1 spike table |

---

#### Raises

Possible exceptions include

* file not found
* unreadable CSV
* malformed CSV
* missing required columns

These exceptions are intentionally allowed to propagate to the caller.

---

#### Side Effects

None.

The input file is never modified.

---

### align_spikes_to_trials()

#### Purpose

Assign each movie-aligned spike to the trial window or windows that contain
it.

This is the core Align 2 transformation.

---

#### Parameters

| Parameter              | Type        | Required | Description                            |
| ---------------------- | ----------- | -------- | -------------------------------------- |
| `movie_aligned_spikes` | `DataFrame` | Yes      | Movie-aligned spike table from Align 1 |
| `trial_table`          | `DataFrame` | Yes      | Standardized trial/clip table          |

---

#### Returns

| Name      | Type               | Description               |
| --------- | ------------------ | ------------------------- |
| DataFrame | `pandas.DataFrame` | Trial-aligned spike table |

---

#### Notes

A spike is assigned to a trial when

```text
clipStartTimeMs <= movieAlignedTimeMs <= clipEndTimeMs
```

The module also computes spike time relative to clip start in both
milliseconds and seconds.

---

### save_trial_aligned_spikes()

#### Purpose

Write one trial-aligned spike table to disk.

---

#### Parameters

| Parameter     | Type          | Required | Description               |
| ------------- | ------------- | -------- | ------------------------- |
| `df`          | `DataFrame`   | Yes      | Trial-aligned spike table |
| `output_path` | `str \| Path` | Yes      | Output CSV path           |

---

#### Returns

| Name | Type           | Description              |
| ---- | -------------- | ------------------------ |
| Path | `pathlib.Path` | Written Align 2 CSV path |

---

#### Side Effects

Creates or overwrites the output CSV.

---

### align_one_neuron()

#### Purpose

Create one Align 2 output file for a single neuron.

This is the single-neuron wrapper around the lower-level loading and trial
assignment functions.

---

#### Parameters

| Parameter           | Type          | Required | Description                            |
| ------------------- | ------------- | -------- | -------------------------------------- |
| `align1_csv_path`   | `str \| Path` | Yes      | Input Align 1 CSV                      |
| `trial_table`       | `DataFrame`   | Yes      | Standardized trial table               |
| `align2_output_dir` | `str \| Path` | Yes      | Folder where Align 2 files are written |

---

#### Returns

| Name | Type           | Description              |
| ---- | -------------- | ------------------------ |
| Path | `pathlib.Path` | Written Align 2 CSV path |

---

#### Side Effects

Creates the output directory if needed.

Writes one Align 2 CSV.

---

### align_session_folder()

#### Purpose

Create Align 2 files for every Align 1 CSV in one folder.

This is the folder-level wrapper for Align 2.

---

#### Parameters

| Parameter           | Type          | Required | Description                            |
| ------------------- | ------------- | -------- | -------------------------------------- |
| `align1_input_dir`  | `str \| Path` | Yes      | Folder containing Align 1 CSVs         |
| `trial_table`       | `DataFrame`   | Yes      | Standardized trial table               |
| `align2_output_dir` | `str \| Path` | Yes      | Folder where Align 2 files are written |

---

#### Returns

| Name       | Type                   | Description                        |
| ---------- | ---------------------- | ---------------------------------- |
| list[Path] | list of `pathlib.Path` | Paths to the written Align 2 files |

---

#### Side Effects

Creates the output directory if needed.

Writes one Align 2 CSV per input neuron.

---


### Running
```bash
  python analysis/trial_alignment_align2.py \
  --align1-dir "path/to/align1_output" \
  --trial-table "path/to/trial_table.csv" \
  --output-dir "path/to/align2_output"
```
Inputs:
- Align 1 CSVs
- `trial_table.csv`

Output:
- `align2_*.csv`

Columns:
- `units`
- `spikeTimeRawS`
- `movieAlignedTimeS`
- `movieAlignedTimeMs`
- `trialOrder`
- `clipWindowId`
- `clipID`
- `movieID`
- `isAccurate`
- `plotOrder`
- `includeInPlots`
- `clipStartTimeMs`
- `clipEndTimeMs`
- `spikeTimeRelativeToClipStartMs`
- `spikeTimeRelativeToClipStartS`

Rule:
- a spike is assigned to a trial when `clipStartTimeMs <= movieAlignedTimeMs <= clipEndTimeMs`

# binning.py

## Running

```bash
python -m analysis.binning \
    --align1-dir <align1_directory> \
    --output-dir <output_directory> \
    [--bin-size-s 10]
```

## Purpose

The `binning.py` module reproduces the legacy movie-level firing-rate
binning behavior used by the old UCLA helper `bin_firing_rate()`.

It takes movie/session-aligned spike tables and converts them into fixed-width
time bins.

This stage is not trial-based.

It does not use `align2_*.csv`.

Instead, it operates directly on `align1_*.csv` outputs.

---

## Inputs

Primary input

```
align1_*.csv
```

Expected input column

| Column | Description                                      |
| ------ | ------------------------------------------------ |
| `ms`   | Movie/session-aligned spike time in milliseconds |

The module assumes that the input CSV already contains spikes aligned to the
movie/session timeline.

---

## Outputs

Primary output

One binned CSV per Align 1 input file.

Typical output columns

| Column           | Description                                 |
| ---------------- | ------------------------------------------- |
| `bin_<N>s`       | Bin index                                   |
| `spike_count`    | Number of spikes in the bin                 |
| `firing_rate_hz` | Spike count divided by bin width in seconds |

Missing bins are retained and filled with zero spike counts.

---

## Public API

The public interface of `binning.py` consists of a small number of
functions that together implement legacy-style movie-level spike binning.

The intended execution order is

```text
Align 1 CSV
    ↓
load_align1_csv()
    ↓
bin_firing_rate_from_df()
    ↓
bin_firing_rate()
    ↓
bin_align1_file()
    ↓
bin_align1_folder()
```

Although these functions may be called independently, they are normally
orchestrated through `bin_align1_folder()` or the module CLI.

---

### load_align1_csv()

#### Purpose

Load one Align 1 CSV and validate that it contains the expected aligned
spike-time column.

This function performs the minimum amount of processing necessary to prepare
the table for binning.

---

#### Parameters

| Parameter  | Type          | Required | Description                     |
| ---------- | ------------- | -------- | ------------------------------- |
| `csv_path` | `str \| Path` | Yes      | Path to one `align1_*.csv` file |

---

#### Returns

| Name      | Type               | Description                                    |
| --------- | ------------------ | ---------------------------------------------- |
| DataFrame | `pandas.DataFrame` | Align 1 table with cleaned numeric `ms` values |

---

#### Raises

Possible exceptions include

* file not found
* unreadable CSV
* malformed CSV
* missing `ms` column

These exceptions are intentionally allowed to propagate to the caller.

---

#### Side Effects

None.

The input file is never modified.

---

### bin_firing_rate_from_df()

#### Purpose

Convert a movie-aligned spike DataFrame into a fixed-width binned firing-rate
table.

This function mirrors the behavior of the legacy UCLA helper.

---

#### Parameters

| Parameter    | Type      | Description          |
| ------------ | --------- | -------------------- |
| `df`         | DataFrame | Align 1 spike table  |
| `bin_size_s` | `int`     | Bin width in seconds |

---

#### Binning Rule

Spike times are converted from milliseconds to seconds and assigned to bins
using

```text
bin_index = floor(time_seconds / bin_size_s)
```

---

#### Returns

A DataFrame containing one row per bin.

Typical columns

| Column           | Description                         |
| ---------------- | ----------------------------------- |
| `bin_<N>s`       | Bin index                           |
| `spike_count`    | Number of spikes in the bin         |
| `firing_rate_hz` | Spike count divided by `bin_size_s` |

---

#### Notes

Bins with no spikes are retained.

This function does not use trial windows.

---

### bin_firing_rate()

#### Purpose

Legacy-compatible helper that loads an Align 1 CSV and bins it in one step.

This exists for convenience and for compatibility with older calling
patterns.

---

#### Parameters

| Parameter    | Type          | Description                     |
| ------------ | ------------- | ------------------------------- |
| `csv_path`   | `str \| Path` | Path to one `align1_*.csv` file |
| `bin_size_s` | `int`         | Bin width in seconds            |

---

#### Returns

Binned DataFrame.

---

#### Notes

This is the most direct single-file entry point for the module.

---

### bin_align1_file()

#### Purpose

Bin one Align 1 CSV and write the binned output to disk.

---

#### Parameters

| Parameter         | Type          | Description                    |
| ----------------- | ------------- | ------------------------------ |
| `align1_csv_path` | `str \| Path` | Input Align 1 CSV              |
| `output_csv_path` | `str \| Path` | Output path for the binned CSV |
| `bin_size_s`      | `int`         | Bin width in seconds           |

---

#### Returns

| Name | Type           | Description                        |
| ---- | -------------- | ---------------------------------- |
| Path | `pathlib.Path` | Location of the written binned CSV |

---

#### Side Effects

Creates or overwrites the output CSV.

---

### bin_align1_folder()

#### Purpose

Bin every Align 1 CSV in one folder.

---

#### Parameters

| Parameter    | Type          | Description                              |
| ------------ | ------------- | ---------------------------------------- |
| `align1_dir` | `str \| Path` | Folder containing `align1_*.csv` files   |
| `output_dir` | `str \| Path` | Folder where binned CSVs will be written |
| `bin_size_s` | `int`         | Bin width in seconds                     |

---

#### Returns

| Name       | Type                   | Description                       |
| ---------- | ---------------------- | --------------------------------- |
| list[Path] | list of `pathlib.Path` | Paths to written binned CSV files |

---

#### Side Effects

Creates the output directory if needed.

---

# statistics.py

## Running

```bash
python -m analysis.statistics \
    --align1-dir <align1_directory> \
    --clips-table <trial_table.csv> \
    --patient-id <patient_id> \
    --output-csv <summary.csv>
```

## Purpose

The `statistics.py` module reproduces the legacy neuron-level statistics
workflow from the monolithic script.

It works from movie/session-aligned spike tables and a clip timing table.

It computes pre/post window firing rates, correct-vs-wrong Welch t-tests,
per-neuron summary rows, and population-level summaries.

This module does **not** use `align2_*.csv`.

---

## Inputs

Primary inputs

* `align1_*.csv`
* clip/TTL timing table

Expected aligned spike column

| Column | Description                                      |
| ------ | ------------------------------------------------ |
| `ms`   | Movie/session-aligned spike time in milliseconds |

The clip table may use either legacy or refactored timing names.

---

## Outputs

Primary output

One summary CSV with one row per neuron.

Typical output columns include

| Column                      | Description                                |
| --------------------------- | ------------------------------------------ |
| `Patient`                   | Patient label                              |
| `Neuron Name`               | Neuron identifier                          |
| `Pre-Stim T-Score`          | Welch t-test statistic for the pre window  |
| `Pre-Stim P-Value`          | Pre-window p-value                         |
| `Pre-Stim Significant`      | Pre-window significance flag               |
| `Post-Stim T-Score`         | Welch t-test statistic for the post window |
| `Post-Stim P-Value`         | Post-window p-value                        |
| `Post-Stim Significant`     | Post-window significance flag              |
| `T-Score Diff (Pre - Post)` | Difference between pre and post t-scores   |
| `Post-Stim Mean Rate (Hz)`  | Mean post-stimulus firing rate             |
| `N Clips`                   | Number of clips used in the summary        |

Population summaries may also be computed from the output table.

---

## Public API

The public interface of `statistics.py` consists of functions that together
implement the legacy statistics workflow.

The intended execution order is

```text
Align 1 CSV
    ↓
load_clip_table()
    ↓
analyze_align1_file()
    ↓
build_neuron_summary_row()
    ↓
analyze_align1_folder()
    ↓
summary CSV
    ↓
analyze_population_table()
```

Although these functions may be called independently, they are normally
orchestrated through `analyze_align1_folder()` or the module CLI.

---

### load_clip_table()

#### Purpose

Load a clip timing table and normalize the column names used by the
statistics code.

This function allows the module to accept either legacy `seen frames to ms`
style tables or the newer refactored `trial_table.csv` naming.

---

#### Parameters

| Parameter  | Type          | Required | Description                       |
| ---------- | ------------- | -------- | --------------------------------- |
| `csv_path` | `str \| Path` | Yes      | Path to the clip/TTL timing table |

---

#### Returns

| Name      | Type               | Description                               |
| --------- | ------------------ | ----------------------------------------- |
| DataFrame | `pandas.DataFrame` | Timing table with normalized column names |

---

#### Notes

The module normalizes common timing and plotting column names to the legacy
names used by the statistical logic.

---

### compute_rate_hz_in_window()

#### Purpose

Compute the mean firing rate in one time window across all clips.

This mirrors the rate calculation used by the monolithic script for neuron
screening.

---

#### Parameters

| Parameter   | Type            | Description                                         |
| ----------- | --------------- | --------------------------------------------------- |
| `spikes_ms` | `numpy.ndarray` | Movie-aligned spike times in milliseconds           |
| `clips_df`  | DataFrame       | Clip timing table                                   |
| `win_start` | `int`           | Window start in milliseconds relative to clip start |
| `win_end`   | `int`           | Window end in milliseconds relative to clip start   |

---

#### Returns

| Name          | Type            | Description                                         |
| ------------- | --------------- | --------------------------------------------------- |
| float or None | `float \| None` | Mean firing rate in Hz, or `None` if not computable |

---

### compute_correct_vs_wrong_ttest()

#### Purpose

Perform the legacy correct-vs-wrong Welch t-test for one time window.

This is the core statistical helper used by the monolithic script.

---

#### Parameters

| Parameter             | Type            | Description                               |
| --------------------- | --------------- | ----------------------------------------- |
| `spikes_ms`           | `numpy.ndarray` | Movie-aligned spike times in milliseconds |
| `clips_df`            | DataFrame       | Clip timing table                         |
| `window_start_ms`     | `int`           | Window start relative to clip start       |
| `window_end_ms`       | `int`           | Window end relative to clip start         |
| `alpha`               | `float`         | Significance threshold                    |
| `significance_method` | `str`           | `p_value` or `t_score`                    |

---

#### Returns

A dictionary containing

| Key           | Description                     |
| ------------- | ------------------------------- |
| `ok`          | Whether the test was computable |
| `p_value`     | Welch t-test p-value            |
| `t_stat`      | Welch t-test statistic          |
| `n_correct`   | Number of correct trials        |
| `n_incorrect` | Number of incorrect trials      |
| `significant` | Significance flag               |

---

#### Notes

The statistical comparison is between correct and incorrect clips, not
between pre and post windows directly.

---

### build_neuron_summary_row()

#### Purpose

Build the legacy-style summary row for one neuron.

This function mirrors the row creation logic that was embedded in the old
raster/statistics pipeline.

---

#### Parameters

| Parameter             | Type              | Description                        |
| --------------------- | ----------------- | ---------------------------------- |
| `align1_df`           | DataFrame         | One movie-aligned spike table      |
| `clips_df`            | DataFrame         | Clip timing table                  |
| `neuron_name`         | `str`             | Neuron identifier                  |
| `patient_id`          | `str`             | Patient identifier                 |
| `output_tag`          | `str`             | Optional output tag                |
| `min_rate_hz`         | `float`           | Minimum post-stimulus firing rate  |
| `pre_window_ms`       | `tuple[int, int]` | Pre window relative to clip start  |
| `post_window_ms`      | `tuple[int, int]` | Post window relative to clip start |
| `alpha`               | `float`           | Significance threshold             |
| `significance_method` | `str`             | `p_value` or `t_score`             |

---

#### Returns

| Name         | Type           | Description                                                    |
| ------------ | -------------- | -------------------------------------------------------------- |
| dict or None | `dict \| None` | Summary row for one neuron, or `None` if the neuron is skipped |

---

#### Notes

The returned dictionary is shaped to match the legacy neuron summary CSV.

---

### analyze_align1_file()

#### Purpose

Analyze one Align 1 file and return a summary row.

---

#### Parameters

| Parameter             | Type              | Description                        |
| --------------------- | ----------------- | ---------------------------------- |
| `align1_csv_path`     | `str \| Path`     | Path to one Align 1 CSV            |
| `clips_df`            | DataFrame         | Clip timing table                  |
| `patient_id`          | `str`             | Patient identifier                 |
| `output_tag`          | `str`             | Optional output tag                |
| `min_rate_hz`         | `float`           | Minimum post-stimulus firing rate  |
| `pre_window_ms`       | `tuple[int, int]` | Pre window relative to clip start  |
| `post_window_ms`      | `tuple[int, int]` | Post window relative to clip start |
| `alpha`               | `float`           | Significance threshold             |
| `significance_method` | `str`             | `p_value` or `t_score`             |

---

#### Returns

| Name         | Type           | Description                           |
| ------------ | -------------- | ------------------------------------- |
| dict or None | `dict \| None` | Summary row for one neuron, or `None` |

---

### analyze_align1_folder()

#### Purpose

Analyze every Align 1 file in one folder and write a summary CSV.

---

#### Parameters

| Parameter             | Type              | Description                            |
| --------------------- | ----------------- | -------------------------------------- |
| `align1_dir`          | `str \| Path`     | Folder containing `align1_*.csv` files |
| `clips_df`            | DataFrame         | Clip timing table                      |
| `patient_id`          | `str`             | Patient identifier                     |
| `output_csv`          | `str \| Path`     | Output summary CSV                     |
| `output_tag`          | `str`             | Optional output tag                    |
| `min_rate_hz`         | `float`           | Minimum post-stimulus firing rate      |
| `pre_window_ms`       | `tuple[int, int]` | Pre window relative to clip start      |
| `post_window_ms`      | `tuple[int, int]` | Post window relative to clip start     |
| `alpha`               | `float`           | Significance threshold                 |
| `significance_method` | `str`             | `p_value` or `t_score`                 |

---

#### Returns

| Name      | Type               | Description             |
| --------- | ------------------ | ----------------------- |
| DataFrame | `pandas.DataFrame` | Aggregate summary table |

---

#### Side Effects

Writes the summary CSV to disk.

---

### population_chisq_vs_chance()

#### Purpose

Perform the legacy chi-square summary used for swarm-style population plots.

This mirrors the old `chisq_vs_chance` branch.

---

#### Parameters

| Parameter    | Type            | Description                  |
| ------------ | --------------- | ---------------------------- |
| `df`         | DataFrame       | Summary table                |
| `metric_col` | `str`           | Metric to test               |
| `thresh`     | `float \| None` | Optional threshold           |
| `sig_col`    | `str \| None`   | Optional significance column |

---

#### Returns

A dictionary containing summary counts and chi-square results.

---

### population_chisq_vs_5050()

#### Purpose

Perform the legacy chi-square summary for positive-vs-negative difference
scores.

This mirrors the old `chisq_vs_5050` branch.

---

#### Parameters

| Parameter    | Type      | Description    |
| ------------ | --------- | -------------- |
| `df`         | DataFrame | Summary table  |
| `metric_col` | `str`     | Metric to test |

---

#### Returns

A dictionary containing summary counts and chi-square results.

---

### population_one_sample_ttest()

#### Purpose

Perform a one-sample t-test on a population metric.

This is a configurable alternative to the legacy chi-square summaries.

---

#### Parameters

| Parameter    | Type      | Description    |
| ------------ | --------- | -------------- |
| `df`         | DataFrame | Summary table  |
| `metric_col` | `str`     | Metric to test |
| `popmean`    | `float`   | Null mean      |

---

#### Returns

A dictionary containing the t statistic, p-value, and summary counts.

---

### analyze_population_table()

#### Purpose

Load a summary table and compute one population-level summary.

---

#### Parameters

| Parameter     | Type            | Description                                               |
| ------------- | --------------- | --------------------------------------------------------- |
| `summary_csv` | `str \| Path`   | Summary CSV path                                          |
| `metric_col`  | `str`           | Metric to test                                            |
| `test_mode`   | `str`           | `chisq_vs_chance`, `chisq_vs_5050`, or `one_sample_ttest` |
| `thresh`      | `float \| None` | Optional threshold                                        |
| `sig_col`     | `str \| None`   | Optional significance column                              |
| `popmean`     | `float`         | Null mean for the one-sample t-test                       |

---

#### Returns

A dictionary containing the requested population summary.

---

# Testing

Every public module inside `analysis` should have corresponding automated
tests.

Current automated tests should include

| Test                        | Purpose                          |
| --------------------------- | -------------------------------- |
| `test_binning.py`           | Validate movie-level binning     |
| `test_statistics.py`        | Validate neuron-level statistics |
| `test_session_alignment.py` | Validate Align 1                 |
| `test_trial_alignment.py`   | Validate Align 2                 |

---

# Summary

The `analysis` package contains the scientific computation layer of the
pipeline.

Its modules transform standardized metadata and aligned spike tables into
binned rates, statistical summaries, and eventually figures.

The package is intentionally separated from `data_io` so that metadata
parsing, alignment, analysis, and plotting remain independent and easier to
test.

