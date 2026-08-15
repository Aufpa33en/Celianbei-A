"""Battery-level cycle-life estimation for Questions 1 and 2.

The organizer defines cycle life as the cycle at which SOH reaches 80%.
Because no observed trajectory reaches that threshold, this module estimates
T80 from a common early-cycle prefix and keeps short-horizon backtesting
separate from the unobserved long-range endpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LifetimeSettings:
    threshold: float = 0.8
    prefix_cycle: int = 150
    validation_end_cycle: int = 200
    candidate_windows: tuple[int, ...] = (30, 40, 50, 60, 80)
    slope_epsilon: float = 1e-7


def _fit_late_linear(frame: pd.DataFrame, end_cycle: int, window: int) -> tuple[float, float]:
    prefix = frame.loc[frame["cycle"] <= end_cycle].sort_values("cycle").tail(window)
    if len(prefix) < window:
        raise ValueError(f"battery has {len(prefix)} rows, fewer than the required window {window}")
    cycles = prefix["cycle"].to_numpy(dtype=float)
    values = prefix["SOH_clean"].to_numpy(dtype=float)
    design = np.column_stack((np.ones(len(prefix)), cycles))
    intercept, slope = np.linalg.lstsq(design, values, rcond=None)[0]
    return float(intercept), float(slope)


def _t80_from_line(
    intercept: float,
    slope: float,
    last_cycle: int,
    settings: LifetimeSettings,
) -> tuple[float, str]:
    if not np.isfinite(slope) or slope >= -settings.slope_epsilon:
        return np.nan, "non_decreasing_tail"
    t80 = (settings.threshold - intercept) / slope
    if not np.isfinite(t80):
        return np.nan, "non_finite_crossing"
    if t80 <= last_cycle:
        return np.nan, "crossing_not_after_prefix"
    return float(t80), "finite_extrapolation"


def validate_lifetime_windows(
    cycles: pd.DataFrame,
    settings: LifetimeSettings = LifetimeSettings(),
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Select the late-trend window by predicting observed cycles 151--200."""
    required_end = settings.validation_end_cycle
    complete = cycles.groupby("battery_id")["cycle"].max()
    complete_ids = complete.loc[complete >= required_end].index
    cohort = cycles.loc[cycles["battery_id"].isin(complete_ids)].copy()
    battery_rows: list[dict[str, float | int | str]] = []
    summary_rows: list[dict[str, float | int]] = []

    for window in settings.candidate_windows:
        window_rows = []
        for battery_id, frame in cohort.groupby("battery_id", sort=False):
            intercept, slope = _fit_late_linear(frame, settings.prefix_cycle, window)
            held_out = frame.loc[
                frame["cycle"].between(settings.prefix_cycle + 1, required_end)
            ].sort_values("cycle")
            prediction = intercept + slope * held_out["cycle"].to_numpy(dtype=float)
            error = prediction - held_out["SOH_clean"].to_numpy(dtype=float)
            row = {
                "Window": window,
                "BatteryId": int(battery_id),
                "Policy": str(frame["policy"].iloc[0]),
                "NTrain": window,
                "NValidation": len(held_out),
                "RMSE": float(np.sqrt(np.mean(error**2))),
                "MAE": float(np.mean(np.abs(error))),
                "Bias": float(np.mean(error)),
                "FittedSlope": slope,
            }
            battery_rows.append(row)
            window_rows.append(row)

        current = pd.DataFrame(window_rows)
        policy_mse = current.assign(MSE=current["RMSE"] ** 2).groupby("Policy")["MSE"].mean()
        summary_rows.append(
            {
                "Window": window,
                "NBattery": len(current),
                "NPolicy": current["Policy"].nunique(),
                "StrategyEqualRMSE": float(np.sqrt(policy_mse.mean())),
                "MeanBatteryRMSE": float(current["RMSE"].mean()),
                "MedianBatteryRMSE": float(current["RMSE"].median()),
                "WorstBatteryRMSE": float(current["RMSE"].max()),
                "MeanBatteryMAE": float(current["MAE"].mean()),
                "NonDecreasingSlopeCount": int((current["FittedSlope"] >= 0).sum()),
            }
        )

    summary = pd.DataFrame(summary_rows).sort_values(
        ["StrategyEqualRMSE", "WorstBatteryRMSE", "Window"], kind="stable"
    ).reset_index(drop=True)
    selected_window = int(summary.iloc[0]["Window"])
    summary["Selected"] = summary["Window"].eq(selected_window)
    return pd.DataFrame(battery_rows), summary, selected_window


def estimate_battery_lifetimes(
    cycles: pd.DataFrame,
    window: int,
    settings: LifetimeSettings = LifetimeSettings(),
) -> pd.DataFrame:
    """Estimate one comparable T80 value per battery from cycles 1--150."""
    rows = []
    for battery_id, frame in cycles.groupby("battery_id", sort=False):
        frame = frame.sort_values("cycle")
        intercept, slope = _fit_late_linear(frame, settings.prefix_cycle, window)
        t80, status = _t80_from_line(intercept, slope, settings.prefix_cycle, settings)
        prefix = frame.loc[frame["cycle"] <= settings.prefix_cycle]
        rows.append(
            {
                "BatteryId": int(battery_id),
                "Policy": str(frame["policy"].iloc[0]),
                "AvailableLastCycle": int(frame["cycle"].max()),
                "LifetimePrefixCycle": settings.prefix_cycle,
                "TailWindow": window,
                "SOH150": float(prefix.loc[prefix["cycle"].eq(settings.prefix_cycle), "SOH_clean"].iloc[0]),
                "SlopeTail": slope,
                "InterceptTail": intercept,
                "EstimatedT80": t80,
                "ExtrapolationMultiple": t80 / settings.prefix_cycle if np.isfinite(t80) else np.nan,
                "T80Status": status,
            }
        )
    return pd.DataFrame(rows)


