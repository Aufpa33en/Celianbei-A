"""Correctness and integrity tests for optimized Q2 formal validation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.core import battery_degradation_summary, load_clean_data, strategy_summary  # noqa: E402
from q2_models.formal_validation import (  # noqa: E402
    _fit_full_feature,
    evaluate_exposure_models,
    make_cohort_arrays,
    run_bootstrap,
    sensitivity_table,
)


def main() -> None:
    cycles, meta = load_clean_data(PROJECT_ROOT)
    battery = battery_degradation_summary(cycles, meta)
    strategy = strategy_summary(battery)
    cohort = make_cohort_arrays(battery, strategy, "explicit_new_structure")

    # Optimized implementation must reproduce the original smoke metrics.
    new = sensitivity_table(battery, strategy)
    assert not new.loc[new["model"].eq("constant_mean"), "selected_explanatory"].astype(bool).any()
    assert new.groupby(["cohort", "exclude_battery41"])["selected_by_cv"].sum().eq(1).all()
    selected_constant = new["model"].eq("constant_mean") & new["selected_by_cv"].astype(bool)
    assert selected_constant.any()
    new = new[
        new["cohort"].eq("explicit_new_structure")
        & ~new["exclude_battery41"]
    ].set_index("model")
    old = pd.read_csv(
        PROJECT_ROOT / "result" / "q2" / "02_model_selection" / "scalar_model_comparison.csv"
    )
    old = old[old["cohort"].eq("explicit_new_structure")]
    for model in ("ridge_Jhigh50", "ridge_Jhigh60", "ridge_Jhigh70", "ridge_H"):
        for response, column in (("relative_loss200", "relative_loss_rmse"), ("soh200", "soh200_rmse")):
            reference = float(old[old["model"].eq(model) & old["response"].eq(response)]["rmse"].iloc[0])
            assert abs(float(new.loc[model, column]) - reference) < 1e-12

    # Deterministic seed streams must reproduce the first 20 stored replicates.
    temporary = PROJECT_ROOT / "tmp" / "q2_formal_test_checkpoint.csv"
    replay, _ = run_bootstrap(cohort, 20, 20260814, 1, temporary, chunk_size=10)
    stored = pd.read_csv(
        PROJECT_ROOT / "result" / "q2" / "03_formal_validation" / "bootstrap_replicates.csv"
    )
    stored = stored[stored["replicate"].lt(20)].sort_values(["replicate", "model"]).reset_index(drop=True)
    compare_columns = [
        "relative_loss_rmse", "soh200_rmse", "relative_loss_coef_standardized",
        "soh200_coef_standardized",
    ]
    assert np.allclose(replay[compare_columns], stored[compare_columns], rtol=0, atol=1e-14)
    temporary.unlink()

    # Synthetic directional signal must produce the expected coefficient signs.
    x = cohort.exposure[:, 2]
    z = (x - x.mean()) / x.std()
    synthetic = np.column_stack((0.01 + 0.004 * z, 0.99 - 0.006 * z))
    synthetic_result = evaluate_exposure_models(synthetic, cohort.exposure, cohort.groups)
    high70 = next(row for row in synthetic_result["models"] if row["model"] == "ridge_Jhigh70")
    assert high70["coef_standardized"][0] > 0
    assert high70["coef_standardized"][1] < 0
    assert np.all(high70["improvement"] > 0)

    # A constant feature is an explicit non-identifiability boundary.
    _, slope, _, _ = _fit_full_feature(np.ones(6), synthetic[:, 0], cohort.groups)
    assert abs(slope) < 1e-15

    output = PROJECT_ROOT / "result" / "q2" / "03_formal_validation"
    raw = pd.read_csv(output / "bootstrap_replicates.csv")
    permutation = pd.read_csv(output / "permutation_distribution.csv")
    permutation_summary = pd.read_csv(output / "permutation_test_summary.csv")
    decision = pd.read_csv(output / "formal_model_decision.csv")
    assert raw["replicate"].nunique() == 2000
    assert len(raw) == 8000
    assert len(permutation) == 720
    assert "exact_p_one_sided" not in permutation_summary
    assert not permutation_summary["confirmatory_p_value_available"].astype(bool).any()
    assert permutation_summary["artifact_role"].eq("diagnostic_not_confirmatory_test").all()
    assert decision["decision"].eq(
        "do_not_claim_independent_parameter_effect; descriptive_association_only"
    ).all()
    print("Q2 formal validation tests passed")


if __name__ == "__main__":
    main()
