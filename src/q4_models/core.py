"""Auditable Q4 discrete Pareto and constrained single-exposure models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from q3_models.core import load_records


Q4_VERSION = "q4_smoke_v1"
SEED = 20260815
LAMBDA_GRID = np.array([0.0, 0.25, 0.5, 0.75, 1.0])


@dataclass(frozen=True)
class PolicyObservation:
    policy: str
    n_battery: int
    time_mean: float
    time_sd: float
    loss_mean: float
    loss_sd: float
    late_slope_mean: float
    c1: float
    q1: float
    c2: float
    j: float
    h: float
    coordinate: tuple[float, float, float] | None


def _finite_mean(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").dropna()
    return float(values.mean()) if len(values) else float("nan")


def collect_policy_observations(project_root: Path) -> tuple[list[PolicyObservation], pd.DataFrame]:
    records, meta, _ = load_records(project_root)
    complete_ids = set(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int))
    rows = []
    observations: list[PolicyObservation] = []
    for policy, group in meta.loc[meta["battery_id"].isin(complete_ids)].groupby("policy", sort=True):
        metadata_by_battery = group.set_index("battery_id")
        battery_rows = []
        for battery_id in sorted(group["battery_id"].astype(int)):
            record = records[battery_id]
            cycles = record.cycles
            time_column = "chargetime_raw" if "chargetime_raw" in cycles.columns else "chargetime"
            if time_column not in cycles.columns:
                raise KeyError("Q4 requires chargetime_raw (or legacy chargetime) in cleaned cycle data")
            time_series = pd.to_numeric(cycles[time_column], errors="coerce")
            time_value = float(metadata_by_battery.loc[battery_id, "mean_chargetime"])
            cycle_time_value = float(time_series.mean())
            loss_value = float(1.0 - record.relative_at(200))
            late_values = record.relative_soh[150:200]
            x = np.arange(151, 201, dtype=float)
            xc = x - x.mean()
            slope = float(xc @ (late_values - late_values.mean()) / (xc @ xc))
            battery_rows.append({"battery_id": battery_id, "time": time_value,
                                 "cycle_time_sensitivity": cycle_time_value,
                                 "loss": loss_value, "late_slope_loss": max(0.0, -slope)})
        values = pd.DataFrame(battery_rows)
        first = group.iloc[0]
        c1, q1, c2 = (float(first[col]) if pd.notna(first[col]) else np.nan for col in ("C1", "Q1", "C2"))
        q = q1 / 100.0 if np.isfinite(q1) else np.nan
        j = q * c1 + (0.8 - q) * c2 if np.isfinite([c1, q, c2]).all() else np.nan
        h = 0.5 * (c1 * q**2 + c2 * (0.8**2 - q**2)) if np.isfinite([c1, q, c2]).all() else np.nan
        coordinate = (c1, q1, c2) if np.isfinite([c1, q1, c2]).all() else None
        observations.append(PolicyObservation(
            policy=str(policy), n_battery=len(values), time_mean=float(values["time"].mean()),
            time_sd=float(values["time"].std(ddof=1)) if len(values) > 1 else 0.0,
            loss_mean=float(values["loss"].mean()),
            loss_sd=float(values["loss"].std(ddof=1)) if len(values) > 1 else 0.0,
            late_slope_mean=float(values["late_slope_loss"].mean()),
            c1=c1, q1=q1, c2=c2, j=j, h=h, coordinate=coordinate,
        ))
        for row in battery_rows:
            row.update({"policy": str(policy), "c1": c1, "q1": q1, "c2": c2, "j": j, "h": h})
            rows.append(row)
    return observations, pd.DataFrame(rows)


def observation_frame(observations: list[PolicyObservation]) -> pd.DataFrame:
    return pd.DataFrame([obs.__dict__ for obs in observations])


def _normalise(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    lo, hi = np.nanmin(values), np.nanmax(values)
    return np.zeros_like(values) if hi - lo < 1e-12 else (values - lo) / (hi - lo)


def pareto_mask(time: np.ndarray, loss: np.ndarray) -> np.ndarray:
    time, loss = np.asarray(time, float), np.asarray(loss, float)
    mask = np.ones(len(time), dtype=bool)
    for i in range(len(time)):
        dominated = (time <= time[i] + 1e-12) & (loss <= loss[i] + 1e-12)
        strictly = (time < time[i] - 1e-12) | (loss < loss[i] - 1e-12)
        mask[i] = not bool(np.any(dominated & strictly))
    return mask


def choose_scalar(time: np.ndarray, loss: np.ndarray, policies: list[str], weight: float) -> int:
    score = weight * _normalise(time) + (1.0 - weight) * _normalise(loss)
    order = sorted(range(len(score)), key=lambda i: (score[i], loss[i], time[i], policies[i]))
    return order[0]


def bootstrap_pareto(
    frame: pd.DataFrame,
    repetitions: int = 2000,
    seed: int = SEED,
    lambda_grid: np.ndarray | None = None,
    loss_limits: tuple[float, ...] = (),
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    lambda_grid = LAMBDA_GRID if lambda_grid is None else np.asarray(lambda_grid, dtype=float)
    policies = sorted(frame["policy"].unique())
    records = {policy: frame.loc[frame["policy"].eq(policy)].reset_index(drop=True) for policy in policies}
    rows = []
    for rep in range(repetitions):
        summary = []
        for policy in policies:
            data = records[policy]
            idx = rng.integers(0, len(data), size=len(data))
            sample = data.iloc[idx]
            late_slope = float(sample["late_slope_loss"].mean()) if "late_slope_loss" in sample else np.nan
            summary.append((policy, float(sample["time"].mean()), float(sample["loss"].mean()), late_slope))
        t = np.array([row[1] for row in summary]); d = np.array([row[2] for row in summary])
        front = pareto_mask(t, d)
        choices = {w: summary[choose_scalar(t, d, policies, w)][0] for w in lambda_grid}
        constrained_choices = {}
        for limit in loss_limits:
            feasible = np.flatnonzero(d <= limit)
            constrained_choices[limit] = (
                min(feasible, key=lambda i: (t[i], d[i], policies[i])) if len(feasible) else None
            )
        for index, ((policy, time_value, loss_value, late_slope), is_front) in enumerate(zip(summary, front)):
            rows.append({"version": Q4_VERSION, "replicate": rep, "policy": policy,
                         "time": time_value, "loss": loss_value, "late_slope_loss": late_slope,
                         "pareto": bool(is_front),
                         **{f"selected_lambda_{w:.2f}": choices[w] == policy for w in lambda_grid},
                         **{f"selected_loss_limit_{limit:.4f}": constrained_choices[limit] == index
                            for limit in loss_limits}})
    return pd.DataFrame(rows)


def fit_single_exposure(train: pd.DataFrame, exposure: str, lam: float) -> tuple[float, float, float, float]:
    loss_column = "loss" if "loss" in train.columns else "loss_mean"
    train = train.dropna(subset=[exposure, loss_column])
    if len(train) < 2 or train[exposure].std(ddof=0) < 1e-8:
        return float(train[loss_column].mean()), 0.0, float(train[exposure].mean()), 1.0
    mean, scale = float(train[exposure].mean()), float(train[exposure].std(ddof=0))
    z = (train[exposure].to_numpy(float) - mean) / scale
    x = np.column_stack([np.ones(len(z)), z]); y = train[loss_column].to_numpy(float)
    penalty = np.diag([0.0, lam]); coef = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    return float(coef[0]), float(coef[1]), mean, scale


def loso_single_exposure(
    frame: pd.DataFrame,
    exposure: str = "j",
    ridge_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0),
) -> pd.DataFrame:
    usable = frame.dropna(subset=[exposure, "coordinate", "loss_mean"]).copy()
    usable["coordinate_key"] = usable["coordinate"].astype(str)
    rows = []
    for held_out in sorted(usable["coordinate_key"].unique()):
        train = usable.loc[usable["coordinate_key"].ne(held_out)]
        test = usable.loc[usable["coordinate_key"].eq(held_out)]
        best = None
        for lam in ridge_grid:
            intercept, slope, mean, scale = fit_single_exposure(train, exposure, lam)
            if len(test) == 0 or scale < 1e-8:
                pred = np.full(len(test), intercept)
            else:
                pred = intercept + slope * (test[exposure].to_numpy(float) - mean) / scale
            rmse = float(np.sqrt(np.mean((pred - test["loss_mean"].to_numpy(float)) ** 2))) if len(test) else np.nan
            candidate = (rmse, -lam, intercept, slope, mean, scale)
            if best is None or candidate[:2] < best[:2]: best = candidate
        assert best is not None
        baseline_rmse = float(np.sqrt(np.mean((test["loss_mean"].to_numpy(float) - train["loss_mean"].mean()) ** 2))) if len(test) else np.nan
        rows.append({"version": Q4_VERSION, "exposure": exposure, "held_out_coordinate": held_out,
                     "n_test_policy": len(test), "rmse": best[0], "lambda": -best[1],
                     "constant_rmse": baseline_rmse, "improvement": baseline_rmse - best[0],
                     "intercept": best[2], "slope": best[3], "train_mean": best[4],
                     "train_scale": best[5], "validation_type": "coordinate_LOSO_extrapolation_pressure"})
    return pd.DataFrame(rows)
