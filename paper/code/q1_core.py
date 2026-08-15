"""Numerical core for the three comparable Question 1 curve models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


MODEL_POLYNOMIAL = "polynomial_mixed"
MODEL_SPLINE = "spline_mixed"
MODEL_FUNCTIONAL = "functional_ridge"
MODEL_TYPES = (MODEL_POLYNOMIAL, MODEL_SPLINE, MODEL_FUNCTIONAL)


@dataclass(frozen=True)
class ModelConfig:
    lambda_random: float = 0.1
    lambda_curve: float = 0.01


@dataclass
class PopulationCurveModel:
    model_type: str
    config: ModelConfig
    policy_names: tuple[str, ...]
    fixed_coef: np.ndarray
    battery_ids: np.ndarray
    random_coef: np.ndarray | None = None
    cell_coef: np.ndarray | None = None
    cell_policy: np.ndarray | None = None

    def predict(self, policy: str | Iterable[str], cycle: Iterable[float]) -> np.ndarray:
        cycles = np.asarray(cycle, dtype=float).reshape(-1)
        policies = np.asarray([policy] * len(cycles) if isinstance(policy, str) else policy, dtype=str)
        if len(policies) != len(cycles):
            raise ValueError("policy and cycle must have the same length")
        basis = make_basis(self.model_type, cycles)
        output = np.full(len(cycles), np.nan, dtype=float)
        policy_to_index = {name: i for i, name in enumerate(self.policy_names)}
        for name in np.unique(policies):
            if name not in policy_to_index:
                raise KeyError(f"policy absent from training data: {name}")
            use = policies == name
            output[use] = basis[use] @ self.fixed_coef[policy_to_index[name]]
        return output


def make_basis(model_type: str, cycle: Iterable[float]) -> np.ndarray:
    """Return the explicitly specified cycle basis, using x=t/200."""
    x = np.asarray(cycle, dtype=float).reshape(-1) / 200.0
    if model_type == MODEL_POLYNOMIAL:
        return np.column_stack((np.ones_like(x), x, x**2))
    if model_type in (MODEL_SPLINE, MODEL_FUNCTIONAL):
        columns = [np.ones_like(x), x, x**2, x**3]
        columns.extend(np.maximum(x - knot, 0.0) ** 3 for knot in (0.25, 0.50, 0.75))
        return np.column_stack(columns)
    raise ValueError(f"unknown model type: {model_type}")


def candidate_configs(model_type: str) -> list[ModelConfig]:
    if model_type == MODEL_POLYNOMIAL:
        return [ModelConfig(value, 0.0) for value in (0.01, 0.1, 1.0, 10.0)]
    if model_type == MODEL_SPLINE:
        return [
            ModelConfig(random_penalty, curve_penalty)
            for random_penalty in (0.03, 0.3, 3.0)
            for curve_penalty in (0.001, 0.01, 0.1, 1.0)
        ]
    if model_type == MODEL_FUNCTIONAL:
        return [ModelConfig(0.0, value) for value in (0.0001, 0.001, 0.01, 0.1, 1.0)]
    raise ValueError(f"unknown model type: {model_type}")


def fit_population_model(data: pd.DataFrame, model_type: str, config: ModelConfig) -> PopulationCurveModel:
    """Fit a strategy population curve with equal inferential units at battery level.

    The two mixed candidates minimize
        ||y - F beta - Z b||^2 + lambda_curve ||P beta||^2
                                   + lambda_random ||b||^2,
    where Z contains a random intercept and slope for each battery.  The
    functional candidate first smooths each battery, then averages cell
    coefficients within strategy so batteries receive equal weight.
    """
    required = {"battery_id", "cycle", "policy", "SOH_clean"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")
    frame = data.loc[np.isfinite(data["SOH_clean"]) & np.isfinite(data["cycle"])].copy()
    frame["policy"] = frame["policy"].astype(str)
    policy_names = tuple(pd.unique(frame["policy"]).tolist())
    battery_ids = pd.unique(frame["battery_id"]).astype(int)
    policy_index = {name: i for i, name in enumerate(policy_names)}
    battery_index = {int(value): i for i, value in enumerate(battery_ids)}
    basis = make_basis(model_type, frame["cycle"].to_numpy())
    n_rows, n_basis = basis.shape

    if model_type in (MODEL_POLYNOMIAL, MODEL_SPLINE):
        fixed = np.zeros((n_rows, len(policy_names) * n_basis), dtype=float)
        pidx = frame["policy"].map(policy_index).to_numpy(dtype=int)
        rows = np.arange(n_rows)
        for j in range(n_basis):
            fixed[rows, pidx * n_basis + j] = basis[:, j]

        random = np.zeros((n_rows, 2 * len(battery_ids)), dtype=float)
        bidx = frame["battery_id"].map(battery_index).to_numpy(dtype=int)
        x = frame["cycle"].to_numpy(dtype=float) / 200.0
        random[rows, 2 * bidx] = 1.0
        random[rows, 2 * bidx + 1] = x
        design = np.column_stack((fixed, random))

        penalty = np.zeros(design.shape[1], dtype=float)
        if model_type == MODEL_SPLINE:
            for p in range(len(policy_names)):
                start = p * n_basis
                penalty[start + 2 : start + n_basis] = config.lambda_curve
        penalty[len(policy_names) * n_basis :] = config.lambda_random
        coefficient = _penalized_solve(design, frame["SOH_clean"].to_numpy(), penalty)
        fixed_coef = coefficient[: len(policy_names) * n_basis].reshape(len(policy_names), n_basis)
        random_coef = coefficient[len(policy_names) * n_basis :].reshape(len(battery_ids), 2)
        return PopulationCurveModel(
            model_type, config, policy_names, fixed_coef, battery_ids, random_coef=random_coef
        )

    if model_type == MODEL_FUNCTIONAL:
        cell_coef = np.empty((len(battery_ids), n_basis), dtype=float)
        cell_policy = np.empty(len(battery_ids), dtype=object)
        penalty = np.zeros(n_basis, dtype=float)
        penalty[2:] = config.lambda_curve
        for i, battery_id in enumerate(battery_ids):
            use = frame["battery_id"].to_numpy() == battery_id
            cell_coef[i] = _penalized_solve(basis[use], frame.loc[use, "SOH_clean"].to_numpy(), penalty)
            cell_policy[i] = frame.loc[use, "policy"].iloc[0]
        fixed_coef = np.vstack([cell_coef[cell_policy == name].mean(axis=0) for name in policy_names])
        return PopulationCurveModel(
            model_type,
            config,
            policy_names,
            fixed_coef,
            battery_ids,
            cell_coef=cell_coef,
            cell_policy=cell_policy,
        )
    raise ValueError(f"unknown model type: {model_type}")


def _penalized_solve(design: np.ndarray, response: np.ndarray, penalty: np.ndarray) -> np.ndarray:
    lhs = design.T @ design
    scale = max(float(np.trace(lhs)) / max(lhs.shape[0], 1), 1.0)
    lhs.flat[:: lhs.shape[0] + 1] += penalty + 1e-12 * scale
    rhs = design.T @ response
    try:
        return np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(lhs, rhs, rcond=1e-12)[0]
