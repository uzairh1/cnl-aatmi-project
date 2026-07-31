"""Legacy-style movie/session binning for Align 1 outputs."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

DEFAULT_BIN_SIZE_S = 10


def load_align1_csv(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    if 'ms' not in df.columns:
        if 'movieAlignedTimeMs' in df.columns:
            df = df.copy()
            df['ms'] = pd.to_numeric(df['movieAlignedTimeMs'], errors='coerce')
        elif 'movieAlignedTimeS' in df.columns:
            df = df.copy()
            df['ms'] = pd.to_numeric(df['movieAlignedTimeS'], errors='coerce') * 1000.0
        else:
            raise ValueError(f"{csv_path.name} is missing required column 'ms' or 'movieAlignedTimeMs'")
    out = df.copy()
    out['ms'] = pd.to_numeric(out['ms'], errors='coerce')
    out = out.dropna(subset=['ms']).copy()
    return out


def bin_firing_rate_from_df(df: pd.DataFrame, bin_size_s: int = DEFAULT_BIN_SIZE_S) -> pd.DataFrame:
    if bin_size_s <= 0:
        raise ValueError('bin_size_s must be positive')
    if df.empty:
        return pd.DataFrame(columns=[f'bin_{bin_size_s}s', 'spike_count', 'firing_rate_hz'])
    if 'ms' not in df.columns:
        raise ValueError("DataFrame must contain 'ms'")
    s = pd.to_numeric(df['ms'], errors='coerce').dropna().to_numpy(dtype=float) / 1000.0
    if s.size == 0:
        return pd.DataFrame(columns=[f'bin_{bin_size_s}s', 'spike_count', 'firing_rate_hz'])
    bin_idx = np.floor(s / float(bin_size_s)).astype(int)
    counts = pd.Series(bin_idx).value_counts().sort_index()
    maxbin = int(counts.index.max()) if len(counts) else 0
    full_index = pd.Index(range(0, maxbin + 1), name=f'bin_{bin_size_s}s')
    counts = counts.reindex(full_index, fill_value=0)
    out = counts.reset_index(name='spike_count')
    out['firing_rate_hz'] = out['spike_count'] / float(bin_size_s)
    return out


def bin_firing_rate(csv_path: str | Path, bin_size_s: int = DEFAULT_BIN_SIZE_S) -> pd.DataFrame:
    return bin_firing_rate_from_df(load_align1_csv(csv_path), bin_size_s=bin_size_s)


def bin_align1_file(align1_csv_path: str | Path, output_csv_path: str | Path, bin_size_s: int = DEFAULT_BIN_SIZE_S) -> Path:
    align1_csv_path = Path(align1_csv_path)
    output_csv_path = Path(output_csv_path)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    binned_df = bin_firing_rate(align1_csv_path, bin_size_s=bin_size_s)
    binned_df.to_csv(output_csv_path, index=False)
    return output_csv_path


def bin_align1_folder(align1_dir: str | Path, output_dir: str | Path, bin_size_s: int = DEFAULT_BIN_SIZE_S) -> list[Path]:
    align1_dir = Path(align1_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    for csv_path in sorted(align1_dir.glob('align1_*.csv')):
        out_path = output_dir / csv_path.name.replace('.csv', f'_binned_{bin_size_s}s.csv')
        outs.append(bin_align1_file(csv_path, out_path, bin_size_s=bin_size_s))
    return outs


def main() -> int:
    p = argparse.ArgumentParser(description='Bin Align 1 movie-aligned spikes into fixed-width firing-rate tables.')
    p.add_argument('--align1-dir', required=True)
    p.add_argument('--output-dir', required=True)
    p.add_argument('--bin-size-s', type=int, default=DEFAULT_BIN_SIZE_S)
    args = p.parse_args()
    outs = bin_align1_folder(args.align1_dir, args.output_dir, bin_size_s=args.bin_size_s)
    print(f'Wrote {len(outs)} binned CSV files to {args.output_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())