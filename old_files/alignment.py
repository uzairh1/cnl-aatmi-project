import os
import glob
import pandas as pd
import numpy as np

# -----------------------------
# Configs: one dict per patient/session
# -----------------------------
configs = [
    {
        "patients": "p563",                     # patient ID
        "movie": "24",                          # movie name
        "signal_path": "563",                   # folder that contains neural data in CSVs (relative to base_directory)
        "matLab": 1680468570.608406,            # Matlab reference timestamp (unix seconds)
        "start_unix_0": 1680468596.211406,      # movie start time in unix seconds 
        "drift_rate": -4.67 * (10**-5),         
        "fps": 30,                              
        "duration": 2476.867,                   # movie duration in seconds
    },
    {
        "patients": "p562",
        "movie": "24",
        "signal_path": "562",
        "matLab": 1675460855.9275053,
        "start_unix_0": 1675460990.1245053,
        "drift_rate": -4.5 * (10**-5),
        "fps": 30,
        "duration": 2476.867,
    }
]

run_align = True            #  if True,  align spike timestamps to the movie time
BIN_SIZE_S = 10             # default bin size (seconds) for calculating firing rate 

def align_firing_with_movie(signal_path: str, output_dir: str, timeStart: float, timeEnd: float):
    """
    Align spike timestamps to the movie time window, and save the processed file to the output directory.

    Parameters:
    - signal_path (str): Directory containing raw spike CSV files. Each CSV is expected to have a column 's'
        representing spike times in seconds.
    - output_dir (str): Where to save processed CSVs.
    - timeStart (float): Start time (seconds) of the movie relative to the spike-time reference.
    - timeEnd (float): End time (seconds) of the movie relative to the spike-time reference.
    """
    csv_files = glob.glob(os.path.join(signal_path, "*.csv"))

    os.makedirs(output_dir, exist_ok=True)

    for file in csv_files:
        df = pd.read_csv(file)
        # Skip empty files 
        if df.empty:
            continue
        # Filter spikes to only those occurring during the movie window
        df = df[(df["s"] >= timeStart) & (df["s"] <= timeEnd)].copy()

        # Shift time so that movie onset is at 0 seconds
        df["s"] = df["s"] - timeStart
        df["ms"] = df["s"] * 1000
        df.drop(columns=["s"], inplace=True)

        # Save aligned file to output directory, using the same filename
        output_file = os.path.join(output_dir, os.path.basename(file))
        df.to_csv(output_file, index=False)


def bin_firing_rate(csv_path: str, bin_size_s: int = BIN_SIZE_S):
    """
    Bin spikes into fixed-width time bins and compute firing rate.

    Parameters
    - csv_path (str): Path to an aligned CSV with a 'ms' column.
    - bin_size_s : Bin width in seconds.

    Returns
    -------
    pandas.DataFrame with columns:
      - bin_{bin_size_s}s : integer bin index (0, 1, 2, ...)
      - spike_count       : number of spikes in the bin
      - firing_rate_hz    : spike_count / bin_size_s
    """
    df = pd.read_csv(csv_path)
    s = df["ms"].to_numpy(dtype=float) / 1000.0

    bin_idx = np.floor(s / bin_size_s).astype(int)

    # Count spikes per bin index
    counts = pd.Series(bin_idx).value_counts().sort_index()

    maxbin = int(counts.index.max()) if len(counts) else 0

    full_index = pd.Index(range(0, maxbin + 1), name=f"bin_{bin_size_s}s")

    counts = counts.reindex(full_index, fill_value=0)

    out = counts.reset_index(name="spike_count")

    out["firing_rate_hz"] = out["spike_count"] / float(bin_size_s)

    return out


# -----------------------------
# Main loop: per patient config
# -----------------------------
for cfg in configs:
    patients = cfg["patients"]

    # Base folder for this patient/session
    base_directory = f"/Users/macbookpro/Desktop/CNL/concept/{patients}"

    mov_name = cfg["movie"]

    # Raw spike CSV directory
    signal_path = os.path.join(base_directory, cfg["signal_path"])

    # Output directory for aligned spike CSVs
    processed_signal_path = os.path.join(base_directory, f"align_{mov_name}")

    # timeStart is movie start (in seconds) relative to Matlab reference.
    timeStart = cfg["start_unix_0"] - cfg["matLab"]

    duration = cfg["duration"]
    timeEnd = timeStart + duration

    # Run alignment step (save processed unit CSVs into processed_signal_path)
    if run_align:
        align_firing_with_movie(signal_path, processed_signal_path, timeStart, timeEnd)
