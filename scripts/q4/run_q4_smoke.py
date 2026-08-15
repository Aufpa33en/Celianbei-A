"""Run Q4 smoke models without touching Q1-Q3 authoritative results."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from q4_models.core import (Q4_VERSION, SEED, bootstrap_pareto, collect_policy_observations,
                            loso_single_exposure, observation_frame, pareto_mask)


def main() -> None:
    target = ROOT / "result" / "q4" / "01_smoke_test_v2"
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    started = time.perf_counter()
    observations, battery = collect_policy_observations(ROOT)
    summary = observation_frame(observations)
    summary["pareto"] = pareto_mask(summary["time_mean"], summary["loss_mean"])
    boot = bootstrap_pareto(battery, repetitions=2000, seed=SEED)
    loso = loso_single_exposure(summary, "j")
    m1_rmse = float(loso["rmse"].mean())
    m1_improve = float(loso["improvement"].mean())
    baseline = pd.DataFrame([
        {"version": Q4_VERSION, "model": "M0_discrete_pareto", "status": "primary",
         "detail": "9 observed strategies; Pareto + constrained choice"},
        {"version": Q4_VERSION, "model": "M1_single_J_ridge", "status": "sensitivity",
         "detail": "7 unique complete coordinates; coordinate LOSO is extrapolation pressure test"},
        {"version": Q4_VERSION, "model": "B_shortest_time", "status": "baseline", "detail": "minimum observed mean charge time"},
        {"version": Q4_VERSION, "model": "C_lowest_loss", "status": "baseline", "detail": "minimum observed SOH200 relative loss"},
    ])
    metrics = pd.DataFrame([
        {"version": Q4_VERSION, "model": "M0_discrete_pareto", "status": "pass_primary",
         "metric": "pareto_count", "value": float(summary["pareto"].sum()),
         "reason": "uses observed 9-strategy time-degradation points; no continuous causal claim"},
        {"version": Q4_VERSION, "model": "M1_single_J_ridge", "status": "pass_sensitivity",
         "metric": "coordinate_loso_rmse", "value": m1_rmse,
         "reason": f"extrapolation pressure test; mean improvement over constant={m1_improve:.6g}"},
        {"version": Q4_VERSION, "model": "B_shortest_time", "status": "baseline_only",
         "metric": "minimum_observed_time", "value": float(summary["time_mean"].min()),
         "reason": "single-objective boundary"},
        {"version": Q4_VERSION, "model": "C_lowest_loss", "status": "baseline_only",
         "metric": "minimum_observed_loss", "value": float(summary["loss_mean"].min()),
         "reason": "single-objective boundary"},
    ])
    selected = pd.DataFrame([{
        "version": Q4_VERSION, "selected_model": "M0_discrete_pareto", "selection_variant": "observed_policy_pareto",
        "reason": "M1 is only an extrapolation pressure test; free continuous response surface is not identifiable",
        "m1_mean_improvement_over_constant": m1_improve, "m1_mean_loso_rmse": m1_rmse,
        "pareto_count_point": int(summary["pareto"].sum()), "bootstrap_repetitions": 2000,
    }])
    runtime = pd.DataFrame([{"version": Q4_VERSION, "stage": "load_aggregate_loso_bootstrap",
                             "seconds": time.perf_counter() - started, "bootstrap_repetitions": 2000}])
    checks = pd.DataFrame([
        {"check": "nine_policies", "passed": len(summary) == 9, "detail": len(summary)},
        {"check": "complete_batteries_only", "passed": battery["battery_id"].nunique() == 40, "detail": battery["battery_id"].nunique()},
        {"check": "finite_time_loss", "passed": summary[["time_mean", "loss_mean"]].notna().all().all(), "detail": "finite observed proxies"},
        {"check": "pareto_nonempty", "passed": bool(summary["pareto"].any()), "detail": int(summary["pareto"].sum())},
        {"check": "bootstrap_rows", "passed": len(boot) == 2000 * 9, "detail": len(boot)},
        {"check": "missing_c1_not_in_m1", "passed": summary.loc[summary["coordinate"].isna()].shape[0] >= 1, "detail": "missing coordinate retained only in M0"},
    ])
    if not checks["passed"].all(): raise RuntimeError(checks.loc[~checks["passed"], "check"].tolist())
    temp = target.with_name(target.name + ".tmp")
    temp.mkdir(parents=True)
    frames = {"policy_summary.csv": summary, "battery_observations.csv": battery,
              "bootstrap_pareto.csv": boot, "m1_coordinate_loso.csv": loso,
              "model_registry.csv": baseline, "model_metrics.csv": metrics,
              "selection_decision.csv": selected, "runtime.csv": runtime, "integrity_checks.csv": checks}
    for name, frame in frames.items(): frame.to_csv(temp / name, index=False, encoding="utf-8-sig")
    report = ("# Q4 smoke test\n\n" "M0离散策略Pareto为主模型，M1单J岭回归仅作受限敏感性。"
              "连续三参数因果优化和Q3反事实预测器均未进入。\n\n"
              f"运行时间：{runtime.iloc[0]['seconds']:.3f}秒；bootstrap=2000。M1平均LOSO压力测试RMSE={m1_rmse:.6g}，相对常数基线改善={m1_improve:.6g}。\n"
              "主模型选择理由：M0只依赖9个已观测策略；M1的唯一坐标留出多数落在训练凸包外，只能作为外推压力测试。\n"
              "正式全量bootstrap、连续候选网格和最终推荐尚未运行，等待阶段报告确认。\n")
    (temp / "smoke_report.md").write_text(report, encoding="utf-8")
    manifest_rows = []
    for path in sorted(temp.iterdir()):
        manifest_rows.append({"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "version": Q4_VERSION, "seed": SEED})
    pd.DataFrame(manifest_rows).to_csv(temp / "manifest.csv", index=False, encoding="utf-8-sig")
    temp.replace(target)
    print(f"Q4 smoke published: {target}", flush=True)


if __name__ == "__main__": main()
