"""Question 3 smoke experiment orchestration."""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CONFIG, Q3Config
from .core import (
    BatteryRecord,
    complete_battery_ids,
    fit_power_law,
    load_records,
    power_law_eol,
    prediction_metrics,
    project_absolute_prediction,
)
from .models import (
    predict_individual_power,
    predict_linear_trend,
    predict_persistence,
    predict_strategy_transfer,
    predict_trajectory_ridge,
    select_strategy_lambda,
    select_trajectory_hyperparameters,
)


MODELS = ("P0_persistence", "P1_linear", "A_power", "B_strategy", "C_ridge", "D_ensemble")
STAGES = ("load", "features", "fit", "predict", "eol", "write", "total")


def _frozen_smoke_split(
    records: dict[int, BatteryRecord], meta: pd.DataFrame, config: Q3Config
) -> tuple[list[BatteryRecord], list[BatteryRecord]]:
    complete = meta.loc[meta["prediction_test"].eq(0)].copy()
    rng = np.random.default_rng(config.seed)
    sampled: list[int] = []
    for _, group in complete.groupby("policy", sort=True):
        ids = np.sort(group["battery_id"].astype(int).to_numpy())
        sampled.append(int(rng.choice(ids)))
    if tuple(sampled) != config.smoke_battery_ids:
        raise AssertionError(f"Frozen smoke IDs changed: {sampled}")
    validation = [records[battery_id] for battery_id in sampled]
    validation_ids = set(sampled)
    training = [records[battery_id] for battery_id in complete_battery_ids(meta) if battery_id not in validation_ids]
    if len({record.policy for record in validation}) != 9:
        raise AssertionError("Smoke validation batteries must cover all nine strategies")
    return training, validation


def _choose_ensemble_weight(
    records: list[BatteryRecord],
    b_oof: dict[int, np.ndarray],
    c_oof: dict[int, np.ndarray],
    config: Q3Config,
) -> float:
    scores: dict[float, float] = {}
    for weight in config.ensemble_weight_grid:
        errors = []
        for record in records:
            pred_rel = weight * b_oof[record.battery_id] + (1.0 - weight) * c_oof[record.battery_id]
            pred_abs = record.baseline * pred_rel
            truth = record.absolute_future(config.future_start, config.future_end)
            errors.append(float(np.sqrt(np.mean((pred_abs - truth) ** 2))))
        scores[weight] = float(np.mean(errors))
    best_score = min(scores.values())
    tied = [w for w, score in scores.items() if np.isclose(score, best_score, rtol=0, atol=1e-12)]
    tied.sort(key=lambda w: (-abs(w - 0.5), -w))
    return float(tied[0])


def _scenario_eol(
    record: BatteryRecord,
    L: int,
    pred_relative: np.ndarray,
    model: str,
    config: Q3Config,
    direct_fit: dict[str, float] | None = None,
) -> tuple[float, str]:
    if L != 150:
        return np.nan, "not_evaluated_for_L"
    if model == "P0_persistence":
        return np.nan, "not_applicable_constant"
    if direct_fit is not None:
        return power_law_eol(direct_fit, record.baseline, config)
    stitched = np.concatenate([record.relative_soh[:150], np.asarray(pred_relative, dtype=float)])
    fit = fit_power_law(np.arange(1, 201, dtype=float), stitched, config)
    return power_law_eol(fit, record.baseline, config)


