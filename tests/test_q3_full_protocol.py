"""Pre-run and post-run checks for the additive Q3 full protocol."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models.config import CONFIG  # noqa: E402
from q3_models.core import complete_battery_ids, load_records  # noqa: E402
from q3_models.full_validation import (  # noqa: E402
    _choose_ensemble_weight,
    protected_file_hashes,
    validate_record_shapes,
)


def main() -> None:
    records, meta, _ = load_records(PROJECT_ROOT)
    for battery_id, record in records.items():
        expected = float(meta.loc[meta["battery_id"].eq(battery_id), "baseline_soh_cycles_1_5"].iloc[0])
        assert abs(record.baseline - expected) < 1e-12
        assert np.allclose(record.relative_soh, record.cycles["SOH_relative_clean"], rtol=0.0, atol=1e-12)
    shapes = validate_record_shapes(records, meta)
    assert len(shapes) == 49 and shapes["continuous_unique_cycles"].all()
    complete = [records[battery_id] for battery_id in complete_battery_ids(meta)]
    assert len(complete) == 40
    test_ids = set(meta.loc[meta["prediction_test"].eq(1), "battery_id"].astype(int))
    assert test_ids == {2, 5, 9, 10, 11, 14, 16, 24, 25}
    assert all(len(records[battery_id].relative_soh) == 150 for battery_id in test_ids)

    subset = complete[:4]
    identical = {record.battery_id: np.full(50, record.relative_at(150)) for record in subset}
    weight, _ = _choose_ensemble_weight(subset, identical, identical, CONFIG)
    assert weight == 1.0

    hashes = protected_file_hashes(PROJECT_ROOT)
    assert not hashes.empty and hashes["path"].is_unique

    full_dir = PROJECT_ROOT / "result" / "q3" / "02_full_validation"
    final_dir = PROJECT_ROOT / "result" / "q3" / "03_final_predictions"
    assert full_dir.is_dir(), f"Missing authoritative Q3 result directory: {full_dir}"
    assert final_dir.is_dir(), f"Missing authoritative Q3 result directory: {final_dir}"
    pred = pd.read_csv(full_dir / "predictions_long.csv")
    assert len(pred) == 36000
    assert pred.groupby(["model", "L", "battery_id"])["cycle"].nunique().eq(50).all()
    assert pd.read_csv(full_dir / "integrity_checks.csv")["passed"].astype(bool).all()
    selection = pd.read_csv(full_dir / "selection_decision.csv")
    assert selection["decision_role"].eq("multi_length_robustness_sensitivity_not_deployment").all()
    deployment = pd.read_csv(full_dir / "deployment_candidate_comparison.csv")
    selected = deployment.loc[deployment["selected_for_L150_deployment"].astype(bool)]
    assert len(selected) == 1
    assert deployment["selection_scope"].eq("L150_only_matches_final_prediction_information").all()
    freeze = pd.read_csv(full_dir / "deployment_freeze.csv").iloc[0]
    assert freeze["selected_model"] == selected.iloc[0]["model"]
    pred = pd.read_csv(final_dir / "test_predictions_long.csv")
    assert len(pred) == 450 and pred["battery_id"].nunique() == 9
    assert "y_true" not in pred and set(pred["cycle"]) == set(range(151, 201))
    summary = pd.read_csv(final_dir / "test_battery_summary.csv")
    assert "scenario_T80_default" not in summary.columns
    assert {
        "stitched_power_scenario_T80_start1", "stitched_power_scenario_status",
        "deployed_linear_native_T80", "deployed_linear_native_status",
    }.issubset(summary.columns)
    assert summary["deployed_linear_native_status"].eq("beyond_5000").any()
    calibration = pd.read_csv(final_dir / "prediction_interval_calibration.csv")
    assert calibration["target_marginal_coverage"].eq(0.95).all()
    assert calibration["order_statistic_rank"].eq(39).all()
    assert calibration["empirical_order_level"].eq(0.975).all()
    assert calibration["calibration_reuses_model_selection_residuals"].astype(bool).all()
    assert calibration["interval_status"].eq(
        "post_selection_diagnostic_not_independent_coverage"
    ).all()
    settings = pd.read_csv(final_dir / "final_model_settings.csv")
    assert settings.loc[settings["parameter"].eq("P1_linear_trend_window"), "value"].eq("50").all()
    assert settings.loc[settings["parameter"].eq("P1_linear_trend_window"), "parameter_role"].eq(
        "used_by_selected_model"
    ).all()
    assert not {"lambda_gamma", "K", "alpha", "w_strategy"}.intersection(settings["parameter"])
    assert settings.loc[
        settings["parameter_role"].eq("frozen_nonselected_candidate"), "parameter"
    ].str.match(r"^[BCD]_").all()
    assert pd.read_csv(final_dir / "integrity_checks.csv")["passed"].astype(bool).all()
    for directory in (full_dir, final_dir):
        manifest = pd.read_csv(directory / "manifest.csv")
        assert "git_head_at_manifest_generation" in manifest.columns
        assert "git_commit_at_run" not in manifest.columns
    print("Q3 full protocol tests passed")


if __name__ == "__main__":
    main()
