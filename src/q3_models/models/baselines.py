"""Persistence and recent-linear-trend baselines."""

from __future__ import annotations

import numpy as np

from ..config import CONFIG, Q3Config
from ..core import BatteryRecord, slope


def future_cycles(config: Q3Config = CONFIG) -> np.ndarray:
    return np.arange(config.future_start, config.future_end + 1, dtype=float)


def predict_persistence(record: BatteryRecord, L: int, config: Q3Config = CONFIG) -> np.ndarray:
    return np.full(config.future_end - config.future_start + 1, record.relative_at(L), dtype=float)


def predict_linear_trend(record: BatteryRecord, L: int, config: Q3Config = CONFIG) -> np.ndarray:
    window = min(50, L)
    values = record.relative_soh[L - window : L]
    times = np.arange(L - window + 1, L + 1, dtype=float)
    local_slope = min(0.0, slope(values, times))
    return record.relative_at(L) + local_slope * (future_cycles(config) - L)
