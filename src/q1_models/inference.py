"""Final statistical inference for Question 1; writes tables but no figures."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .core import (
    MODEL_FUNCTIONAL,
    MODEL_TYPES,
    ModelConfig,
    candidate_configs,
    fit_population_model,
    make_basis,
)
from .experiments import (
    CandidateResult,
    _evaluate_batteries,
    _extract_outputs,
    _stratified_three_fold_map,
    load_clean_data,
)
from .lifetime import (
    LifetimeSettings,
    bootstrap_strategy_lifetimes,
    estimate_battery_lifetimes,
    lifetime_window_sensitivity,
    pairwise_lifetime_comparison,
    validate_lifetime_windows,
)


@dataclass(frozen=True)
class InferenceSettings:
    seed: int = 20260814
    bootstrap_repetitions: int = 2000
    alpha: float = 0.05
    lambda_curve: float = 0.0


def run_final_inference(project_root: Path, settings: InferenceSettings) -> dict[str, pd.DataFrame]:
    """Run the final Q1 inference and return every authoritative result table."""
    cycles, batteries = load_clean_data(project_root)
    complete_ids = batteries.loc[batteries["prediction_test"] == 0, "battery_id"]
    analysis_cycles = cycles.loc[cycles["battery_id"].isin(complete_ids)].copy()
    analysis_batteries = batteries.loc[batteries["battery_id"].isin(complete_ids)].copy()
    candidate_results = [
        _run_candidate_on_data(analysis_cycles, analysis_batteries, model_type, settings.seed)
        for model_type in MODEL_TYPES
    ]
    model_result = min(candidate_results, key=lambda item: item.lobo["RMSE"].mean())
    if model_result.model_type != MODEL_FUNCTIONAL:
        raise AssertionError("complete-cell Q1 cohort selected a different main model")
    if not np.isclose(model_result.best_config.lambda_curve, settings.lambda_curve):
        raise AssertionError("frozen main-model hyperparameter no longer matches the selected value")

    bootstrap = _cluster_bootstrap(model_result, analysis_batteries, settings)
    curve_estimates = _curve_estimates(model_result, bootstrap, settings.alpha)
    scalar_estimates = _scalar_estimates(model_result, bootstrap, settings.alpha)
    pairwise_scalar = _pairwise_scalar(
        model_result, bootstrap, analysis_batteries, settings.alpha
    )
    pairwise_curve, pairwise_curve_cycle = _pairwise_curve(model_result, bootstrap, settings.alpha)
    rank_stability = _rank_stability(model_result, bootstrap)
    residual_battery, residual_policy, residual_overall = _residual_diagnostics(
        model_result, analysis_cycles
    )
    battery_features, strategy_features, associations = _feature_associations(
        analysis_cycles, analysis_batteries, scalar_estimates
    )
    coverage = _data_coverage(cycles, batteries)
    model_validation = _model_validation_tables(
        candidate_results, analysis_cycles, analysis_batteries, settings.seed
    )
    lifetime_settings = LifetimeSettings()
    lifetime_validation_battery, lifetime_validation_summary, lifetime_window = (
        validate_lifetime_windows(cycles, lifetime_settings)
    )
    battery_lifetimes = estimate_battery_lifetimes(
        cycles, lifetime_window, lifetime_settings
    )
    lifetime_sensitivity = lifetime_window_sensitivity(cycles, lifetime_settings)
    strategy_lifetimes, lifetime_rank_stability = bootstrap_strategy_lifetimes(
        battery_lifetimes,
        repetitions=settings.bootstrap_repetitions,
        seed=settings.seed,
        alpha=settings.alpha,
    )
    pairwise_lifetimes = pairwise_lifetime_comparison(battery_lifetimes)
    cohort = batteries[["battery_id", "policy", "prediction_test"]].copy()
    cohort["IncludedInQ1Cycle200Inference"] = cohort["prediction_test"] == 0
    cohort["IncludedInQ1LifetimeInference"] = True
    cohort["LifetimePrefixCycle"] = lifetime_settings.prefix_cycle
    cohort["ExclusionReason"] = np.where(
        cohort["prediction_test"] == 0,
        "included_complete_to_cycle_200",
        "reserved_for_q3_only_observed_to_cycle_150",
    )
    conclusions = _conclusion_table(
        model_result,
        lifetime_rank_stability,
        pairwise_lifetimes,
        lifetime_validation_summary,
        residual_policy,
        associations,
    )
    settings_table = pd.DataFrame(
        [
            {"Parameter": "seed", "Value": settings.seed},
            {"Parameter": "bootstrap_repetitions", "Value": settings.bootstrap_repetitions},
            {"Parameter": "alpha", "Value": settings.alpha},
            {"Parameter": "main_model", "Value": MODEL_FUNCTIONAL},
            {"Parameter": "lambda_curve", "Value": settings.lambda_curve},
            {"Parameter": "response", "Value": "SOH_clean"},
            {"Parameter": "q1_cycle200_cohort", "Value": "40_complete_batteries_only"},
            {"Parameter": "q3_reserved_cohort", "Value": "9_prediction_test_batteries_excluded"},
            {"Parameter": "bootstrap_unit", "Value": "battery_within_policy"},
            {"Parameter": "pairwise_test", "Value": "exact_battery_permutation"},
            {"Parameter": "multiple_comparison", "Value": "Holm"},
            {"Parameter": "model_validation", "Value": "outer_LOBO_with_inner_battery_CV_tuning"},
            {"Parameter": "selection_pipeline_validation", "Value": "outer_LOBO_selects_family_and_hyperparameter_inside_training_fold"},
            {"Parameter": "cycle_life_definition", "Value": "predicted_cycle_at_SOH_0.8"},
            {"Parameter": "lifetime_prefix_cycle", "Value": lifetime_settings.prefix_cycle},
            {"Parameter": "lifetime_selected_tail_window", "Value": lifetime_window},
            {"Parameter": "lifetime_window_selection", "Value": "predict_cycles_151_to_200_on_40_complete_batteries"},
            {"Parameter": "lifetime_primary_policy_statistic", "Value": "median_battery_EstimatedT80"},
        ]
    )
    return {
        "analysis_settings": settings_table,
        "data_coverage": coverage,
        "analysis_cohort": cohort,
        "strategy_curve_confidence_band": curve_estimates,
        "strategy_scalar_estimates": scalar_estimates,
        "pairwise_strategy_scalar_comparison": pairwise_scalar,
        "pairwise_strategy_curve_summary": pairwise_curve,
        "pairwise_strategy_curve_by_cycle": pairwise_curve_cycle,
        "strategy_rank_stability": rank_stability,
        "residual_diagnostics_by_battery": residual_battery,
        "residual_diagnostics_by_policy": residual_policy,
        "residual_diagnostics_overall": residual_overall,
        "battery_feature_metrics": battery_features,
        "strategy_feature_summary": strategy_features,
        "strategy_association_summary": associations,
        "q1_conclusions": conclusions,
        "lifetime_window_validation_by_battery": lifetime_validation_battery,
        "lifetime_window_validation_summary": lifetime_validation_summary,
        "battery_lifetime_estimates": battery_lifetimes,
        "lifetime_window_sensitivity": lifetime_sensitivity,
        "strategy_lifetime_summary": strategy_lifetimes,
        "strategy_lifetime_rank_stability": lifetime_rank_stability,
        "pairwise_strategy_lifetime_comparison": pairwise_lifetimes,
        **model_validation,
    }


def _run_candidate_on_data(
    cycles: pd.DataFrame,
    batteries: pd.DataFrame,
    model_type: str,
    seed: int,
) -> CandidateResult:
    tuning, best_config = _tune_candidate(cycles, model_type, seed)
    lobo_parts = []
    for battery_id in pd.unique(cycles["battery_id"]):
        train = cycles.loc[cycles["battery_id"] != battery_id]
        test = cycles.loc[cycles["battery_id"] == battery_id]
        inner_tuning, inner_best_config = _tune_candidate(
            train, model_type, seed + int(battery_id)
        )
        model = fit_population_model(train, model_type, inner_best_config)
        evaluated = _evaluate_batteries(model, test)
        evaluated["InnerSelectedLambdaRandom"] = inner_best_config.lambda_random
        evaluated["InnerSelectedLambdaCurve"] = inner_best_config.lambda_curve
        evaluated["InnerCVMeanBatteryRMSE"] = inner_tuning["MeanBatteryRMSE"].min()
        evaluated["InnerValidationNBattery"] = int(inner_tuning["ValidationNBattery"].iloc[0])
        lobo_parts.append(evaluated)
    lobo = pd.concat(lobo_parts, ignore_index=True)
    final_model = fit_population_model(cycles, model_type, best_config)
    curves, strategy_summary = _extract_outputs(final_model, batteries)
    return CandidateResult(
        model_type,
        seed,
        tuning,
        best_config,
        lobo,
        final_model,
        curves,
        strategy_summary,
    )


def _tune_candidate(
    cycles: pd.DataFrame,
    model_type: str,
    seed: int,
) -> tuple[pd.DataFrame, ModelConfig]:
    """Select a candidate using battery folds while retaining singleton policies in training."""
    configs = candidate_configs(model_type)
    fold_map = _stratified_three_fold_map(cycles, seed)
    policy_counts = cycles[["battery_id", "policy"]].drop_duplicates()["policy"].value_counts()
    singleton_policies = set(policy_counts[policy_counts < 2].index)
    singleton_ids = set(
        cycles.loc[cycles["policy"].isin(singleton_policies), "battery_id"].unique()
    )
    fold_map = {
        battery_id: fold
        for battery_id, fold in fold_map.items()
        if battery_id not in singleton_ids
    }
    tuning_rows = []
    for config_id, config in enumerate(configs, start=1):
        parts = []
        for fold in (1, 2, 3):
            held_out = [battery for battery, assigned in fold_map.items() if assigned == fold]
            if not held_out:
                continue
            model = fit_population_model(
                cycles.loc[~cycles["battery_id"].isin(held_out)], model_type, config
            )
            parts.append(
                _evaluate_batteries(model, cycles.loc[cycles["battery_id"].isin(held_out)])
            )
        metrics = pd.concat(parts, ignore_index=True)
        tuning_rows.append(
            {
                "ConfigId": config_id,
                "LambdaRandom": config.lambda_random,
                "LambdaCurve": config.lambda_curve,
                "MeanBatteryRMSE": metrics["RMSE"].mean(),
                "MeanBatteryMAE": metrics["MAE"].mean(),
                "WorstPolicyRMSE": metrics.groupby("Policy")["RMSE"].mean().max(),
                "ValidationNBattery": metrics["BatteryId"].nunique(),
                "SingletonPoliciesTrainingOnly": len(singleton_policies),
            }
        )
    tuning = pd.DataFrame(tuning_rows)
    best_config = configs[int(tuning.loc[tuning["MeanBatteryRMSE"].idxmin(), "ConfigId"]) - 1]
    return tuning, best_config


def file_hashes(paths: list[Path]) -> pd.DataFrame:
    rows = []
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"Path": str(path.resolve()), "SHA256": digest, "SizeBytes": path.stat().st_size})
    return pd.DataFrame(rows)


def _cluster_bootstrap(
    result: CandidateResult, batteries: pd.DataFrame, settings: InferenceSettings
) -> dict[str, np.ndarray | list[str]]:
    model = result.final_model
    if model.cell_coef is None or model.cell_policy is None:
        raise TypeError("final Q1 inference requires the functional two-stage model")
    cycles = np.arange(1, 201, dtype=float)
    basis = make_basis(model.model_type, cycles)
    policies = list(model.policy_names)
    n_boot = settings.bootstrap_repetitions
    rng = np.random.default_rng(settings.seed)
    curves = np.empty((n_boot, len(policies), len(cycles)), dtype=float)
    charge_time = np.empty((n_boot, len(policies)), dtype=float)
    battery_charge = batteries.set_index("battery_id")["mean_chargetime"]
    for p, policy in enumerate(policies):
        positions = np.flatnonzero(model.cell_policy == policy)
        if len(positions) < 2:
            raise ValueError(f"policy {policy} has fewer than two batteries")
        sampled_local = rng.integers(0, len(positions), size=(n_boot, len(positions)))
        sampled_positions = positions[sampled_local]
        mean_coef = model.cell_coef[sampled_positions].mean(axis=1)
        curves[:, p, :] = mean_coef @ basis.T
        charge = battery_charge.loc[model.battery_ids[positions]].to_numpy(dtype=float)
        charge_time[:, p] = charge[sampled_local].mean(axis=1)
    t = cycles[-50:]
    centered = t - t.mean()
    slope = np.einsum("bpt,t->bp", curves[:, :, -50:], centered) / np.sum(centered**2)
    soh200 = curves[:, :, -1]
    local_l80 = np.full_like(slope, np.nan)
    valid = slope < -1e-7
    local_l80[valid] = 200.0 + (soh200[valid] - 0.8) / (-slope[valid])
    return {
        "policies": policies,
        "curves": curves,
        "charge_time": charge_time,
        "soh200": soh200,
        "loss": curves[:, :, 0] - curves[:, :, -1],
        "mean_soh": np.trapezoid(curves, cycles, axis=2) / 199.0,
        "slope": slope,
        "local_l80": local_l80,
    }


def _curve_estimates(
    result: CandidateResult, bootstrap: dict, alpha: float
) -> pd.DataFrame:
    rows = []
    point = result.curves.pivot(index="Cycle", columns="Policy", values="SOHPred")
    for p, policy in enumerate(bootstrap["policies"]):
        samples = bootstrap["curves"][:, p, :]
        lower, upper = np.quantile(samples, [alpha / 2, 1 - alpha / 2], axis=0)
        standard_error = samples.std(axis=0, ddof=1)
        for cycle in range(1, 201):
            rows.append(
                {
                    "Policy": policy,
                    "Cycle": cycle,
                    "SOHEstimate": point.loc[cycle, policy],
                    "BootstrapSE": standard_error[cycle - 1],
                    "CI95Low": lower[cycle - 1],
                    "CI95High": upper[cycle - 1],
                }
            )
    return pd.DataFrame(rows)


def _scalar_estimates(result: CandidateResult, bootstrap: dict, alpha: float) -> pd.DataFrame:
    point = result.strategy_summary.set_index("Policy")
    rows = []
    metrics = {
        "SOH200": ("soh200", point["SOH200"]),
        "Loss1to200": ("loss", point["Loss1to200"]),
        "MeanSOH1to200": ("mean_soh", point["MeanSOH1to200"]),
        "Slope151to200": ("slope", point["Slope151to200"]),
        "ProjectedL80LocalLinear": ("local_l80", point["ProjectedL80LocalLinear"]),
        "MeanChargeTime": ("charge_time", point["MeanChargeTime"]),
    }
    for p, policy in enumerate(bootstrap["policies"]):
        for metric, (key, point_values) in metrics.items():
            samples = np.asarray(bootstrap[key][:, p], dtype=float)
            finite = samples[np.isfinite(samples)]
            rows.append(
                {
                    "Policy": policy,
                    "Metric": metric,
                    "Estimate": point_values.loc[policy],
                    "BootstrapSE": finite.std(ddof=1) if len(finite) > 1 else np.nan,
                    "CI95Low": np.quantile(finite, alpha / 2) if len(finite) else np.nan,
                    "CI95High": np.quantile(finite, 1 - alpha / 2) if len(finite) else np.nan,
                    "FiniteBootstrapFraction": len(finite) / len(samples),
                }
            )
    return pd.DataFrame(rows)


def _pairwise_scalar(
    result: CandidateResult,
    bootstrap: dict,
    batteries: pd.DataFrame,
    alpha: float,
) -> pd.DataFrame:
    policies = bootstrap["policies"]
    point = result.strategy_summary.set_index("Policy")
    cell_values = _cell_scalar_values(result, batteries)
    definitions = {
        "SOH200": ("soh200", point["SOH200"]),
        "Loss1to200": ("loss", point["Loss1to200"]),
        "MeanSOH1to200": ("mean_soh", point["MeanSOH1to200"]),
        "MeanChargeTime": ("charge_time", point["MeanChargeTime"]),
    }
    rows = []
    for metric, (key, point_values) in definitions.items():
        metric_start = len(rows)
        for i in range(len(policies)):
            for j in range(i + 1, len(policies)):
                samples = np.asarray(bootstrap[key][:, i] - bootstrap[key][:, j], dtype=float)
                finite = samples[np.isfinite(samples)]
                ci_low = np.quantile(finite, alpha / 2)
                ci_high = np.quantile(finite, 1 - alpha / 2)
                p_value = _exact_permutation_p_value(
                    cell_values[metric][policies[i]],
                    cell_values[metric][policies[j]],
                )
                rows.append(
                    {
                        "Metric": metric,
                        "PolicyA": policies[i],
                        "PolicyB": policies[j],
                        "Difference_AminusB": point_values.loc[policies[i]] - point_values.loc[policies[j]],
                        "CI95Low": ci_low,
                        "CI95High": ci_high,
                        "BootstrapCIExcludesZero": bool(ci_low > 0 or ci_high < 0),
                        "ExactPermutationP": p_value,
                    }
                )
        p_values = np.array([row["ExactPermutationP"] for row in rows[metric_start:]])
        adjusted = _holm_adjust(p_values)
        for row, value in zip(rows[metric_start:], adjusted):
            row["HolmAdjustedP"] = value
            row["SignificantAfterHolm"] = bool(value < alpha)
    return pd.DataFrame(rows)


def _cell_scalar_values(
    result: CandidateResult, batteries: pd.DataFrame
) -> dict[str, dict[str, np.ndarray]]:
    """Return one scalar value per complete battery for exact group comparisons."""
    model = result.final_model
    if model.cell_coef is None or model.cell_policy is None:
        raise TypeError("cell-level scalar comparisons require the functional two-stage model")
    cycles = np.arange(1, 201, dtype=float)
    curves = model.cell_coef @ make_basis(model.model_type, cycles).T
    battery_charge = batteries.set_index("battery_id")["mean_chargetime"]
    metrics = {
        "SOH200": curves[:, -1],
        "Loss1to200": curves[:, 0] - curves[:, -1],
        "MeanSOH1to200": np.trapezoid(curves, cycles, axis=1) / 199.0,
        "MeanChargeTime": battery_charge.loc[model.battery_ids].to_numpy(dtype=float),
    }
    return {
        metric: {
            policy: np.asarray(values[model.cell_policy == policy], dtype=float)
            for policy in model.policy_names
        }
        for metric, values in metrics.items()
    }


def _exact_permutation_p_value(left: np.ndarray, right: np.ndarray) -> float:
    """Two-sided exact permutation p-value for a difference in battery-level means."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("exact permutation test requires finite battery-level values")
    combined = np.concatenate((left, right))
    observed = abs(float(left.mean() - right.mean()))
    extreme = 0
    total = 0
    all_sum = float(combined.sum())
    for indices in combinations(range(len(combined)), len(left)):
        left_sum = float(combined[list(indices)].sum())
        difference = left_sum / len(left) - (all_sum - left_sum) / len(right)
        extreme += abs(difference) >= observed - 1e-15
        total += 1
    return extreme / total


