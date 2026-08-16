"""Primary Question 2 analysis with predicted T80 as the lifetime response."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd

from q1_models.experiments import load_clean_data as load_q1_clean_data
from q1_models.lifetime import (
    LifetimeSettings,
    estimate_battery_lifetimes,
    validate_lifetime_windows,
)

from .core import add_protocol_features


SEED = 20260816
EXPOSURES = ("J", "H", "J_high_50", "J_high_60", "J_high_70")


@dataclass(frozen=True)
class LifetimeValidationSettings:
    bootstrap_repetitions: int = 2000
    seed: int = SEED


def prepare_lifetime_design(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    cycles, meta = load_q1_clean_data(project_root)
    _, window_summary, selected_window = validate_lifetime_windows(cycles, LifetimeSettings())
    battery = estimate_battery_lifetimes(cycles, selected_window, LifetimeSettings())
    meta_columns = meta[["battery_id", "policy", "C1", "Q1", "C2"]].rename(
        columns={"battery_id": "BatteryId", "policy": "MetaPolicy"}
    )
    battery = battery.merge(meta_columns, on="BatteryId", how="left", validate="one_to_one")
    if not battery["Policy"].eq(battery["MetaPolicy"]).all():
        raise ValueError("Q1 lifetime policy does not match cleaned battery metadata")
    battery = battery.drop(columns="MetaPolicy").rename(columns={"Policy": "policy"})
    battery["log_t80"] = np.log(battery["EstimatedT80"])
    battery = add_protocol_features(battery)

    parameterized = battery.loc[battery["C1"].notna()].copy()
    features = [
        "C1", "Q1", "C2", "q", "T0", "E1", "E2", "J", "H",
        "J_high_50", "J_high_60", "J_high_70", "structure_batch", "coordinate_id",
    ]
    aggregation = {column: (column, "first") for column in features}
    aggregation.update(
        {
            "n_batteries": ("BatteryId", "size"),
            "mean_log_t80": ("log_t80", "mean"),
            "median_t80": ("EstimatedT80", "median"),
            "mean_t80": ("EstimatedT80", "mean"),
            "minimum_t80": ("EstimatedT80", "min"),
            "maximum_t80": ("EstimatedT80", "max"),
        }
    )
    strategy = parameterized.groupby("policy", as_index=False, observed=True).agg(**aggregation)
    strategy["explicit_new_structure_cohort"] = strategy["structure_batch"].eq(1)
    strategy["lifetime_prefix_cycle"] = 150
    strategy["lifetime_tail_window"] = selected_window
    return battery, strategy.sort_values("policy").reset_index(drop=True), selected_window


def _fit_line(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    design = np.column_stack((np.ones(len(x)), x))
    intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
    return float(intercept), float(slope)


def evaluate_exposure_models(strategy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cohort = strategy.loc[strategy["explicit_new_structure_cohort"].astype(bool)].copy()
    y = cohort["mean_log_t80"].to_numpy(dtype=float)
    prediction_rows = []
    metric_rows = []
    models: tuple[tuple[str, str | None], ...] = (("constant_mean", None),) + tuple(
        (f"linear_{feature}", feature) for feature in EXPOSURES
    )
    for model, feature in models:
        predictions = np.empty(len(cohort), dtype=float)
        for heldout in range(len(cohort)):
            train = np.arange(len(cohort)) != heldout
            if feature is None:
                predictions[heldout] = y[train].mean()
            else:
                x = cohort[feature].to_numpy(dtype=float)
                intercept, slope = _fit_line(x[train], y[train])
                predictions[heldout] = intercept + slope * x[heldout]
        error = predictions - y
        if feature is None:
            intercept = float(y.mean())
            slope = np.nan
        else:
            intercept, slope = _fit_line(cohort[feature].to_numpy(dtype=float), y)
        for row, prediction, residual in zip(cohort.itertuples(), predictions, error):
            prediction_rows.append(
                {
                    "model": model,
                    "feature": feature or "none",
                    "heldout_policy": row.policy,
                    "observed_mean_log_t80": row.mean_log_t80,
                    "predicted_mean_log_t80": prediction,
                    "error": residual,
                }
            )
        metric_rows.append(
            {
                "model": model,
                "feature": feature or "none",
                "n_strategy": len(cohort),
                "loco_rmse_log_t80": float(np.sqrt(np.mean(error**2))),
                "loco_mae_log_t80": float(np.mean(np.abs(error))),
                "full_intercept": intercept,
                "full_slope_original_scale": slope,
                "expected_negative_direction": bool(feature is not None and slope < 0),
            }
        )
    metrics = pd.DataFrame(metric_rows)
    baseline = float(metrics.loc[metrics["model"].eq("constant_mean"), "loco_rmse_log_t80"].iloc[0])
    metrics["relative_rmse_improvement_vs_constant"] = 1.0 - metrics["loco_rmse_log_t80"] / baseline
    metrics["eligible_explanatory"] = (
        metrics["model"].ne("constant_mean")
        & metrics["expected_negative_direction"]
        & metrics["relative_rmse_improvement_vs_constant"].gt(0)
    )
    eligible = metrics.loc[metrics["eligible_explanatory"]].sort_values(
        ["loco_rmse_log_t80", "model"]
    )
    selected = str(eligible.iloc[0]["model"]) if len(eligible) else None
    metrics["selected_primary_explanatory"] = (
        False if selected is None else metrics["model"].eq(selected)
    )
    metrics["selection_status"] = (
        "selected_eligible_explanatory_model" if selected is not None
        else "no_eligible_explanatory_model"
    )
    return pd.DataFrame(prediction_rows), metrics.sort_values("loco_rmse_log_t80").reset_index(drop=True)


def bootstrap_exposure_selection(
    battery: pd.DataFrame,
    strategy: pd.DataFrame,
    settings: LifetimeValidationSettings,
) -> pd.DataFrame:
    rng = np.random.default_rng(settings.seed)
    cohort = strategy.loc[strategy["explicit_new_structure_cohort"].astype(bool)].copy()
    values = {
        policy: battery.loc[battery["policy"].eq(policy), "log_t80"].to_numpy(dtype=float)
        for policy in cohort["policy"]
    }
    records = {f"linear_{feature}": {"wins": 0, "improvement": [], "slope": []} for feature in EXPOSURES}
    records["constant_mean"] = {"wins": 0, "improvement": [], "slope": []}
    for _ in range(settings.bootstrap_repetitions):
        sampled = cohort.copy()
        sampled["mean_log_t80"] = [
            rng.choice(values[policy], size=len(values[policy]), replace=True).mean()
            for policy in sampled["policy"]
        ]
        _, metrics = evaluate_exposure_models(sampled)
        selected = metrics.loc[metrics["selected_primary_explanatory"], "model"]
        winner = str(selected.iloc[0]) if len(selected) else "constant_mean"
        records[winner]["wins"] += 1
        for row in metrics.itertuples():
            records[row.model]["improvement"].append(row.relative_rmse_improvement_vs_constant)
            records[row.model]["slope"].append(row.full_slope_original_scale)

    rows = []
    for model, record in records.items():
        improvement = np.asarray(record["improvement"], dtype=float)
        slope = np.asarray(record["slope"], dtype=float)
        finite_slope = slope[np.isfinite(slope)]
        rows.append(
            {
                "model": model,
                "bootstrap_repetitions": settings.bootstrap_repetitions,
                "selected_frequency": record["wins"] / settings.bootstrap_repetitions,
                "median_improvement_vs_constant": float(np.median(improvement)),
                "improvement_ci95_low": float(np.quantile(improvement, 0.025)),
                "improvement_ci95_high": float(np.quantile(improvement, 0.975)),
                "negative_slope_frequency": (
                    float(np.mean(finite_slope < 0)) if len(finite_slope) else np.nan
                ),
            }
        )
    return pd.DataFrame(rows).sort_values("selected_frequency", ascending=False).reset_index(drop=True)


def deletion_diagnostics(strategy: pd.DataFrame) -> pd.DataFrame:
    cohort = strategy.loc[strategy["explicit_new_structure_cohort"].astype(bool)].copy()
    rows = []
    for excluded in cohort["policy"]:
        reduced = cohort.loc[cohort["policy"].ne(excluded)].copy()
        reduced["explicit_new_structure_cohort"] = True
        _, metrics = evaluate_exposure_models(reduced)
        selected = metrics.loc[metrics["selected_primary_explanatory"]]
        best = selected.iloc[0] if len(selected) else metrics.loc[metrics["model"].eq("constant_mean")].iloc[0]
        rows.append(
            {
                "excluded_policy": excluded,
                "remaining_strategy": len(reduced),
                "selection_status": "selected_explanatory" if len(selected) else "constant_only",
                "selected_model": best["model"],
                "selected_improvement_vs_constant": best["relative_rmse_improvement_vs_constant"],
            }
        )
    return pd.DataFrame(rows)


def max_direction_permutation_diagnostic(strategy: pd.DataFrame) -> pd.DataFrame:
    cohort = strategy.loc[strategy["explicit_new_structure_cohort"].astype(bool)].copy()
    y = cohort["mean_log_t80"].to_numpy(dtype=float)
    y_scale = y.std(ddof=0)

    def statistic(values: np.ndarray) -> float:
        scores = []
        for feature in EXPOSURES:
            x = cohort[feature].to_numpy(dtype=float)
            _, slope = _fit_line(x, values)
            scores.append(-slope * x.std(ddof=0) / y_scale)
        return float(max(scores))

    observed = statistic(y)
    distribution = np.asarray([statistic(y[list(order)]) for order in permutations(range(len(y)))])
    exceed = int(np.sum(distribution >= observed - 1e-12))
    return pd.DataFrame(
        [
            {
                "n_strategy": len(cohort),
                "n_exact_permutations": len(distribution),
                "observed_max_direction_score": observed,
                "tail_fraction": exceed / len(distribution),
                "minimum_resolution": 1.0 / len(distribution),
                "interpretation": "diagnostic_only_nonrandom_heteroscedastic_strategy_means_not_exchangeable",
            }
        ]
    )


def run_lifetime_validation(
    project_root: Path,
    settings: LifetimeValidationSettings = LifetimeValidationSettings(),
) -> dict[str, pd.DataFrame]:
    battery, strategy, selected_window = prepare_lifetime_design(project_root)
    predictions, metrics = evaluate_exposure_models(strategy)
    bootstrap = bootstrap_exposure_selection(battery, strategy, settings)
    deletion = deletion_diagnostics(strategy)
    permutation = max_direction_permutation_diagnostic(strategy)
    metadata = pd.DataFrame(
        [
            {"parameter": "lifetime_definition", "value": "predicted_cycle_at_SOH_0.8"},
            {"parameter": "lifetime_prefix_cycle", "value": 150},
            {"parameter": "selected_tail_window", "value": selected_window},
            {"parameter": "primary_response", "value": "strategy_mean_log_battery_T80"},
            {"parameter": "primary_cohort", "value": "6_explicit_NEWSTRUCTURE_strategies"},
            {"parameter": "validation", "value": "leave_one_strategy_coordinate_out"},
            {"parameter": "bootstrap_repetitions", "value": settings.bootstrap_repetitions},
            {"parameter": "seed", "value": settings.seed},
        ]
    )
    return {
        "lifetime_battery_design": battery,
        "lifetime_strategy_design": strategy,
        "lifetime_loco_predictions": predictions,
        "lifetime_model_comparison": metrics,
        "lifetime_bootstrap_selection": bootstrap,
        "lifetime_deletion_diagnostics": deletion,
        "lifetime_permutation_diagnostic": permutation,
        "lifetime_validation_metadata": metadata,
    }
