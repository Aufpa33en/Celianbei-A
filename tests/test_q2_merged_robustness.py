"""Checks for the merged Q2 robustness analysis."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.merged_robustness import extract_late_rate, run_merged_robustness  # noqa: E402


def main() -> None:
    increasing_cycles = pd.DataFrame({
        "battery_id": 999,
        "cycle": range(1, 201),
        "SOH_relative_clean": [1.0 + 0.0001 * cycle for cycle in range(1, 201)],
    })
    increasing_meta = pd.DataFrame({
        "battery_id": [999], "policy": ["synthetic"], "dataset_id": [0],
        "C1": [4.0], "Q1": [50.0], "C2": [4.0],
    })
    nonpositive = extract_late_rate(increasing_cycles, increasing_meta).iloc[0]
    assert not bool(nonpositive["late_rate_valid_for_log_model"])
    assert nonpositive["late_rate_exclusion_reason"] == "nonpositive_rate"
    assert pd.isna(nonpositive["log_late_degradation_rate"])

    outputs = run_merged_robustness(PROJECT_ROOT, repetitions=200, seed=20260814)
    battery = outputs["battery_late_rate"]
    strategy = outputs["strategy_late_rate"]
    sensitivity = outputs["jh_coordinate_sensitivity"]
    fold_diagnostics = outputs["jh_coordinate_fold_diagnostics"]
    assert len(battery) == 40
    assert battery["policy"].nunique() == 9
    assert battery["late_degradation_rate"].gt(0).all()
    assert battery["late_rate_valid_for_log_model"].astype(bool).all()
    assert len(strategy) == 9
    all_complete = sensitivity[
        sensitivity["cohort"].eq("all_complete") & sensitivity["model"].eq("log_rate_J_H")
    ].iloc[0]
    explicit = sensitivity[
        sensitivity["cohort"].eq("explicit_new_structure")
        & sensitivity["model"].eq("log_rate_J_H")
    ].iloc[0]
    assert all_complete["coordinate_equal_log_RMSE"] < 0.5
    assert explicit["coordinate_equal_log_RMSE"] > 4.0
    explicit_folds = fold_diagnostics[
        fold_diagnostics["cohort"].eq("explicit_new_structure")
        & fold_diagnostics["model"].eq("log_rate_J_H")
    ]
    assert len(explicit_folds) == 6
    assert explicit_folds["n_train_policy_rows"].eq(5).all()
    assert explicit_folds["n_parameters_including_intercept"].eq(3).all()
    assert explicit_folds["residual_df_proxy"].eq(2).all()
    assert explicit_folds["validation_support"].eq("very_low_df_diagnostic_only").all()
    matched = outputs["matched_4p8_comparison"].iloc[0]
    assert matched["relative_change"] < -0.7
    assert matched["causal_status"].startswith("not_identified")
    assert matched["n_label_assignments"] == 21
    assert matched["minimum_attainable_two_sided_p"] == 1 / 21
    assert bool(matched["p_at_minimum_resolution"])
    global_diagnostic = outputs["global_strategy_permutation"].iloc[0]
    assert global_diagnostic["artifact_role"] == "diagnostic_not_confirmatory_test"
    assert not bool(global_diagnostic["confirmatory_p_value_available"])
    assert "permutation_p" not in outputs["global_strategy_permutation"].columns
    q1_pairwise = pd.read_csv(
        PROJECT_ROOT / "result" / "q1" / "raw" / "pairwise_strategy_scalar_comparison.csv"
    )
    q1_soh200 = q1_pairwise[q1_pairwise["Metric"].eq("SOH200")]
    assert not q1_soh200["SignificantAfterHolm"].astype(bool).any()
    q1_lifetime = pd.read_csv(
        PROJECT_ROOT / "result" / "q1" / "raw" / "pairwise_strategy_lifetime_comparison.csv"
    )
    assert not q1_lifetime["SignificantAfterHolm"].astype(bool).any()
    paper = (
        PROJECT_ROOT / "result" / "q2" / "04_paper_materials" / "第二问完整回答.md"
    ).read_text(encoding="utf-8")
    assert "预测循环数T80" in paper
    assert "[-10.96%, 48.28%]" in paper
    assert "尾部比例为0.1556" in paper
    assert "不能称为确认性p值" in paper
    assert "删除3.7C-31%-5.9C极端策略后，没有解释模型优于常数基线" in paper
    assert "独立显著效应" in paper
    assert "因果效应量" in paper
    print("Q2 merged robustness tests passed")


if __name__ == "__main__":
    main()
