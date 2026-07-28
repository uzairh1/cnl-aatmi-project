###### 0.25 HZ and T test printing ######


import os
import re
import glob
import math
import shutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
from scipy.stats import ttest_ind, gaussian_kde, chisquare


# =============================================================================
# USER EDIT SECTION
# =============================================================================
PATIENT_CONFIGS: List[Dict[str, object]] = [
{
   "patient_id": "566",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/566TMexp7presleep",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/566TMexp7presleep/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-566_localizations.xlsx",
   "output_tag": "exp7presleep",
   "matLab": 1691272807.193047,
   "start_unix_0": 1691273171.2970471,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "567",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/567TMexp8presleep",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/567TMexp8presleep/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-567_localizations.xlsx",
   "output_tag": "exp8presleep",
   "matLab": 1692747794.1907692,
   "start_unix_0": 1692748176.5677693,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "568",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/568TMexp5presleep",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/568TMexp5presleep/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-568_localizations.xlsx",
   "output_tag": "exp5presleep",
   "matLab": 1700603867.2240472,
   "start_unix_0": 1700604469.2170877,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "570",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/570TMexp4presleep",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/570TMexp4presleep/570_TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-570_localizations.xlsx",
   "output_tag": "exp4presleep",
   "matLab": 1706304396.2999392,
   "start_unix_0": 1706308502.2209392,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "572",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/572TMexp9presleepviewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/572TMexp9presleepviewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-572_localizations.xlsx",
   "output_tag": "exp9presleepviewing",
   "matLab": 1711142763.6770148,
   "start_unix_0": 1711143392.781015,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "573",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/573TMexp7presleepviewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/573TMexp7presleepviewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-573_localizations.xlsx",
   "output_tag": "exp7presleepviewing",
   "matLab": 1714775636.2359192,
   "start_unix_0": 1714775660.3849192,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "574",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/574TMexp10viewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/574TMexp10viewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-574_localizations.xlsx",
   "output_tag": "exp10viewing",
   "matLab": 1721747817.881015,
   "start_unix_0": 1721747828.862015,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "576",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/576TMexp14Viewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/576TMexp14Viewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-576_localizations.xlsx",
   "output_tag": "exp14Viewing",
   "matLab": 1726515700.953,
   "start_unix_0": 1726515776.9090002,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "577",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/577TMexp4viewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/577TMexp4viewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-577_localizations.xlsx",
   "output_tag": "exp4viewing",
   "matLab": 1726269951.420004,
   "start_unix_0": 1726269994.518004,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "579",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/579TMexp6viewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/579TMexp6viewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-579_localizations.xlsx",
   "output_tag": "exp6viewing",
   "matLab": 1734025549.335989,
   "start_unix_0": 1734025573.176989,
   "duration": 2476.867,
   "fps": 29.97
},
{
   "patient_id": "582",
   "movie_label": "24",
   "signal_path": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/582TMexp8viewing",
   "clip_ttl_csv": "/Users/aatmi/Aatmi CML work/Clip Capstone alignments/582TMexp8viewing/TTL_table.csv",
   "localization_file": "/Users/aatmi/Desktop/UCLA/CNL Capstone/Pipeline spreadsheets/sub-582_localizations.xlsx",
   "output_tag": "exp8viewing",
   "matLab": 1742751241.165916,
   "start_unix_0": 1742751270.809916,
   "duration": 2476.867,
   "fps": 29.97
}
]


# Toggle output steps
CREATE_SEEN_FRAMES_FILE = True
CREATE_ALIGN1_FILES = True
CREATE_ALIGN2_FILES = True
CREATE_RASTER_PLOTS = True


# Global output dirs for significance
BASE_OUTPUT_DIR = Path("/Users/aatmi/Aatmi CML work/Clip Capstone alignments")
AGGREGATE_DIR = BASE_OUTPUT_DIR / "Aggregate Patients outputs"
ALL_SIG_DIR = AGGREGATE_DIR / "All significant plots"
ALL_NON_SIG_DIR = AGGREGATE_DIR / "All Non significant plots"


# Global CSV paths mapped to new smart names
GLOBAL_CSV_PATH = AGGREGATE_DIR / "Aggregate T score sheet across patients.csv"
GLOBAL_SIG_CSV_PATH = ALL_SIG_DIR / "Aggregate significant T score sheet.csv"
GLOBAL_NONSIG_CSV_PATH = ALL_NON_SIG_DIR / "Aggregate non significant T score sheet.csv"


# Bipolar Mapping Dictionary (Strict 1-to-1 Mapping for Labels)
BIPOLAR_REGIONS = {
   "AMY": "amygdala",
   "BAS": "basal ganglia (putamen, pallidum)",
   "CC": "anterior cingulate cortex",
   "CENT": "pre-/para/POST-central (motor) cortex",
   "ERC": "entorhinal cortex",
   "FC": "frontal cortex (includes SFG, MFG, IFG, OFC)",
   "FUS": "fusiform cortex",
   "HPC": "hippocampus",
   "INS": "insula",
   "LTC": "lateral temporal cortex (includes STG, MTG, IFG, banksSTS and TP)",
   "MCC": "to differentiate from ACC (includes MCC and PCC)",
   "PARS": "pars orbitalis/triangularis/opercularis",
   "PC": "parietal cortex (precuneus, inferiorparietal, somatosensory, supramarginal)",
   "PHC": "parahippocampal gyrus (parahippocampal, perirhinal)",
   "UNKNOWN": "Unknown",
   "VIS": "visual cortex (includes lingual, pericalcarine, cuneus)",
   "WM": "white matter"
}


# The explicit targeted output folders requested
TARGET_FOLDERS = {
   "HPC": ["HPC"],
   "ERC": ["ERC"],
   "FC": ["FC"],
   "LTC": ["LTC"],
   "MTL": ["AMY", "ERC", "HPC", "PHC"]  # MTL acts as the macro grouping
}


# Raster appearance
RASTER_FIGSIZE: Tuple[float, float] = (12, 8)
RASTER_DPI = 200
LINE_LENGTH = 0.8
LINE_WIDTH = 0.6


# PSTH settings
PSTH_BIN_MS = 100
PSTH_LINE_WIDTH = 2.0


# Colors
COLOR_ALL = "black"
COLOR_CORRECT = "green"    # Right
COLOR_INCORRECT = "red"    # Wrong
COLOR_CLIP_END = "blue"


# Extended window settings
NEG3_TO_5_START_MS = -3000
NEG3_TO_5_END_MS = 5000
CLIP_END_MARKER_HALF_HEIGHT = 0.32


# Extra folder outputs & SME math variables
MIN_RATE_HZ_FOR_FILTERED_FOLDERS = 0.25
TTEST_WINDOW_START_MS = 200
TTEST_WINDOW_END_MS = 1200
PRE_WINDOW_START_MS = -1000
PRE_WINDOW_END_MS = 0
TTEST_ALPHA = 0.05


# Significance Method Toggle
# "t_score" = Visual standard. Any T-score >= 1.96 or <= -1.96 is marked True. (Matches graphs perfectly)
# "p_value" = Strict math. Only exact P-values < 0.05 are marked True. (May hide some T>2 neurons if variance is high)
SIGNIFICANCE_METHOD = "p_value"




# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def load_localization_map(file_path: str) -> pd.DataFrame:
   if not os.path.exists(file_path):
       print(f"Warning: Localization file not found at {file_path}")
       return pd.DataFrame()
  
   df = pd.read_excel(file_path)
   df.columns = [str(col).strip() for col in df.columns]
  
   if 'electrode' in df.columns:
       df = df[df['electrode'].astype(str).str.contains('micro', case=False, na=False)]
      
   return df




def get_neuron_localization(neuron_filename: str, loc_df: pd.DataFrame) -> Tuple[str, str, str]:
   if loc_df.empty:
       return "Unknown", "Unknown Location", "UNKNOWN"


   match_hyphen = re.search(r"-([a-zA-Z]+)", neuron_filename)
   if match_hyphen:
       abbr = match_hyphen.group(1).upper()
   else:
       match_no_hyphen = re.search(r"([a-zA-Z]+)[0-9]*", neuron_filename)
       abbr = match_no_hyphen.group(1).upper() if match_no_hyphen else "UNKNOWN"
  
   row = loc_df[loc_df['electrode'].astype(str).str.upper().str.startswith(abbr + "_")]
  
   if row.empty:
       row = loc_df[loc_df['electrode'].astype(str).str.upper().str.contains(abbr)]
  
   if not row.empty:
       electrode_code = abbr
       full_name = str(row.iloc[0].get('aparc+aseg', 'Unknown Location'))
      
       # Robust fetch 3-letter region abbr from 'bipolar' column
       region_abbr = "UNKNOWN"
       bipolar_cols = [c for c in loc_df.columns if 'bipolar' in str(c).lower()]
       if bipolar_cols:
           val = str(row.iloc[0][bipolar_cols[0]]).strip().upper()
           if val in BIPOLAR_REGIONS:
               region_abbr = val
           else:
               region_abbr = val # Might be something outside the list, keep exact code
       else:
           # Fallback
           for c in loc_df.columns:
               if 'region' in str(c).lower():
                   region_abbr = str(row.iloc[0][c]).strip().upper()
                   break


       return electrode_code, full_name, region_abbr


   return abbr, "Unknown Location", "UNKNOWN"




def extract_patient_number_from_path(path_str: str) -> Optional[str]:
   match = re.search(r"(?<!\d)(\d{3})(?!\d)", Path(path_str).name)
   return match.group(1) if match else None




def frames_to_ms(frame_value: object, fps: float) -> Optional[int]:
   try:
       if pd.isna(frame_value): return None
       return int(round((float(frame_value) / fps) * 1000.0))
   except (TypeError, ValueError):
       return None




def find_spike_time_column(df: pd.DataFrame) -> Optional[str]:
   df.columns = [str(col).strip() for col in df.columns]
   if "s" in df.columns:
       return "s"
   if len(df.columns) >= 2:
       return df.columns[1]
   return None




def list_raw_neuron_csvs(raw_signal_dir: str, ttl_csv_path: str) -> List[str]:
   all_csvs = sorted(glob.glob(os.path.join(raw_signal_dir, "*.csv")))
   ttl_name = Path(ttl_csv_path).name.lower()


   raw_files: List[str] = []
   for csv_path in all_csvs:
       name = Path(csv_path).name.lower()
       if name == ttl_name or name.startswith("align1_") or name.startswith("align2_") or "seen frames to ms" in name or "ttl" in name:
           continue
       # Exclusion for Unit 0 files
       if "unit_0" in name:
           continue
          
       raw_files.append(csv_path)


   return raw_files




def _list_valid_align1_files(align1_dir: str) -> List[Path]:
   all_files = sorted(Path(align1_dir).glob("*.csv"))
   valid_files: List[Path] = []
   for file_path in all_files:
       name = file_path.name.lower()
       if not name.startswith("align1_") or "ttl" in name or "seen frames to ms" in name:
           continue
       # Exclusion for Unit 0 files
       if "unit_0" in name:
           continue
          
       valid_files.append(file_path)


   return valid_files




def _safe_clip_id(clip_row: pd.Series, fallback_index: int) -> object:
   if "clipID" in clip_row and pd.notna(clip_row["clipID"]):
       return clip_row["clipID"]
   return fallback_index + 1




def _extract_clip_rows_for_window(
   spikes_ms: np.ndarray,
   clips_df: pd.DataFrame,
   window_start_ms: int,
   window_end_ms: int,
) -> List[Dict[str, object]]:
   plot_rows: List[Dict[str, object]] = []


   for clip_index, clip_row in clips_df.reset_index(drop=True).iterrows():
       start_ms = clip_row.get("ms start")
       end_ms = clip_row.get("ms end")


       if pd.isna(start_ms) or pd.isna(end_ms):
           continue


       start_ms = float(start_ms)
       end_ms = float(end_ms)
       clip_duration_ms = end_ms - start_ms


       abs_window_start = start_ms + window_start_ms
       abs_window_end = start_ms + window_end_ms


       in_window = spikes_ms[(spikes_ms >= abs_window_start) & (spikes_ms <= abs_window_end)]
       aligned_spikes = (in_window - start_ms).tolist()


       plot_rows.append(
           {
               "clip_index": clip_index + 1,
               "clipID": _safe_clip_id(clip_row, clip_index),
               "accurate": int(clip_row.get("Accurate", 0)) if pd.notna(clip_row.get("Accurate")) else 0,
               "clip_duration_ms": clip_duration_ms,
               "clip_end_marker_ms": clip_duration_ms,
               "aligned_spikes_ms": aligned_spikes,
               # Carry the designated Plot Y-Axis number over for the raster tick labels
               "plot_y_axis": int(clip_row.get("Plot Y-Axis", clip_index + 1)),
           }
       )


   return plot_rows




def _compute_psth_hz(
   clip_rows: List[List[float]],
   x_min: int,
   x_max: int,
   bin_ms: int,
) -> Tuple[np.ndarray, np.ndarray]:
   edges = np.arange(x_min, x_max + bin_ms, bin_ms)
   if len(edges) < 2:
       edges = np.array([x_min, x_max], dtype=float)
   centers = edges[:-1] + (np.diff(edges) / 2.0)


   n_trials = len(clip_rows)
   if n_trials == 0:
       return centers, np.zeros(len(centers), dtype=float)


   counts_per_trial = np.zeros((n_trials, len(edges) - 1), dtype=float)


   for i, row in enumerate(clip_rows):
       if len(row) == 0:
           continue
       counts, _ = np.histogram(np.asarray(row, dtype=float), bins=edges)
       counts_per_trial[i, :] = counts


   psth_hz = counts_per_trial.mean(axis=0) / (bin_ms / 1000.0)
   return centers, psth_hz




