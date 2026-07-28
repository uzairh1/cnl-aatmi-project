# Stage 0 Preprocessing

This folder contains the first step of the Movie SME pipeline.

## What this step does

- reads `times_manual*.mat` files produced by Wave_Clus / the lab export
- reads the `cluster_class` dataset from each file
- transposes the data when needed
- splits spikes by unit
- writes one CSV per unit using the existing naming convention:
  - `times_manual*_unit_#.csv`
- skips `unit 0` during conversion

## Assumed input format

The `.mat` files are expected to be MATLAB v7.3 / HDF5 files.
After transpose, `cluster_class` is treated as:

- column 0: unit number
- column 1: spike time in seconds
- column 2: ignored

## Dependencies

Install the preprocessing dependency with:

```bash
conda install -c conda-forge h5py
```

## Current scope

This stage only handles conversion from `.mat` to per-unit CSVs.
The later Python analysis steps will consume those CSVs.
