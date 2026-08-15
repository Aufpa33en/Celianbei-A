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

FORMAL_VERSION = "q4_full_v2"
FORMAL_LAMBDAS = np.arange(0.0, 1.000001, 0.1)
RIDGE_GRID = (0.01, 0.1, 1.0, 10.0)
LOSS_LIMITS = (0.0005, 0.0010, 0.0015, 0.0017)
TIME_EQUIVALENCE_MINUTES = 0.01


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
    for weight in FORMAL_LAMBDAS:
        idx = choose_scalar(summary["time_mean"].to_numpy(), summary["loss_mean"].to_numpy(),
                            summary["policy"].astype(str).tolist(), float(weight))
        selected = summary.iloc[idx]
        rows.append({"rule": "weighted_minmax_all_policies_diagnostic", "lambda": float(weight),
                     "threshold_type": "not_applicable", "policy": str(selected["policy"]),
                     "time_mean": float(selected["time_mean"]),
                     "loss_mean": float(selected["loss_mean"]),
                     "pareto": bool(selected["pareto"])})
    for limit in LOSS_LIMITS:
        feasible = summary.loc[summary["loss_mean"] <= limit]
        if feasible.empty:
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                         "policy": "NO_FEASIBLE_POLICY"})
        else:
            selected = feasible.sort_values(["time_mean", "loss_mean", "policy"]).iloc[0]
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
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


def time_model_sensitivity(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    meta = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv")
    official = (meta.loc[meta["prediction_test"].eq(0)]
                .groupby("policy", as_index=False)["mean_chargetime"].mean()
                .rename(columns={"mean_chargetime": "summary_time_mean"}))
    table = summary[["policy", "c1", "q1", "c2", "time_mean", "loss_mean"]].merge(
        official, on="policy", how="left")
    table = table.rename(columns={"time_mean": "cycle_time_mean"})
    q = table["q1"] / 100.0
    table["t0_nominal"] = 60.0 * (q / table["c1"] + (0.8 - q) / table["c2"])
    table["cycle_minus_t0"] = table["cycle_time_mean"] - table["t0_nominal"]
    table["summary_minus_t0"] = table["summary_time_mean"] - table["t0_nominal"]
    table["cycle_minus_summary"] = table["cycle_time_mean"] - table["summary_time_mean"]
    table["pareto_cycle_time"] = pareto_mask(table["cycle_time_mean"], table["loss_mean"])
    table["pareto_summary_time"] = pareto_mask(table["summary_time_mean"], table["loss_mean"])
    fastest = float(table["cycle_time_mean"].min())
    table["cycle_time_equivalent_fastest"] = table["cycle_time_mean"] <= fastest + TIME_EQUIVALENCE_MINUTES
    decisions = []
    for metric in ("cycle_time_mean", "summary_time_mean"):
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
        reference_policy, "5_3C_54PER_4C_NEWSTRUCTURE",
        "3_7C_31PER_5_9C_NEWSTRUCTURE"]),
        ["policy", "n_battery", "time_mean", "loss_mean", "late_slope_mean"]].copy()
    selected["comparison_role"] = selected["policy"].map({
        reference_policy: "typical_long_life_reference",
        "5_3C_54PER_4C_NEWSTRUCTURE": "recommended_fast_pareto",
        "3_7C_31PER_5_9C_NEWSTRUCTURE": "typical_short_life_reference",
    })
    selected["time_difference_vs_long"] = selected["time_mean"] - float(reference["time_mean"])
    selected["loss_difference_vs_long"] = selected["loss_mean"] - float(reference["loss_mean"])
    return sensitivity, selected


