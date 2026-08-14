"""Constrained individual power-law extrapolation."""

from __future__ import annotations

import numpy as np

from ..config import CONFIG, Q3Config
from ..core import BatteryRecord, fit_power_law, predict_power_law


def predict_individual_power(
    record: BatteryRecord,
    L: int,
    config: Q3Config = CONFIG,
) -> tuple[np.ndarray, dict[str, float]]:
    cycles = np.arange(1, L + 1, dtype=float)
    fit = fit_power_law(cycles, record.relative_soh[:L], config)
    future = np.arange(config.future_start, config.future_end + 1, dtype=float)
    return predict_power_law(fit, future), fit
