"""Shared numerical core for Question 2 smoke tests.

The strategy parameter coordinate, rather than a cycle row or a battery, is the
independent design unit.  All parameter-response regressions therefore average
within strategy first and validate by leaving an entire parameter coordinate out.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260814
LAMBDA_GRID = (0.0, 0.01, 0.1, 1.0, 10.0, 100.0)
CHECKPOINTS = np.array([25, 50, 75, 100, 125, 150, 175, 200], dtype=int)


@dataclass(frozen=True)
class Candidate:
    name: str
    features: tuple[str, ...]
    family: str = "ridge"
    quadratic_cycle: bool = False


STRATEGY_CANDIDATES = (
    Candidate("constant_mean", (), "constant"),
    Candidate("nearest_coordinate", ("C1", "q", "C2"), "nearest"),
    Candidate("ridge_raw_C1_q_C2", ("C1", "q", "C2")),
    Candidate("ridge_stage_E1_E2", ("E1", "E2")),
    Candidate("ridge_J", ("J",)),
    Candidate("ridge_H", ("H",)),
    Candidate("ridge_J_H", ("J", "H")),
    Candidate("ridge_Jhigh50", ("J_high_50",)),
    Candidate("ridge_Jhigh60", ("J_high_60",)),
    Candidate("ridge_Jhigh70", ("J_high_70",)),
)


HIERARCHICAL_CANDIDATES = (
    Candidate("hier_cycle_no_stress", (), "hierarchical", False),
    Candidate("hier_cycle_J_linear", ("J",), "hierarchical", False),
    Candidate("hier_cycle_H_linear", ("H",), "hierarchical", False),
    Candidate("hier_cycle_J_H_linear", ("J", "H"), "hierarchical", False),
    Candidate("hier_cycle_J_quadratic", ("J",), "hierarchical", True),
)


def load_clean_data(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    cycle_path = project_root / "data" / "processed" / "q1_cleaned" / "cycle_train_clean.csv"
    summary_path = project_root / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv"
    cycles = pd.read_csv(cycle_path)
    summary = pd.read_csv(summary_path)
    counts = cycles.groupby("battery_id", observed=True)["cycle"].nunique()
    complete_ids = counts[counts.eq(200)].index
    cycles = cycles[cycles["battery_id"].isin(complete_ids)].copy()
    summary = summary[summary["battery_id"].isin(complete_ids)].copy()
    if cycles["SOH_clean"].isna().any():
        raise ValueError("SOH_clean contains missing values in the complete cohort")
    return cycles, summary


def coordinate_id(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["C1"].map(lambda value: f"{value:.3f}")
        + "|"
        + frame["q"].map(lambda value: f"{value:.3f}")
        + "|"
        + frame["C2"].map(lambda value: f"{value:.3f}")
    )


def add_protocol_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["q"] = result["Q1"] / 100.0
    result["structure_batch"] = result["policy"].astype(str).str.contains("NEWSTRUCTURE").astype(int)
    result["T0"] = 60.0 * (result["q"] / result["C1"] + (0.8 - result["q"]) / result["C2"])
    result["E1"] = result["q"] * result["C1"]
    result["E2"] = (0.8 - result["q"]) * result["C2"]
    result["J"] = result["E1"] + result["E2"]
    result["H"] = 0.5 * (
        result["C1"] * result["q"] ** 2
        + result["C2"] * (0.8**2 - result["q"] ** 2)
    )
    for threshold in (0.5, 0.6, 0.7):
        result[f"J_high_{int(threshold * 100)}"] = np.where(
            threshold < result["q"],
            result["C1"] * (result["q"] - threshold)
            + result["C2"] * (0.8 - result["q"]),
            result["C2"] * (0.8 - threshold),
        )
    result["coordinate_id"] = coordinate_id(result)
    return result


def battery_degradation_summary(cycles: pd.DataFrame, battery_meta: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []
    meta = battery_meta.set_index("battery_id")
    for battery_id, group in cycles.groupby("battery_id", observed=True):
        group = group.sort_values("cycle")
        baseline = float(group.loc[group["cycle"].between(1, 5), "SOH_clean"].mean())
        end_soh = float(group.loc[group["cycle"].between(196, 200), "SOH_clean"].mean())
        x = group["cycle"].to_numpy(dtype=float) / 200.0
        degradation = 1.0 - group["SOH_clean"].to_numpy(dtype=float) / baseline
        design = np.column_stack((np.ones_like(x), x, x**2))
        coef = np.linalg.lstsq(design, degradation, rcond=None)[0]
        row = meta.loc[battery_id]
        records.append(
            {
                "battery_id": int(battery_id),
                "policy": str(row["policy"]),
                "C1": float(row["C1"]) if np.isfinite(row["C1"]) else np.nan,
                "Q1": float(row["Q1"]),
                "C2": float(row["C2"]),
                "baseline_soh": baseline,
                "soh200": end_soh,
                "relative_loss200": 1.0 - end_soh / baseline,
                "curve_loss200": float(coef.sum()),
                "curve_linear": float(coef[1]),
                "curve_quadratic": float(coef[2]),
                "mean_chargetime": float(row["mean_chargetime"]),
                "mean_IR": float(row["mean_IR"]),
                "mean_Tavg": float(row["mean_Tavg"]),
                "flag_battery41": int(battery_id == 41),
            }
        )
    return add_protocol_features(pd.DataFrame.from_records(records))


def strategy_summary(battery: pd.DataFrame) -> pd.DataFrame:
    complete = battery[battery["C1"].notna()].copy()
    feature_columns = [
        "C1", "Q1", "C2", "q", "T0", "E1", "E2", "J", "H",
        "J_high_50", "J_high_60", "J_high_70", "structure_batch",
    ]
    response_columns = [
        "soh200", "relative_loss200", "curve_loss200", "curve_linear", "curve_quadratic",
        "mean_chargetime", "mean_IR", "mean_Tavg",
    ]
    aggregations: dict[str, str | tuple[str, str]] = {column: "first" for column in feature_columns}
    aggregations.update({column: "mean" for column in response_columns})
    aggregations["n_batteries"] = ("battery_id", "size")
    result = complete.groupby("policy", as_index=False, observed=True).agg(**{
        key: value if isinstance(value, tuple) else (key, value) for key, value in aggregations.items()
    })
    result["coordinate_id"] = coordinate_id(result)
    result["equal_time_cohort"] = result["policy"].ne("3_6C-80PER_3_6C").astype(int)
    result["explicit_new_structure_cohort"] = result["structure_batch"].eq(1).astype(int)
    return result.sort_values("policy").reset_index(drop=True)


def standardized(train: pd.DataFrame, test: pd.DataFrame, features: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not features:
        return np.empty((len(train), 0)), np.empty((len(test), 0)), np.array([]), np.array([])
    mean = train.loc[:, features].mean(axis=0).to_numpy(dtype=float, copy=True)
    scale = train.loc[:, features].std(axis=0, ddof=0).to_numpy(dtype=float, copy=True)
    scale[scale < 1e-12] = 1.0
    return (
        (train.loc[:, features].to_numpy(dtype=float) - mean) / scale,
        (test.loc[:, features].to_numpy(dtype=float) - mean) / scale,
        mean,
        scale,
    )


def ridge_fit(x: np.ndarray, y: np.ndarray, ridge_lambda: float) -> np.ndarray:
    design = np.column_stack((np.ones(len(x)), x))
    penalty = np.eye(design.shape[1]) * ridge_lambda
    penalty[0, 0] = 0.0
    lhs = design.T @ design + penalty
    return np.linalg.lstsq(lhs, design.T @ y, rcond=None)[0]


def ridge_predict(coef: np.ndarray, x: np.ndarray) -> np.ndarray:
    return np.column_stack((np.ones(len(x)), x)) @ coef


def select_lambda_inner(train: pd.DataFrame, response: str, features: tuple[str, ...]) -> float:
    groups = train["coordinate_id"].unique().tolist()
    if len(groups) <= 3:
        return 10.0
    scores: list[tuple[float, float]] = []
    for ridge_lambda in LAMBDA_GRID:
        errors: list[float] = []
        for group in groups:
            inner_train = train[train["coordinate_id"].ne(group)]
            inner_test = train[train["coordinate_id"].eq(group)]
            x_train, x_test, _, _ = standardized(inner_train, inner_test, features)
            coef = ridge_fit(x_train, inner_train[response].to_numpy(dtype=float), ridge_lambda)
            prediction = ridge_predict(coef, x_test)
            errors.append(float(np.mean((prediction - inner_test[response].to_numpy(dtype=float)) ** 2)))
        scores.append((float(np.mean(errors)), ridge_lambda))
    minimum = min(value for value, _ in scores)
    tolerance = minimum * 1.01 + 1e-15
    return max(ridge_lambda for value, ridge_lambda in scores if value <= tolerance)


def nearest_prediction(train: pd.DataFrame, test: pd.DataFrame, response: str) -> np.ndarray:
    features = ("C1", "q", "C2")
    x_train, x_test, _, _ = standardized(train, test, features)
    y = train[response].to_numpy(dtype=float)
    output = np.empty(len(test), dtype=float)
    for index, row in enumerate(x_test):
        distance = np.sum((x_train - row) ** 2, axis=1)
        output[index] = y[int(np.argmin(distance))]
    return output


def fit_hierarchical_penalized(
    train_cycles: pd.DataFrame,
    train_strategy: pd.DataFrame,
    features: tuple[str, ...],
    quadratic: bool,
    lambda_fixed: float = 1.0,
    lambda_battery: float = 1.0,
    lambda_policy: float = 10.0,
) -> tuple[np.ndarray, dict[str, object]]:
    """Fit a linearized smoke surrogate of Model C by penalized least squares.

    y_it = beta0 + beta_x*x + sum beta_k*z_pk*x + beta_q*x^2
           + a_i + u_i*x + v_p*x + error.

    For runtime, this smoke fit uses cycle 1 and every fifth cycle. The formal
    nonlinear exponential-link/AR(1) likelihood is intentionally not claimed
    here. This surrogate answers whether the additional hierarchy has enough
    predictive signal to justify a later full Model C fit.
    """
    strategy_lookup = train_strategy.set_index("policy")
    frame = train_cycles[
        train_cycles["policy"].isin(strategy_lookup.index)
        & (train_cycles["cycle"].eq(1) | train_cycles["cycle"].mod(5).eq(0))
    ].copy()
    policies = sorted(frame["policy"].unique().tolist())
    batteries = sorted(frame["battery_id"].unique().tolist())
    p_index = {name: index for index, name in enumerate(policies)}
    b_index = {value: index for index, value in enumerate(batteries)}
    means = train_strategy.loc[:, features].mean(axis=0).to_numpy(dtype=float, copy=True) if features else np.array([])
    scales = train_strategy.loc[:, features].std(axis=0, ddof=0).to_numpy(dtype=float, copy=True) if features else np.array([])
    if len(scales):
        scales[scales < 1e-12] = 1.0
    x = frame["cycle"].to_numpy(dtype=float) / 200.0
    fixed_columns = [np.ones(len(frame)), x]
    for feature, mean, scale in zip(features, means, scales):
        z = frame["policy"].map(strategy_lookup[feature]).to_numpy(dtype=float)
        fixed_columns.append(((z - mean) / scale) * x)
    if quadratic:
        fixed_columns.append(x**2)
    fixed = np.column_stack(fixed_columns)
    random_battery = np.zeros((len(frame), 2 * len(batteries)))
    random_policy = np.zeros((len(frame), len(policies)))
    rows = np.arange(len(frame))
    bidx = frame["battery_id"].map(b_index).to_numpy(dtype=int)
    pidx = frame["policy"].map(p_index).to_numpy(dtype=int)
    random_battery[rows, 2 * bidx] = 1.0
    random_battery[rows, 2 * bidx + 1] = x
    random_policy[rows, pidx] = x
    design = np.column_stack((fixed, random_battery, random_policy))
    penalty = np.zeros(design.shape[1])
    penalty[2 : 2 + len(features)] = lambda_fixed
    penalty[fixed.shape[1] : fixed.shape[1] + random_battery.shape[1]] = lambda_battery
    penalty[fixed.shape[1] + random_battery.shape[1] :] = lambda_policy
    lhs = design.T @ design
    lhs.flat[:: lhs.shape[0] + 1] += penalty + 1e-10
    rhs = design.T @ frame["SOH_clean"].to_numpy(dtype=float)
    try:
        coef = np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        coef = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
    fitted = design @ coef
    residual = frame["SOH_clean"].to_numpy(dtype=float) - fitted
    residual_frame = pd.DataFrame({"battery_id": frame["battery_id"].to_numpy(), "cycle": frame["cycle"].to_numpy(), "residual": residual})
    pairs = []
    for _, group in residual_frame.groupby("battery_id", observed=True):
        values = group.sort_values("cycle")["residual"].to_numpy()
        if len(values) > 1:
            pairs.append(np.corrcoef(values[:-1], values[1:])[0, 1])
    info = {
        "fixed_coef": coef[: fixed.shape[1]],
        "feature_mean": means,
        "feature_scale": scales,
        "features": features,
        "quadratic": quadratic,
        "train_rmse": float(np.sqrt(np.mean(residual**2))),
        "lag1_residual_correlation": float(np.nanmean(pairs)),
        "n_policy": len(policies),
        "n_battery": len(batteries),
    }
    return coef, info


def predict_hierarchical(info: dict[str, object], test_strategy: pd.DataFrame, cycles: np.ndarray) -> np.ndarray:
    features = tuple(info["features"])
    means = np.asarray(info["feature_mean"], dtype=float)
    scales = np.asarray(info["feature_scale"], dtype=float)
    fixed_coef = np.asarray(info["fixed_coef"], dtype=float)
    predictions: list[dict[str, float | int | str]] = []
    x = cycles.astype(float) / 200.0
    for _, row in test_strategy.iterrows():
        columns = [np.ones(len(x)), x]
        for feature, mean, scale in zip(features, means, scales):
            columns.append(np.repeat((float(row[feature]) - mean) / scale, len(x)) * x)
        if bool(info["quadratic"]):
            columns.append(x**2)
        value = np.column_stack(columns) @ fixed_coef
        for cycle, prediction in zip(cycles, value):
            predictions.append({"policy": row["policy"], "cycle": int(cycle), "prediction": float(prediction)})
    return pd.DataFrame(predictions)
