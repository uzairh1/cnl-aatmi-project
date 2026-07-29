# data_io

> Standardized input/output layer for experimental metadata.

---

# Table of Contents

- [Purpose](#purpose)
- [Package Philosophy](#package-philosophy)
- [Responsibilities](#responsibilities)
- [Non-Responsibilities](#non-responsibilities)
- [Package Structure](#package-structure)
- [Current Modules](#current-modules)
- [Shared Design Principles](#shared-design-principles)
- [Behavioral Metadata Pipeline](#behavioral-metadata-pipeline)
- [Localization Pipeline](#localization-pipeline)
- [ttl_table_parser.py](#ttl_table_parserpy)
- [localization.py](#localizationpy)
- [Testing](#testing)
- [Future Work](#future-work)

---

# Purpose

The `data_io` package is responsible for loading, validating,
standardizing, and exposing experimental metadata to the remainder of the
analysis pipeline.

Unlike the original monolithic implementation, this package does **not**
perform spike alignment, statistical analyses, or plotting.

Instead, it defines the canonical interfaces through which the remainder of
the repository accesses behavioral and anatomical metadata.

In many ways, `data_io` forms the "contract" between the raw experimental
files and the downstream analysis code.

---

# Package Philosophy

The package is built around three core ideas.

## 1. Preserve Experimental Data

Raw experimental files should never be modified.

Instead,

```
Raw file

↓

Standardized representation

↓

Analysis
```

Every transformation creates a new representation while leaving the
original file untouched.

---

## 2. Standardize Once

Behavioral metadata should be standardized exactly once.

Every downstream module should consume the standardized representation
rather than repeatedly parsing raw experimental files.

For example,

```
TTL_table.csv

↓

trial_table.csv

↓

Spike Alignment

↓

Statistics

↓

Plots
```

rather than

```
TTL_table.csv

↓

Analysis A

TTL_table.csv

↓

Analysis B

TTL_table.csv

↓

Analysis C
```

This reduces duplicated code and minimizes inconsistencies.

---

## 3. Separate Metadata from Analysis

The `data_io` package should only answer questions such as

> "What trial is this?"

or

> "Where is this neuron located?"

It should never answer questions such as

> "Is this neuron selective?"

Those questions belong in later analysis modules.

---

# Responsibilities

The package is responsible for

- Reading raw behavioral metadata.
- Reading localization workbooks.
- Standardizing behavioral timing.
- Producing canonical trial tables.
- Matching neuron filenames to anatomical locations.
- Returning standardized metadata objects.

---

# Non-Responsibilities

The package is **not** responsible for

- MATLAB preprocessing
- Spike alignment
- Baseline calculations
- Statistical analyses
- Figure generation
- Data visualization

These responsibilities belong to other packages.

---

# Package Structure

```
data_io/

├── __init__.py

├── ttl_table_parser.py

├── localization.py

└── README.md
```

Each module has exactly one primary responsibility.

---

# Current Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `ttl_table_parser.py` | Standardize behavioral metadata | Complete |
| `localization.py` | Infer neuron localization | Complete |

Future modules should follow the same architectural style.

---

# Shared Design Principles

Every module inside `data_io` should follow the same rules.

## Single Responsibility

Each module performs one task.

For example,

- TTL parsing
- localization lookup

should remain separate.

---

## Pure Data Transformations

Functions should transform data.

They should avoid hidden state and unnecessary side effects whenever
possible.

---

## Explicit Inputs

Every public function should clearly document

- required files
- expected columns
- optional parameters
- return values

---

## Stable Outputs

Downstream modules should be able to depend on the output schema without
needing to understand how it was produced.

---

# Behavioral Metadata Pipeline

Behavioral metadata begin as the raw experimental TTL table.

```
TTL_table.csv

↓

load_ttl_table()

↓

filter_trials()

↓

derive_timing_columns()

↓

derive_analysis_columns()

↓

trial_table.csv
```

Every stage performs one transformation.

No stage performs statistical analysis.

---

# Localization Pipeline

Localization metadata begin as the clinical localization workbook.

```
sub-*_localizations.xlsx

↓

load_localization_map()

↓

infer_neuron_localization()

↓

Standardized localization metadata
```

Unlike behavioral metadata, localization information is currently returned
as Python objects rather than exported to a standardized CSV.

Future versions of the repository may introduce a canonical localization
table if doing so simplifies downstream analyses.

---

# ttl_table_parser.py

## Purpose

Convert the raw behavioral TTL table into the standardized trial table
used throughout the remainder of the analysis pipeline.

The parser preserves raw behavioral metadata while creating a collection of
analysis-specific variables with descriptive names.

The resulting `trial_table.csv` becomes the canonical behavioral dataset
used throughout the repository.

---

## Inputs

Expected input

```
TTL_table.csv
```

Primary raw variables include

| Column | Description |
| --- | --- |
| `experimentPhase` | Experimental phase |
| `trialNumber` | Trial identifier |
| `movieID` | Movie identifier |
| `clipID` | Clip identifier |
| `response` | Behavioral response |
| `clipStartTime` | Clip start (seconds) |
| `clipEndTime` | Clip end (seconds) |
| `frameOn` | First frame of clip |
| `frameOff` | Last frame of clip |

Additional behavioral variables are preserved whenever present.

---

## Outputs

Primary output

```
trial_table.csv
```

The parser preserves raw columns while creating standardized derived
columns.

| Derived Column | Purpose |
| --- | --- |
| `clipStartTimeMs` | Canonical clip start time |
| `clipEndTimeMs` | Canonical clip end time |
| `clipDurationMs` | Clip duration |
| `clipDurationSec` | Clip duration |
| `clipFrameRange` | Human-readable frame interval |
| `clipTimeRangeMs` | Human-readable millisecond interval |
| `clipWindowId` | Unique alignment identifier |
| `isAccurate` | Recognition accuracy |
| `trialOrder` | Chronological ordering |
| `plotOrder` | Raster plotting order |
| `includeInPlots` | Manual plotting flag |

---

## Public API

The following sections document the public interface of
`ttl_table_parser.py`.

Each function is documented independently so that it may be understood
without reading the implementation.

## Public API

The public interface of `ttl_table_parser.py` consists of a small number of
functions that together implement the behavioral metadata pipeline.

The intended execution order is

```

Raw TTL Table

↓

load_ttl_table()

↓

filter_trials()

↓

derive_timing_columns()

↓

derive_analysis_columns()

↓

restore_plot_preferences()

↓

save_trial_table()

↓

trial_table.csv

```

Although these functions may be called independently, they are normally
orchestrated through `build_trial_table()`.

---

### load_ttl_table()

#### Purpose

Load the raw behavioral TTL table from disk.

This function performs the minimum amount of processing necessary to
prepare the table for later stages.

Specifically, it

- reads the CSV
- removes leading/trailing whitespace from column names
- returns an unmodified DataFrame

No filtering is performed.

No timing variables are derived.

No analysis variables are created.

---

#### Parameters

| Parameter | Type | Required | Description |
| ---------- | ---- | -------- | ----------- |
| `ttl_csv` | `str \| Path` | Yes | Path to the raw TTL table. |

---

#### Returns

| Name | Type | Description |
| ---- | ---- | ----------- |
| DataFrame | `pandas.DataFrame` | Raw TTL table with cleaned column names. |

---

#### Raises

Possible exceptions include

- file not found
- unreadable CSV
- malformed CSV

These exceptions are intentionally allowed to propagate to the caller.

---

#### Side Effects

None.

The input file is never modified.

---

#### Called By

Normally called only by

```
build_trial_table()
```

---

#### Design Notes

This function intentionally performs almost no processing.

The goal is to keep "reading a file" separate from "understanding the
contents of the file."

---

### filter_trials()

#### Purpose

Reduce the raw TTL table to the subset of trials used for downstream
analysis.

The original monolithic pipeline primarily analyzed

- recognition trials
- movie 1

This function preserves that behavior while allowing future analyses to
override the defaults.

---

#### Parameters

| Parameter | Type | Default | Description |
| ---------- | ---- | ------- | ----------- |
| `df` | DataFrame | — | Raw TTL table |
| `phase` | `str` | `"recog_task"` | Experimental phase to retain |
| `movie_id` | `int \| None` | `1` | Movie to retain |

---

#### Returns

Filtered DataFrame.

Row order is preserved.

Indices are reset.

---

#### Side Effects

None.

---

#### Notes

Passing

```python
movie_id=None
```

retains every movie.

This behavior exists primarily to support future analyses.

---

### derive_timing_columns()

#### Purpose

Create the canonical timing variables used throughout the repository.

This function is the only place where behavioral timing variables are
standardized.

Future analysis modules should rely on these derived variables rather than
repeating timing calculations.

---

#### Timing Philosophy

The refactored pipeline treats

```
clipStartTime

clipEndTime
```

as the authoritative timing source.

The original monolithic script derived timing primarily from

```
frameOn

frameOff
```

Those variables are now preserved strictly as experimental metadata.

---

#### Parameters

| Parameter | Type |
| ---------- | ---- |
| `df` | DataFrame |

---

#### Creates

| Column | Units | Description |
| -------- | ----- | ----------- |
| `clipStartTimeMs` | ms | Canonical clip start |
| `clipEndTimeMs` | ms | Canonical clip end |
| `clipDurationMs` | ms | Clip duration |
| `clipDurationSec` | s | Clip duration |
| `clipFrameRange` | — | Frame interval |
| `clipTimeRangeMs` | — | Millisecond interval |
| `clipWindowId` | — | Unique alignment identifier |

---

#### Preserves

The following raw experimental variables remain unchanged.

- frameOn
- frameOff
- clipStartTime
- clipEndTime

---

#### Why Preserve frameOn / frameOff?

Although they are no longer treated as the canonical timing source, they
remain valuable because they identify the original stimulus frames shown to
the participant.

Future analyses or debugging sessions may still require this information.

---

#### Side Effects

None.

---

### _infer_accuracy()

#### Purpose

Determine whether each behavioral trial was correctly recognized.

---

#### Priority Order

Accuracy is inferred using the following rules.

1.

Existing

```
Accurate
```

or

```
Accuracy
```

column.

2.

Behavioral response.

```
response == 2
```

3.

Otherwise

```
False
```

---

#### Output

Creates

```
isAccurate
```

which is used throughout downstream analyses.

---

#### Notes

This helper function is intentionally private because it exists solely to
support `derive_analysis_columns()`.

---

### derive_analysis_columns()

#### Purpose

Generate metadata used by downstream analysis and visualization.

These variables are not experimental observations.

Instead, they exist solely because they simplify later stages of the
analysis pipeline.

---

#### Creates

| Variable | Purpose |
| ---------- | -------- |
| `isAccurate` | Recognition accuracy |
| `trialOrder` | Chronological order |
| `plotOrder` | Raster ordering |
| `includeInPlots` | Manual inclusion flag |

---

#### plotOrder

Correct trials are intentionally assigned lower plot indices than
incorrect trials.

This preserves the behavior of the original monolithic raster plots.

---

#### includeInPlots

Allows individual trials to be manually excluded from visualizations while
preserving the underlying behavioral data.

Future statistical analyses should ignore this variable unless explicitly
requested by the user.

---

### restore_plot_preferences()

#### Purpose

Restore manually curated visualization settings from an existing trial
table.

This prevents manual plotting decisions from being lost when the behavioral
metadata are regenerated.

---

#### Matching Strategy

Rows are matched using

```
clipWindowId
```

rather than row number.

This makes the restoration robust to changes in row ordering.

---

#### Side Effects

None.

The existing trial table is never modified.

---

### save_trial_table()

#### Purpose

Write the standardized behavioral table to disk.

---

#### Inputs

- standardized DataFrame
- output path

---

#### Output

```
trial_table.csv
```

---

#### Side Effects

Creates or overwrites the output CSV.

---

### build_trial_table()

#### Purpose

Primary public interface for the behavioral metadata pipeline.

Most users should call only this function.

---

#### Internal Execution Order

1. Read the raw TTL table.
2. Filter trials.
3. Standardize timing.
4. Create analysis metadata.
5. Restore plotting preferences.
6. Write the standardized table.

---

#### Returns

| Return | Description |
| -------- | ----------- |
| DataFrame | Standardized behavioral table |
| Path | Location of the written CSV |

---

#### Why Does This Function Exist?

The helper functions remain independently testable.

`build_trial_table()` exists to provide a convenient public entry point
that executes the complete pipeline in the correct order.

---

# localization.py

## Purpose

The localization module provides a standardized interface for mapping
recorded neurons to their anatomical locations.

Unlike the behavioral parser, which transforms experimental timing data,
the localization module performs metadata lookup.

Its primary responsibility is to answer the question

> "Where in the brain was this neuron recorded?"

The remainder of the repository should obtain anatomical information
through this module rather than interacting directly with localization
workbooks.

---

## Inputs

Primary input

```
sub-*_localizations.xlsx
```

The exact workbook structure may differ slightly between recording
sessions.

The localization module attempts to isolate those differences so that
downstream analysis code does not depend on workbook formatting.

Typical columns include

| Column | Description |
| -------- | ----------- |
| `electrode` | Electrode identifier |
| `region` | Electrode region |
| `aparc+aseg` | Anatomical label |
| `BIPOLAR` | Region abbreviation |
| `isMicro` | Indicates microelectrode recordings |

Additional workbook columns are preserved but ignored unless required for
future analyses.

---

## Outputs

Unlike the TTL parser, the localization module currently returns Python
objects rather than writing standardized files.

Typical outputs include

| Value | Description |
| ------- | ----------- |
| Electrode abbreviation | Parsed from neuron filename |
| Anatomical label | Human-readable brain region |
| Region abbreviation | Compact label used in plots |

Future versions of the repository may optionally export standardized
localization tables if downstream modules would benefit from a persistent
representation.

---

## Public API

---

### load_localization_map()

#### Purpose

Load the localization workbook into a standardized pandas DataFrame.

The function performs minimal preprocessing while preserving the original
experimental metadata.

---

#### Responsibilities

- Open the workbook.
- Read the selected worksheet.
- Remove leading and trailing whitespace from column names.
- Return a cleaned DataFrame.

---

#### Non-Responsibilities

This function does **not**

- infer neuron locations
- parse filenames
- classify brain regions
- perform statistics

Those tasks belong to later functions.

---

#### Parameters

| Parameter | Type | Description |
| ---------- | ---- | ----------- |
| `file_path` | `str \| Path` | Path to the localization workbook |
| `sheet_name` | optional | Worksheet to load |

---

#### Returns

Standardized localization DataFrame.

---

#### Side Effects

None.

The workbook is never modified.

---

### infer_neuron_localization()

#### Purpose

Determine the anatomical location associated with a neuron filename.

This function represents the primary public interface of the localization
module.

Most downstream code should call this function rather than interacting
directly with the localization workbook.

---

#### Inputs

Neuron filename

Example

```
times_manual_GA1-RA2_unit_5.csv
```

Localization DataFrame

Returned by

```
load_localization_map()
```

---

#### Matching Strategy

The matching process consists of several stages.

1.

Extract the electrode abbreviation from the neuron filename.

↓

2.

Locate the corresponding electrode inside the localization workbook.

↓

3.

Extract anatomical metadata.

↓

4.

Return a standardized tuple.

---

#### Returns

| Position | Description |
| -------- | ----------- |
| 1 | Electrode abbreviation |
| 2 | Anatomical label |
| 3 | Region abbreviation |

---

#### Why Return a Tuple?

Only three values are currently required throughout the remainder of the
repository.

Returning a lightweight tuple keeps the interface simple while allowing
future implementations to migrate to richer data models if needed.

---

#### Side Effects

None.

---

### region_description()

#### Purpose

Convert abbreviated region labels into human-readable anatomical names.

This function exists primarily for visualization and reporting.

For example

```
AMY

↓

Amygdala
```

or

```
HPC

↓

Hippocampus
```

The exact mapping depends on the localization conventions adopted by the
laboratory.

---

#### Side Effects

None.

---

# Testing

Every public module inside `data_io` should have corresponding automated
tests.

Current automated tests include

| Test | Purpose |
| ----- | ------- |
| `test_ttl_table_parser.py` | Validate behavioral metadata parsing |
| `test_localization.py` | Validate localization lookup |

Manual debugging scripts should exist whenever interactive inspection
provides additional value.

---

## Testing Philosophy

The repository intentionally separates

### Unit Tests

Verify one function.

Examples

- timing conversion
- localization lookup
- trial filtering

---

### Manual Tests

Allow developers to inspect intermediate DataFrames, filenames, and
metadata while developing new features.

---

### Regression Tests

Future work.

Regression tests should verify that the refactored pipeline continues to
produce behavior consistent with the original monolithic implementation
when provided identical experimental inputs.

---

# Design Decisions

This section documents architectural decisions that may not be obvious
from the implementation alone.

---

## Why separate preprocessing from data_io?

MATLAB preprocessing produces spike trains.

Behavioral parsing produces trial metadata.

These are independent problems.

Keeping them separate allows each stage to be developed, tested, and
executed independently.

---

## Why preserve raw columns?

Variables originating from the experiment should remain unchanged whenever
possible.

Examples include

- frameOn
- frameOff
- clipStartTime
- clipEndTime

Preserving raw variables

- simplifies debugging
- preserves provenance
- facilitates comparison with the original experiment

---

## Why rename derived columns?

Variables created by the repository should describe their purpose rather
than their historical implementation.

Examples

| Legacy | Current |
| -------- | -------- |
| `ms start` | `clipStartTimeMs` |
| `ms end` | `clipEndTimeMs` |
| `Plot Toggle` | `includeInPlots` |
| `Accurate` | `isAccurate` |

This distinction makes it immediately obvious which variables originate
from the experiment and which were generated by the software.

---

## Why use clipStartTime instead of frameOn?

The behavioral software already provides timestamps.

Those timestamps represent the canonical timing of the experiment.

Frame numbers remain valuable metadata but should no longer serve as the
primary timing source.

---

## Why produce intermediate files?

Intermediate representations such as

```
trial_table.csv
```

make the pipeline easier to

- debug
- inspect
- validate
- test

Every major transformation should therefore produce an explicit data
product rather than remaining hidden inside memory.

---

# Extension Guide

New modules added to `data_io` should follow the same architectural
principles.

Every module should

- perform one responsibility
- expose a small public API
- preserve raw experimental metadata
- document every public function
- include automated tests
- include a package README

Whenever possible, downstream modules should consume standardized outputs
rather than repeatedly parsing raw experimental files.

---

# Future Work

Potential future additions include

- standardized localization tables
- additional behavioral parsers
- schema validation
- metadata versioning
- support for multiple behavioral paradigms

Current status

**Not implemented.**

---

# Related Documentation

Additional information is provided in

- Repository `README.md`
- `preprocessing/README.md`
- `tests/README.md`
- `test_scripts/README.md`

Future documentation will include

- `docs/PIPELINE.md`
- `docs/DATA_MODEL.md`
- `docs/LOCALIZATION.md`
- `docs/TESTING.md`

---

# Summary

The `data_io` package serves as the canonical interface between raw
experimental metadata and the remainder of the analysis pipeline.

Its responsibilities are intentionally limited to loading,
standardizing, and exposing metadata.

By keeping metadata handling separate from preprocessing, analysis, and
visualization, the repository remains modular, testable, and easier to
maintain as new functionality is added.