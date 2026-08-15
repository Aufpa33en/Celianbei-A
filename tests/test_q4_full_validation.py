from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_q4_full_validation_protocol() -> None:
    target = ROOT / "result" / "q4" / "02_full_validation"
    assert target.is_dir(), f"Missing authoritative Q4 result directory: {target}"
    checks = pd.read_csv(target / "integrity_checks.csv")
    assert checks["passed"].astype(bool).all()
    summary = pd.read_csv(target / "policy_summary.csv")
    assert len(summary) == 9
    assert int(summary["pareto"].astype(bool).sum()) == 3
    boot = pd.read_csv(target / "bootstrap_pareto.csv")
    assert len(boot) == 45000
    assert len([column for column in boot if column.startswith("selected_lambda_")]) == 11
    assert len([column for column in boot if column.startswith("selected_loss_limit_")]) == 4
    assert boot["late_slope_loss"].notna().all()
    assert boot.groupby("replicate").size().eq(9).all()
    lambda_columns = [column for column in boot if column.startswith("selected_lambda_")]
    assert boot.groupby("replicate")[lambda_columns].sum().eq(1).all().all()
    frequency = pd.read_csv(target / "selection_frequency.csv")
    assert set(frequency["policy"]) == set(summary["policy"])
    recommendations = pd.read_csv(target / "recommendations.csv")
    weighted = recommendations.loc[
        recommendations["rule"].eq("weighted_minmax_all_policies_diagnostic")
    ]
    assert len(weighted) == 11
    assert weighted["pareto"].astype(bool).all()
    assert weighted["decision_role"].eq(
        "diagnostic_weight_sensitivity_not_primary_recommendation"
    ).all()
    assert weighted["normalization_method"].eq("minmax").all()
    assert weighted["normalization_scope"].eq(
        "all_9_observed_policies_including_dominated"
    ).all()
    assert weighted["normalization_n_policies"].eq(9).all()
    constraints = pd.read_csv(target / "constraint_selection_frequency.csv")
    assert len(constraints) == 40
    assert constraints.groupby("loss_limit")["selection_frequency"].sum().round(12).eq(1.0).all()
    sensitivity = pd.read_csv(target / "time_model_sensitivity.csv")
    assert sensitivity["primary_equals_summary"].astype(bool).all()
    assert summary.set_index("policy")["time_mean"].sort_index().equals(
        sensitivity.set_index("policy")["summary_time_mean"].sort_index()
    )
    cycle_front = set(sensitivity.loc[sensitivity["pareto_cycle_time"].astype(bool), "policy"])
    primary_front = set(sensitivity.loc[sensitivity["pareto_primary_time"].astype(bool), "policy"])
    assert cycle_front == primary_front
    uncertainty = pd.read_csv(target / "policy_uncertainty.csv")
    assert uncertainty["interval_type"].eq("strategy_mean_whole_battery_bootstrap").all()
    scaling = pd.read_csv(target / "scaling_sensitivity.csv")
    at_point_one = scaling.loc[np.isclose(scaling["lambda"], 0.1)].set_index("scaling")["policy"]
    assert at_point_one["all_policy_minmax"] != at_point_one["pareto_minmax"]
    fast_pair = pd.read_csv(target / "fast_pair_comparison.csv")
    assert len(fast_pair) == 2
    assert fast_pair["point_pareto"].astype(bool).sum() == 1
    assert fast_pair.loc[fast_pair["point_pareto"].astype(bool), "decision_status"].eq(
        "point_pareto_fast_tradeoff_recommendation"
    ).all()
    assert fast_pair.loc[~fast_pair["point_pareto"].astype(bool), "decision_status"].eq(
        "uncertainty_near_tie_nonpareto_sensitivity"
    ).all()
    assert fast_pair["probability_lower_loss_than_pair"].max() < 0.95
    assert fast_pair["probability_not_slower_by_more_than_0_01_min"].max() < 0.95
    assert (fast_pair["pair_loss_difference_first_minus_second_p025"] < 0).all()
    assert (fast_pair["pair_loss_difference_first_minus_second_p975"] > 0).all()
    m1 = pd.read_csv(target / "m1_coordinate_loso.csv")
    assert m1["worst_fold"].astype(bool).sum() == 1
    assert np.isclose(m1["squared_error_share"].sum(), 1.0)
    worst = m1.loc[m1["worst_fold"].astype(bool)].iloc[0]
    assert bool(worst["outside_train_exposure_range"])
    assert bool(worst["prediction_below_zero"])
    remaining = m1.loc[~m1["worst_fold"].astype(bool)]
    assert remaining["rmse"].mean() > remaining["constant_rmse"].mean()
    concentration_check = checks.loc[checks["check"].eq("m1_failure_concentration_exposed")].iloc[0]
    assert "excluding worst M1 RMSE=" in concentration_check["detail"]
    assert " > baseline=" in concentration_check["detail"]
    assert fast_pair["q3_role"].eq("not_used_no_early_trajectory_for_new_policy").all()
    manifest = pd.read_csv(target / "manifest.csv")
    assert "run_config.json" in set(manifest["path"])


if __name__ == "__main__":
    test_q4_full_validation_protocol()
    print("Q4 full validation protocol tests passed")
