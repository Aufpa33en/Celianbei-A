"""Tests for the T80-primary Question 2 validation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q2_models.lifetime_validation import (  # noqa: E402
    LifetimeValidationSettings,
    evaluate_exposure_models,
    run_lifetime_validation,
)


def main() -> None:
    stress = np.linspace(1.0, 2.0, 6)
    synthetic = pd.DataFrame(
        {
            "policy": [f"P{i}" for i in range(6)],
            "explicit_new_structure_cohort": True,
            "mean_log_t80": 9.0 - 0.8 * stress,
            "J": stress,
            "H": stress[::-1],
            "J_high_50": stress,
            "J_high_60": stress,
            "J_high_70": stress,
        }
    )
    _, metrics = evaluate_exposure_models(synthetic)
    selected = metrics.loc[metrics["selected_primary_explanatory"]]
    assert len(selected) == 1
    assert selected.iloc[0]["expected_negative_direction"]
    assert selected.iloc[0]["relative_rmse_improvement_vs_constant"] > 0

    outputs = run_lifetime_validation(
        ROOT, LifetimeValidationSettings(bootstrap_repetitions=50, seed=20260815)
    )
    battery = outputs["lifetime_battery_design"]
    strategy = outputs["lifetime_strategy_design"]
    assert len(battery) == 49
    assert battery["EstimatedT80"].notna().all()
    assert strategy["n_batteries"].sum() == 46
    assert strategy["lifetime_tail_window"].eq(40).all()
    assert outputs["lifetime_permutation_diagnostic"]["n_exact_permutations"].iloc[0] == 720
    print("Q2 lifetime validation tests passed")


if __name__ == "__main__":
    main()