def lifetime_window_sensitivity(
    cycles: pd.DataFrame,
    settings: LifetimeSettings = LifetimeSettings(),
) -> pd.DataFrame:
    parts = []
    for window in settings.candidate_windows:
        current = estimate_battery_lifetimes(cycles, window, settings)
        current.insert(0, "SensitivityWindow", window)
        parts.append(current)
    return pd.concat(parts, ignore_index=True)


def bootstrap_strategy_lifetimes(
    battery_lifetimes: pd.DataFrame,
    repetitions: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Estimate policy median T80 and its battery-cluster ranking uncertainty."""
    policies = list(pd.unique(battery_lifetimes["Policy"]))
    rng = np.random.default_rng(seed)
    samples = np.empty((repetitions, len(policies)), dtype=float)
    rows = []
    for index, policy in enumerate(policies):
        values = battery_lifetimes.loc[
            battery_lifetimes["Policy"].eq(policy), "EstimatedT80"
        ].dropna().to_numpy(dtype=float)
        if len(values) < 2:
            raise ValueError(f"policy {policy} has fewer than two finite battery T80 estimates")
        sampled = values[rng.integers(0, len(values), size=(repetitions, len(values)))]
        samples[:, index] = np.median(sampled, axis=1)
        rows.append(
            {
                "Policy": policy,
                "NBattery": len(values),
                "MedianEstimatedT80": float(np.median(values)),
                "MeanEstimatedT80": float(np.mean(values)),
                "Q25EstimatedT80": float(np.quantile(values, 0.25)),
                "Q75EstimatedT80": float(np.quantile(values, 0.75)),
                "BootstrapSEMedianT80": float(samples[:, index].std(ddof=1)),
                "BootstrapCI95Low": float(np.quantile(samples[:, index], alpha / 2)),
                "BootstrapCI95High": float(np.quantile(samples[:, index], 1 - alpha / 2)),
            }
        )

    point = pd.DataFrame(rows)
    point_rank = point.set_index("Policy")["MedianEstimatedT80"].rank(
        method="first", ascending=False
    ).astype(int)
    order = np.argsort(-samples, axis=1, kind="stable")
    ranks = np.empty_like(order)
    ranks[np.arange(repetitions)[:, None], order] = np.arange(1, len(policies) + 1)
    rank_rows = []
    for index, policy in enumerate(policies):
        rank_rows.append(
            {
                "Policy": policy,
                "PointT80Rank": int(point_rank.loc[policy]),
                "MeanRank": float(ranks[:, index].mean()),
                "MedianRank": float(np.median(ranks[:, index])),
                "ProbabilityTop3": float(np.mean(ranks[:, index] <= 3)),
                "ProbabilityBottom3": float(np.mean(ranks[:, index] >= len(policies) - 2)),
            }
        )
    rank = pd.DataFrame(rank_rows).sort_values("MeanRank").reset_index(drop=True)
    return point.sort_values("MedianEstimatedT80", ascending=False).reset_index(drop=True), rank


def _exact_permutation_p_value(first: np.ndarray, second: np.ndarray) -> float:
    pooled = np.concatenate((first, second))
    observed = abs(float(first.mean() - second.mean()))
    exceed = 0
    total = 0
    first_size = len(first)
    all_indices = np.arange(len(pooled))
    for selected in combinations(range(len(pooled)), first_size):
        mask = np.zeros(len(pooled), dtype=bool)
        mask[list(selected)] = True
        difference = abs(float(pooled[mask].mean() - pooled[all_indices[~mask]].mean()))
        exceed += difference >= observed - 1e-12
        total += 1
    return exceed / total


def pairwise_lifetime_comparison(battery_lifetimes: pd.DataFrame) -> pd.DataFrame:
    policies = list(pd.unique(battery_lifetimes["Policy"]))
    rows = []
    for first_index, first_policy in enumerate(policies):
        first = battery_lifetimes.loc[
            battery_lifetimes["Policy"].eq(first_policy), "EstimatedT80"
        ].dropna().to_numpy(dtype=float)
        for second_policy in policies[first_index + 1 :]:
            second = battery_lifetimes.loc[
                battery_lifetimes["Policy"].eq(second_policy), "EstimatedT80"
            ].dropna().to_numpy(dtype=float)
            rows.append(
                {
                    "PolicyA": first_policy,
                    "PolicyB": second_policy,
                    "MeanDifferenceT80_AminusB": float(first.mean() - second.mean()),
                    "MedianDifferenceT80_AminusB": float(np.median(first) - np.median(second)),
                    "ExactPermutationP": _exact_permutation_p_value(first, second),
                }
            )
    result = pd.DataFrame(rows)
    order = np.argsort(result["ExactPermutationP"].to_numpy())
    adjusted = np.empty(len(result), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(result) - rank) * result.iloc[index]["ExactPermutationP"]))
        adjusted[index] = running
    result["HolmAdjustedP"] = adjusted
    result["SignificantAfterHolm"] = result["HolmAdjustedP"] < 0.05
    return result
