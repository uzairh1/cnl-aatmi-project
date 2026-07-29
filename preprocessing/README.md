# preprocessing

> Converts raw MATLAB spike sorting output into standardized per-neuron CSV files used throughout the analysis pipeline.

---

# Table of Contents

- [Purpose](#purpose)
- [Responsibilities](#responsibilities)
- [Non-Responsibilities](#non-responsibilities)
- [Pipeline Position](#pipeline-position)
- [Directory Structure](#directory-structure)
- [Supported Input Files](#supported-input-files)
- [Supported Output Files](#supported-output-files)
- [MATLAB File Assumptions](#matlab-file-assumptions)
- [MATLAB Data Structure](#matlab-data-structure)
- [Output CSV Schema](#output-csv-schema)
- [Naming Conventions](#naming-conventions)
- [Public Modules](#public-modules)
- [Processing Pipeline](#processing-pipeline)
- [Testing](#testing)
- [Design Decisions](#design-decisions)
- [Common Failure Modes](#common-failure-modes)
- [Future Work](#future-work)

---

# Purpose

The `preprocessing` package converts raw MATLAB spike sorting output into a
collection of standardized CSV files that can be consumed by the remainder
of the analysis pipeline.

The original monolithic analysis script assumed these CSV files already
existed.

This package reproduces that preprocessing step in Python so that the
entire workflow can be run without MATLAB.

---

# Responsibilities

The preprocessing package is responsible for:

- Reading MATLAB spike sorting files.
- Extracting clustered spike times.
- Separating spikes by unit.
- Writing one CSV file per neuron.
- Preserving the original laboratory naming convention.

---

# Non-Responsibilities

The preprocessing package does **not**:

- Read behavioral data.
- Read localization workbooks.
- Compute spike statistics.
- Align spikes to behavioral events.
- Generate plots.
- Modify experimental metadata.

These responsibilities belong to later stages of the pipeline.

---

# Pipeline Position

The preprocessing stage is the first computational step in the analysis
pipeline.

```text
Raw MATLAB

↓

convert_matlab_to_csv.py

↓

Per-neuron CSV files

↓

Spike alignment (future)
```

---

# Directory Structure

```text
preprocessing/

├── convert_matlab_to_csv.py
├── __init__.py
└── README.md
```

---

# Supported Input Files

## MATLAB Spike Sorting Files

Expected filename

```text
times_manual*.mat
```

Examples

```text
times_manual_GA1-RA2.mat

times_manual_LA3-LA4.mat
```

Supported version

- MATLAB v7.3

Unsupported versions

- MATLAB v5
- MATLAB v6
- MATLAB files requiring `scipy.io.loadmat()`

The repository intentionally assumes MATLAB v7.3 to simplify the codebase.

---

# MATLAB File Assumptions

The parser assumes the MATLAB file contains the following dataset.

## cluster_class

Expected shape

```text
(3, N)
```

After transposition

```text
(N, 3)
```

Columns

| Column | Description |
| --- | --- |
| 0 | Unit identifier |
| 1 | Spike time (seconds) |
| 2 | Reserved (currently ignored) |

Only the first two columns are used by the repository.

---

# Output CSV Schema

One CSV file is written for every detected neuron.

Example filename

```text
times_manual_GA1-RA2_unit_5.csv
```

Columns

| Column | Type | Units | Description |
| --- | --- | --- | --- |
| `units` | integer | — | Cluster identifier |
| `s` | float | seconds | Spike time |

Formatting

- Spike times are written with four decimal places.
- Original spike timing precision is otherwise preserved.
- Rows remain in chronological order.

---

# Naming Conventions

Input

```text
times_manual_GA1-RA2.mat
```

Output

```text
times_manual_GA1-RA2_unit_1.csv

times_manual_GA1-RA2_unit_2.csv

times_manual_GA1-RA2_unit_3.csv
```

The naming convention intentionally matches the historical laboratory
workflow to maximize compatibility with existing scripts.

---

# Public Modules

## convert_matlab_to_csv.py

### Purpose

Convert a MATLAB spike sorting file into one CSV file per detected neuron.

### Inputs

- MATLAB v7.3 file
- `cluster_class`

### Outputs

- One CSV per neuron

### Side Effects

Creates CSV files in the selected output directory.

### Does

- Opens the MATLAB file.
- Reads `cluster_class`.
- Transposes the matrix.
- Groups spikes by unit.
- Skips Unit 0.
- Writes one CSV per neuron.

### Does Not

- Modify spike times.
- Modify unit numbers.
- Merge neurons.
- Perform analysis.

---

# Processing Pipeline

```text
times_manual.mat

↓

Open MATLAB file

↓

Read cluster_class

↓

Transpose matrix

↓

Separate spikes by unit

↓

Discard Unit 0

↓

Write one CSV per neuron
```

Each stage is intentionally explicit.

Intermediate transformations are kept simple so that failures are easy to
diagnose.

---

# Testing

The preprocessing module should be tested independently of the remainder
of the repository.

Recommended checks include:

- MATLAB file opens successfully.
- `cluster_class` exists.
- Matrix dimensions are correct.
- Unit 0 is excluded.
- Every remaining unit receives its own CSV.
- Spike times remain unchanged.
- CSV filenames follow the expected naming convention.

Future automated tests should verify these behaviors.

---

# Design Decisions

## Why use Python instead of MATLAB?

Removing the MATLAB dependency makes the repository easier to install,
maintain, and reproduce.

---

## Why assume MATLAB v7.3?

Supporting every historical MATLAB format would substantially complicate
the codebase.

The laboratory's current data are stored in MATLAB v7.3 format, making
this assumption reasonable.

---

## Why preserve the laboratory naming convention?

Many downstream scripts and historical analyses assume filenames of the
form

```text
times_manual_*_unit_#.csv
```

Maintaining this convention minimizes compatibility issues.

---

## Why discard Unit 0?

Unit 0 represents unsorted spikes and is not analyzed in the downstream
pipeline.

Discarding it during preprocessing simplifies every later stage of the
analysis.

---

## Why write one CSV per neuron?

This mirrors the behavior of the original monolithic workflow and greatly
simplifies neuron-by-neuron analyses.

---

# Common Failure Modes

| Problem | Likely Cause |
| --- | --- |
| MATLAB file cannot be opened | Incorrect MATLAB version or missing file |
| `cluster_class` missing | Unexpected spike sorting output |
| No CSV files produced | No valid units detected |
| Unit numbering incorrect | Unexpected `cluster_class` format |

---

# Future Work

Future enhancements may include:

- Batch conversion of multiple recording sessions.
- Parallel processing of large datasets.
- Optional metadata export.
- Additional validation checks.

Current status:

**Not implemented.**