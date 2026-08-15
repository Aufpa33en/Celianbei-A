from pathlib import Path

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
    constraints = pd.read_csv(target / "constraint_selection_frequency.csv")
    assert len(constraints) == 40
    assert constraints.groupby("loss_limit")["selection_frequency"].sum().round(12).eq(1.0).all()
    sensitivity = pd.read_csv(target / "time_model_sensitivity.csv")
    cycle_front = set(sensitivity.loc[sensitivity["pareto_cycle_time"].astype(bool), "policy"])
    summary_front = set(sensitivity.loc[sensitivity["pareto_summary_time"].astype(bool), "policy"])
    assert cycle_front == summary_front
    uncertainty = pd.read_csv(target / "policy_uncertainty.csv")
    assert uncertainty["interval_type"].eq("strategy_mean_whole_battery_bootstrap").all()
    manifest = pd.read_csv(target / "manifest.csv")
    assert "run_config.json" in set(manifest["path"])


if __name__ == "__main__":
    test_q4_full_validation_protocol()
    print("Q4 full validation protocol tests passed")
