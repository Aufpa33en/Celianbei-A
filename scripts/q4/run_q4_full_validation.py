"""Run and atomically publish the complete Q4 observed-policy protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from q4_models.core import (  # noqa: E402
    SEED,
    bootstrap_pareto,
    choose_scalar,
    collect_policy_observations,
    loso_single_exposure,
    observation_frame,
    pareto_mask,
)

FORMAL_VERSION = "q4_full_v4"
FORMAL_LAMBDAS = np.arange(0.0, 1.000001, 0.1)
RIDGE_GRID = (0.01, 0.1, 1.0, 10.0)
LOSS_LIMITS = (0.0005, 0.0010, 0.0015, 0.0017)
TIME_EQUIVALENCE_MINUTES = 0.01
SUPERIORITY_PROBABILITY = 0.95
FAST_PAIR = (
    "5_3C_54PER_4C_NEWSTRUCTURE",
    "5C_67PER_4C_NEWSTRUCTURE",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_hashes() -> dict[str, str]:
    roots = [ROOT / "data", ROOT / "src" / "q4_models", ROOT / "scripts" / "q4",
             ROOT / "result" / "q4" / "01_smoke_test",
             ROOT / "result" / "q4" / "01_smoke_test_v2"]
    files = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*")
                         if path.is_file() and "__pycache__" not in path.parts)
    return {str(path.relative_to(ROOT)): _sha256(path) for path in sorted(files)}


def policy_uncertainty(battery: pd.DataFrame, boot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, group in battery.groupby("policy", sort=True):
        row = {"policy": policy, "n_battery": len(group),
               "interval_type": "strategy_mean_whole_battery_bootstrap"}
        boot_group = boot.loc[boot["policy"].eq(policy)]
        for metric in ("time", "loss", "late_slope_loss"):
            values = pd.to_numeric(boot_group[metric], errors="coerce").dropna()
            row[f"{metric}_p025"] = float(values.quantile(0.025))
            row[f"{metric}_p50"] = float(values.quantile(0.5))
            row[f"{metric}_p975"] = float(values.quantile(0.975))
        rows.append(row)
    return pd.DataFrame(rows)


def point_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    normalization = {
        "decision_role": "diagnostic_weight_sensitivity_not_primary_recommendation",
        "normalization_method": "minmax",
        "normalization_scope": "all_9_observed_policies_including_dominated",
        "normalization_n_policies": len(summary),
        "normalization_time_min": float(summary["time_mean"].min()),
        "normalization_time_max": float(summary["time_mean"].max()),
        "normalization_loss_min": float(summary["loss_mean"].min()),
        "normalization_loss_max": float(summary["loss_mean"].max()),
    }
    for weight in FORMAL_LAMBDAS:
        idx = choose_scalar(summary["time_mean"].to_numpy(), summary["loss_mean"].to_numpy(),
                            summary["policy"].astype(str).tolist(), float(weight))
        selected = summary.iloc[idx]
        rows.append({"rule": "weighted_minmax_all_policies_diagnostic", "lambda": float(weight),
                     "threshold_type": "not_applicable", "policy": str(selected["policy"]),
                     "time_mean": float(selected["time_mean"]),
                     "loss_mean": float(selected["loss_mean"]), **normalization,
                     "pareto": bool(selected["pareto"])})
    for limit in LOSS_LIMITS:
        feasible = summary.loc[summary["loss_mean"] <= limit]
        if feasible.empty:
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                         "decision_role": "illustrative_constraint_sensitivity_not_primary_recommendation",
                         "policy": "NO_FEASIBLE_POLICY"})
        else:
            selected = feasible.sort_values(["time_mean", "loss_mean", "policy"]).iloc[0]
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                         "decision_role": "illustrative_constraint_sensitivity_not_primary_recommendation",
                         "policy": str(selected["policy"]), "time_mean": float(selected["time_mean"]),
                         "loss_mean": float(selected["loss_mean"]), "pareto": bool(selected["pareto"])})
    return pd.DataFrame(rows)


def selection_frequencies(boot: pd.DataFrame, repetitions: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    pareto_frequency = (boot.groupby("policy", as_index=False)["pareto"].mean()
                        .rename(columns={"pareto": "pareto_frequency"}).set_index("policy"))
    for column in [name for name in boot if name.startswith("selected_lambda_")]:
        counts = boot.loc[boot[column]].groupby("policy").size() / repetitions
        pareto_frequency[column] = counts
    weighted = pareto_frequency.fillna(0.0).reset_index()
    constrained_rows = []
    for limit in LOSS_LIMITS:
        column = f"selected_loss_limit_{limit:.4f}"
        counts = boot.loc[boot[column]].groupby("policy").size()
        selected_replicates = int(counts.sum())
        for policy in sorted(boot["policy"].unique()):
            constrained_rows.append({"loss_limit": limit,
                                     "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                                     "policy": policy,
                                     "selection_frequency": float(counts.get(policy, 0) / repetitions)})
        constrained_rows.append({"loss_limit": limit,
                                 "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                                 "policy": "NO_FEASIBLE_POLICY",
                                 "selection_frequency": float((repetitions - selected_replicates) / repetitions)})
    return weighted, pd.DataFrame(constrained_rows)


def fast_pair_comparison(
    summary: pd.DataFrame, boot: pd.DataFrame, uncertainty: pd.DataFrame,
    selection_frequency: pd.DataFrame,
) -> pd.DataFrame:
    """Compare the two practically fastest observed policies without forcing a winner."""
    first, second = FAST_PAIR
    point = summary.set_index("policy")
    wide = boot.pivot(index="replicate", columns="policy", values=["time", "loss", "pareto"])
    time_difference = wide["time"][first] - wide["time"][second]
    loss_difference = wide["loss"][first] - wide["loss"][second]
    loss_probability_first_better = float((loss_difference < 0).mean())
    time_probability_first_faster = float((time_difference < 0).mean())
    time_probability_first_not_slower = float(
        (time_difference <= TIME_EQUIVALENCE_MINUTES).mean()
    )
    time_probability_second_not_slower = float(
        (-time_difference <= TIME_EQUIVALENCE_MINUTES).mean()
    )
    unique_winner = (
        first if (
            loss_probability_first_better >= SUPERIORITY_PROBABILITY
            and time_probability_first_not_slower >= SUPERIORITY_PROBABILITY
        )
        else second if (
            1.0 - loss_probability_first_better >= SUPERIORITY_PROBABILITY
            and time_probability_second_not_slower >= SUPERIORITY_PROBABILITY
        )
        else None
    )
    intervals = uncertainty.set_index("policy")
    frequencies = selection_frequency.set_index("policy")
    rows = []
    for policy in FAST_PAIR:
        other = second if policy == first else first
        point_pareto = bool(point.loc[policy, "pareto"])
        rows.append({
            "version": FORMAL_VERSION,
            "policy": policy,
            "comparison_policy": other,
            "decision_status": (
                "unique_fast_tradeoff_recommendation" if policy == unique_winner
                else "point_pareto_fast_tradeoff_recommendation"
                if unique_winner is None and point_pareto
                else "uncertainty_near_tie_nonpareto_sensitivity"
                if unique_winner is None
                else "not_selected"
            ),
            "point_pareto": point_pareto,
            "time_mean": float(point.loc[policy, "time_mean"]),
            "time_p025": float(intervals.loc[policy, "time_p025"]),
            "time_p975": float(intervals.loc[policy, "time_p975"]),
            "loss_mean": float(point.loc[policy, "loss_mean"]),
            "loss_p025": float(intervals.loc[policy, "loss_p025"]),
            "loss_p975": float(intervals.loc[policy, "loss_p975"]),
            "pareto_frequency": float(frequencies.loc[policy, "pareto_frequency"]),
            "probability_lower_loss_than_pair": (
                loss_probability_first_better if policy == first else 1.0 - loss_probability_first_better
            ),
            "probability_faster_than_pair": (
                time_probability_first_faster if policy == first else 1.0 - time_probability_first_faster
            ),
            "probability_not_slower_by_more_than_0_01_min": (
                time_probability_first_not_slower if policy == first
                else time_probability_second_not_slower
            ),
            "probability_time_difference_within_0_01_min": float(
                (time_difference.abs() <= TIME_EQUIVALENCE_MINUTES).mean()
            ),
            "pair_time_difference_first_minus_second_p025": float(time_difference.quantile(0.025)),
            "pair_time_difference_first_minus_second_p50": float(time_difference.quantile(0.5)),
            "pair_time_difference_first_minus_second_p975": float(time_difference.quantile(0.975)),
            "pair_loss_difference_first_minus_second_p025": float(loss_difference.quantile(0.025)),
            "pair_loss_difference_first_minus_second_p50": float(loss_difference.quantile(0.5)),
            "pair_loss_difference_first_minus_second_p975": float(loss_difference.quantile(0.975)),
            "unique_recommendation_probability_threshold": SUPERIORITY_PROBABILITY,
            "q3_role": "not_used_no_early_trajectory_for_new_policy",
        })
    return pd.DataFrame(rows)


def time_model_sensitivity(summary: pd.DataFrame, battery: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv")
    official = (meta.loc[meta["prediction_test"].eq(0)]
                .groupby("policy", as_index=False)["mean_chargetime"].mean()
                .rename(columns={"mean_chargetime": "summary_time_mean"}))
    cycle = (battery.groupby("policy", as_index=False)["cycle_time_sensitivity"].mean()
             .rename(columns={"cycle_time_sensitivity": "cycle_time_mean"}))
    table = summary[["policy", "c1", "q1", "c2", "time_mean", "loss_mean"]].merge(
        official, on="policy", how="left").merge(cycle, on="policy", how="left")
    table = table.rename(columns={"time_mean": "primary_time_mean"})
    q = table["q1"] / 100.0
    table["t0_nominal"] = 60.0 * (q / table["c1"] + (0.8 - q) / table["c2"])
    table["primary_minus_t0"] = table["primary_time_mean"] - table["t0_nominal"]
    table["summary_minus_t0"] = table["summary_time_mean"] - table["t0_nominal"]
    table["cycle_minus_summary"] = table["cycle_time_mean"] - table["summary_time_mean"]
    table["primary_equals_summary"] = np.isclose(
        table["primary_time_mean"], table["summary_time_mean"], rtol=0.0, atol=1e-12
    )
    table["pareto_primary_time"] = pareto_mask(table["primary_time_mean"], table["loss_mean"])
    table["pareto_cycle_time"] = pareto_mask(table["cycle_time_mean"], table["loss_mean"])
    table["pareto_summary_time"] = pareto_mask(table["summary_time_mean"], table["loss_mean"])
    fastest = float(table["primary_time_mean"].min())
    table["primary_time_equivalent_fastest"] = table["primary_time_mean"] <= fastest + TIME_EQUIVALENCE_MINUTES
    decisions = []
    for metric in ("primary_time_mean", "cycle_time_mean"):
        for weight in FORMAL_LAMBDAS:
            idx = choose_scalar(table[metric].to_numpy(), table["loss_mean"].to_numpy(),
                                table["policy"].astype(str).tolist(), float(weight))
            decisions.append({"time_metric": metric, "lambda": float(weight),
                              "policy": str(table.iloc[idx]["policy"]),
                              "time_mean": float(table.iloc[idx][metric]),
                              "loss_mean": float(table.iloc[idx]["loss_mean"])})
    return table, pd.DataFrame(decisions)


def _scaled_score(time_values: np.ndarray, loss_values: np.ndarray, weight: float,
                  mode: str, front: np.ndarray) -> np.ndarray:
    def scale(values: np.ndarray, indices: np.ndarray, robust: bool) -> np.ndarray:
        reference = values[indices]
        lo, hi = (np.quantile(reference, [0.1, 0.9]) if robust
                  else (float(reference.min()), float(reference.max())))
        if hi - lo < 1e-12:
            return np.zeros_like(values)
        scaled = (values - lo) / (hi - lo)
        return np.clip(scaled, 0.0, 1.0) if robust else scaled
    indices = np.flatnonzero(front) if mode == "pareto_minmax" else np.arange(len(time_values))
    robust = mode == "robust_q10_q90"
    return weight * scale(time_values, indices, robust) + (1.0 - weight) * scale(loss_values, indices, robust)


def scaling_sensitivity(summary: pd.DataFrame) -> pd.DataFrame:
    time_values = summary["time_mean"].to_numpy(float)
    loss_values = summary["loss_mean"].to_numpy(float)
    policies = summary["policy"].astype(str).tolist()
    front = summary["pareto"].to_numpy(bool)
    rows = []
    for mode in ("all_policy_minmax", "pareto_minmax", "robust_q10_q90"):
        eligible = np.flatnonzero(front) if mode == "pareto_minmax" else np.arange(len(summary))
        for weight in FORMAL_LAMBDAS:
            score = _scaled_score(time_values, loss_values, float(weight), mode, front)
            idx = min(eligible, key=lambda i: (score[i], loss_values[i], time_values[i], policies[i]))
            rows.append({"scaling": mode, "lambda": float(weight), "policy": policies[idx],
                         "score": float(score[idx]), "time_mean": time_values[idx],
                         "loss_mean": loss_values[idx], "pareto": bool(front[idx])})
    return pd.DataFrame(rows)


def slope_and_typical_comparisons(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sensitivity = summary[["policy", "n_battery", "time_mean", "loss_mean", "late_slope_mean"]].copy()
    sensitivity["pareto_soh200"] = pareto_mask(sensitivity["time_mean"], sensitivity["loss_mean"])
    sensitivity["pareto_late_slope"] = pareto_mask(sensitivity["time_mean"], sensitivity["late_slope_mean"])
    reference_policy = "3_6C-80PER_3_6C"
    reference = summary.loc[summary["policy"].eq(reference_policy)].iloc[0]
    selected = summary.loc[summary["policy"].isin([
        reference_policy, *FAST_PAIR,
        "3_7C_31PER_5_9C_NEWSTRUCTURE"]),
        ["policy", "n_battery", "time_mean", "loss_mean", "late_slope_mean"]].copy()
    selected["comparison_role"] = selected["policy"].map({
        reference_policy: "typical_long_life_reference",
        "5_3C_54PER_4C_NEWSTRUCTURE": "point_pareto_fast_tradeoff_recommendation",
        "5C_67PER_4C_NEWSTRUCTURE": "uncertainty_near_tie_nonpareto_sensitivity",
        "3_7C_31PER_5_9C_NEWSTRUCTURE": "typical_short_life_reference",
    })
    selected["time_difference_vs_long"] = selected["time_mean"] - float(reference["time_mean"])
    selected["loss_difference_vs_long"] = selected["loss_mean"] - float(reference["loss_mean"])
    return sensitivity, selected


def integrity_checks(summary: pd.DataFrame, battery: pd.DataFrame, boot: pd.DataFrame,
                     loso: pd.DataFrame, recommendations: pd.DataFrame,
                     time_table: pd.DataFrame, fast_pair: pd.DataFrame,
                     before: dict[str, str], repetitions: int) -> pd.DataFrame:
    meta = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv")
    expected_ids = set(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int))
    actual_ids = set(battery["battery_id"].astype(int))
    lambda_columns = [name for name in boot if name.startswith("selected_lambda_")]
    constraint_columns = [name for name in boot if name.startswith("selected_loss_limit_")]
    per_rep = boot.groupby("replicate").size()
    lambda_sums = boot.groupby("replicate")[lambda_columns].sum()
    recommendation_policies = set(recommendations.loc[recommendations["policy"].ne("NO_FEASIBLE_POLICY"), "policy"])
    pareto_policies = set(summary.loc[summary["pareto"], "policy"])
    repeated_coordinate = loso.loc[loso["n_test_policy"].eq(2), "held_out_coordinate"]
    return pd.DataFrame([
        {"check": "nine_policies", "passed": len(summary) == 9, "detail": len(summary)},
        {"check": "exact_complete_battery_ids", "passed": actual_ids == expected_ids and len(actual_ids) == 40, "detail": len(actual_ids)},
        {"check": "test_battery_ids_excluded", "passed": actual_ids.isdisjoint(set(meta.loc[meta["prediction_test"].eq(1), "battery_id"].astype(int))), "detail": "prediction_test=1 intersection empty"},
        {"check": "finite_policy_metrics", "passed": bool(summary[["time_mean", "loss_mean", "late_slope_mean"]].notna().all().all()), "detail": "finite time/loss/slope"},
        {"check": "bootstrap_replicates_complete", "passed": len(boot) == repetitions * 9 and per_rep.eq(9).all() and len(per_rep) == repetitions, "detail": len(boot)},
        {"check": "each_lambda_selects_one", "passed": len(lambda_columns) == 11 and lambda_sums.eq(1).all().all(), "detail": len(lambda_columns)},
        {"check": "constraint_rules_bootstrapped", "passed": len(constraint_columns) == len(LOSS_LIMITS), "detail": len(constraint_columns)},
        {"check": "late_slope_bootstrapped", "passed": bool(boot["late_slope_loss"].notna().all()), "detail": "strategy mean per replicate"},
        {"check": "point_recommendations_pareto", "passed": recommendation_policies.issubset(pareto_policies), "detail": len(recommendation_policies)},
        {"check": "weighted_normalization_machine_readable", "passed": recommendations.loc[recommendations["rule"].eq("weighted_minmax_all_policies_diagnostic"), "normalization_scope"].eq("all_9_observed_policies_including_dominated").all(), "detail": "weighted score is diagnostic; all-policy minmax scope exposed"},
        {"check": "m1_coordinate_folds", "passed": len(loso) == 7 and len(repeated_coordinate) == 1, "detail": "7 unique coordinates; duplicate coordinate jointly held out"},
        {"check": "m1_failure_concentration_exposed", "passed": loso["worst_fold"].sum() == 1 and bool(loso.loc[loso["worst_fold"], "outside_train_exposure_range"].all()) and bool(loso.loc[loso["worst_fold"], "prediction_below_zero"].all()) and loso.loc[~loso["worst_fold"], "rmse"].mean() > loso.loc[~loso["worst_fold"], "constant_rmse"].mean(), "detail": f"worst-fold SSE share={loso['squared_error_share'].max():.6f}; excluding worst M1 RMSE={loso.loc[~loso['worst_fold'], 'rmse'].mean():.6f} > baseline={loso.loc[~loso['worst_fold'], 'constant_rmse'].mean():.6f}"},
        {"check": "fast_pair_point_pareto_roles", "passed": len(fast_pair) == 2 and fast_pair["point_pareto"].sum() == 1 and fast_pair.loc[fast_pair["point_pareto"], "decision_status"].eq("point_pareto_fast_tradeoff_recommendation").all() and fast_pair.loc[~fast_pair["point_pareto"], "decision_status"].eq("uncertainty_near_tie_nonpareto_sensitivity").all(), "detail": "point Pareto recommendation separated from non-Pareto uncertainty sensitivity"},
        {"check": "fast_pair_difference_intervals_cross_zero", "passed": bool((fast_pair["pair_time_difference_first_minus_second_p025"] < 0).all() and (fast_pair["pair_time_difference_first_minus_second_p975"] > 0).all() and (fast_pair["pair_loss_difference_first_minus_second_p025"] < 0).all() and (fast_pair["pair_loss_difference_first_minus_second_p975"] > 0).all()), "detail": "time and loss pairwise bootstrap intervals overlap zero"},
        {"check": "q3_not_used_as_counterfactual", "passed": fast_pair["q3_role"].eq("not_used_no_early_trajectory_for_new_policy").all(), "detail": "Q3 is conditional prediction, not a policy response surface"},
        {"check": "primary_time_matches_q1_q2", "passed": bool(time_table["primary_equals_summary"].all()), "detail": "Q4 primary equals battery_summary mean_chargetime"},
        {"check": "time_metric_pareto_stable", "passed": set(time_table.loc[time_table["pareto_cycle_time"], "policy"]) == set(time_table.loc[time_table["pareto_primary_time"], "policy"]), "detail": "cycle sensitivity versus primary battery_summary time"},
        {"check": "protected_inputs_unchanged", "passed": before == protected_hashes(), "detail": "data, q4 source, smoke outputs"},
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "result" / "q4",
        help="Directory containing the generated 02_full_validation directory.",
    )
    args = parser.parse_args()
    target = args.output_root.resolve() / "02_full_validation"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    started = time.perf_counter()
    before = protected_hashes()
    observations, battery = collect_policy_observations(ROOT)
    summary = observation_frame(observations)
    summary["pareto"] = pareto_mask(summary["time_mean"], summary["loss_mean"])
    summary["version"] = FORMAL_VERSION
    boot = bootstrap_pareto(battery, repetitions=args.bootstrap, seed=SEED,
                            lambda_grid=FORMAL_LAMBDAS, loss_limits=LOSS_LIMITS)
    boot["version"] = FORMAL_VERSION
    loso = loso_single_exposure(summary, "j", ridge_grid=RIDGE_GRID)
    loso["version"] = FORMAL_VERSION
    uncertainty = policy_uncertainty(battery, boot)
    recommendations = point_recommendations(summary)
    selection_frequency, constraint_frequency = selection_frequencies(boot, args.bootstrap)
    fast_pair = fast_pair_comparison(summary, boot, uncertainty, selection_frequency)
    time_table, time_decisions = time_model_sensitivity(summary, battery)
    scale_sensitivity = scaling_sensitivity(summary)
    slope_sensitivity, typical_comparison = slope_and_typical_comparisons(summary)
    checks = integrity_checks(summary, battery, boot, loso, recommendations, time_table, fast_pair, before, args.bootstrap)
    if not checks["passed"].all():
        raise RuntimeError(checks.loc[~checks["passed"], "check"].tolist())
    elapsed = time.perf_counter() - started
    metrics = pd.DataFrame([
        {"model": "M0_discrete_pareto", "status": "pass_primary", "metric": "pareto_count", "value": float(summary["pareto"].sum()), "detail": "9 observed policies; no continuous causal extrapolation"},
        {"model": "M1_single_J_ridge", "status": "failed_validation_continuous_search_not_activated", "metric": "oracle_coordinate_pressure_rmse", "value": float(loso["rmse"].mean()), "detail": f"rejects this single-J ridge only; mean improvement={loso['improvement'].mean():.9g}; worst-fold SSE share={loso['squared_error_share'].max():.6f}"},
        {"model": "B_shortest_time", "status": "near_tie_baseline", "metric": "minimum_observed_time", "value": float(summary["time_mean"].min()), "detail": f"policies within {TIME_EQUIVALENCE_MINUTES} min treated as practical near-tie set"},
        {"model": "C_lowest_loss", "status": "baseline", "metric": "minimum_observed_loss", "value": float(summary["loss_mean"].min()), "detail": "single-objective boundary"},
    ])
    registry = pd.DataFrame([
        {"version": FORMAL_VERSION, "model": "M0_discrete_pareto", "status": "primary", "detail": "observed policy Pareto, constraints and bootstrap"},
        {"version": FORMAL_VERSION, "model": "M1_single_J_ridge", "status": "failed_validation", "detail": "this single-J ridge is unusable; broader continuous model classes remain untested"},
    ])
    runtime = pd.DataFrame([{"version": FORMAL_VERSION, "stage": "full_q4_protocol",
                             "seconds": elapsed, "bootstrap_repetitions": args.bootstrap,
                             "seed": SEED, "lambda_count": len(FORMAL_LAMBDAS)}])
    run_config = {"version": FORMAL_VERSION, "seed": SEED, "bootstrap": args.bootstrap,
                  "formal_lambda_grid": FORMAL_LAMBDAS.tolist(), "ridge_grid": list(RIDGE_GRID),
                  "loss_limits": list(LOSS_LIMITS),
                  "loss_limit_type": "illustrative_decision_scenario_not_safety_standard",
                  "primary_charge_time_metric": "battery_summary_clean.mean_chargetime",
                  "cycle_charge_time_metric_role": "sensitivity_only",
                  "time_equivalence_minutes": TIME_EQUIVALENCE_MINUTES,
                  "unique_recommendation_probability_threshold": SUPERIORITY_PROBABILITY,
                  "weighted_score_role": "diagnostic_weight_sensitivity_not_primary_recommendation",
                  "weighted_score_normalization": "minmax_all_9_observed_policies_including_dominated",
                  "q3_counterfactual_role": "not_used_no_early_trajectory_for_new_policy",
                  "continuous_model_conclusion": "single_J_ridge_failed_broader_classes_untested"}
    frames = {"policy_summary.csv": summary, "battery_observations.csv": battery,
              "bootstrap_pareto.csv": boot, "policy_uncertainty.csv": uncertainty,
              "selection_frequency.csv": selection_frequency,
              "fast_pair_comparison.csv": fast_pair,
              "constraint_selection_frequency.csv": constraint_frequency,
              "recommendations.csv": recommendations, "scaling_sensitivity.csv": scale_sensitivity,
              "time_model_sensitivity.csv": time_table,
              "time_metric_decision_sensitivity.csv": time_decisions,
              "late_slope_pareto_sensitivity.csv": slope_sensitivity,
              "typical_strategy_comparison.csv": typical_comparison,
              "m1_coordinate_loso.csv": loso, "model_metrics.csv": metrics,
              "model_registry.csv": registry, "runtime.csv": runtime,
              "integrity_checks.csv": checks}
    temp = target.with_name(target.name + ".tmp")
    temp.mkdir(parents=True)
    for name, frame in frames.items():
        frame.to_csv(temp / name, index=False, encoding="utf-8-sig")
    report = f"""# Q4 全量验证结果