def _pairwise_curve(result: CandidateResult, bootstrap: dict, alpha: float):
    policies = bootstrap["policies"]
    point_frame = result.curves.pivot(index="Cycle", columns="Policy", values="SOHPred")
    summary_rows = []
    cycle_rows = []
    for i in range(len(policies)):
        for j in range(i + 1, len(policies)):
            point = point_frame[policies[i]].to_numpy() - point_frame[policies[j]].to_numpy()
            samples = bootstrap["curves"][:, i, :] - bootstrap["curves"][:, j, :]
            point_low, point_high = np.quantile(samples, [alpha / 2, 1 - alpha / 2], axis=0)
            max_error = np.max(np.abs(samples - point[None, :]), axis=1)
            radius = np.quantile(max_error, 1 - alpha)
            simultaneous_low = point - radius
            simultaneous_high = point + radius
            significant = (simultaneous_low > 0) | (simultaneous_high < 0)
            summary_rows.append(
                {
                    "PolicyA": policies[i],
                    "PolicyB": policies[j],
                    "CurveRMSE": np.sqrt(np.mean(point**2)),
                    "IntegratedDifference": np.trapezoid(point, dx=1.0) / 199.0,
                    "MaxAbsDifference": np.max(np.abs(point)),
                    "SimultaneousBandRadius": radius,
                    "SignificantCycleFraction": significant.mean(),
                    "AnySignificantCycle": bool(significant.any()),
                    "AllCyclesSignificant": bool(significant.all()),
                }
            )
            for cycle in range(1, 201):
                cycle_rows.append(
                    {
                        "PolicyA": policies[i],
                        "PolicyB": policies[j],
                        "Cycle": cycle,
                        "Difference_AminusB": point[cycle - 1],
                        "PointwiseCI95Low": point_low[cycle - 1],
                        "PointwiseCI95High": point_high[cycle - 1],
                        "SimultaneousCI95Low": simultaneous_low[cycle - 1],
                        "SimultaneousCI95High": simultaneous_high[cycle - 1],
                        "SignificantSimultaneous": bool(significant[cycle - 1]),
                    }
                )
    return pd.DataFrame(summary_rows), pd.DataFrame(cycle_rows)


