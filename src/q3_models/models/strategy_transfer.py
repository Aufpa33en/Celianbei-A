"""Strategy-mean trajectory transfer with dimensionless slope shrinkage."""

from __future__ import annotations

import numpy as np

from ..config import CONFIG, Q3Config
from ..core import BatteryRecord, robust_slope_scale, slope, strategy_parameters


def _curve_for_target(train: list[BatteryRecord], target: BatteryRecord) -> np.ndarray:
    same = [record for record in train if record.policy == target.policy]
    if same:
        return np.mean([record.relative_soh[:200] for record in same], axis=0)

    grouped: dict[str, list[BatteryRecord]] = {}
    for record in train:
        grouped.setdefault(record.policy, []).append(record)
    if not grouped:
        raise ValueError("Strategy transfer requires at least one training battery")

    train_params = np.vstack([strategy_parameters(record) for record in train])
    medians = np.nanmedian(train_params, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    filled = np.where(np.isfinite(train_params), train_params, medians)
    scales = np.std(filled, axis=0, ddof=1) if len(train) > 1 else np.ones(3)
    scales = np.where(np.isfinite(scales) & (scales > 1e-12), scales, 1.0)
    target_params = strategy_parameters(target)
    target_params = np.where(np.isfinite(target_params), target_params, medians)

    policy_distance: list[tuple[float, str]] = []
    for policy, records in grouped.items():
        policy_params = np.nanmean(
            np.where(
                np.isfinite(np.vstack([strategy_parameters(r) for r in records])),
                np.vstack([strategy_parameters(r) for r in records]),
                medians,
            ),
            axis=0,
        )
        distance = float(np.linalg.norm((policy_params - target_params) / scales))
        policy_distance.append((distance, policy))
    policy_distance.sort(key=lambda pair: (pair[0], pair[1]))
    chosen = grouped[policy_distance[0][1]]
    return np.mean([record.relative_soh[:200] for record in chosen], axis=0)


def predict_strategy_transfer(
    train: list[BatteryRecord],
    target: BatteryRecord,
    L: int,
    lambda_gamma: float,
    config: Q3Config = CONFIG,
) -> tuple[np.ndarray, float]:
    mean_curve = _curve_for_target(train, target)
    window = min(20, L)
    target_slope = slope(target.relative_soh[L - window : L])
    strategy_slope = slope(mean_curve[L - window : L])
    training_slopes = [slope(record.relative_soh[L - window : L]) for record in train]
    sigma = robust_slope_scale(training_slopes)
    scaled_penalty = lambda_gamma * sigma**2
    gamma = (target_slope * strategy_slope + scaled_penalty) / (
        strategy_slope**2 + scaled_penalty
    )
    gamma = float(np.clip(gamma, *config.gamma_bounds))
    future_delta = mean_curve[config.future_start - 1 : config.future_end] - mean_curve[L - 1]
    return target.relative_at(L) + gamma * future_delta, gamma


def select_strategy_lambda(
    records: list[BatteryRecord],
    L: int,
    config: Q3Config = CONFIG,
) -> tuple[float, dict[float, dict[int, np.ndarray]]]:
    candidates: dict[float, dict[int, np.ndarray]] = {
        value: {} for value in config.lambda_gamma_grid
    }
    scores: dict[float, list[float]] = {value: [] for value in config.lambda_gamma_grid}
    for target in records:
        inner_train = [record for record in records if record.battery_id != target.battery_id]
        truth = target.absolute_future(config.future_start, config.future_end)
        for value in config.lambda_gamma_grid:
            pred_rel, _ = predict_strategy_transfer(inner_train, target, L, value, config)
            pred_abs = target.baseline * pred_rel
            candidates[value][target.battery_id] = pred_rel
            scores[value].append(float(np.sqrt(np.mean((pred_abs - truth) ** 2))))
    ranked = sorted(
        config.lambda_gamma_grid,
        key=lambda value: (float(np.mean(scores[value])), -value),
    )
    return float(ranked[0]), candidates