def _summary_tables(
    predictions: pd.DataFrame,
    config: Q3Config,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    battery_rows: list[dict[str, object]] = []
    for (model, L, battery_id, policy), group in predictions.groupby(
        ["model", "L", "battery_id", "policy"], sort=True
    ):
        truth = group["y_true"].to_numpy(float)
        raw = group["y_pred_raw"].to_numpy(float)
        projected = group["y_pred_projected"].to_numpy(float)
        projection_change = float(np.sqrt(np.mean((raw - projected) ** 2)))
        for variant, pred in (("raw", raw), ("projected", projected)):
            metrics = prediction_metrics(truth, pred)
            battery_rows.append(
                {
                    "version": config.version,
                    "model": model,
                    "L": int(L),
                    "prediction_variant": variant,
                    "battery_id": int(battery_id),
                    "policy": policy,
                    **metrics,
                    "projection_change": projection_change,
                    "t80": group[f"t80_{variant}"].iloc[0],
                    "eol_status": group[f"eol_status_{variant}"].iloc[0],
                }
            )
    battery = pd.DataFrame(battery_rows)

    summary_rows: list[dict[str, object]] = []
    for (model, L, variant), group in battery.groupby(
        ["model", "L", "prediction_variant"], sort=True
    ):
        pred_column = "y_pred_raw" if variant == "raw" else "y_pred_projected"
        subset = predictions.loc[predictions["model"].eq(model) & predictions["L"].eq(L)]
        residual = subset[pred_column].to_numpy(float) - subset["y_true"].to_numpy(float)
        policy_rmse = []
        for _, policy_group in subset.groupby("policy"):
            r = policy_group[pred_column].to_numpy(float) - policy_group["y_true"].to_numpy(float)
            policy_rmse.append(float(np.sqrt(np.mean(r**2))))
        summary_rows.append(
            {
                "version": config.version,
                "model": model,
                "L": int(L),
                "prediction_variant": variant,
                "n_battery": int(group["battery_id"].nunique()),
                "strategy_equal_rmse": float(np.mean(policy_rmse)),
                "pooled_rmse": float(np.sqrt(np.mean(residual**2))),
                "mae": float(np.mean(np.abs(residual))),
                "worst_battery_rmse": float(group["rmse"].max()),
            }
        )
    return battery, pd.DataFrame(summary_rows)


def run_smoke_test(project_root: Path, config: Q3Config = CONFIG) -> dict[str, pd.DataFrame | str]:
    overall_start = time.perf_counter()
    load_start = time.perf_counter()
    records, meta, _ = load_records(project_root)
    training, validation = _frozen_smoke_split(records, meta, config)
    load_seconds = time.perf_counter() - load_start

    prediction_rows: list[dict[str, object]] = []
    runtime_rows: list[dict[str, object]] = []
    tuning_rows: list[dict[str, object]] = []

    for L in config.early_lengths:
        model_times: dict[str, dict[str, float]] = {
            model: {stage: 0.0 for stage in STAGES} for model in MODELS
        }
        for model in MODELS:
            model_times[model]["load"] = load_seconds / (len(MODELS) * len(config.early_lengths))

        fit_start = time.perf_counter()
        selected_lambda, b_candidates = select_strategy_lambda(training, L, config)
        model_times["B_strategy"]["fit"] = time.perf_counter() - fit_start

        fit_start = time.perf_counter()
        selected_c, c_candidates = select_trajectory_hyperparameters(training, L, config)
        model_times["C_ridge"]["fit"] = time.perf_counter() - fit_start

        b_oof = b_candidates[selected_lambda]
        c_oof = c_candidates[selected_c]
        fit_start = time.perf_counter()
        selected_weight = _choose_ensemble_weight(training, b_oof, c_oof, config)
        model_times["D_ensemble"]["fit"] = time.perf_counter() - fit_start

        tuning_rows.extend(
            [
                {"L": L, "model": "B_strategy", "hyperparameters": f"lambda_gamma={selected_lambda}"},
                {"L": L, "model": "C_ridge", "hyperparameters": f"K={selected_c[0]};alpha={selected_c[1]}"},
                {"L": L, "model": "D_ensemble", "hyperparameters": f"w_strategy={selected_weight}"},
            ]
        )

        for target in validation:
            truth = target.absolute_future(config.future_start, config.future_end)
            relative_predictions: dict[str, np.ndarray] = {}
            direct_fits: dict[str, dict[str, float] | None] = defaultdict(lambda: None)

            start = time.perf_counter()
            relative_predictions["P0_persistence"] = predict_persistence(target, L, config)
            model_times["P0_persistence"]["predict"] += time.perf_counter() - start

            start = time.perf_counter()
            relative_predictions["P1_linear"] = predict_linear_trend(target, L, config)
            model_times["P1_linear"]["predict"] += time.perf_counter() - start

            start = time.perf_counter()
            power_prediction, power_fit = predict_individual_power(target, L, config)
            relative_predictions["A_power"] = power_prediction
            direct_fits["A_power"] = power_fit
            model_times["A_power"]["fit"] += time.perf_counter() - start

            start = time.perf_counter()
            b_prediction, _ = predict_strategy_transfer(training, target, L, selected_lambda, config)
            relative_predictions["B_strategy"] = b_prediction
            model_times["B_strategy"]["predict"] += time.perf_counter() - start

            start = time.perf_counter()
            c_prediction = predict_trajectory_ridge(training, target, L, selected_c, config)
            relative_predictions["C_ridge"] = c_prediction
            model_times["C_ridge"]["predict"] += time.perf_counter() - start
            relative_predictions["D_ensemble"] = (
                selected_weight * b_prediction + (1.0 - selected_weight) * c_prediction
            )

            for model, pred_relative in relative_predictions.items():
                raw_absolute = target.baseline * pred_relative
                projected_absolute = project_absolute_prediction(
                    raw_absolute, target.baseline * target.relative_at(L), config
                )
                eol_start = time.perf_counter()
                raw_t80, raw_status = _scenario_eol(
                    target, L, pred_relative, model, config, direct_fits[model]
                )
                projected_relative = projected_absolute / target.baseline
                projected_t80, projected_status = _scenario_eol(
                    target, L, projected_relative, model, config, None
                )
                model_times[model]["eol"] += time.perf_counter() - eol_start
                for offset, cycle in enumerate(range(config.future_start, config.future_end + 1)):
                    prediction_rows.append(
                        {
                            "version": config.version,
                            "model": model,
                            "L": L,
                            "battery_id": target.battery_id,
                            "policy": target.policy,
                            "cycle": cycle,
                            "y_true": truth[offset],
                            "y_pred_raw": raw_absolute[offset],
                            "y_pred_projected": projected_absolute[offset],
                            "t80_raw": raw_t80,
                            "eol_status_raw": raw_status,
                            "t80_projected": projected_t80,
                            "eol_status_projected": projected_status,
                        }
                    )

        for model in MODELS:
            model_times[model]["total"] = sum(
                model_times[model][stage] for stage in STAGES if stage != "total"
            )
            for stage in STAGES:
                runtime_rows.append(
                    {
                        "version": config.version,
                        "model": model,
                        "L": L,
                        "stage": stage,
                        "seconds": model_times[model][stage],
                    }
                )

    predictions = pd.DataFrame(prediction_rows)
    battery_metrics, model_summary = _summary_tables(predictions, config)

    raw_summary = model_summary.loc[model_summary["prediction_variant"].eq("raw")]
    score_weights = {50: 0.15, 100: 0.25, 150: 0.60}
    decision_rows = []
    model_scores: dict[str, float] = {}
    worst_scores: dict[str, float] = {}
    for model in MODELS:
        rows = raw_summary.loc[raw_summary["model"].eq(model)].set_index("L")
        score = sum(score_weights[L] * float(rows.loc[L, "strategy_equal_rmse"]) for L in config.early_lengths)
        model_scores[model] = score
        worst_scores[model] = sum(score_weights[L] * float(rows.loc[L, "worst_battery_rmse"]) for L in config.early_lengths)
    ordered_by_score = sorted(model_scores, key=model_scores.get)
    final_order: list[str] = []
    while ordered_by_score:
        group_best = model_scores[ordered_by_score[0]]
        tied = [
            model
            for model in ordered_by_score
            if (model_scores[model] - group_best) / max(group_best, 1e-15)
            <= config.tie_relative_tolerance
        ]
        tied.sort(key=lambda model: (worst_scores[model], MODELS.index(model)))
        final_order.extend(tied)
        ordered_by_score = [model for model in ordered_by_score if model not in tied]
    ranking = {model: rank + 1 for rank, model in enumerate(final_order)}
    runtime = pd.DataFrame(runtime_rows)
    for model in MODELS:
        total_seconds = float(runtime.loc[(runtime["model"].eq(model)) & runtime["stage"].eq("total"), "seconds"].sum())
        engineering_pass = total_seconds <= config.runtime_limit_seconds and np.isfinite(model_scores[model])
        decision_rows.append(
            {
                "version": config.version,
                "model": model,
                "selection_variant": "raw",
                "smoke_score": model_scores[model],
                "weighted_worst_battery_rmse": worst_scores[model],
                "provisional_rank": ranking[model],
                "engineering_pass": engineering_pass,
                "failure_reason": "" if engineering_pass else "runtime_or_nonfinite",
                "final_model_selected": False,
                "must_enter_full_validation": engineering_pass,
            }
        )
    selection = pd.DataFrame(decision_rows).merge(pd.DataFrame(tuning_rows), on=["model"], how="left")
    selection["total_wall_seconds"] = time.perf_counter() - overall_start
    return {
        "predictions_long.csv": predictions,
        "battery_metrics.csv": battery_metrics,
        "model_summary.csv": model_summary,
        "runtime.csv": runtime,
        "selection_decision.csv": selection,
    }
