# data_io

## Purpose

The `data_io` package is the canonical entry point for all experimental
metadata.

Modules in this package **read**, **standardize**, and **validate**
experimental inputs. They should not perform statistics or plotting.

------------------------------------------------------------------------

## ttl_table_parser.py

### Responsibility

Convert raw `TTL_table.csv` into the standardized `trial_table.csv`.

### Input

`TTL_table.csv`

Important raw columns:

-   experimentPhase
-   trialNumber
-   movieID
-   clipID
-   response
-   clipStartTime
-   clipEndTime
-   frameOn
-   frameOff
-   reactionTimePTB
-   trialStartTimePTB
-   trialEndTimePTB

### Output

`trial_table.csv`

Derived columns:

-   clipStartTimeMs
-   clipEndTimeMs
-   clipDurationMs
-   clipDurationSec
-   clipFrameRange
-   clipTimeRangeMs
-   clipWindowId
-   isAccurate
-   trialOrder
-   plotOrder
-   includeInPlots

### Public Functions

-   `load_ttl_table()`
-   `filter_trials()`
-   `derive_timing_columns()`
-   `_infer_accuracy()`
-   `derive_analysis_columns()`
-   `restore_plot_preferences()`
-   `save_trial_table()`
-   `build_trial_table()`

------------------------------------------------------------------------

## localization.py

### Responsibility

Infer anatomical localization for each neuron.

### Input

Localization workbook (`sub-*_localizations.xlsx`)

Typical important columns:

-   electrode
-   aparc+aseg
-   BIPOLAR
-   region
-   isMicro

### Output

Tuple:

1.  Electrode abbreviation
2.  Anatomical label
3.  Region abbreviation

### Public Functions

-   `load_localization_map()`
-   `infer_neuron_localization()`
-   `region_description()`

------------------------------------------------------------------------

## Design Rules

-   Never modify raw input files.
-   Preserve original column names whenever they originate from the
    experiment.
-   New columns must clearly indicate that they are derived.
