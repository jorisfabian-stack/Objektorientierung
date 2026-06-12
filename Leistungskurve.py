import numpy as np
import pandas as pd
from typing import Optional, Sequence, Union


def create_power_curve(
    data: Union[pd.DataFrame, pd.Series, np.ndarray, Sequence[float]],
    power_column: str = "PowerOriginal",
    time_column: str = "Duration",
    time: Optional[Union[pd.Series, np.ndarray, Sequence[float]]] = None,
) -> pd.DataFrame:

    if isinstance(data, pd.DataFrame):
        subset = data[[power_column, time_column]].dropna(subset=[power_column, time_column])
        power = subset[power_column].to_numpy(dtype=float)
        time_values = subset[time_column].to_numpy(dtype=float)
    else:
        power = np.asarray(data, dtype=float)
        if time is None:
            time_values = None
        else:
            time_values = np.asarray(time, dtype=float)
            if time_values.shape != power.shape:
                raise ValueError("Laenge von Leistung und Zeit muss ueberinstimmen.")

    if power.size == 0:
        raise ValueError("Keine gueltigen Daten fuer die Power Curve gefunden.")

    if time_values is None:
        sample_durations = np.ones_like(power, dtype=float)
    elif np.all(np.diff(time_values) >= 0) and np.any(np.diff(time_values) > 0):
        sample_durations = np.diff(np.concatenate(([0.0], time_values)))
    else:
        sample_durations = time_values

    sample_durations = np.maximum(sample_durations, 0.0)

    energy = power * sample_durations
    cumulative_time = np.concatenate(([0.0], np.cumsum(sample_durations)))
    cumulative_energy = np.concatenate(([0.0], np.cumsum(energy)))

    n = len(power)
    durations = []
    max_powers = []

    for window in range(1, n + 1):
        window_times = cumulative_time[window:] - cumulative_time[:-window]
        window_energy = cumulative_energy[window:] - cumulative_energy[:-window]

        valid = window_times > 0.0
        if not np.any(valid):
            durations.append(0.0)
            max_powers.append(np.nan)
            continue

        average_powers = np.full_like(window_times, np.nan, dtype=float)
        average_powers[valid] = window_energy[valid] / window_times[valid]

        best_idx = np.nanargmax(average_powers)
        durations.append(window_times[best_idx])
        max_powers.append(average_powers[best_idx])

    return pd.DataFrame({
        "duration_s": durations,
        "power_w": max_powers
    })