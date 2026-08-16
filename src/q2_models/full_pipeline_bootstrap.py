"""Full-pipeline bootstrap for Q2, including Q1 window and T80 re-estimation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

import numpy as np
import pandas as pd

from q1_models.experiments import load_clean_data as load_q1_clean_data
from q1_models.lifetime import (
    LifetimeSettings,
    estimate_battery_lifetimes,
    lifetime_window_sensitivity,
    validate_lifetime_windows,
)

from .lifetime_validation import (
    LifetimeValidationSettings,
    evaluate_exposure_models,
    prepare_lifetime_design,
)


@dataclass(frozen=True)
class FullPipelineBootstrapSettings:
    repetitions: int = 2000
    seed: int = 20260816


def make_sample_plan(
    battery: pd.DataFrame,
    settings: FullPipelineBootstrapSettings,
) -> pd.DataFrame:
    rng = np.random.default_rng(settings.seed)
    policies = sorted(battery["policy"].unique())
    rows = []
    for replicate in range(settings.repetitions):
        clone_id = 1
        for policy in policies:
            ids = battery.loc[battery["policy"].eq(policy), "BatteryId"].to_numpy(dtype=int)
            selected = rng.choice(ids, size=len(ids), replace=True)
            for source_id in selected:
                rows.append(
                    {
                        "replicate": replicate,
                        "clone_id": clone_id,
                        "source_battery_id": int(source_id),
                        "policy": policy,
                    }
                )
                clone_id += 1
    return pd.DataFrame(rows)


def _strategy_with_sampled_t80(
    strategy_template: pd.DataFrame,
    sampled_lifetimes: pd.DataFrame,
) -> pd.DataFrame:
    means = (
        sampled_lifetimes.assign(log_t80=np.log(sampled_lifetimes["EstimatedT80"]))
        .groupby("policy", as_index=False)["log_t80"]
        .mean()
        .rename(columns={"log_t80": "sampled_mean_log_t80"})
    )
    sampled = strategy_template.merge(means, on="policy", how="left", validate="one_to_one")
    if sampled["sampled_mean_log_t80"].isna().any():
        raise ValueError("bootstrap sample lost a parameterized strategy")
    sampled["mean_log_t80"] = sampled["sampled_mean_log_t80"]
    return sampled.drop(columns="sampled_mean_log_t80")


def _metric_rows(replicate: int, window: int, metrics: pd.DataFrame) -> list[dict[str, object]]:
    selected = metrics.loc[metrics["selected_primary_explanatory"].astype(bool), "model"]
    winner = str(selected.iloc[0]) if len(selected) else "constant_mean"
    return [
        {
            "replicate": replicate,
            "selected_tail_window": window,
            "model": row.model,
            "selected_model": winner,
            "selected_this_replicate": row.model == winner,
            "relative_rmse_improvement_vs_constant": row.relative_rmse_improvement_vs_constant,
            "full_slope_original_scale": row.full_slope_original_scale,
            "loco_rmse_log_t80": row.loco_rmse_log_t80,
        }
        for row in metrics.itertuples(index=False)
    ]


def run_naive_full_pipeline_bootstrap(
    project_root: Path,
    settings: FullPipelineBootstrapSettings,
    sample_plan: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Trusted DataFrame implementation used for row-equivalence checks."""
    cycles, _ = load_q1_clean_data(project_root)
    battery, strategy, _ = prepare_lifetime_design(project_root)
    plan = make_sample_plan(battery, settings) if sample_plan is None else sample_plan
    frames = {int(battery_id): frame.copy() for battery_id, frame in cycles.groupby("battery_id")}
    rows = []
    for replicate, current_plan in plan.groupby("replicate", sort=True):
        parts = []
        for item in current_plan.itertuples(index=False):
            clone = frames[int(item.source_battery_id)].copy()
            clone["battery_id"] = int(item.clone_id)
            parts.append(clone)
        sampled_cycles = pd.concat(parts, ignore_index=True)
        _, _, selected_window = validate_lifetime_windows(sampled_cycles, LifetimeSettings())
        sampled_t80 = estimate_battery_lifetimes(
            sampled_cycles, selected_window, LifetimeSettings()
        ).rename(columns={"Policy": "policy"})
        sampled_strategy = _strategy_with_sampled_t80(strategy, sampled_t80)
        _, metrics = evaluate_exposure_models(sampled_strategy)
        rows.extend(_metric_rows(int(replicate), selected_window, metrics))
    return pd.DataFrame(rows)