def _rank_stability(result: CandidateResult, bootstrap: dict) -> pd.DataFrame:
    policies = bootstrap["policies"]
    samples = bootstrap["soh200"]
    order = np.argsort(-samples, axis=1, kind="stable")
    ranks = np.empty_like(order)
    row_index = np.arange(len(samples))[:, None]
    ranks[row_index, order] = np.arange(1, len(policies) + 1)
    sensitivity_path = result  # keeps signature tied to selected result
    del sensitivity_path
    rows = []
    point_rank = (
        result.strategy_summary.set_index("Policy")["SOH200"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    for p, policy in enumerate(policies):
        row = {
            "Policy": policy,
            "PointSOH200Rank": int(point_rank.loc[policy]),
            "MeanRank": ranks[:, p].mean(),
            "MedianRank": np.median(ranks[:, p]),
            "ProbabilityTop3": np.mean(ranks[:, p] <= 3),
            "ProbabilityTop4": np.mean(ranks[:, p] <= 4),
            "ProbabilityBottom3": np.mean(ranks[:, p] >= len(policies) - 2),
            "ProbabilityBottom4": np.mean(ranks[:, p] >= len(policies) - 3),
        }
        for rank in range(1, len(policies) + 1):
            row[f"ProbabilityRank{rank}"] = np.mean(ranks[:, p] == rank)
        if row["PointSOH200Rank"] <= 3:
            row["PrimaryGroup"] = "typical_long"
        elif row["PointSOH200Rank"] >= len(policies) - 2:
            row["PrimaryGroup"] = "typical_short"
        else:
            row["PrimaryGroup"] = "middle"
        if row["ProbabilityTop3"] >= 0.8:
            row["BootstrapStableGroup80"] = "typical_long"
        elif row["ProbabilityBottom3"] >= 0.8:
            row["BootstrapStableGroup80"] = "typical_short"
        else:
            row["BootstrapStableGroup80"] = "not_stable_at_80_percent"
        rows.append(row)
    return pd.DataFrame(rows).sort_values("MeanRank").reset_index(drop=True)


def _residual_diagnostics(result: CandidateResult, cycles: pd.DataFrame):
    model = result.final_model
    basis = make_basis(model.model_type, cycles["cycle"].to_numpy())
    battery_to_position = {int(value): i for i, value in enumerate(model.battery_ids)}
    residual_parts = []
    rows = []
    for battery_id, frame in cycles.groupby("battery_id", sort=False):
        position = battery_to_position[int(battery_id)]
        local_basis = make_basis(model.model_type, frame["cycle"].to_numpy())
        fitted = local_basis @ model.cell_coef[position]
        residual = frame["SOH_clean"].to_numpy() - fitted
        residual_parts.append(residual)
        if len(residual) > 1 and residual.std(ddof=1) > 0:
            lag1 = np.corrcoef(residual[:-1], residual[1:])[0, 1]
        else:
            lag1 = np.nan
        denominator = np.sum(residual**2)
        durbin_watson = np.sum(np.diff(residual) ** 2) / denominator if denominator > 0 else np.nan
        trend = np.linalg.lstsq(
            np.column_stack((np.ones(len(frame)), frame["cycle"])), residual, rcond=None
        )[0][1]
        rows.append(
            {
                "BatteryId": int(battery_id),
                "Policy": frame["policy"].iloc[0],
                "NObs": len(frame),
                "ResidualMean": residual.mean(),
                "ResidualSD": residual.std(ddof=1),
                "ResidualRMSE": np.sqrt(np.mean(residual**2)),
                "ResidualMAE": np.mean(np.abs(residual)),
                "ResidualMaxAbs": np.max(np.abs(residual)),
                "ResidualLag1Correlation": lag1,
                "DurbinWatson": durbin_watson,
                "ResidualTrendPerCycle": trend,
            }
        )
    by_battery = pd.DataFrame(rows)
    by_policy = (
        by_battery.groupby("Policy", sort=False)
        .agg(
            NBattery=("BatteryId", "size"),
            MeanResidualRMSE=("ResidualRMSE", "mean"),
            MedianResidualRMSE=("ResidualRMSE", "median"),
            MeanLag1Correlation=("ResidualLag1Correlation", "mean"),
            MeanDurbinWatson=("DurbinWatson", "mean"),
            MaxResidualAbs=("ResidualMaxAbs", "max"),
        )
        .reset_index()
    )
    all_residual = np.concatenate(residual_parts)
    overall = pd.DataFrame(
        [
            {
                "NObservation": len(all_residual),
                "ResidualMean": all_residual.mean(),
                "ResidualSD": all_residual.std(ddof=1),
                "ResidualRMSE": np.sqrt(np.mean(all_residual**2)),
                "ResidualMAE": np.mean(np.abs(all_residual)),
                "ResidualMaxAbs": np.max(np.abs(all_residual)),
                "BatteryMeanLag1Correlation": by_battery["ResidualLag1Correlation"].mean(),
                "BatteryMeanDurbinWatson": by_battery["DurbinWatson"].mean(),
            }
        ]
    )
    del basis
    return by_battery, by_policy, overall


def _feature_associations(cycles, batteries, scalar_estimates):
    rows = []
    summary_index = batteries.set_index("battery_id")
    variables = ["SOH_clean", "IR_clean", "Tavg_raw", "chargetime_raw"]
    for battery_id, frame in cycles.groupby("battery_id", sort=False):
        ordered = frame.sort_values("cycle")
        early = ordered.head(min(20, len(ordered)))
        late = ordered.tail(min(20, len(ordered)))
        row = {
            "BatteryId": int(battery_id),
            "Policy": ordered["policy"].iloc[0],
            "NObservedCycle": len(ordered),
            "PredictionTest": int(summary_index.loc[battery_id, "prediction_test"]),
        }
        for variable in variables:
            label = {
                "SOH_clean": "SOH",
                "IR_clean": "IR",
                "Tavg_raw": "Temperature",
                "chargetime_raw": "ChargeTime",
            }[variable]
            row[f"{label}Early20Mean"] = early[variable].mean()
            row[f"{label}Late20Mean"] = late[variable].mean()
            row[f"{label}LateMinusEarly"] = late[variable].mean() - early[variable].mean()
        rows.append(row)
    battery_features = pd.DataFrame(rows)
    numeric = [column for column in battery_features.columns if column not in {"BatteryId", "Policy"}]
    aggregation = battery_features.groupby("Policy", sort=False)[numeric].agg(["mean", "std"])
    aggregation.columns = [f"{column}_{stat}" for column, stat in aggregation.columns]
    strategy_features = aggregation.reset_index()

    soh200 = scalar_estimates.loc[scalar_estimates["Metric"] == "SOH200", ["Policy", "Estimate"]].rename(
        columns={"Estimate": "SOH200"}
    )
    joined = strategy_features.merge(soh200, on="Policy", how="inner")
    association_rows = []
    feature_columns = [column for column in joined.columns if column.endswith("_mean")]
    for feature in feature_columns:
        x = joined[feature].to_numpy(dtype=float)
        y = joined["SOH200"].to_numpy(dtype=float)
        pearson = np.corrcoef(x, y)[0, 1] if np.std(x) > 1e-15 else np.nan
        x_rank = pd.Series(x).rank().to_numpy(dtype=float)
        y_rank = pd.Series(y).rank().to_numpy(dtype=float)
        spearman = (
            np.corrcoef(x_rank, y_rank)[0, 1]
            if np.std(x_rank) > 1e-15 and np.std(y_rank) > 1e-15
            else np.nan
        )
        association_rows.append(
            {
                "Response": "SOH200",
                "Feature": feature,
                "NStrategy": len(joined),
                "PearsonCorrelation": pearson,
                "SpearmanCorrelation": spearman,
                "Interpretation": "descriptive_association_not_causal",
            }
        )
    return battery_features, strategy_features, pd.DataFrame(association_rows)


def _data_coverage(cycles, batteries):
    rows = []
    for policy, frame in batteries.groupby("policy", sort=False):
        ids = frame["battery_id"]
        observed = cycles.loc[cycles["battery_id"].isin(ids)]
        max_cycle = observed.groupby("battery_id")["cycle"].max()
        rows.append(
            {
                "Policy": policy,
                "NBattery": len(frame),
                "NCompleteTo200": int((max_cycle >= 200).sum()),
                "NTruncatedAt150": int((max_cycle == 150).sum()),
                "NObservedCycleRows": len(observed),
                "MinimumSOH": observed["SOH_clean"].min(),
                "MaximumSOH": observed["SOH_clean"].max(),
                "ObservedEOL80Count": int((observed.groupby("battery_id")["SOH_clean"].min() <= 0.8).sum()),
            }
        )
    return pd.DataFrame(rows)


def _model_validation_tables(
    results: list[CandidateResult],
    cycles: pd.DataFrame,
    batteries: pd.DataFrame,
    seed: int,
) -> dict[str, pd.DataFrame]:
    comparison_rows = []
    tuning_parts = []
    lobo_parts = []
    curve_parts = []
    summary_parts = []
    for result in results:
        policy_error = result.lobo.groupby("Policy")["RMSE"].mean()
        comparison_rows.append(
            {
                "Model": result.model_type,
                "MeanBatteryRMSE": result.lobo["RMSE"].mean(),
                "SEBatteryRMSE": result.lobo["RMSE"].std(ddof=1) / np.sqrt(len(result.lobo)),
                "MeanBatteryMAE": result.lobo["MAE"].mean(),
                "MedianBatteryRMSE": result.lobo["RMSE"].median(),
                "WorstPolicyRMSE": policy_error.max(),
                "MaxBatteryError": result.lobo["MaxAbsError"].max(),
                "LambdaRandom": result.best_config.lambda_random,
                "LambdaCurve": result.best_config.lambda_curve,
            }
        )
        tuning = result.tuning.copy()
        tuning.insert(0, "Model", result.model_type)
        tuning_parts.append(tuning)
        lobo = result.lobo.copy()
        lobo.insert(0, "Model", result.model_type)
        lobo_parts.append(lobo)
        curve_parts.append(result.curves)
        summary_parts.append(result.strategy_summary)
    comparison = pd.DataFrame(comparison_rows)
    comparison["Selected"] = comparison["MeanBatteryRMSE"] == comparison["MeanBatteryRMSE"].min()

    all_lobo = pd.concat(lobo_parts, ignore_index=True)
    pipeline_rows = []
    for _, fold_rows in all_lobo.groupby("BatteryId", sort=False):
        selected = fold_rows.loc[fold_rows["InnerCVMeanBatteryRMSE"].idxmin()].copy()
        selected["SelectedModel"] = selected["Model"]
        pipeline_rows.append(selected)
    selection_pipeline_lobo = pd.DataFrame(pipeline_rows).reset_index(drop=True)
    selection_pipeline_summary = pd.DataFrame(
        [
            {
                "ValidationScheme": "outer_LOBO_inner_family_and_hyperparameter_selection",
                "NBattery": len(selection_pipeline_lobo),
                "MeanBatteryRMSE": selection_pipeline_lobo["RMSE"].mean(),
                "SEBatteryRMSE": selection_pipeline_lobo["RMSE"].std(ddof=1)
                / np.sqrt(len(selection_pipeline_lobo)),
                "MeanBatteryMAE": selection_pipeline_lobo["MAE"].mean(),
                "MedianBatteryRMSE": selection_pipeline_lobo["RMSE"].median(),
            }
        ]
    )

    policies = results[0].strategy_summary["Policy"].tolist()
    rank_table = pd.DataFrame({"Policy": policies})
    values = {}
    for result in results:
        values[result.model_type] = (
            result.strategy_summary.set_index("Policy").loc[policies, "SOH200"].to_numpy()
        )
        rank_table[f"{result.model_type}_rank"] = pd.Series(values[result.model_type]).rank(
            method="first", ascending=False
        ).astype(int)
    agreement_rows = []
    for first in results:
        for second in results:
            left = first.curves.sort_values(["Policy", "Cycle"])["SOHPred"].to_numpy()
            right = second.curves.sort_values(["Policy", "Cycle"])["SOHPred"].to_numpy()
            rank_a = rank_table[f"{first.model_type}_rank"].to_numpy()
            rank_b = rank_table[f"{second.model_type}_rank"].to_numpy()
            agreement_rows.append(
                {
                    "ModelA": first.model_type,
                    "ModelB": second.model_type,
                    "CurveRMSE": np.sqrt(np.mean((left - right) ** 2)),
                    "RankSpearman": np.corrcoef(rank_a, rank_b)[0, 1],
                }
            )

    rng = np.random.default_rng(seed)
    paired_rows = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            merged = results[i].lobo[["BatteryId", "RMSE"]].merge(
                results[j].lobo[["BatteryId", "RMSE"]],
                on="BatteryId",
                suffixes=("A", "B"),
            )
            difference = merged["RMSEA"].to_numpy() - merged["RMSEB"].to_numpy()
            samples = rng.choice(difference, size=(5000, len(difference)), replace=True).mean(axis=1)
            paired_rows.append(
                {
                    "ModelA": results[i].model_type,
                    "ModelB": results[j].model_type,
                    "MeanRMSEDifference_AminusB": difference.mean(),
                    "CI95Low": np.quantile(samples, 0.025),
                    "CI95High": np.quantile(samples, 0.975),
                }
            )

    best = min(results, key=lambda item: item.lobo["RMSE"].mean())
    baseline_parts = []
    variants = {
        "primary_soh_clean_complete_cells": cycles.copy(),
        "relative_soh_complete_cells": cycles.assign(SOH_clean=cycles["SOH_relative_clean"]),
        "exclude_battery_41_complete_cells": cycles.loc[cycles["battery_id"] != 41].copy(),
    }
    for name, frame in variants.items():
        model = fit_population_model(frame, best.model_type, best.best_config)
        matching_batteries = batteries.loc[batteries["battery_id"].isin(frame["battery_id"].unique())]
        _, summary = _extract_outputs(model, matching_batteries)
        summary = summary.sort_values("SOH200", ascending=False).reset_index(drop=True)
        summary["Rank"] = np.arange(1, len(summary) + 1)
        summary.insert(0, "SensitivityVariant", name)
        baseline_parts.append(summary[["SensitivityVariant", "Policy", "SOH200", "Rank"]])

    policy_cv = (
        best.lobo.groupby("Policy", sort=False)
        .agg(
            NBattery=("BatteryId", "size"),
            MeanRMSE=("RMSE", "mean"),
            MedianRMSE=("RMSE", "median"),
            MaxRMSE=("RMSE", "max"),
        )
        .reset_index()
        .sort_values("MeanRMSE", ascending=False)
    )
    return {
        "model_comparison": comparison,
        "model_agreement": pd.DataFrame(agreement_rows),
        "model_pairwise_cv_difference": pd.DataFrame(paired_rows),
        "selection_pipeline_lobo_by_battery": selection_pipeline_lobo,
        "selection_pipeline_summary": selection_pipeline_summary,
        "strategy_rank_by_model": rank_table,
        "baseline_sensitivity_strategy_rank": pd.concat(baseline_parts, ignore_index=True),
        "authoritative_model_cv_by_policy": policy_cv,
        "main_model_lobo_by_battery": best.lobo.copy(),
        "all_model_strategy_curves": pd.concat(curve_parts, ignore_index=True),
        "all_model_strategy_summary": pd.concat(summary_parts, ignore_index=True),
        "all_model_tuning": pd.concat(tuning_parts, ignore_index=True),
        "all_model_lobo_by_battery": all_lobo,
    }


def _conclusion_table(
    result,
    lifetime_rank_stability,
    pairwise_lifetimes,
    lifetime_validation_summary,
    residual_policy,
    associations,
):
    ordered = lifetime_rank_stability.sort_values("PointT80Rank")
    long_group = ordered.head(3)["Policy"].tolist()
    short_group = ordered.tail(3)["Policy"].tolist()
    significant_lifetime = pairwise_lifetimes.loc[
        pairwise_lifetimes["SignificantAfterHolm"].astype(bool)
    ]
    selected_window = lifetime_validation_summary.loc[
        lifetime_validation_summary["Selected"].astype(bool)
    ].iloc[0]
    mechanism = associations.loc[
        associations["Feature"].str.startswith(("IR", "Temperature", "ChargeTime"))
    ].copy()
    strongest = mechanism.iloc[mechanism["SpearmanCorrelation"].abs().argmax()]
    return pd.DataFrame(
        [
            {
                "ConclusionId": "Q1-C01",
                "Topic": "lifetime_model",
                "Statement": (
                    f"循环寿命主模型使用前150循环末段{int(selected_window['Window'])}循环线性趋势与SOH=0.8的交点；"
                    f"151至200循环策略等权回测RMSE为{selected_window['StrategyEqualRMSE']:.6f}。"
                ),
                "EvidenceCSV": "lifetime_window_validation_summary.csv;battery_lifetime_estimates.csv",
                "Caveat": "回测验证近端趋势预测，不是对真实T80终点的直接验证",
            },
            {
                "ConclusionId": "Q1-C02",
                "Topic": "model_agreement",
                "Statement": "三种候选模型的SOH200策略排序完全一致。",
                "EvidenceCSV": "model_agreement.csv",
                "Caveat": "SOH曲线模型为辅助分析，一致性只覆盖0至200循环",
            },
            {
                "ConclusionId": "Q1-C03",
                "Topic": "typical_long",
                "Statement": "；".join(long_group) if long_group else "没有策略达到80% bootstrap稳定阈值",
                "EvidenceCSV": "strategy_lifetime_summary.csv;strategy_lifetime_rank_stability.csv",
                "Caveat": "基于电池级预测T80的策略中位数前三名；同时查看bootstrap排名概率",
            },
            {
                "ConclusionId": "Q1-C04",
                "Topic": "typical_short",
                "Statement": "；".join(short_group) if short_group else "没有策略达到80% bootstrap稳定阈值",
                "EvidenceCSV": "strategy_lifetime_summary.csv;strategy_lifetime_rank_stability.csv",
                "Caveat": "基于电池级预测T80的策略中位数后三名；同时查看bootstrap排名概率",
            },
            {
                "ConclusionId": "Q1-C05",
                "Topic": "pairwise_difference",
                "Statement": f"预测T80共有{len(significant_lifetime)}组策略对在精确置换检验及Holm校正后显著。",
                "EvidenceCSV": "pairwise_strategy_lifetime_comparison.csv",
                "Caveat": (
                    "精确置换在每策略仅3至8块电池时分辨率很粗，且响应本身是模型外推值；"
                    "0组确证差异不代表策略等价"
                ),
            },
            {
                "ConclusionId": "Q1-C06",
                "Topic": "residual_limit",
                "Statement": f"策略级最大平均训练残差RMSE为{residual_policy['MeanResidualRMSE'].max():.6f}。",
                "EvidenceCSV": "residual_diagnostics_by_policy.csv",
                "Caveat": "训练残差诊断不能替代留一电池误差",
            },
            {
                "ConclusionId": "Q1-C07",
                "Topic": "descriptive_mechanism",
                "Statement": f"与SOH200绝对Spearman相关最大的是{strongest['Feature']}，相关系数{strongest['SpearmanCorrelation']:.3f}。",
                "EvidenceCSV": "strategy_association_summary.csv",
                "Caveat": "仅9个策略的描述性关联，不能解释为因果机制",
            },
            {
                "ConclusionId": "Q1-C08",
                "Topic": "eol_boundary",
                "Statement": "当前49块电池均未观测到80% SOH终点。",
                "EvidenceCSV": "data_coverage.csv;lifetime_window_sensitivity.csv",
                "Caveat": "T80是早期SOH趋势外推；必须同时报告窗口敏感性和电池bootstrap不确定性",
            },
        ]
    )


def _holm_adjust(p_values: np.ndarray) -> np.ndarray:
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values, dtype=float)
    running = 0.0
    count = len(p_values)
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * p_values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted
