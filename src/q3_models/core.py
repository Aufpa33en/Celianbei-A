"""Data loading, trajectory utilities, metrics, and constrained extrapolation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .config import CONFIG, Q3Config


@dataclass
class BatteryRecord:
    battery_id: int
    policy: str
    meta: pd.Series
    cycles: pd.DataFrame
    baseline: float
    relative_soh: np.ndarray

    def relative_at(self, cycle: int) -> float:
        return float(self.relative_soh[cycle - 1])

    def absolute_future(self, start: int = 151, end: int = 200) -> np.ndarray:
        return self.baseline * self.relative_soh[start - 1 : end]


def load_records(project_root: Path) -> tuple[dict[int, BatteryRecord], pd.DataFrame, pd.DataFrame]:
    data_dir = project_root / "data" / "processed" / "q1_cleaned"
    meta = pd.read_csv(data_dir / "battery_summary_clean.csv")
    cycles = pd.read_csv(data_dir / "cycle_train_clean.csv")
    records: dict[int, BatteryRecord] = {}
    for battery_id, frame in cycles.groupby("battery_id", sort=True):
        row = meta.loc[meta["battery_id"].eq(battery_id)].iloc[0]
        frame = frame.sort_values("cycle").reset_index(drop=True)
        baseline = float(frame.loc[frame["cycle"].between(1, 5), "SOH_clean"].mean())
        records[int(battery_id)] = BatteryRecord(
            battery_id=int(battery_id),
            policy=str(row["policy"]),
            meta=row,
            cycles=frame,
            baseline=baseline,
            relative_soh=frame["SOH_clean"].to_numpy(float) / baseline,
        )
    return records, meta, cycles


def complete_battery_ids(meta: pd.DataFrame) -> list[int]:
    return sorted(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int).tolist())


def slope(values: np.ndarray, cycles: np.ndarray | None = None) -> float:
    values = np.asarray(values, dtype=float)
    if cycles is None:
        cycles = np.arange(1, len(values) + 1, dtype=float)
    else:
        cycles = np.asarray(cycles, dtype=float)
    good = np.isfinite(values) & np.isfinite(cycles)
    if good.sum() < 2:
        return 0.0
    x = cycles[good]
    y = values[good]
    xc = x - x.mean()
    denom = float(xc @ xc)
    return 0.0 if denom <= 0 else float(xc @ (y - y.mean()) / denom)


def robust_slope_scale(slopes: Iterable[float]) -> float:
    values = np.asarray(list(slopes), dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return 1e-8
    median = float(np.median(values))
    scale = 1.4826 * float(np.median(np.abs(values - median)))
    if scale < 1e-8:
        scale = max(float(np.std(values, ddof=1)) if values.size > 1 else 0.0, 1e-8)
    return scale


def fit_power_law(
    cycles: np.ndarray,
    relative_soh: np.ndarray,
    config: Q3Config = CONFIG,
) -> dict[str, float]:
    t = np.asarray(cycles, dtype=float)
    y = np.asarray(relative_soh, dtype=float)
    good = np.isfinite(t) & np.isfinite(y)
    t, y = t[good], y[good]
    if t.size < 5:
        return {"beta0": float(np.nanmean(y)), "a": 0.0, "p": 1.0, "sse": np.inf}
    L = float(t.max())
    weights = 1.0 + 2.0 * (t / L) ** 2
    root_w = np.sqrt(weights)
    best: dict[str, float] | None = None
    for p in config.power_grid:
        z = t**p
        design = np.column_stack([np.ones_like(t), -z])
        coef, *_ = np.linalg.lstsq(design * root_w[:, None], y * root_w, rcond=None)
        beta0, a = float(coef[0]), float(coef[1])
        if a < 0:
            a = 0.0
            beta0 = float(np.average(y, weights=weights))
        pred = beta0 - a * z
        sse = float(np.sum(weights * (y - pred) ** 2))
        candidate = {"beta0": beta0, "a": a, "p": float(p), "sse": sse}
        if best is None or sse < best["sse"]:
            best = candidate
    assert best is not None
    return best


def predict_power_law(fit: dict[str, float], cycles: np.ndarray) -> np.ndarray:
    t = np.asarray(cycles, dtype=float)
    return fit["beta0"] - fit["a"] * t ** fit["p"]


def power_law_eol(fit: dict[str, float], baseline: float, config: Q3Config = CONFIG) -> tuple[float, str]:
    threshold = 0.8 / baseline
    beta0, a, p = fit["beta0"], fit["a"], fit["p"]
    if not np.isfinite([beta0, a, p]).all() or a <= 0 or beta0 <= threshold or p <= 0:
        return np.nan, "no_finite_intersection"
    cycle = float(((beta0 - threshold) / a) ** (1.0 / p))
    if not np.isfinite(cycle) or cycle > config.eol_max_cycle:
        return np.nan, "beyond_5000"
    if cycle <= 150:
        return cycle, "before_or_at_observation"
    return cycle, "finite_scenario"


def project_absolute_prediction(raw: np.ndarray, anchor: float, config: Q3Config = CONFIG) -> np.ndarray:
    clipped = np.clip(np.asarray(raw, dtype=float), *config.soh_bounds)
    return np.minimum.accumulate(np.concatenate([[float(anchor)], clipped]))[1:]


def prediction_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    residual = np.asarray(y_pred) - np.asarray(y_true)
    return {
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "mae": float(np.mean(np.abs(residual))),
        "error_cycle200": float(residual[-1]),
    }


def strategy_parameters(record: BatteryRecord) -> np.ndarray:
    row = record.meta
    return np.asarray([row.get("C1", np.nan), row.get("Q1", np.nan), row.get("C2", np.nan)], dtype=float)
