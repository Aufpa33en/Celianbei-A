"""Fold-local PCA future basis with multi-output ridge score prediction."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from ..config import CONFIG, Q3Config
from ..core import BatteryRecord
from ..features import PrefixFeatureTransformer


def _target_matrix(records: list[BatteryRecord], L: int, config: Q3Config) -> np.ndarray:
    return np.vstack(
        [
            record.relative_soh[config.future_start - 1 : config.future_end]
            - record.relative_at(L)
            for record in records
        ]
    )


def _fit_predict_all_candidates(
    train: list[BatteryRecord],
    target: BatteryRecord,
    L: int,
    config: Q3Config,
) -> dict[tuple[int, float], np.ndarray]:
    transformer = PrefixFeatureTransformer.fit(train, L)
    X = transformer.transform(train, L)
    x_target = transformer.transform([target], L)
    Y = _target_matrix(train, L, config)
    y_mean = Y.mean(axis=0)
    centered = Y - y_mean
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    max_rank = max(1, min(centered.shape[0] - 1, centered.shape[1], vt.shape[0]))
    outputs: dict[tuple[int, float], np.ndarray] = {}
    xtx = X.T @ X
    eye = np.eye(X.shape[1])
    for requested_k in config.k_grid:
        k = min(requested_k, max_rank)
        basis = vt[:k].T
        scores = centered @ basis
        xts = X.T @ scores
        for alpha in config.alpha_grid:
            coef = np.linalg.solve(xtx + alpha * eye, xts)
            future_delta = y_mean + (x_target @ coef @ basis.T).ravel()
            outputs[(requested_k, float(alpha))] = target.relative_at(L) + future_delta
    return outputs


def select_trajectory_hyperparameters(
    records: list[BatteryRecord],
    L: int,
    config: Q3Config = CONFIG,
) -> tuple[tuple[int, float], dict[tuple[int, float], dict[int, np.ndarray]]]:
    predictions: dict[tuple[int, float], dict[int, np.ndarray]] = defaultdict(dict)
    errors: dict[tuple[int, float], list[float]] = defaultdict(list)
    for target in records:
        inner_train = [record for record in records if record.battery_id != target.battery_id]
        fold_predictions = _fit_predict_all_candidates(inner_train, target, L, config)
        truth = target.absolute_future(config.future_start, config.future_end)
        for key, pred_rel in fold_predictions.items():
            predictions[key][target.battery_id] = pred_rel
            pred_abs = target.baseline * pred_rel
            errors[key].append(float(np.sqrt(np.mean((pred_abs - truth) ** 2))))
    ranked = sorted(
        errors,
        key=lambda key: (float(np.mean(errors[key])), -key[1], key[0]),
    )
    return ranked[0], dict(predictions)


def predict_trajectory_ridge(
    train: list[BatteryRecord],
    target: BatteryRecord,
    L: int,
    hyperparameters: tuple[int, float],
    config: Q3Config = CONFIG,
) -> np.ndarray:
    return _fit_predict_all_candidates(train, target, L, config)[hyperparameters]
