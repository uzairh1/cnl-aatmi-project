# analysis

> Alignment layer for spike data.

## Purpose

The `analysis` package contains the alignment stages that sit between preprocessing/data_io and later statistical analysis.

## Current Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `session_alignment.py` | Align per-unit spike CSVs to the movie/session timebase | Complete |
| `trial_alignment.py` | Assign movie-aligned spikes to trial windows | Complete |
| `README.md` | Package documentation | Complete |

## Session Alignment (Align 1)

Inputs:
- per-unit CSVs from `preprocessing/`
- `start_unix_0`
- `matLab`
- `duration`

Output:
- `align1_*.csv`

Columns:
- `units`
- `spikeTimeRawS`
- `movieAlignedTimeS`
- `movieAlignedTimeMs`

Rule:
- keep spikes in the movie/session window
- subtract session start so movie onset is 0

## Trial Alignment (Align 2)

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

## Future Work

Not implemented:
- statistical analyses
- plotting
- population summaries
