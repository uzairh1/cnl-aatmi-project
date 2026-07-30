# analysis

> Alignment layer for spike data.

## Purpose

The `analysis` package contains the alignment stages that sit between preprocessing/data_io and later statistical analysis.

## Current Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `session_alignment_align1.py` | Align per-unit spike CSVs to the movie/session timebase | Complete |
| `trial_alignment_align2.py` | Assign movie-aligned spikes to trial windows | Complete |
| `README.md` | Package documentation | Complete |

## Session Alignment (Align 1)

### Running
```bash
  python -m analysis.session_alignment_align1 \
  --input-dir "path/to/times_manual_unit_csvs" \
  --output-dir "path/to/align1_output" \
  --start-unix-0 [number] \
  --matlab [number] \
  --duration [number]
```
Example:

```bash
python -m analysis.session_alignment_align1 \
  --input-dir "C:/Users/Uzair/Desktop/CNL/patients/570 - new" \
  --output-dir "C:/Users/Uzair/Desktop/CNL/patients/new_script_output_570" \
  --start-unix-0 1706308502.2209392 \
  --matlab 1706304396.2999392 \
  --duration 2476.867
```

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

## Future Work

Not implemented:
- statistical analyses
- plotting
- population summaries
