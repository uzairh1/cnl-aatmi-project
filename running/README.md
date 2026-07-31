# running

> Pipeline entry point and execution configuration.

---

# Table of Contents

- [Purpose](#purpose)
- [Responsibilities](#responsibilities)
- [Package Structure](#package-structure)
- [Current Files](#current-files)
- [Running](#running)
- [Execution Flow](#execution-flow)
- [Configuration](#configuration)
- [Summary](#summary)

---

# Purpose

The `running` package contains the files responsible for executing the
end-to-end analysis pipeline.

Unlike the remainder of the repository, these files do not implement
individual analysis algorithms.

Instead, they coordinate the execution order of the existing modules.

---

# Responsibilities

The package is responsible for

- defining patient/session configurations
- defining analysis-wide configuration
- executing the pipeline in the correct order
- providing a single entry point for running the repository
- providing a lightweight smoke test

The package does **not** implement preprocessing, metadata parsing,
alignment, statistical analyses, or plotting.

---

# Package Structure

```text
running/

├── patients.py

├── config.py

├── run_pipeline.py

├── test_run_on_patients.py

└── README.md
```

Each file has exactly one primary responsibility.

---

# Current Files

| File | Purpose | Status |
| --- | --- | --- |
| `patients.py` | Patient/session configuration objects | Complete |
| `config.py` | Analysis-wide configuration | Complete |
| `run_pipeline.py` | Execute the full pipeline | Complete |
| `test_run_on_patients.py` | Validate one complete pipeline run | Complete |

---

# Running

Run the complete pipeline

```bash
python running/run_pipeline.py \
    --output-root <output_directory>
```

Run a test

```bash
python running/test_run_on_patients.py \
    --output-root <output_directory>
```

Run a test for one patient

```bash
python running/test_run_on_patients.py \
    --output-root <output_directory> \
    --patient-id 570
```

---

# Execution Flow

The pipeline executes the following stages.

```text
PatientConfig

↓

TTL parser

↓

Align 1

↓

Align 2

↓

Binning

↓

Statistics

↓

Raster plots

↓

Swarm plots

↓

Summary figures
```

Each stage consumes the outputs of the previous stage.

---

# Configuration

Patient-specific settings are stored in

```text
patients.py
```

Typical parameters include

- patient identifier
- spike input directory
- localization workbook
- TTL table
- MATLAB reference time
- movie start time
- movie duration

Analysis-wide settings are stored in

```text
config.py
```

Typical parameters include

- pre-stimulus window
- post-stimulus window
- minimum firing rate
- significance threshold
- raster plotting window
- PSTH smoothing method

The pipeline imports these objects directly.

No JSON configuration files are required.

---

# Summary

The `running` package provides the executable entry point for the
repository.

It loads patient and analysis configuration objects, executes each stage
of the pipeline in sequence, and provides a simple smoke test for
end-to-end validation.
````