def precompute_lifetime_kernel(
    project_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cycles, _ = load_q1_clean_data(project_root)
    battery, strategy, _ = prepare_lifetime_design(project_root)
    validation, _, _ = validate_lifetime_windows(cycles, LifetimeSettings())
    sensitivity = lifetime_window_sensitivity(cycles, LifetimeSettings()).rename(
        columns={"BatteryId": "source_battery_id", "Policy": "policy"}
    )
    validation = validation.rename(columns={"BatteryId": "source_battery_id"})
    return battery, strategy, validation, sensitivity


def run_cached_full_pipeline_bootstrap(
    project_root: Path,
    settings: FullPipelineBootstrapSettings,
    sample_plan: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Equivalent cached implementation avoiding repeated curve fits."""
    started = time.perf_counter()
    battery, strategy, validation, sensitivity = precompute_lifetime_kernel(project_root)
    plan = make_sample_plan(battery, settings) if sample_plan is None else sample_plan
    complete_ids = set(validation["source_battery_id"].astype(int))
    t80_lookup = (
        sensitivity[["source_battery_id", "SensitivityWindow", "EstimatedT80"]]
        .drop_duplicates()
        .set_index(["source_battery_id", "SensitivityWindow"])["EstimatedT80"]
    )
    rmse_lookup = validation.set_index(["source_battery_id", "Window"])["RMSE"]
    rows = []
    for replicate, current_plan in plan.groupby("replicate", sort=True):
        complete_plan = current_plan.loc[
            current_plan["source_battery_id"].isin(complete_ids)
        ].copy()
        window_scores = []
        for window in LifetimeSettings().candidate_windows:
            current = complete_plan[["source_battery_id", "policy"]].copy()
            current["MSE"] = [
                float(rmse_lookup.loc[(int(source_id), window)]) ** 2
                for source_id in current["source_battery_id"]
            ]
            policy_mse = current.groupby("policy")["MSE"].mean()
            worst = float(np.sqrt(current["MSE"]).max())
            window_scores.append(
                (float(np.sqrt(policy_mse.mean())), worst, window)
            )
        selected_window = min(window_scores)[2]
        sampled_t80 = current_plan[["source_battery_id", "policy"]].copy()
        sampled_t80["EstimatedT80"] = [
            float(t80_lookup.loc[(int(source_id), selected_window)])
            for source_id in sampled_t80["source_battery_id"]
        ]
        sampled_strategy = _strategy_with_sampled_t80(strategy, sampled_t80)
        _, metrics = evaluate_exposure_models(sampled_strategy)
        rows.extend(_metric_rows(int(replicate), selected_window, metrics))
    runtime = pd.DataFrame(
        [
            {
                "backend": "cached_precomputed_battery_window_kernel",
                "repetitions": settings.repetitions,
                "seed": settings.seed,
                "runtime_seconds": time.perf_counter() - started,
                "sample_rows": len(plan),
            }
        ]
    )
    return pd.DataFrame(rows), runtime


def summarize_full_pipeline_bootstrap(replicates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    total = replicates["replicate"].nunique()
    for model, current in replicates.groupby("model", sort=True):
        improvement = current["relative_rmse_improvement_vs_constant"].to_numpy(dtype=float)
        slope = current["full_slope_original_scale"].to_numpy(dtype=float)
        finite_slope = slope[np.isfinite(slope)]
        rows.append(
            {
                "model": model,
                "bootstrap_repetitions": total,
                "selected_frequency": float(current["selected_this_replicate"].mean()),
                "median_improvement_vs_constant": float(np.median(improvement)),
                "improvement_ci95_low": float(np.quantile(improvement, 0.025)),
                "improvement_ci95_high": float(np.quantile(improvement, 0.975)),
                "negative_slope_frequency": (
                    float(np.mean(finite_slope < 0)) if len(finite_slope) else np.nan
                ),
            }
        )
    window = (
        replicates[["replicate", "selected_tail_window"]]
        .drop_duplicates()
        .value_counts("selected_tail_window", sort=False)
        .rename("count")
        .reset_index()
    )
    window["frequency"] = window["count"] / total
    return pd.DataFrame(rows).sort_values("selected_frequency", ascending=False), window


def compare_backends(naive: pd.DataFrame, cached: pd.DataFrame) -> pd.DataFrame:
    keys = ["replicate", "model"]
    merged = naive.merge(cached, on=keys, suffixes=("_naive", "_cached"), validate="one_to_one")
    numeric = [
        "relative_rmse_improvement_vs_constant",
        "full_slope_original_scale",
        "loco_rmse_log_t80",
    ]
    differences = []
    for column in numeric:
        first = merged[f"{column}_naive"].to_numpy(dtype=float)
        second = merged[f"{column}_cached"].to_numpy(dtype=float)
        differences.append(np.nanmax(np.abs(first - second)))
    mismatch = (
        merged["selected_tail_window_naive"].ne(merged["selected_tail_window_cached"])
        | merged["selected_model_naive"].ne(merged["selected_model_cached"])
    )
    return pd.DataFrame(
        [
            {
                "rows_compared": len(merged),
                "decision_mismatch_count": int(mismatch.sum()),
                "maximum_numeric_difference": float(max(differences)),
            }
        ]
    )


def run_full_pipeline_lifetime_validation(
    project_root: Path,
    settings: LifetimeValidationSettings,
) -> dict[str, pd.DataFrame]:
    """Run the existing point analysis and replace its bootstrap with full propagation."""
    from .lifetime_validation import run_lifetime_validation

    tables = run_lifetime_validation(project_root, settings)
    fixed_t80 = tables["lifetime_bootstrap_selection"].copy()
    bootstrap_settings = FullPipelineBootstrapSettings(
        repetitions=settings.bootstrap_repetitions, seed=settings.seed
    )
    replicates, runtime = run_cached_full_pipeline_bootstrap(
        project_root, bootstrap_settings
    )
    summary, window = summarize_full_pipeline_bootstrap(replicates)
    tables["lifetime_fixed_t80_bootstrap_selection"] = fixed_t80
    tables["lifetime_bootstrap_replicates"] = replicates
    tables["lifetime_bootstrap_selection"] = summary
    tables["lifetime_bootstrap_window_frequency"] = window
    tables["lifetime_full_pipeline_runtime"] = runtime
    metadata = tables["lifetime_validation_metadata"]
    extra = pd.DataFrame(
        [
            {
                "parameter": "bootstrap_scope",
                "value": "resample_batteries_reselect_tail_window_reestimate_T80_reselect_exposure_model",
            },
            {"parameter": "bootstrap_backend", "value": "cached_row_equivalent_to_naive_dataframe_path"},
        ]
    )
    tables["lifetime_validation_metadata"] = pd.concat((metadata, extra), ignore_index=True)
    return tables
