"""Checks for the merged Q2 robustness analysis."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.merged_robustness import run_merged_robustness  # noqa: E402


def main() -> None:
    outputs = run_merged_robustness(PROJECT_ROOT, repetitions=200, seed=20260814)
    battery = outputs["battery_late_rate"]
    strategy = outputs["strategy_late_rate"]
    sensitivity = outputs["jh_coordinate_sensitivity"]
    assert len(battery) == 40
    assert battery["policy"].nunique() == 9
    assert battery["late_degradation_rate"].gt(0).all()
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
    matched = outputs["matched_4p8_comparison"].iloc[0]
    assert matched["relative_change"] < -0.7
    assert matched["causal_status"].startswith("not_identified")
    q1_pairwise = pd.read_csv(
        PROJECT_ROOT / "result" / "q1" / "raw" / "pairwise_strategy_scalar_comparison.csv"
    )
    q1_soh200 = q1_pairwise[q1_pairwise["Metric"].eq("SOH200")]
    assert not q1_soh200["SignificantAfterHolm"].astype(bool).any()
    paper = (
        PROJECT_ROOT / "result" / "q2" / "04_paper_materials" / "第二问完整回答.md"
    ).read_text(encoding="utf-8")
    assert "16 组经 Holm" not in paper
    assert "p=0.06528" in paper
    assert "p=0.000050" in paper
    assert "37.4% SOC换向阈值" in paper
    print("Q2 merged robustness tests passed")


if __name__ == "__main__":
    main()