版本`{FORMAL_VERSION}`，整块电池bootstrap {args.bootstrap}次，随机种子{SEED}，运行{elapsed:.3f}秒。

M0离散观测策略Pareto为主模型；M1单J岭模型的oracle坐标压力测试失败，所以本数据下不启动连续搜索。最差的3.6C留一折位于训练J范围外，产生负退化预测并贡献{loso['squared_error_share'].max():.1%}总平方误差；剔除该折后，M1平均RMSE仍为{loso.loc[~loso['worst_fold'], 'rmse'].mean():.6f}，略差于常数基线{loso.loc[~loso['worst_fold'], 'constant_rmse'].mean():.6f}。因此失败方向不依赖该折，但总体RMSE幅度明显受它驱动。该结果只否定当前单J岭代理，不证明所有连续代理或后续新增实验均无效。点估计Pareto策略为：{', '.join(summary.loc[summary['pareto'], 'policy'].astype(str))}。

充电时间主指标统一采用`battery_summary_clean.csv`中的逐电池`mean_chargetime`，与问题1、2一致。前200循环的逐循环均值仅作覆盖窗口敏感性，不能替代主指标。点估计上5.3C的时间和退化都低于5.0C，因此前者是快速区域的Pareto推荐，后者是非前沿的不确定性近似并列敏感性项。二者时间差和退化差的整块电池bootstrap区间均跨0，5.3C退化更低的概率不足0.95，因此不把5.0C排除为近似并列方案，但也不将严格被支配点标成共同主推荐。

