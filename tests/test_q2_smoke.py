"""Lightweight integrity tests for Question 2 smoke-test outputs."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.core import add_protocol_features, battery_degradation_summary, load_clean_data  # noqa: E402
from q2_models.experiments import selection_table  # noqa: E402


def main() -> None:
    sample = pd.DataFrame(
        {
            "policy": ["test"],
            "C1": [4.8],
            "Q1": [80.0],
            "C2": [4.8],
        }
    )
    featured = add_protocol_features(sample)
    assert np.isclose(featured.loc[0, "T0"], 10.0)
    assert np.isclose(featured.loc[0, "E2"], 0.0)
    assert np.isclose(featured.loc[0, "J_high_70"], 0.48)

    cycles, summary = load_clean_data(PROJECT_ROOT)
    assert cycles["battery_id"].nunique() == 40
    assert len(summary) == 40
    assert cycles.groupby("battery_id")["cycle"].nunique().eq(200).all()
    battery = battery_degradation_summary(cycles, summary).set_index("battery_id")
    expected_baseline = summary.set_index("battery_id")["baseline_soh_cycles_1_5"]
    assert np.allclose(battery["baseline_soh"], expected_baseline, rtol=0.0, atol=1e-12)

    audit = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "00_design" / "design_audit.csv")
    assert len(audit) == 8
    assert audit["coordinate_id"].nunique() == 7
    assert audit["equal_time_cohort"].sum() == 7
    assert audit.loc[audit["equal_time_cohort"].eq(1), "coordinate_id"].nunique() == 6
    assert audit["explicit_new_structure_cohort"].sum() == 6
    assert audit.loc[audit["explicit_new_structure_cohort"].eq(1), "coordinate_id"].nunique() == 6

    selection = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "02_model_selection" / "smoke_model_selection.csv")
    assert selection["selected_explanatory_smoke_model"].sum() == 1
    assert selection["explanatory_selection_status"].eq("selected_eligible_explanatory_model").all()
    assert selection["best_predictive_benchmark"].sum() == 1
    scalar_metrics = pd.read_csv(
        PROJECT_ROOT / "result" / "q2" / "02_model_selection" / "scalar_model_comparison.csv"
    )
    scalar_metrics.loc[~scalar_metrics["model"].isin(["constant_mean", "nearest_coordinate"]),
                       "relative_rmse_improvement"] = -0.01
    no_eligible = selection_table(scalar_metrics, pd.DataFrame(), pd.DataFrame())
    assert not no_eligible["selected_explanatory_smoke_model"].any()
    assert no_eligible["explanatory_selection_status"].eq("no_eligible_explanatory_model").all()
    manifest = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "result_manifest.csv")
    required_paths = {
        f"result/q2/{folder}/{filename}"
        for folder, filename in (
            ("00_design", "design_audit.csv"),
            ("01_smoke_test", "battery_degradation_summary.csv"),
            ("01_smoke_test", "strategy_degradation_summary.csv"),
            ("01_smoke_test", "scalar_fold_predictions.csv"),
            ("01_smoke_test", "hierarchical_fold_predictions.csv"),
            ("02_model_selection", "scalar_model_comparison.csv"),
            ("02_model_selection", "coefficient_stability.csv"),
            ("02_model_selection", "hierarchical_model_comparison.csv"),
            ("02_model_selection", "hierarchical_diagnostics.csv"),
            ("02_model_selection", "smoke_model_selection.csv"),
            ("02_model_selection", "selected_model_fit.csv"),
            ("02_model_selection", "selected_model_predictions.csv"),
        )
    }
    assert not manifest["relative_path"].str.contains("\\", regex=False).any()
    assert required_paths.issubset(set(manifest["relative_path"]))
    print("Q2 smoke tests passed")


if __name__ == "__main__":
    main()