def _compute_smoothed_psth_hz(
   clip_rows: List[List[float]],
   x_min: int,
   x_max: int,
   bin_ms: int = 100,
   smooth_type: str = "none",
) -> Tuple[np.ndarray, np.ndarray]:
   all_spikes = np.concatenate([r for r in clip_rows if len(r) > 0]) if any(len(r) > 0 for r in clip_rows) else np.array([])
   n_trials = len(clip_rows)


   if len(all_spikes) < 2 or n_trials == 0:
       edges = np.arange(x_min, x_max + bin_ms, bin_ms)
       if len(edges) < 2:
           edges = np.array([x_min, x_max], dtype=float)
       centers = edges[:-1] + (np.diff(edges) / 2.0)
       return centers, np.zeros(len(centers), dtype=float)


   if smooth_type == "gaussian_kde":
       centers = np.linspace(x_min, x_max, max(200, int((x_max - x_min) / 10)))
       try:
           kde = gaussian_kde(all_spikes, bw_method='scott')
           y_hz = kde.evaluate(centers) * 1000.0 * (len(all_spikes) / n_trials)
           return centers, y_hz
       except np.linalg.LinAlgError:
           pass


   elif smooth_type == "bin_resize_trial_1":
       small_bin = 50
       edges = np.arange(x_min, x_max + small_bin, small_bin)
       if len(edges) < 2:
           edges = np.array([x_min, x_max], dtype=float)
       centers = edges[:-1] + (np.diff(edges) / 2.0)


       counts, _ = np.histogram(all_spikes, bins=edges)
       raw_hz = (counts / n_trials) / (small_bin / 1000.0)


       window_len = 7
       sigma = 1.5
       x_arr = np.arange(-window_len//2 + 1, window_len//2 + 1)
       kernel = np.exp(-0.5 * (x_arr / sigma)**2)
       kernel = kernel / kernel.sum()


       smooth_hz = np.convolve(raw_hz, kernel, mode='same')
       return centers, smooth_hz


   small_bin = 25
   edges = np.arange(x_min, x_max + small_bin, small_bin)
   if len(edges) < 2:
       edges = np.array([x_min, x_max], dtype=float)
   centers = edges[:-1] + (np.diff(edges) / 2.0)


   counts, _ = np.histogram(all_spikes, bins=edges)
   raw_hz = (counts / n_trials) / (small_bin / 1000.0)


   window_len = 11
   triangle = np.concatenate([np.arange(1, (window_len//2)+2), np.arange(window_len//2, 0, -1)])
   triangle = triangle / triangle.sum()


   smooth_hz = np.convolve(raw_hz, triangle, mode='same')
   return centers, smooth_hz




def _sort_rows_accuracy_top_bottom(
   plot_rows: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], int]:
   correct_rows = [row for row in plot_rows if row["accurate"] == 1]
   incorrect_rows = [row for row in plot_rows if row["accurate"] == 0]
   return correct_rows + incorrect_rows, len(correct_rows)




def _draw_clip_end_markers(
   ax: plt.Axes,
   plot_rows: List[Dict[str, object]],
   x_max: int,
) -> None:
   for row_idx, row in enumerate(plot_rows):
       clip_end_x = float(row.get("clip_end_marker_ms", 0))
       shade_end = min(clip_end_x, x_max)
       if shade_end > 0:
           ax.barh(y=row_idx, width=shade_end, left=0, height=1.0, color='lightgreen', alpha=0.3, zorder=0, edgecolor='none')




def _has_any_spikes(plot_rows: List[Dict[str, object]]) -> bool:
   return any(len(row["aligned_spikes_ms"]) > 0 for row in plot_rows)




def _compute_rate_hz_in_window(spikes_ms: np.ndarray, clips_df: pd.DataFrame, win_start: int, win_end: int) -> Optional[float]:
   """Computes specific firing rate in a designated window (e.g. 200-1200ms) across all valid active clips."""
   dur_s = (win_end - win_start) / 1000.0
   if dur_s <= 0 or clips_df.empty:
       return None


   total_spikes = 0
   valid_clips = 0
   for _, row in clips_df.iterrows():
       start = row.get("ms start")
       if pd.isna(start): continue
       start = float(start)
       abs_start = start + win_start
       abs_end = start + win_end
       total_spikes += np.sum((spikes_ms >= abs_start) & (spikes_ms <= abs_end))
       valid_clips += 1
      
   if valid_clips == 0: return None
   return float(total_spikes) / (valid_clips * dur_s)




def _compute_correct_vs_wrong_ttest(
   spikes_ms: np.ndarray,
   clips_df: pd.DataFrame,
   window_start_ms: int,
   window_end_ms: int,
) -> Dict[str, object]:
   correct_rates: List[float] = []
   incorrect_rates: List[float] = []
   window_dur_s = (window_end_ms - window_start_ms) / 1000.0


   if window_dur_s <= 0:
       return {"ok": False, "p_value": None, "t_stat": None, "n_correct": 0, "n_incorrect": 0, "significant": False}


   for _, clip_row in clips_df.reset_index(drop=True).iterrows():
       start_ms = clip_row.get("ms start")
       if pd.isna(start_ms):
           continue


       start_ms = float(start_ms)
       abs_start = start_ms + window_start_ms
       abs_end = start_ms + window_end_ms
       spike_count = int(np.sum((spikes_ms >= abs_start) & (spikes_ms <= abs_end)))
       rate_hz = spike_count / window_dur_s


       accurate = int(clip_row.get("Accurate", 0)) if pd.notna(clip_row.get("Accurate")) else 0
       if accurate == 1:
           correct_rates.append(rate_hz)
       else:
           incorrect_rates.append(rate_hz)


   if len(correct_rates) < 2 or len(incorrect_rates) < 2:
       return {"ok": False, "p_value": None, "t_stat": None, "n_correct": len(correct_rates), "n_incorrect": len(incorrect_rates), "significant": False}


   t_stat, p_value = ttest_ind(correct_rates, incorrect_rates, equal_var=False, nan_policy="omit")
   if np.isnan(t_stat) or np.isnan(p_value):
       return {"ok": False, "p_value": None, "t_stat": None, "n_correct": len(correct_rates), "n_incorrect": len(incorrect_rates), "significant": False}


   # STANDARD: Align mathematically defined significance exactly to visual threshold
   if SIGNIFICANCE_METHOD == "t_score":
       is_sig = bool(abs(t_stat) >= 1.96)
   else:
       is_sig = bool(p_value < TTEST_ALPHA)


   return {
       "ok": True,
       "p_value": float(p_value),
       "t_stat": float(t_stat),
       "n_correct": len(correct_rates),
       "n_incorrect": len(incorrect_rates),
       "significant": is_sig,
   }




def _plot_raster_with_optional_split_and_psth(
   plot_rows: List[Dict[str, object]],
   out_path: Path,
   patient_id: str,
   neuron_name: str,
   title_suffix: str,
   x_min: int,
   x_max: int,
   split_by_accuracy: bool,
   show_clip_end_marker: bool,
   ttest_label: str = "",
   loc_df: pd.DataFrame = pd.DataFrame(),
   output_tag: str = "",
   sig_status_str: str = "nonsig",
   smooth_type: str = "none",
) -> Optional[Path]:
   if len(plot_rows) == 0:
       return None


   if split_by_accuracy:
       plot_rows, n_correct = _sort_rows_accuracy_top_bottom(plot_rows)
       raster_rows = [row["aligned_spikes_ms"] for row in plot_rows]
       raster_colors = [
           COLOR_CORRECT if row["accurate"] == 1 else COLOR_INCORRECT
           for row in plot_rows
       ]
   else:
       n_correct = 0
       raster_rows = [row["aligned_spikes_ms"] for row in plot_rows]
       raster_colors = COLOR_ALL


   if not any(len(row) > 0 for row in raster_rows):
       return None


   y_labels = [str(row.get("plot_y_axis", i+1)) for i, row in enumerate(plot_rows)]


   electrode_code, full_location, region_abbr = get_neuron_localization(neuron_name, loc_df)
   clean_loc = str(electrode_code).replace(" ", "_")
  
   bipolar_desc = BIPOLAR_REGIONS.get(region_abbr, "UNKNOWN")
   loc_bipolar_str = f"{region_abbr} - {bipolar_desc}"
  
   std_filename = f"P{patient_id}_{output_tag}_{clean_loc}_{neuron_name}_neg3_to_5_{sig_status_str}.png"
  
   base_ind_rasters_dir = out_path.parent.parent
   plot_folder_name = out_path.parent.name
  
   fig = plt.figure(figsize=RASTER_FIGSIZE)
   gs = GridSpec(2, 1, height_ratios=[4.6, 1.4], hspace=0.08)


   ax_raster = fig.add_subplot(gs[0])
   ax_psth = fig.add_subplot(gs[1], sharex=ax_raster)


   ax_raster.eventplot(
       raster_rows,
       colors=raster_colors,
       linelengths=LINE_LENGTH,
       linewidths=LINE_WIDTH,
       zorder=3,
   )


   if show_clip_end_marker:
       _draw_clip_end_markers(ax_raster, plot_rows, x_max)


   if split_by_accuracy and 0 < n_correct < len(plot_rows):
       ax_raster.axhline(n_correct - 0.5, color="0.5", linestyle="--", linewidth=1, zorder=4)


   ax_raster.axvline(0, color="0.5", linestyle="--", linewidth=1, zorder=4)
   ax_psth.axvline(0, color="0.5", linestyle="--", linewidth=1)


   title_lines = [
       f"Patient {patient_id} | {full_location} ({electrode_code}) | Region: {loc_bipolar_str} | Neuron {neuron_name}",
       title_suffix,
   ]
   if ttest_label:
       title_lines.append(ttest_label)


   newline = chr(10)
   full_title = newline.join(title_lines)
   ax_raster.set_title(full_title, fontsize=14)
   ax_raster.set_ylabel("Clip Plot Y-Axis", fontsize=12)
   ax_raster.set_xlim(x_min, x_max)


   n_rows = len(plot_rows)
   if n_rows <= 40:
       tick_positions = list(range(n_rows))
   else:
       step = max(1, n_rows // 20)
       tick_positions = list(range(0, n_rows, step))
   ax_raster.set_yticks(tick_positions)
   ax_raster.set_yticklabels([y_labels[i] for i in tick_positions])
   ax_raster.grid(axis="x", linestyle=":", alpha=0.4)


   if split_by_accuracy:
       correct_rows = [row["aligned_spikes_ms"] for row in plot_rows if row["accurate"] == 1]
       incorrect_rows = [row["aligned_spikes_ms"] for row in plot_rows if row["accurate"] == 0]


       if len(correct_rows) > 0:
           if smooth_type == "none":
               x_c, y_c = _compute_psth_hz(correct_rows, x_min, x_max, PSTH_BIN_MS)
           else:
               x_c, y_c = _compute_smoothed_psth_hz(correct_rows, x_min, x_max, PSTH_BIN_MS, smooth_type)
           ax_psth.plot(x_c, y_c, linewidth=PSTH_LINE_WIDTH, color=COLOR_CORRECT, label="Correct (Green)")


       if len(incorrect_rows) > 0:
           if smooth_type == "none":
               x_i, y_i = _compute_psth_hz(incorrect_rows, x_min, x_max, PSTH_BIN_MS)
           else:
               x_i, y_i = _compute_smoothed_psth_hz(incorrect_rows, x_min, x_max, PSTH_BIN_MS, smooth_type)
           ax_psth.plot(x_i, y_i, linewidth=PSTH_LINE_WIDTH, color=COLOR_INCORRECT, label="Incorrect (Red)")


       ax_psth.legend(frameon=False, fontsize=10, loc="upper right")
   else:
       if smooth_type == "none":
           x_all, y_all = _compute_psth_hz(raster_rows, x_min, x_max, PSTH_BIN_MS)
       else:
           x_all, y_all = _compute_smoothed_psth_hz(raster_rows, x_min, x_max, PSTH_BIN_MS, smooth_type)
       ax_psth.plot(x_all, y_all, linewidth=PSTH_LINE_WIDTH, color=COLOR_ALL)


   ax_psth.set_xlabel("Time from clip start (ms)", fontsize=12)
   ax_psth.set_ylabel("Hz", fontsize=12)
   ax_psth.grid(axis="x", linestyle=":", alpha=0.4)


   fig.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.09, hspace=0.08)
  
   window_dir = out_path.parent
  
   all_rasters_dir = window_dir / "All Rasters"
   os.makedirs(all_rasters_dir, exist_ok=True)
   final_file_path = all_rasters_dir / std_filename
   plt.savefig(final_file_path, dpi=RASTER_DPI, bbox_inches="tight")
  
   is_sig_overall = "nonsig" not in sig_status_str
   status_folder_name = "Significant" if is_sig_overall else "Non Significant"
   status_dir = window_dir / status_folder_name
   os.makedirs(status_dir, exist_ok=True)
   shutil.copy(final_file_path, status_dir / std_filename)
  
   global_target = ALL_SIG_DIR if is_sig_overall else ALL_NON_SIG_DIR
   os.makedirs(global_target, exist_ok=True)
   shutil.copy(final_file_path, global_target / std_filename)


   # Route specifically to the 5 requested TARGET_FOLDERS
   for region_name, abbr_list in TARGET_FOLDERS.items():
       if region_abbr in abbr_list:
           region_raster_dir = AGGREGATE_DIR / f"{region_name} plots" / "Individual_Rasters"
           os.makedirs(region_raster_dir, exist_ok=True)
           shutil.copy(final_file_path, region_raster_dir / std_filename)


   plt.close(fig)
   return final_file_path




# =============================================================================
# STEP 1: BUILD PATIENT-SPECIFIC CLIP FILE
# =============================================================================
def build_seen_frames_table(
   clip_ttl_csv: str,
   fps: float,
   patient_id: Optional[str] = None,
   output_tag: str = "",
) -> Tuple[pd.DataFrame, Path]:
   df = pd.read_csv(clip_ttl_csv)
   df.columns = [str(col).strip() for col in df.columns]


   col_map = {c.lower(): c for c in df.columns}
   std_names = {
       "movieid": "movieID", "clipid": "clipID", "response": "response",
       "reactiontimeptb": "reactionTimePTB", "frameon": "frameOn",
       "frameoff": "frameOff", "clipstarttime": "clipStartTime", "clipendtime": "clipEndTime"
   }
  
   for lower_col, standard_col in std_names.items():
       if lower_col in col_map and col_map[lower_col] != standard_col:
           df.rename(columns={col_map[lower_col]: standard_col}, inplace=True)


   if "movieID" in df.columns:
       df_movie = df.copy()
       df_movie["movieID"] = pd.to_numeric(df_movie["movieID"], errors="coerce")
       movie1_df = df_movie[df_movie["movieID"] == 1].copy()
       if not movie1_df.empty: df = movie1_df
       else: print(f"    [!] Warning: movieID == 1 yielded 0 rows. Using all available rows as a fallback.")


   if df.empty:
       print(f"    [!] Warning: TTL file has NO rows after filtering.")


   if "frameOn" in df.columns and "frameOff" in df.columns:
       df["frameOn"] = pd.to_numeric(df["frameOn"], errors="coerce")
       df["frameOff"] = pd.to_numeric(df["frameOff"], errors="coerce")
      
       df["ms start"] = df["frameOn"].apply(lambda x: frames_to_ms(x, fps))
       df["ms end"] = df["frameOff"].apply(lambda x: frames_to_ms(x, fps))
       df["clip duration ms"] = df["ms end"] - df["ms start"]
       df["frame range"] = df["frameOn"].astype(str) + "-" + df["frameOff"].astype(str)
       df["ms range"] = df["ms start"].astype(str) + "-" + df["ms end"].astype(str)
       df["ms ID"] = "1-" + df["ms range"]
   else:
       print(f"    [!] Warning: TTL file is missing 'frameOn' or 'frameOff' columns.")


   acc_col_candidates = [c for c in df.columns if c.lower() in ["accurate", "accuracy"]]
   if acc_col_candidates:
       df["Accurate"] = pd.to_numeric(df[acc_col_candidates[0]], errors="coerce").fillna(0).astype(int)
   elif "response" in df.columns:
       df["Accurate"] = (df["response"].astype(str).str.replace(".0", "", regex=False).str.strip() == "2").astype(int)
   else:
       df["Accurate"] = 0


   patient_number = extract_patient_number_from_path(clip_ttl_csv) or patient_id
   tag_suffix = f" - {output_tag}" if output_tag else ""
   output_filename = f"P{patient_number}{tag_suffix} - seen frames to ms.csv"
   output_path = Path(clip_ttl_csv).parent / output_filename


   # Traceability & Plotting logic
   if "Accurate" in df.columns:
       df['Chronological Index'] = range(1, len(df) + 1)
       correct_mask = df['Accurate'] == 1
       incorrect_mask = df['Accurate'] == 0
       df.loc[correct_mask, 'Plot Y-Axis'] = range(1, correct_mask.sum() + 1)
       df.loc[incorrect_mask, 'Plot Y-Axis'] = range(correct_mask.sum() + 1, len(df) + 1)
       df['Plot Y-Axis'] = df['Plot Y-Axis'].astype(int)
   else:
       df['Plot Y-Axis'] = range(1, len(df) + 1)
      
   df['Plot Toggle'] = 1
  
   if str(patient_id) == "573":
       df.loc[df['Plot Y-Axis'].isin([43, 45]), 'Plot Toggle'] = 0


   if output_path.exists():
       try:
           old_df = pd.read_csv(output_path)
           if 'Plot Toggle' in old_df.columns and 'ms ID' in old_df.columns:
               toggle_map = old_df.set_index('ms ID')['Plot Toggle'].to_dict()
               df['Plot Toggle'] = df['ms ID'].map(toggle_map).fillna(df['Plot Toggle']).astype(int)
       except Exception as e:
           print(f"    [!] Could not read existing Plot Toggles from past file: {e}")


   desired_columns = [
       "movieID", "clipID", "response", "Accurate", "reactionTimePTB",
       "frameOn", "frameOff", "clipStartTime", "clipEndTime",
       "ms start", "ms end", "clip duration ms", "frame range", "ms range", "ms ID",
       "Plot Y-Axis", "Plot Toggle"
   ]
  
   final_columns = [col for col in desired_columns if col in df.columns]
   final_df = df[final_columns].copy()
   final_df.to_csv(output_path, index=False)


   return final_df, output_path




# =============================================================================
# STEP 2: GLOBAL ALIGNMENT
# =============================================================================
def align_firing_with_movie(
   signal_path: str,
   ttl_csv_path: str,
   output_dir: str,
   time_start: float,
   time_end: float,
) -> List[Path]:
   raw_files = list_raw_neuron_csvs(signal_path, ttl_csv_path)
   os.makedirs(output_dir, exist_ok=True)
   saved_files: List[Path] = []


   for file in raw_files:
       df = pd.read_csv(file)
       df.columns = [str(col).strip() for col in df.columns]
       spike_col = find_spike_time_column(df)
       if spike_col is None: continue
       if spike_col != "s": df.rename(columns={spike_col: "s"}, inplace=True)


       df["s"] = pd.to_numeric(df["s"], errors="coerce")
       df = df.dropna(subset=["s"]).copy()
       df = df[(df["s"] >= time_start) & (df["s"] <= time_end)].copy()
       df["s"] = df["s"] - time_start
       df["ms"] = df["s"] * 1000.0


       keep_cols = [col for col in ["units", "ms"] if col in df.columns]
       if not keep_cols: keep_cols = ["ms"]
       df = df[keep_cols].copy()
       output_file = Path(output_dir) / f"align1_{Path(file).name}"
       df.to_csv(output_file, index=False)
       saved_files.append(output_file)


   return saved_files




# =============================================================================
# STEP 3: CLIP ALIGNMENT (LONG-FORM ALIGN 2)
# =============================================================================
def build_clip_aligned_spike_table(align1_file: Path, clips_df: pd.DataFrame) -> pd.DataFrame:
   neuron_df = pd.read_csv(align1_file)
   neuron_df.columns = [str(col).strip() for col in neuron_df.columns]
   spikes_ms = pd.to_numeric(neuron_df.get("ms", []), errors="coerce").dropna().to_numpy()
   rows: List[Dict[str, object]] = []
   if clips_df.empty: return pd.DataFrame()


   for clip_index, clip_row in clips_df.reset_index(drop=True).iterrows():
       start_ms = clip_row.get("ms start")
       end_ms = clip_row.get("ms end")
       if pd.isna(start_ms) or pd.isna(end_ms): continue


       in_clip = spikes_ms[(spikes_ms >= start_ms) & (spikes_ms <= end_ms)]
       for spike_ms in in_clip:
           rows.append({
               "clip_index": clip_index + 1,
               "clipID": clip_row.get("clipID", clip_index + 1),
               "Accurate": clip_row.get("Accurate", None),
               "clip_ms_start": start_ms,
               "clip_ms_end": end_ms,
               "clip_duration_ms": end_ms - start_ms,
               "spike_ms_global": spike_ms,
               "spike_ms_from_clip_start": spike_ms - start_ms,
           })


   return pd.DataFrame(rows)




def save_align2_tables(align1_dir: str, align2_dir: str, clips_df: pd.DataFrame) -> List[Path]:
   os.makedirs(align2_dir, exist_ok=True)
   align1_files = _list_valid_align1_files(align1_dir)
   saved_files: List[Path] = []
   for align1_file in align1_files:
       clip_aligned_df = build_clip_aligned_spike_table(align1_file, clips_df)
       output_path = Path(align2_dir) / f"align2_{align1_file.name}"
       clip_aligned_df.to_csv(output_path, index=False)
       saved_files.append(output_path)
   return saved_files




# =============================================================================
# SWARM PLOTS & STATISTICAL EXPORT
# =============================================================================
def _create_swarm_and_stats(df: pd.DataFrame, metric_col: str, plot_id: str, title_label: str, thresh: Optional[float], out_dir: Path, stats_rows: List[Dict], test_type: str, sig_col: Optional[str] = None):
   df_clean = df.dropna(subset=[metric_col]).copy()
   if df_clean.empty:
       return
      
   N = len(df_clean)
   mean_val = df_clean[metric_col].mean()
   sem_val = df_clean[metric_col].sem()
  
   stat_dict = {
       "Plot ID": plot_id,
       "Metric": metric_col,
       "N Total": N,
       "Mean": mean_val,
       "SEM": sem_val,
   }
  
   if test_type == "chisq_vs_chance":
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
          
       stat_dict.update({
           "Sig Positive": n_sig_pos,
           "Sig Negative": n_sig_neg,
           "Total Sig": n_sig,
           "Expected Sig (5%)": expected_sig,
           "Chi2 Stat": chi2,
           "P-Value": p_val
       })
      
   elif test_type == "chisq_vs_5050":
       n_pre_driven = (df_clean[metric_col] > 0).sum()
       n_post_driven = (df_clean[metric_col] < 0).sum()
       n_exact_zero = (df_clean[metric_col] == 0).sum()
      
       valid_N = n_pre_driven + n_post_driven
       expected = valid_N / 2.0
      
       if expected > 0:
           chi2, p_val = chisquare([n_pre_driven, n_post_driven], f_exp=[expected, expected])
       else:
           chi2, p_val = None, None
          
       stat_dict.update({
           "Pre-Driven (>0)": n_pre_driven,
           "Post-Driven (<0)": n_post_driven,
           "Exact Zero": n_exact_zero,
           "Valid N (excluding 0)": valid_N,
           "Expected (50/50)": expected,
           "Chi2 Stat": chi2,
           "P-Value": p_val
       })
      
   stats_rows.append(stat_dict)
  
   # -----------------------------
   # Plot Generation
   # -----------------------------
   fig = plt.figure(figsize=(7, 8))
   gs = GridSpec(1, 2, width_ratios=[4, 1.5], wspace=0.05)
   ax_swarm = fig.add_subplot(gs[0])
   ax_hist = fig.add_subplot(gs[1], sharey=ax_swarm)
  
   df_clean['Group'] = 'Neurons'
   sns.stripplot(
       x='Group', y=metric_col, data=df_clean,
       color='#2c3e50', size=4.0, alpha=0.6, jitter=0.25,
       edgecolor='white', linewidth=0.3, zorder=2, ax=ax_swarm
   )
  
   ax_swarm.errorbar(
       x=0, y=mean_val, yerr=sem_val,
       color='#e74c3c', capsize=6, elinewidth=2.5, capthick=2.5,
       marker='_', markersize=18, label='Mean ± SEM', zorder=4
   )
  
   # Margin Histogram
   ax_hist.hist(df_clean[metric_col], bins=30, orientation='horizontal', color='gray', alpha=0.7)
   ax_hist.tick_params(axis='y', left=False, labelleft=False)
   ax_hist.set_xlabel('Count')
  
   if thresh is not None:
       ax_swarm.axhline(thresh, color='#3498db', linestyle='--', alpha=0.6, label=f'Significance Guide (+/- {thresh})')
       ax_swarm.axhline(-thresh, color='#3498db', linestyle='--', alpha=0.6)
       ax_hist.axhline(thresh, color='#3498db', linestyle='--', alpha=0.6)
       ax_hist.axhline(-thresh, color='#3498db', linestyle='--', alpha=0.6)
      
   ax_swarm.axhline(0, color='gray', linestyle='-', alpha=0.3)
   ax_hist.axhline(0, color='gray', linestyle='-', alpha=0.3)
  
   ax_swarm.set_title(f"{title_label}", fontsize=13, pad=20)
   ax_swarm.set_ylabel(metric_col, fontsize=12)
   ax_swarm.set_xlabel("")
   ax_swarm.set_xticks([])
  
   sns.despine(ax=ax_swarm, bottom=True)
   sns.despine(ax=ax_hist, left=True, bottom=False)
  
   ax_swarm.legend(frameon=True, loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2)
   ax_swarm.grid(axis='y', linestyle='-', alpha=0.15)
  
   filename = f"{plot_id}.png"
   plt.savefig(out_dir / filename, dpi=300, bbox_inches='tight')
   plt.close()




def generate_population_swarm_plot():
   if not GLOBAL_CSV_PATH.exists() or GLOBAL_CSV_PATH.stat().st_size == 0:
       print("Global CSV data missing or empty. Cannot generate Swarm plot.")
       return


   df = pd.read_csv(GLOBAL_CSV_PATH)
   if df.empty: return


   regions = {
       "Global": None,
       **TARGET_FOLDERS
   }


   summary_overview_data = []


   for region_name, abbr_list in regions.items():
       if region_name == "Global":
           df_sub = df.copy()
           out_dir = AGGREGATE_DIR
       else:
           if "Localization - Bipolar" not in df.columns:
               continue
           pattern = "^(?:" + "|".join(abbr_list) + ") -"
           df_sub = df[df["Localization - Bipolar"].str.contains(pattern, case=False, na=False)].copy()
           out_dir = AGGREGATE_DIR / f"{region_name} plots"
      
       if df_sub.empty:
           continue
          
       out_dir.mkdir(parents=True, exist_ok=True)
       stats_rows = []
      
       _create_swarm_and_stats(
           df_sub, "Post-Stim T-Score", "P1_Post-Stim_T-Scores",
           f"[{region_name}] Stim-Locked Post-Clip (200-1200ms)\nT-Scores", 1.96, out_dir, stats_rows, test_type="chisq_vs_chance", sig_col="Post-Stim Significant"
       )
      
       _create_swarm_and_stats(
           df_sub, "Pre-Stim T-Score", "P2_Pre-Stim_T-Scores",
           f"[{region_name}] Pre-Stimulus (-1000 to 0ms)\nT-Scores", 1.96, out_dir, stats_rows, test_type="chisq_vs_chance", sig_col="Pre-Stim Significant"
       )
      
       df_p3 = df_sub[(df_sub['Pre-Stim Significant'] == True) | (df_sub['Post-Stim Significant'] == True)]
       _create_swarm_and_stats(
           df_p3, "T-Score Diff (Pre - Post)", "P3_Diff_SigOnly",
           f"[{region_name}] T-Score Diff (Pre - Post)\n[Significant Pre OR Post Neurons]", None, out_dir, stats_rows, test_type="chisq_vs_5050"
       )
      
       _create_swarm_and_stats(
           df_sub, "T-Score Diff (Pre - Post)", "P4_Diff_All",
           f"[{region_name}] T-Score Diff (Pre - Post)\n[All Active Neurons]", None, out_dir, stats_rows, test_type="chisq_vs_5050"
       )
      
       df_p5 = df_sub[df_sub["Post-Stim T-Score"] >= 1.0]
       _create_swarm_and_stats(
           df_p5, "T-Score Diff (Pre - Post)", "P5_Diff_Post_GTE_1",
           f"[{region_name}] T-Score Diff (Pre - Post)\n[Post-Stim T-Score >= +1.0]", None, out_dir, stats_rows, test_type="chisq_vs_5050"
       )
      
       if stats_rows:
           pd.DataFrame(stats_rows).to_csv(out_dir / f"Swarm_Statistics_{region_name}.csv", index=False)
           print(f"Generated {region_name} Swarm Plots and Saved Statistics to {out_dir.name}")


       sig_pre_count = df_sub['Pre-Stim Significant'].sum() if 'Pre-Stim Significant' in df_sub.columns else 0
       sig_post_count = df_sub['Post-Stim Significant'].sum() if 'Post-Stim Significant' in df_sub.columns else 0
      
       region_summary = {
           "Scope": region_name,
           "Total Patients": df_sub['Patient'].nunique() if 'Patient' in df_sub.columns else 0,
           "Total Neurons": len(df_sub),
           "Significant Pre (-1000 to 0)": sig_pre_count,
           "Significant Post (200-1200)": sig_post_count
       }
       summary_overview_data.append(region_summary)


       if region_name != "Global":
           pd.DataFrame([region_summary]).to_csv(out_dir / f"Summary_Overview_{region_name}.csv", index=False)


   if summary_overview_data:
       summary_overview_df = pd.DataFrame(summary_overview_data)
       summary_overview_df.to_csv(AGGREGATE_DIR / "Summary_Global_and_Regional.csv", index=False)
       print("Generated Master Overview Summary (Summary_Global_and_Regional.csv).")


   if 'Patient' in df.columns and 'Localization - Bipolar' in df.columns:
       breakdown_df = df.groupby(['Patient', 'Localization - Bipolar']).agg(
           Num_Neurons=('Neuron Name', 'count'),
           Sig_Pre=('Pre-Stim Significant', 'sum'),
           Sig_Post=('Post-Stim Significant', 'sum')
       ).reset_index()
      
       breakdown_df.rename(columns={
           'Num_Neurons': 'Total Neurons',
           'Sig_Pre': 'Significant Pre',
           'Sig_Post': 'Significant Post'
       }, inplace=True)
      
       breakdown_df.to_csv(AGGREGATE_DIR / "Summary_Patient_Bipolar_Breakdown.csv", index=False)
       print("Generated Detailed Patient/Bipolar Breakdown (Summary_Patient_Bipolar_Breakdown.csv).")




# =============================================================================
# SINGLE NEURON ANALYSIS & RASTER PLOTTING
# =============================================================================
def make_single_neuron_raster_outputs_from_align1(
   align1_file: Path,
   clips_df: pd.DataFrame,
   plot_dir_str: str,
   patient_id: str,
   loc_df: pd.DataFrame,
   output_tag: str
) -> Tuple[Optional[List[Path]], str, Optional[Dict[str, object]]]:
   # Extract clean neuron name
   neuron_name = align1_file.name.replace("align1_", "").replace(".csv", "")
  
   # Load Align 1 firing details
   try:
       neuron_df = pd.read_csv(align1_file)
       if neuron_df.empty or "ms" not in neuron_df.columns:
           return None, "empty", None
       spikes_ms = pd.to_numeric(neuron_df["ms"], errors="coerce").dropna().to_numpy()
   except Exception as e:
       print(f"    [!] Error reading spike file {align1_file.name}: {e}")
       return None, "empty", None
      
   if len(spikes_ms) == 0:
       return None, "empty", None


   # Check active firing master gate: average rate >= 0.25 Hz in stimulus window (200-1200 ms)
   post_rate_hz = _compute_rate_hz_in_window(
       spikes_ms, clips_df, TTEST_WINDOW_START_MS, TTEST_WINDOW_END_MS
   )
  
   if post_rate_hz is None or post_rate_hz < MIN_RATE_HZ_FOR_FILTERED_FOLDERS:
       return None, "low_hz", None


   # Compute Welch's T-Tests for Pre and Post windows
   pre_test = _compute_correct_vs_wrong_ttest(
       spikes_ms, clips_df, PRE_WINDOW_START_MS, PRE_WINDOW_END_MS
   )
   post_test = _compute_correct_vs_wrong_ttest(
       spikes_ms, clips_df, TTEST_WINDOW_START_MS, TTEST_WINDOW_END_MS
   )


   pre_t = pre_test.get("t_stat")
   pre_p = pre_test.get("p_value")
   pre_sig = pre_test.get("significant", False)


   post_t = post_test.get("t_stat")
   post_p = post_test.get("p_value")
   post_sig = post_test.get("significant", False)


   t_diff = None
   if pre_t is not None and post_t is not None:
       t_diff = pre_t - post_t


   # Handle localizations
   electrode_code, full_location, region_abbr = get_neuron_localization(neuron_name, loc_df)
   bipolar_desc = BIPOLAR_REGIONS.get(region_abbr, "UNKNOWN")
   loc_bipolar_str = f"{region_abbr} - {bipolar_desc}"


   # Prepare data dictionary row
   csv_row = {
       "Patient": f"P{patient_id}" if not output_tag else f"P{patient_id}_{output_tag}",
       "Neuron Name": neuron_name,
       "Localization": full_location,
       "Localization - Bipolar": loc_bipolar_str,
       "Pre-Stim T-Score": pre_t,
       "Pre-Stim P-Value": pre_p,
       "Pre-Stim Significant": pre_sig,
       "Post-Stim T-Score": post_t,
       "Post-Stim P-Value": post_p,
       "Post-Stim Significant": post_sig,
       "T-Score Diff (Pre - Post)": t_diff
   }


   # Format raster plotting rows (-3000ms to +5000ms window)
   plot_rows = _extract_clip_rows_for_window(
       spikes_ms, clips_df, NEG3_TO_5_START_MS, NEG3_TO_5_END_MS
   )


   # Label significance status specifically for filenames
   sig_status = "nonsig"
   if pre_sig or post_sig:
       sig_status = "sig"
       if pre_sig and not post_sig:
           sig_status = "sig_pre"
       elif post_sig and not pre_sig:
           sig_status = "sig_post"
       else:
           sig_status = "sig_both"


   title_suffix = f"Average Firing Rate: {post_rate_hz:.2f} Hz"
   ttest_label = f"PRE T: {f'{pre_t:.3f}' if pre_t is not None else 'N/A'} (p={f'{pre_p:.3f}' if pre_p is not None else 'N/A'}) | POST T: {f'{post_t:.3f}' if post_t is not None else 'N/A'} (p={f'{post_p:.3f}' if post_p is not None else 'N/A'})"


   out_path = Path(plot_dir_str) / f"P{patient_id}_{output_tag}_{neuron_name}.png"
  
   # Save the raster & PSTH plots
   saved_plot = _plot_raster_with_optional_split_and_psth(
       plot_rows=plot_rows,
       out_path=out_path,
       patient_id=patient_id,
       neuron_name=neuron_name,
       title_suffix=title_suffix,
       x_min=NEG3_TO_5_START_MS,
       x_max=NEG3_TO_5_END_MS,
       split_by_accuracy=True,
       show_clip_end_marker=True,
       ttest_label=ttest_label,
       loc_df=loc_df,
       output_tag=output_tag,
       sig_status_str=sig_status,
       smooth_type="triangle"
   )


   saved_list = [saved_plot] if saved_plot else []
   return saved_list, "success", csv_row




# =============================================================================
# MAIN PATIENT PIPELINE
# =============================================================================
def run_patient_pipeline(cfg: Dict[str, object]) -> None:
   patient_id = str(cfg["patient_id"])
   signal_path = str(cfg["signal_path"])
   clip_ttl_csv = str(cfg["clip_ttl_csv"])
   localization_file = str(cfg.get("localization_file", ""))
   matLab = float(cfg["matLab"])
   start_unix_0 = float(cfg["start_unix_0"])
   duration = float(cfg["duration"])
   fps = float(cfg.get("fps", 29.97))
   output_tag = str(cfg.get("output_tag", "")).strip()


   print("=" * 80)
   print(f"Starting pipeline for patient {patient_id}")
   print("=" * 80)


   if not os.path.exists(signal_path):
       raise FileNotFoundError(f"Signal directory does not exist: {signal_path}")
      
   ttl_candidates = [str(p) for p in Path(signal_path).glob("*.csv") if "ttl" in p.name.lower()]
  
   if ttl_candidates:
       clip_ttl_csv = ttl_candidates[0]
       print(f"    [*] Auto-located TTL file: {Path(clip_ttl_csv).name}")
   elif not os.path.exists(clip_ttl_csv):
       raise FileNotFoundError(f"TTL file could not be auto-located in {signal_path} and config path is invalid.")


   base_path = Path(signal_path)
   folder_tag = output_tag if output_tag else base_path.name
   align1_dir = base_path / f"p{patient_id} Align 1"
   align2_dir = base_path / f"p{patient_id} Align 2"
   plot_dir = base_path / f"p{patient_id} plots {folder_tag}" / "Individual_Neuron_Rasters"


   loc_df = load_localization_map(localization_file)
   print(f"Loaded localization map (Found {len(loc_df)} micro entries)")


   clips_df, seen_frames_path = build_seen_frames_table(
       clip_ttl_csv=clip_ttl_csv, fps=fps, patient_id=patient_id, output_tag=output_tag,
   )
   print(f"Built frames table: Kept {len(clips_df)} clips.")


   time_start = start_unix_0 - matLab
   time_end = time_start + duration


   if CREATE_ALIGN1_FILES:
       align_files = align_firing_with_movie(signal_path, clip_ttl_csv, str(align1_dir), time_start, time_end)
       print(f"Created {len(align_files)} Align 1 files.")


   if CREATE_ALIGN2_FILES:
       save_align2_tables(str(align1_dir), str(align2_dir), clips_df)


   if CREATE_RASTER_PLOTS:
       align1_files = _list_valid_align1_files(str(align1_dir))
       n_files = len(align1_files)
       all_csv_data: List[Dict] = []
      
       n_plotted = 0
       n_low_hz = 0
       n_empty = 0
      
       active_clips_df = clips_df[clips_df['Plot Toggle'] == 1].copy()
       print(f"Preparing raster plots for {n_files} neuron Align 1 files using {len(active_clips_df)} Active Clips...")


       for i, align1_file in enumerate(align1_files, start=1):
           saved_plots, skip_reason, csv_row = make_single_neuron_raster_outputs_from_align1(
               align1_file, active_clips_df, str(plot_dir), patient_id, loc_df, output_tag
           )
          
           if csv_row:
               all_csv_data.append(csv_row)
          
           if skip_reason == "success":
               n_plotted += 1
           elif skip_reason == "low_hz":
               n_low_hz += 1
           else:
               n_empty += 1


       print(f"\n--- Patient {patient_id} Plotting Summary ---")
       print(f"  Total Neurons Processed: {n_files}")
       print(f"  Successfully Plotted (>= 0.25 Hz in 200-1200ms): {n_plotted}")
       print(f"  Skipped (Low Firing Rate < 0.25 Hz in 200-1200ms): {n_low_hz}")
       print(f"  Skipped (Empty / Missing Data / No Spikes): {n_empty}")


       if not all_csv_data:
           print(f"  [!] No valid data to append for {patient_id}.")
       else:
           df_csv = pd.DataFrame(all_csv_data)
           base_key_dir = plot_dir / "FINAL KEY PLOTS" / "neg3 to 5 sec"
          
           # --- 1. All Rasters Folder ---
           all_raster_dir = base_key_dir / "All Rasters"
           all_raster_dir.mkdir(parents=True, exist_ok=True)
           df_csv.to_csv(all_raster_dir / "T score sheet.csv", index=False)
          
           # --- 2. Significant Folder (Sig in Post OR Pre) ---
           df_sig = df_csv[(df_csv["Post-Stim Significant"] == True) | (df_csv["Pre-Stim Significant"] == True)]
           if not df_sig.empty:
               sig_dir = base_key_dir / "Significant"
               sig_dir.mkdir(parents=True, exist_ok=True)
               df_sig.to_csv(sig_dir / "T score sheet.csv", index=False)
              
           # --- 3. Non Significant Folder (Sig in neither) ---
           df_nonsig = df_csv[(df_csv["Post-Stim Significant"] == False) & (df_csv["Pre-Stim Significant"] == False)]
           if not df_nonsig.empty:
               nonsig_dir = base_key_dir / "Non Significant"
               nonsig_dir.mkdir(parents=True, exist_ok=True)
               df_nonsig.to_csv(nonsig_dir / "T score sheet.csv", index=False)


           # --- Global Appending ---
           def _append_csv_safe(df_to_save: pd.DataFrame, filepath: Path):
               if df_to_save.empty: return
               filepath.parent.mkdir(parents=True, exist_ok=True)
               needs_header = not filepath.exists() or filepath.stat().st_size == 0
               df_to_save.to_csv(filepath, mode='a', header=needs_header, index=False)


           _append_csv_safe(df_csv, GLOBAL_CSV_PATH)
           _append_csv_safe(df_sig, GLOBAL_SIG_CSV_PATH)
           _append_csv_safe(df_nonsig, GLOBAL_NONSIG_CSV_PATH)


           print(f"  Appended {len(df_csv)} active neuron stats to Aggregate CSVs")


   print(f"Finished patient {patient_id}\n")




# =============================================================================
# SCRIPT ENTRY POINT
# =============================================================================
if __name__ == "__main__":
   os.makedirs(ALL_SIG_DIR, exist_ok=True)
   os.makedirs(ALL_NON_SIG_DIR, exist_ok=True)


   for patient_cfg in PATIENT_CONFIGS:
       try:
           run_patient_pipeline(patient_cfg)
       except Exception as e:
           print(f"\n[!] CRITICAL ERROR processing patient {patient_cfg.get('patient_id', 'Unknown')}:")
           traceback.print_exc()
           print("    Skipping to the next patient...\n")


   generate_population_swarm_plot()
   print("All requested patients have been processed and summary generated.")