权重结论依赖标准化集合。`recommendations.csv`中的加权结果明确标为诊断敏感性，使用全部9个观测策略（含被支配点）的min-max范围；该口径在λ=0.1时已选择5.3C，而只用Pareto点归一化要到λ=0.6才从3.6C切换到5.3C。`scaling_sensitivity.csv`保留这种差异，正式决策应报告Pareto前沿、退化约束和bootstrap稳定性，不能把任一加权表当成无条件主推荐。四个退化上限是说明规则用法的决策场景，不是工程安全标准。

`fast_pair_comparison.csv`分开记录点估计Pareto推荐与非前沿近似并列敏感性项，并给出成对区间和胜出概率。Q3模型需要目标电池已有1—150循环轨迹，未被用作新策略反事实响应面。推荐只适用于9个已有策略，不能解释为三参数因果最优。
"""
    (temp / "full_report.md").write_text(report, encoding="utf-8")
    (temp / "run_config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_rows = [{"path": path.name, "sha256": _sha256(path),
                      "version": FORMAL_VERSION, "seed": SEED}
                     for path in sorted(temp.iterdir())]
    pd.DataFrame(manifest_rows).to_csv(temp / "manifest.csv", index=False, encoding="utf-8-sig")
    temp.replace(target)
    print(f"Q4 full validation published: {target}", flush=True)
    print(f"Q4 full wall seconds: {elapsed:.3f}", flush=True)


if __name__ == "__main__":
    main()
