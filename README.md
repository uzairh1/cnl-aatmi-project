# CNL AATMI Project

> Refactored neuroscience analysis pipeline for the UCLA CNL/Fried Lab
> naturalistic movie task.

## Purpose

This repository modernizes a legacy monolithic analysis script while
preserving its scientific behavior. The experimental paradigm
(naturalistic movie viewing, recognition task, spike alignment, and
neuron-level analyses) remains unchanged. The refactor focuses on
readability, modularity, testing, and maintainability.

## Repository Overview

``` text
preprocessing/      Convert raw MATLAB spike files to per-unit CSVs
data_io/            Read and standardize experiment metadata
analysis/           Statistical analyses (future)
plotting/           Raster/PSTH/summary figures (future)
tests/              Automated unit tests
test_scripts/       Manual debugging scripts
config.py           Configuration loading
models.py           Shared dataclasses
```

## Pipeline

1.  MATLAB `times_manual*.mat`
2.  `preprocessing/convert_matlab_to_csv.py`
3.  `times_manual_*_unit_#.csv`
4.  Raw `TTL_table.csv`
5.  `data_io/ttl_table_parser.py`
6.  `trial_table.csv`
7.  Localization workbook
8.  `data_io/localization.py`
9.  Standardized neuron metadata
10. Spike alignment, statistics, and plotting

## Major Inputs

  File                         Purpose
  ---------------------------- ----------------------------------
  `times_manual*.mat`          MATLAB v7.3 spike sorting output
  `TTL_table.csv`              Behavioral/event timing table
  `sub-*_localizations.xlsx`   Electrode localization workbook

## Major Outputs

  -----------------------------------------------------------------------------
  File                          Produced by             Purpose
  ----------------------------- ----------------------- -----------------------
  `times_manual_*_unit_#.csv`   preprocessing           Per-neuron spike trains

  `trial_table.csv`             ttl_table_parser        Canonical trial
                                                        metadata

  Raster/PSTH figures           plotting                Visualization
  -----------------------------------------------------------------------------

## Canonical Trial Table

Raw columns are preserved (`frameOn`, `frameOff`, `clipStartTime`,
`clipEndTime`, etc.).

Derived columns:

  Column              Meaning
  ------------------- -------------------------------------
  `clipStartTimeMs`   Clip start (ms)
  `clipEndTimeMs`     Clip end (ms)
  `clipDurationMs`    Duration (ms)
  `clipDurationSec`   Duration (s)
  `clipFrameRange`    `frameOn-frameOff`
  `clipTimeRangeMs`   `clipStartTimeMs-clipEndTimeMs`
  `clipWindowId`      `movieID-clipTimeRangeMs`
  `isAccurate`        Binary trial accuracy
  `trialOrder`        Chronological order after filtering
  `plotOrder`         Ordering used in rasters
  `includeInPlots`    Manual include/exclude flag

## Coding Philosophy

-   Preserve raw experimental data.
-   Derived values receive descriptive names.
-   Each module has one responsibility.
-   All I/O modules are independently testable.
-   Fake-data unit tests complement regression testing on real data.

## Installation



Create a virtual environment (recommended):

```bash

python -m venv .venv

```

Activate it:

Windows

`.venv\\Scripts\\activate`

macOS/Linux

`source .venv/bin/activate`

Install dependencies:

`pip install -r requirements.txt`

