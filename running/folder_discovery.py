"""
folder_discovery.py

Automatic patient-folder discovery and validation.

This module is intentionally independent of the scientific pipeline.

Responsibilities
----------------
1. Discover files inside one patient folder.
2. Validate that all required inputs exist.
3. Build the dictionary required by PatientConfig.
4. Automatically run preprocessing when neuron CSVs are absent.

This module performs NO scientific analysis.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from preprocessing.convert_matlab_to_csv import convert_folder


@dataclass(slots=True)
class FolderContents:
    """Files discovered inside one patient folder."""

    root: Path
    json_file: Path
    behavioral_table: Path
    localization_file: Path
    mat_files: list[Path]
    neuron_csvs: list[Path]


@dataclass(slots=True)
class ValidationReport:
    """Results of validating a patient folder."""

    errors: list[str]
    warnings: list[str]
    summary: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------
# JSON / numeric helpers
# ---------------------------------------------------------------------

def _is_missing_json_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple)) and len(value) == 0:
        return True
    try:
        if value.__class__.__name__ == 'NAType':
            return True
    except Exception:
        pass
    if isinstance(value, float) and math.isnan(value):
        return True
    if str(value).strip().upper() == '<NA>':
        return True
    return False


def _coerce_required_float(value: Any, field_name: str) -> float:
    """Convert a JSON field to float with a clear error if missing/invalid."""
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"Missing required JSON field: {field_name}")
        value = value[0]

    if _is_missing_json_value(value):
        raise ValueError(f"Missing required JSON field: {field_name}")

    try:
        out = float(value)
    except Exception as exc:
        raise ValueError(f"Invalid numeric JSON field {field_name}: {value!r}") from exc

    if math.isnan(out):
        raise ValueError(f"Invalid numeric JSON field {field_name}: {value!r}")

    return out


def _coerce_optional_float(value: Any, default: float) -> float:
    """Convert a JSON field to float, returning a default when missing."""
    if _is_missing_json_value(value):
        return default

    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return default
        value = value[0]

    try:
        out = float(value)
    except Exception:
        return default

    if math.isnan(out):
        return default

    return out


def _derive_run_metadata(contents: FolderContents) -> tuple[dict[str, Any], str, float]:
    with contents.json_file.open('r', encoding='utf-8') as f:
        meta = json.load(f)

    stem = contents.json_file.stem
    base_tag = stem.split('_movie')[0] if '_movie' in stem else stem
    output_tag = re.sub(r'^\d+_', '', base_tag)

    duration = 2476.867
    vid_segment = meta.get('vid_segment')
    if isinstance(vid_segment, (list, tuple)) and vid_segment:
        first_seg = vid_segment[0]
        if isinstance(first_seg, (list, tuple)) and len(first_seg) > 1:
            try:
                duration = _coerce_required_float(first_seg[1], 'vid_segment[0][1]')
            except Exception:
                pass

    return meta, output_tag, duration


# ---------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------

def _find_exactly_one(folder: Path, pattern: str) -> Path:
    matches = sorted(folder.glob(pattern))
    if len(matches) == 0:
        raise FileNotFoundError(f"No files matching '{pattern}' found in\n{folder}")
    if len(matches) > 1:
        raise RuntimeError(
            f"Expected exactly one '{pattern}' but found:\n" + "\n".join(str(p.name) for p in matches)
        )
    return matches[0]


def _find_behavioral_table(folder: Path) -> Path:
    """
    Prefer refined clip tables over legacy TTL tables.
    """

    refined = sorted(folder.glob("*clip*refined*.csv"))

    if refined:
        return refined[0]

    ttl_candidates = sorted(folder.glob("*TTL_table.csv"))

    if ttl_candidates:
        return ttl_candidates[0]

    raise FileNotFoundError(
        "Could not locate either a refined behavioral table "
        "or a *TTL_table.csv file."
    )


def _find_mat_files(folder: Path) -> list[Path]:
    mats = sorted(folder.glob('times_manual*.mat'))
    if not mats:
        raise FileNotFoundError('No times_manual*.mat files found.')
    return mats


def _find_preprocessed_csvs(folder: Path) -> list[Path]:
    return sorted(folder.glob('times_manual*_unit_*.csv'))


def discover_patient_folder(folder: str | Path) -> FolderContents:
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(folder)

    return FolderContents(
        root=folder,
        json_file=_find_exactly_one(folder, '*.json'),
        behavioral_table=_find_behavioral_table(folder),
        localization_file=_find_exactly_one(folder, 'sub-*_localizations.xlsx'),
        mat_files=_find_mat_files(folder),
        neuron_csvs=_find_preprocessed_csvs(folder),
    )


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def validate_patient_folder(contents: FolderContents) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    summary: list[str] = []

    summary.append(f'JSON: {contents.json_file.name}')
    if 'refined' in contents.behavioral_table.name.lower():
        summary.append(f'Behavioral table: {contents.behavioral_table.name} (Refined)')
    else:
        summary.append(f'Behavioral table: {contents.behavioral_table.name} (Legacy TTL)')
    summary.append(f'Localization: {contents.localization_file.name}')
    summary.append(f'MAT files: {len(contents.mat_files)}')

    if contents.neuron_csvs:
        summary.append(f'Neuron CSVs: {len(contents.neuron_csvs)} (already present)')
    else:
        warnings.append('No neuron CSVs detected. Preprocessing will be run.')

    try:
        with contents.json_file.open('r', encoding='utf-8') as f:
            meta = json.load(f)

        required = ['pID', 'rec_t0_unix', 'start_unix', 'gsheet_drift_rate']
        for key in required:
            if key not in meta:
                errors.append(f"JSON missing '{key}'")

        try:
            _coerce_required_float(meta.get('rec_t0_unix'), 'rec_t0_unix')
        except Exception as exc:
            errors.append(str(exc))
        try:
            _coerce_required_float(meta.get('start_unix'), 'start_unix')
        except Exception as exc:
            errors.append(str(exc))
        try:
            _coerce_required_float(meta.get('gsheet_drift_rate'), 'gsheet_drift_rate')
        except Exception as exc:
            errors.append(str(exc))
    except Exception as exc:
        errors.append(f'Could not parse JSON ({exc})')

    return ValidationReport(errors=errors, warnings=warnings, summary=summary)


def print_validation_report(report: ValidationReport) -> None:
    print()
    print('=' * 70)
    print('Patient Folder Validation')
    print('=' * 70)

    for line in report.summary:
        print(f'✓ {line}')
    for line in report.warnings:
        print(f'! {line}')
    for line in report.errors:
        print(f'X {line}')

    print('=' * 70)
    print('Validation PASSED.' if report.ok else 'Validation FAILED.')
    print()


# ---------------------------------------------------------------------
# PatientConfig construction
# ---------------------------------------------------------------------

def build_patient_dict(contents: FolderContents) -> dict:
    meta, output_tag, duration = _derive_run_metadata(contents)

    return {
        'patient_id': str(meta.get('pID', '')),
        'movie_label': '24',
        'signal_path': str(contents.root),
        'clip_ttl_csv': str(contents.behavioral_table),
        'localization_file': str(contents.localization_file),
        'output_tag': output_tag,
        'matLab': _coerce_required_float(meta.get('rec_t0_unix'), 'rec_t0_unix'),
        'start_unix_0': _coerce_required_float(meta.get('start_unix'), 'start_unix'),
        'duration': duration,
        'fps': _coerce_optional_float(meta.get('fps'), 29.97),
        'drift_rate_slope': _coerce_required_float(meta.get('gsheet_drift_rate'), 'gsheet_drift_rate'),
        'event_time_offset_ms': 0.0,
    }


# ---------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------

def run_preprocessing_if_needed(contents: FolderContents) -> None:
    if contents.neuron_csvs:
        print(f'Found {len(contents.neuron_csvs)} neuron CSVs.')
        print('Skipping preprocessing.')
        return

    print()
    print('No neuron CSVs detected.')
    print('Running preprocessing...')
    print()

    convert_folder(contents.root)

    print()
    print('Preprocessing complete.')


def print_run_summary(contents: FolderContents, report: ValidationReport) -> None:
    meta, output_tag, duration = _derive_run_metadata(contents)
    fps = _coerce_optional_float(meta.get('fps'), 29.97)
    matlab_t0 = _coerce_required_float(meta.get('rec_t0_unix'), 'rec_t0_unix')
    start_unix = _coerce_required_float(meta.get('start_unix'), 'start_unix')
    drift_rate = _coerce_required_float(meta.get('gsheet_drift_rate'), 'gsheet_drift_rate')

    print()
    print('=' * 72)
    print('Pipeline Validation')
    print('=' * 72)

    print(f'Patient folder     : {contents.root}')
    print(f'Metadata JSON      : {contents.json_file.name}')
    print(f'Behavioral table   : {contents.behavioral_table.name}')
    print(f'Localization       : {contents.localization_file.name}')

    print()
    print(f'Patient ID         : {meta.get("pID", "")}')
    print('Movie              : 24')
    print(f'Output tag         : {output_tag}')

    print()
    print('Pipeline Parameters')
    print('-------------------')
    print(f'signal_path        : {contents.root}')
    print(f'clip_ttl_csv       : {contents.behavioral_table}')
    print(f'localization_file  : {contents.localization_file}')
    print(f'patient_id         : {meta.get("pID", "")}')
    print('movie_label        : 24')
    print(f'matLab             : {matlab_t0!r}')
    print(f'start_unix_0       : {start_unix!r}')
    print(f'duration           : {duration!r}')
    print(f'fps                : {fps!r}')
    print(f'drift_rate_slope   : {drift_rate!r}')
    print(f'output_tag         : {output_tag}')

    print()
    print(f'MAT files          : {len(contents.mat_files)}')
    print(f'Neuron CSVs        : {len(contents.neuron_csvs)}')

    if contents.neuron_csvs:
        print('Preprocessing      : skipped (existing CSVs found)')
    else:
        print('Preprocessing      : WILL RUN (no existing CSVs found)')

    print()
    if report.warnings:
        print('Warnings')
        for w in report.warnings:
            print(f'  ! {w}')
        print()
    if report.errors:
        print('Errors')
        for e in report.errors:
            print(f'  X {e}')
        print()

    print('=' * 72)
    print('Validation PASSED.' if report.ok else 'Validation FAILED.')
    print('=' * 72)
    print()


def confirm_run(report: ValidationReport) -> bool:
    if not report.ok:
        print('Errors were found. Pipeline aborted.')
        return False
    answer = input('Proceed with pipeline? [Y/n]: ').strip().lower()
    return answer in ('', 'y', 'yes')