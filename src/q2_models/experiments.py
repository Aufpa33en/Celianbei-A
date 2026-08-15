"""Experiment orchestration for the Question 2 smoke-test stage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .core import (
    CHECKPOINTS,
    HIERARCHICAL_CANDIDATES,
    STRATEGY_CANDIDATES,
    battery_degradation_summary,
    fit_hierarchical_penalized,
    load_clean_data,
    nearest_prediction,
    predict_hierarchical,
    ridge_fit,
    ridge_predict,
    select_lambda_inner,
    standardized,
    strategy_summary,
)
from .outputs import write_outputs


RESPONSES = ("relative_loss200", "soh200")


def design_audit(strategy: pd.DataFrame) -> pd.DataFrame:
    output = strategy.copy()
    output["T0_deviation_from_10"] = output["T0"] - 10.0
    output["actual_minus_T0"] = output["mean_chargetime"] - output["T0"]
    return output[
        [
            "policy", "coordinate_id", "n_batteries", "structure_batch", "equal_time_cohort", "explicit_new_structure_cohort",
            "C1", "Q1", "C2", "T0", "T0_deviation_from_10", "mean_chargetime",
            "actual_minus_T0", "J", "H", "J_high_50", "J_high_60", "J_high_70",
        ]
    ]


def scalar_loco(strategy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions: list[dict[str, object]] = []
    coefficients: list[dict[str, object]] = []
    for cohort_name, cohort in (
        ("all_complete", strategy.copy()),
        ("equal_T0_nonbaseline", strategy[strategy["equal_time_cohort"].eq(1)].copy()),
        ("explicit_new_structure", strategy[strategy["explicit_new_structure_cohort"].eq(1)].copy()),
    ):
        groups = cohort["coordinate_id"].unique().tolist()
        for response in RESPONSES:
            for candidate in STRATEGY_CANDIDATES:
                for fold, group in enumerate(groups, start=1):
                    train = cohort[cohort["coordinate_id"].ne(group)].copy()
                    test = cohort[cohort["coordinate_id"].eq(group)].copy()
                    ridge_lambda = np.nan
                    coef = np.array([train[response].mean()])
                    if candidate.family == "constant":
                        predicted = np.repeat(coef[0], len(test))
                    elif candidate.family == "nearest":
                        predicted = nearest_prediction(train, test, response)
                    else:
                        ridge_lambda = select_lambda_inner(train, response, candidate.features)
                        x_train, x_test, _, _ = standardized(train, test, candidate.features)
                        coef = ridge_fit(x_train, train[response].to_numpy(dtype=float), ridge_lambda)
                        predicted = ridge_predict(coef, x_test)
                    for (_, row), value in zip(test.iterrows(), predicted):
                        predictions.append(
                            {
                                "cohort": cohort_name,
                                "response": response,
                                "model": candidate.name,
                                "fold": fold,
                                "heldout_coordinate": group,
                                "policy": row["policy"],
                                "observed": float(row[response]),
                                "predicted": float(value),
                                "error": float(value - row[response]),
                                "lambda": ridge_lambda,
                            }
                        )
                    coefficient_row: dict[str, object] = {
                        "cohort": cohort_name,
                        "response": response,
                        "model": candidate.name,
                        "fold": fold,
                        "heldout_coordinate": group,
                        "lambda": ridge_lambda,
                        "intercept_standardized": float(coef[0]),
                    }
                    for index, feature in enumerate(candidate.features, start=1):
                        coefficient_row[f"coef_{feature}"] = float(coef[index]) if len(coef) > index else np.nan
                    coefficients.append(coefficient_row)
    prediction_frame = pd.DataFrame(predictions)
    metric_frame = summarize_metrics(prediction_frame)
    return prediction_frame, metric_frame, pd.DataFrame(coefficients)


def observed_policy_curve(cycles: pd.DataFrame, policies: list[str]) -> pd.DataFrame:
    frame = cycles[cycles["policy"].isin(policies) & cycles["cycle"].isin(CHECKPOINTS)].copy()
    return frame.groupby(["policy", "cycle"], as_index=False, observed=True)["SOH_clean"].mean().rename(columns={"SOH_clean": "observed"})


def hierarchical_loco(cycles: pd.DataFrame, strategy: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions: list[pd.DataFrame] = []
    diagnostics: list[dict[str, object]] = []
    for cohort_name, cohort in (
        ("equal_T0_nonbaseline", strategy[strategy["equal_time_cohort"].eq(1)].copy()),
        ("explicit_new_structure", strategy[strategy["explicit_new_structure_cohort"].eq(1)].copy()),
    ):
        groups = cohort["coordinate_id"].unique().tolist()
        cohort_cycles = cycles[cycles["policy"].isin(cohort["policy"])].copy()
        for candidate in HIERARCHICAL_CANDIDATES:
            for fold, group in enumerate(groups, start=1):
                train_strategy = cohort[cohort["coordinate_id"].ne(group)].copy()
                test_strategy = cohort[cohort["coordinate_id"].eq(group)].copy()
                train_cycles = cohort_cycles[cohort_cycles["policy"].isin(train_strategy["policy"])].copy()
                _, info = fit_hierarchical_penalized(
                    train_cycles,
                    train_strategy,
                    candidate.features,
                    candidate.quadratic_cycle,
                    lambda_fixed=10.0 if len(candidate.features) > 1 else 1.0,
                    lambda_battery=1.0,
                    lambda_policy=10.0,
                )
                predicted = predict_hierarchical(info, test_strategy, CHECKPOINTS)
                observed = observed_policy_curve(cohort_cycles, test_strategy["policy"].tolist())
                fold_frame = predicted.merge(observed, on=["policy", "cycle"], how="left")
                fold_frame["error"] = fold_frame["prediction"] - fold_frame["observed"]
                fold_frame["cohort"] = cohort_name
                fold_frame["model"] = candidate.name
                fold_frame["fold"] = fold
                fold_frame["heldout_coordinate"] = group
                predictions.append(fold_frame)
                diagnostics.append(
                    {
                        "cohort": cohort_name,
                        "model": candidate.name,
                        "fold": fold,
                        "heldout_coordinate": group,
                        "train_rmse": info["train_rmse"],
                        "lag1_residual_correlation": info["lag1_residual_correlation"],
                        "n_train_policy": info["n_policy"],
                        "n_train_battery": info["n_battery"],
                        "quadratic_cycle": candidate.quadratic_cycle,
                        "lambda_fixed": 10.0 if len(candidate.features) > 1 else 1.0,
                        "lambda_battery": 1.0,
                        "lambda_policy": 10.0,
                    }
                )
    prediction_frame = pd.concat(predictions, ignore_index=True)
    metrics = (
        prediction_frame.groupby(["cohort", "model"], as_index=False, observed=True)
        .agg(
            curve_rmse=("error", lambda values: float(np.sqrt(np.mean(np.square(values))))),
            curve_mae=("error", lambda values: float(np.mean(np.abs(values)))),
            n_predictions=("error", "size"),
        )
    )
    metrics["response"] = "checkpoint_curve"
    return prediction_frame, metrics, pd.DataFrame(diagnostics)


def summarize_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    policy_metrics = (
        predictions.groupby(["cohort", "response", "model", "heldout_coordinate"], as_index=False, observed=True)
        .agg(fold_mse=("error", lambda values: float(np.mean(np.square(values)))), fold_mae=("error", lambda values: float(np.mean(np.abs(values)))))
    )
    result = (
        policy_metrics.groupby(["cohort", "response", "model"], as_index=False, observed=True)
        .agg(rmse=("fold_mse", lambda values: float(np.sqrt(np.mean(values)))), mae=("fold_mae", "mean"), n_coordinate_folds=("heldout_coordinate", "size"))
    )
    baseline = result[result["model"].eq("constant_mean")][["cohort", "response", "rmse"]].rename(columns={"rmse": "baseline_rmse"})
    result = result.merge(baseline, on=["cohort", "response"], how="left")
    result["relative_rmse_improvement"] = 1.0 - result["rmse"] / result["baseline_rmse"]
    return result.sort_values(["cohort", "response", "rmse"]).reset_index(drop=True)


def selection_table(scalar_metrics: pd.DataFrame, hierarchical_metrics: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    primary = scalar_metrics[scalar_metrics["cohort"].eq("explicit_new_structure")].copy()
    rmse = primary.pivot(index="model", columns="response", values="rmse")
    improvement = primary.pivot(index="model", columns="response", values="relative_rmse_improvement")
    table = pd.DataFrame(index=rmse.index)
    table["relative_loss_rmse"] = rmse["relative_loss200"]
    table["soh200_rmse"] = rmse["soh200"]
    table["relative_loss_improvement"] = improvement["relative_loss200"]
    table["soh200_improvement"] = improvement["soh200"]
    table["rank_relative_loss"] = table["relative_loss_rmse"].rank(method="min")
    table["rank_soh200"] = table["soh200_rmse"].rank(method="min")
    table["mean_scalar_rank"] = (table["rank_relative_loss"] + table["rank_soh200"]) / 2.0
    table["role"] = "explanatory_candidate"
    table.loc[[name for name in ("constant_mean", "nearest_coordinate") if name in table.index], "role"] = "benchmark"
    table["eligible_explanatory"] = (
        table["role"].eq("explanatory_candidate")
        & table["relative_loss_improvement"].gt(0)
        & table["soh200_improvement"].gt(0)
    )
    eligible = table[table["eligible_explanatory"]].sort_values(["mean_scalar_rank", "relative_loss_rmse"])
    selected = eligible.index[0] if len(eligible) else None
    predictive = table[table.index != "constant_mean"].sort_values("relative_loss_rmse").index[0]
    table["selected_explanatory_smoke_model"] = False if selected is None else table.index == selected
    table["explanatory_selection_status"] = (
        "selected_eligible_explanatory_model" if selected is not None
        else "no_eligible_explanatory_model"
    )
    table["best_predictive_benchmark"] = table.index == predictive
    table["selection_scope"] = "explicit_NEWSTRUCTURE; two scalar responses; leave-one-coordinate-out"
    table["formal_model_C_status"] = "not_run; linearized surrogate reported separately"
    return table.reset_index().rename(columns={"index": "model"}).sort_values(["role", "mean_scalar_rank"]).reset_index(drop=True)


def fit_selected_strategy_model(strategy: pd.DataFrame, selection: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows = selection.loc[selection["selected_explanatory_smoke_model"], "model"]
    if len(selected_rows) != 1:
        raise ValueError("Exactly one eligible explanatory model is required; benchmarks cannot be substituted")
    selected_name = selected_rows.iloc[0]
    candidate = next(item for item in STRATEGY_CANDIDATES if item.name == selected_name)
    cohort = strategy[strategy["explicit_new_structure_cohort"].eq(1)].copy()
    fit_rows: list[dict[str, object]] = []
    prediction_rows: list[dict[str, object]] = []
    for response in RESPONSES:
        ridge_lambda = select_lambda_inner(cohort, response, candidate.features)
        x, _, mean, scale = standardized(cohort, cohort, candidate.features)
        coef = ridge_fit(x, cohort[response].to_numpy(dtype=float), ridge_lambda)
        predicted = ridge_predict(coef, x)
        row: dict[str, object] = {
            "model": selected_name,
            "response": response,
            "lambda": ridge_lambda,
            "intercept_standardized": float(coef[0]),
            "train_rmse_strategy_mean": float(np.sqrt(np.mean((predicted - cohort[response].to_numpy(dtype=float)) ** 2))),
            "n_strategy": len(cohort),
            "n_unique_coordinate": cohort["coordinate_id"].nunique(),
        }
        for index, feature in enumerate(candidate.features):
            row[f"feature_{index + 1}"] = feature
            row[f"feature_mean_{index + 1}"] = float(mean[index])
            row[f"feature_scale_{index + 1}"] = float(scale[index])
            row[f"coef_standardized_{index + 1}"] = float(coef[index + 1])
            row[f"coef_original_scale_{index + 1}"] = float(coef[index + 1] / scale[index])
        fit_rows.append(row)
        for (_, policy_row), value in zip(cohort.iterrows(), predicted):
            prediction_rows.append(
                {
                    "model": selected_name,
                    "response": response,
                    "policy": policy_row["policy"],
                    "coordinate_id": policy_row["coordinate_id"],
                    "observed": float(policy_row[response]),
                    "fitted": float(value),
                    "residual": float(value - policy_row[response]),
                }
            )
    return pd.DataFrame(fit_rows), pd.DataFrame(prediction_rows)


def run_smoke_test(project_root: Path) -> dict[str, pd.DataFrame]:
    cycles, meta = load_clean_data(project_root)
    battery = battery_degradation_summary(cycles, meta)
    strategy = strategy_summary(battery)
    audit = design_audit(strategy)
    scalar_predictions, scalar_metrics, coefficients = scalar_loco(strategy)
    hierarchical_predictions, hierarchical_metrics, diagnostics = hierarchical_loco(cycles, strategy)
    selection = selection_table(scalar_metrics, hierarchical_metrics, diagnostics)
    selected_fit, selected_predictions = fit_selected_strategy_model(strategy, selection)
    outputs = {
        "design_audit": audit,
        "battery_summary": battery,
        "strategy_summary": strategy,
        "scalar_predictions": scalar_predictions,
        "scalar_metrics": scalar_metrics,
        "coefficient_stability": coefficients,
        "hierarchical_predictions": hierarchical_predictions,
        "hierarchical_metrics": hierarchical_metrics,
        "hierarchical_diagnostics": diagnostics,
        "model_selection": selection,
        "selected_model_fit": selected_fit,
        "selected_model_predictions": selected_predictions,
    }
    write_outputs(project_root, outputs)
    return outputs