def integrity_checks(summary: pd.DataFrame, battery: pd.DataFrame, boot: pd.DataFrame,
                     loso: pd.DataFrame, recommendations: pd.DataFrame,
                     time_table: pd.DataFrame, before: dict[str, str], repetitions: int) -> pd.DataFrame:
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
        {"check": "m1_coordinate_folds", "passed": len(loso) == 7 and len(repeated_coordinate) == 1, "detail": "7 unique coordinates; duplicate coordinate jointly held out"},
        {"check": "time_metric_pareto_stable", "passed": set(time_table.loc[time_table["pareto_cycle_time"], "policy"]) == set(time_table.loc[time_table["pareto_summary_time"], "policy"]), "detail": "cycle versus battery_summary time"},
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
    time_table, time_decisions = time_model_sensitivity(summary)
    scale_sensitivity = scaling_sensitivity(summary)
    slope_sensitivity, typical_comparison = slope_and_typical_comparisons(summary)
    checks = integrity_checks(summary, battery, boot, loso, recommendations, time_table, before, args.bootstrap)
    if not checks["passed"].all():
        raise RuntimeError(checks.loc[~checks["passed"], "check"].tolist())
    elapsed = time.perf_counter() - started
    metrics = pd.DataFrame([
        {"model": "M0_discrete_pareto", "status": "pass_primary", "metric": "pareto_count", "value": float(summary["pareto"].sum()), "detail": "9 observed policies; no continuous causal extrapolation"},
        {"model": "M1_single_J_ridge", "status": "rejected_as_optimizer", "metric": "oracle_coordinate_pressure_rmse", "value": float(loso["rmse"].mean()), "detail": f"oracle pressure test only; mean improvement={loso['improvement'].mean():.9g}"},
        {"model": "B_shortest_time", "status": "near_tie_baseline", "metric": "minimum_observed_time", "value": float(summary["time_mean"].min()), "detail": f"policies within {TIME_EQUIVALENCE_MINUTES} min treated as practical near-tie set"},
        {"model": "C_lowest_loss", "status": "baseline", "metric": "minimum_observed_loss", "value": float(summary["loss_mean"].min()), "detail": "single-objective boundary"},
    ])
    registry = pd.DataFrame([
        {"version": FORMAL_VERSION, "model": "M0_discrete_pareto", "status": "primary", "detail": "observed policy Pareto, constraints and bootstrap"},
        {"version": FORMAL_VERSION, "model": "M1_single_J_ridge", "status": "rejected_as_optimizer", "detail": "oracle coordinate pressure test; no continuous recommendation"},
    ])
    runtime = pd.DataFrame([{"version": FORMAL_VERSION, "stage": "full_q4_protocol",
                             "seconds": elapsed, "bootstrap_repetitions": args.bootstrap,
                             "seed": SEED, "lambda_count": len(FORMAL_LAMBDAS)}])
    run_config = {"version": FORMAL_VERSION, "seed": SEED, "bootstrap": args.bootstrap,
                  "formal_lambda_grid": FORMAL_LAMBDAS.tolist(), "ridge_grid": list(RIDGE_GRID),
                  "loss_limits": list(LOSS_LIMITS),
                  "loss_limit_type": "illustrative_decision_scenario_not_safety_standard",
                  "time_equivalence_minutes": TIME_EQUIVALENCE_MINUTES}
    frames = {"policy_summary.csv": summary, "battery_observations.csv": battery,
              "bootstrap_pareto.csv": boot, "policy_uncertainty.csv": uncertainty,
              "selection_frequency.csv": selection_frequency,
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
    report = f"""# Q4 全量验证结果\n\n版本`{FORMAL_VERSION}`，整块电池bootstrap {args.bootstrap}次，随机种子{SEED}，运行{elapsed:.3f}秒。\n\nM0离散观测策略Pareto为主模型；M1单J模型的oracle坐标压力测试失败，正式淘汰为优化器。点估计Pareto策略为：{', '.join(summary.loc[summary['pareto'], 'policy'].astype(str))}。\n\n权重结论依赖标准化集合，`scaling_sensitivity.csv`只作敏感性；正式决策应报告Pareto前沿、退化约束和bootstrap稳定性。四个退化上限是说明规则用法的决策场景，不是工程安全标准。四个约10.043分钟策略在0.01分钟容差内视为实际近似并列。\n\n`time_model_sensitivity.csv`同时保存逐循环均值、battery_summary均值和T0；`typical_strategy_comparison.csv`对比推荐策略与典型长/短寿命策略。推荐只适用于9个已有策略，不能解释为三参数因果最优。\n"""
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
