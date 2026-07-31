"""Legacy-style neuron statistics for Align 1 outputs."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import chisquare, ttest_ind, ttest_1samp

DEFAULT_POST_WINDOW_MS = (200, 1200)
DEFAULT_PRE_WINDOW_MS = (-1000, 0)
DEFAULT_MIN_RATE_HZ = 0.25
DEFAULT_ALPHA = 0.05
DEFAULT_SIG_T_SCORE = 1.96


def load_clip_table(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip() for c in df.columns]
    out = df.copy()

    rename_map = {}
    if 'clipStartTimeMs' in out.columns and 'ms start' not in out.columns:
        rename_map['clipStartTimeMs'] = 'ms start'
    if 'clipEndTimeMs' in out.columns and 'ms end' not in out.columns:
        rename_map['clipEndTimeMs'] = 'ms end'
    if 'isAccurate' in out.columns and 'Accurate' not in out.columns:
        rename_map['isAccurate'] = 'Accurate'
    if 'plotOrder' in out.columns and 'Plot Y-Axis' not in out.columns:
        rename_map['plotOrder'] = 'Plot Y-Axis'
    if 'includeInPlots' in out.columns and 'Plot Toggle' not in out.columns:
        rename_map['includeInPlots'] = 'Plot Toggle'
    if rename_map:
        out = out.rename(columns=rename_map)

    for col in ['ms start', 'ms end']:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors='coerce')
    if 'Accurate' in out.columns:
        out['Accurate'] = pd.to_numeric(out['Accurate'], errors='coerce').fillna(0).astype(int)
    if 'Plot Y-Axis' in out.columns:
        out['Plot Y-Axis'] = pd.to_numeric(out['Plot Y-Axis'], errors='coerce')
    if 'Plot Toggle' in out.columns:
        out['Plot Toggle'] = pd.to_numeric(out['Plot Toggle'], errors='coerce').fillna(1).astype(int)
    return out


def _load_align1_for_stats(df_or_path) -> pd.DataFrame:
    if isinstance(df_or_path, (str, Path)):
        df = pd.read_csv(df_or_path)
    else:
        df = df_or_path.copy()
    if 'ms' not in df.columns:
        if 'movieAlignedTimeMs' in df.columns:
            df['ms'] = pd.to_numeric(df['movieAlignedTimeMs'], errors='coerce')
        elif 'movieAlignedTimeS' in df.columns:
            df['ms'] = pd.to_numeric(df['movieAlignedTimeS'], errors='coerce') * 1000.0
        else:
            raise ValueError("Align 1 data must contain 'ms' or 'movieAlignedTimeMs'")
    df['ms'] = pd.to_numeric(df['ms'], errors='coerce')
    return df.dropna(subset=['ms']).copy()


def compute_rate_hz_in_window(spikes_ms: np.ndarray, clips_df: pd.DataFrame, win_start: int, win_end: int) -> Optional[float]:
    dur_s = (win_end - win_start) / 1000.0
    if dur_s <= 0 or clips_df.empty:
        return None
    total_spikes = 0
    valid_clips = 0
    for _, row in clips_df.iterrows():
        start = row.get('ms start')
        if pd.isna(start):
            continue
        start = float(start)
        abs_start = start + win_start
        abs_end = start + win_end
        total_spikes += int(np.sum((spikes_ms >= abs_start) & (spikes_ms <= abs_end)))
        valid_clips += 1
    if valid_clips == 0:
        return None
    return float(total_spikes) / (valid_clips * dur_s)


def compute_correct_vs_wrong_ttest(spikes_ms: np.ndarray, clips_df: pd.DataFrame, window_start_ms: int, window_end_ms: int, alpha: float = DEFAULT_ALPHA, significance_method: str = 'p_value') -> Dict[str, object]:
    correct_rates: List[float] = []
    incorrect_rates: List[float] = []
    window_dur_s = (window_end_ms - window_start_ms) / 1000.0
    if window_dur_s <= 0:
        return {'ok': False, 'p_value': None, 't_stat': None, 'n_correct': 0, 'n_incorrect': 0, 'significant': False}
    for _, clip_row in clips_df.reset_index(drop=True).iterrows():
        start_ms = clip_row.get('ms start')
        if pd.isna(start_ms):
            continue
        start_ms = float(start_ms)
        abs_start = start_ms + window_start_ms
        abs_end = start_ms + window_end_ms
        spike_count = int(np.sum((spikes_ms >= abs_start) & (spikes_ms <= abs_end)))
        rate_hz = spike_count / window_dur_s
        accurate = int(clip_row.get('Accurate', 0)) if pd.notna(clip_row.get('Accurate')) else 0
        if accurate == 1:
            correct_rates.append(rate_hz)
        else:
            incorrect_rates.append(rate_hz)
    if len(correct_rates) < 2 or len(incorrect_rates) < 2:
        return {'ok': False, 'p_value': None, 't_stat': None, 'n_correct': len(correct_rates), 'n_incorrect': len(incorrect_rates), 'significant': False}
    t_stat, p_value = ttest_ind(correct_rates, incorrect_rates, equal_var=False, nan_policy='omit')
    if np.isnan(t_stat) or np.isnan(p_value):
        return {'ok': False, 'p_value': None, 't_stat': None, 'n_correct': len(correct_rates), 'n_incorrect': len(incorrect_rates), 'significant': False}
    if significance_method == 't_score':
        is_sig = bool(abs(t_stat) >= DEFAULT_SIG_T_SCORE)
    else:
        is_sig = bool(p_value < alpha)
    return {'ok': True, 'p_value': float(p_value), 't_stat': float(t_stat), 'n_correct': len(correct_rates), 'n_incorrect': len(incorrect_rates), 'significant': is_sig}


def build_neuron_summary_row(align1_df: pd.DataFrame, clips_df: pd.DataFrame, neuron_name: str, patient_id: str, output_tag: str = '', min_rate_hz: float = DEFAULT_MIN_RATE_HZ, pre_window_ms: tuple[int, int] = DEFAULT_PRE_WINDOW_MS, post_window_ms: tuple[int, int] = DEFAULT_POST_WINDOW_MS, alpha: float = DEFAULT_ALPHA, significance_method: str = 'p_value') -> Optional[dict]:
    if align1_df.empty:
        return None
    df = _load_align1_for_stats(align1_df)
    if df.empty or 'ms' not in df.columns:
        return None
    spikes_ms = pd.to_numeric(df['ms'], errors='coerce').dropna().to_numpy()
    if len(spikes_ms) == 0:
        return None
    post_rate_hz = compute_rate_hz_in_window(spikes_ms, clips_df, post_window_ms[0], post_window_ms[1])
    if post_rate_hz is None or post_rate_hz < min_rate_hz:
        return None
    pre_test = compute_correct_vs_wrong_ttest(spikes_ms, clips_df, pre_window_ms[0], pre_window_ms[1], alpha=alpha, significance_method=significance_method)
    post_test = compute_correct_vs_wrong_ttest(spikes_ms, clips_df, post_window_ms[0], post_window_ms[1], alpha=alpha, significance_method=significance_method)
    pre_t = pre_test.get('t_stat')
    pre_p = pre_test.get('p_value')
    pre_sig = pre_test.get('significant', False)
    post_t = post_test.get('t_stat')
    post_p = post_test.get('p_value')
    post_sig = post_test.get('significant', False)
    return {
        'Patient': f'P{patient_id}' if not output_tag else f'P{patient_id}_{output_tag}',
        'Neuron Name': neuron_name,
        'Pre-Stim T-Score': pre_t,
        'Pre-Stim P-Value': pre_p,
        'Pre-Stim Significant': pre_sig,
        'Post-Stim T-Score': post_t,
        'Post-Stim P-Value': post_p,
        'Post-Stim Significant': post_sig,
        'T-Score Diff (Pre - Post)': (pre_t - post_t) if (pre_t is not None and post_t is not None) else None,
        'Post-Stim Mean Rate (Hz)': post_rate_hz,
        'N Clips': int(clips_df.shape[0]),
    }


def analyze_align1_file(align1_csv_path: str | Path, clips_df: pd.DataFrame, patient_id: str, output_tag: str = '', min_rate_hz: float = DEFAULT_MIN_RATE_HZ, pre_window_ms: tuple[int, int] = DEFAULT_PRE_WINDOW_MS, post_window_ms: tuple[int, int] = DEFAULT_POST_WINDOW_MS, alpha: float = DEFAULT_ALPHA, significance_method: str = 'p_value') -> Optional[dict]:
    align1_csv_path = Path(align1_csv_path)
    align1_df = pd.read_csv(align1_csv_path)
    neuron_name = align1_csv_path.name.replace('align1_', '').replace('.csv', '')
    return build_neuron_summary_row(
        align1_df=align1_df,
        clips_df=clips_df,
        neuron_name=neuron_name,
        patient_id=patient_id,
        output_tag=output_tag,
        min_rate_hz=min_rate_hz,
        pre_window_ms=pre_window_ms,
        post_window_ms=post_window_ms,
        alpha=alpha,
        significance_method=significance_method,
    )


def analyze_align1_folder(align1_dir: str | Path, clips_df: pd.DataFrame, patient_id: str, output_csv: str | Path, output_tag: str = '', min_rate_hz: float = DEFAULT_MIN_RATE_HZ, pre_window_ms: tuple[int, int] = DEFAULT_PRE_WINDOW_MS, post_window_ms: tuple[int, int] = DEFAULT_POST_WINDOW_MS, alpha: float = DEFAULT_ALPHA, significance_method: str = 'p_value') -> pd.DataFrame:
    align1_dir = Path(align1_dir)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for csv_path in sorted(align1_dir.glob('align1_*.csv')):
        summary = analyze_align1_file(
            csv_path,
            clips_df=clips_df,
            patient_id=patient_id,
            output_tag=output_tag,
            min_rate_hz=min_rate_hz,
            pre_window_ms=pre_window_ms,
            post_window_ms=post_window_ms,
            alpha=alpha,
            significance_method=significance_method,
        )
        if summary is not None:
            rows.append(summary)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(output_csv, index=False)
    return out_df


def population_chisq_vs_chance(df: pd.DataFrame, metric_col: str, thresh: Optional[float] = None, sig_col: Optional[str] = None) -> dict:
    df_clean = df.dropna(subset=[metric_col]).copy()
    if df_clean.empty:
        return {'N Total': 0, 'Mean': None, 'SEM': None, 'Sig Positive': 0, 'Sig Negative': 0, 'Total Sig': 0, 'Expected Sig (5%)': 0, 'Chi2 Stat': None, 'P-Value': None}
    N = len(df_clean)
    mean_val = df_clean[metric_col].mean()
    sem_val = df_clean[metric_col].sem()
    if sig_col and sig_col in df_clean.columns:
        sig_mask = df_clean[sig_col] == True
        n_sig_pos = int((sig_mask & (df_clean[metric_col] > 0)).sum())
        n_sig_neg = int((sig_mask & (df_clean[metric_col] < 0)).sum())
    elif thresh is not None:
        n_sig_pos = int((df_clean[metric_col] >= thresh).sum())
        n_sig_neg = int((df_clean[metric_col] <= -thresh).sum())
    else:
        n_sig_pos = n_sig_neg = 0
    n_sig = n_sig_pos + n_sig_neg
    n_nonsig = N - n_sig
    expected_sig = N * 0.05
    expected_nonsig = N * 0.95
    if expected_sig > 0:
        chi2, p_val = chisquare([n_sig, n_nonsig], f_exp=[expected_sig, expected_nonsig])
    else:
        chi2, p_val = None, None
    return {'N Total': N, 'Mean': mean_val, 'SEM': sem_val, 'Sig Positive': n_sig_pos, 'Sig Negative': n_sig_neg, 'Total Sig': n_sig, 'Expected Sig (5%)': expected_sig, 'Chi2 Stat': chi2, 'P-Value': p_val}


def population_chisq_vs_5050(df: pd.DataFrame, metric_col: str) -> dict:
    df_clean = df.dropna(subset=[metric_col]).copy()
    if df_clean.empty:
        return {'N Total': 0, 'Mean': None, 'SEM': None, 'Pre-Driven (>0)': 0, 'Post-Driven (<0)': 0, 'Exact Zero': 0, 'Valid N (excluding 0)': 0, 'Expected (50/50)': 0, 'Chi2 Stat': None, 'P-Value': None}
    N = len(df_clean)
    mean_val = df_clean[metric_col].mean()
    sem_val = df_clean[metric_col].sem()
    n_pre_driven = int((df_clean[metric_col] > 0).sum())
    n_post_driven = int((df_clean[metric_col] < 0).sum())
    n_exact_zero = int((df_clean[metric_col] == 0).sum())
    valid_N = n_pre_driven + n_post_driven
    expected = valid_N / 2.0
    if expected > 0:
        chi2, p_val = chisquare([n_pre_driven, n_post_driven], f_exp=[expected, expected])
    else:
        chi2, p_val = None, None
    return {'N Total': N, 'Mean': mean_val, 'SEM': sem_val, 'Pre-Driven (>0)': n_pre_driven, 'Post-Driven (<0)': n_post_driven, 'Exact Zero': n_exact_zero, 'Valid N (excluding 0)': valid_N, 'Expected (50/50)': expected, 'Chi2 Stat': chi2, 'P-Value': p_val}


def population_one_sample_ttest(df: pd.DataFrame, metric_col: str, popmean: float = 0.0) -> dict:
    df_clean = df.dropna(subset=[metric_col]).copy()
    if df_clean.empty:
        return {'N Total': 0, 'Mean': None, 'SEM': None, 'T Stat': None, 'P-Value': None, 'PopMean': popmean}
    values = pd.to_numeric(df_clean[metric_col], errors='coerce').dropna().to_numpy(dtype=float)
    if values.size < 2:
        return {'N Total': int(values.size), 'Mean': float(values.mean()) if values.size else None, 'SEM': float(pd.Series(values).sem()) if values.size else None, 'T Stat': None, 'P-Value': None, 'PopMean': popmean}
    t_stat, p_val = ttest_1samp(values, popmean, nan_policy='omit')
    return {'N Total': int(values.size), 'Mean': float(values.mean()), 'SEM': float(pd.Series(values).sem()), 'T Stat': float(t_stat), 'P-Value': float(p_val), 'PopMean': popmean}


def analyze_population_table(summary_csv: str | Path, metric_col: str, test_mode: str, thresh: Optional[float] = None, sig_col: Optional[str] = None, popmean: float = 0.0) -> dict:
    df = pd.read_csv(summary_csv)
    if test_mode == 'chisq_vs_chance':
        return population_chisq_vs_chance(df, metric_col=metric_col, thresh=thresh, sig_col=sig_col)
    if test_mode == 'chisq_vs_5050':
        return population_chisq_vs_5050(df, metric_col=metric_col)
    if test_mode == 'one_sample_ttest':
        return population_one_sample_ttest(df, metric_col=metric_col, popmean=popmean)
    raise ValueError(f'Unknown test_mode: {test_mode}')


def main() -> int:
    p = argparse.ArgumentParser(description='Compute legacy-style neuron statistics from Align 1 CSVs.')
    p.add_argument('--align1-dir', required=True)
    p.add_argument('--clips-table', required=True)
    p.add_argument('--patient-id', required=True)
    p.add_argument('--output-csv', required=True)
    p.add_argument('--output-tag', default='')
    p.add_argument('--min-rate-hz', type=float, default=DEFAULT_MIN_RATE_HZ)
    p.add_argument('--pre-window-start-ms', type=int, default=DEFAULT_PRE_WINDOW_MS[0])
    p.add_argument('--pre-window-end-ms', type=int, default=DEFAULT_PRE_WINDOW_MS[1])
    p.add_argument('--post-window-start-ms', type=int, default=DEFAULT_POST_WINDOW_MS[0])
    p.add_argument('--post-window-end-ms', type=int, default=DEFAULT_POST_WINDOW_MS[1])
    p.add_argument('--alpha', type=float, default=DEFAULT_ALPHA)
    p.add_argument('--significance-method', choices=['p_value','t_score'], default='p_value')
    p.add_argument('--population-test-mode', choices=['chisq_vs_chance','chisq_vs_5050','one_sample_ttest'], default='chisq_vs_chance')
    p.add_argument('--population-popmean', type=float, default=0.0)
    args = p.parse_args()
    clips_df = load_clip_table(args.clips_table)
    out_df = analyze_align1_folder(
        align1_dir=args.align1_dir,
        clips_df=clips_df,
        patient_id=args.patient_id,
        output_csv=args.output_csv,
        output_tag=args.output_tag,
        min_rate_hz=args.min_rate_hz,
        pre_window_ms=(args.pre_window_start_ms, args.pre_window_end_ms),
        post_window_ms=(args.post_window_start_ms, args.post_window_end_ms),
        alpha=args.alpha,
        significance_method=args.significance_method,
    )
    print(f'Wrote {len(out_df)} neuron summary rows to {args.output_csv}')
    pop_summary = analyze_population_table(args.output_csv, metric_col='T-Score Diff (Pre - Post)', test_mode=args.population_test_mode, popmean=args.population_popmean)
    print(f'Population summary mode: {args.population_test_mode}')
    print(pop_summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())