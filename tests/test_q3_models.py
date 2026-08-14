"""Boundary, leakage, and numerical tests for Q3 models."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models.config import CONFIG  # noqa: E402
from q3_models.core import (  # noqa: E402
    fit_power_law,
    load_records,
    power_law_eol,
    project_absolute_prediction,
    robust_slope_scale,
)
from q3_models.features import PrefixFeatureTransformer, prefix_numeric_features  # noqa: E402
from q3_models.models import (  # noqa: E402
    predict_strategy_transfer,
    predict_trajectory_ridge,
)


def main() -> None:
    # Known power law: fitted trajectory must retain the decline direction and finite EOL.
    cycles = np.arange(1, 201, dtype=float)
    synthetic = 1.01 - 2.5e-5 * cycles**1.35
    fit = fit_power_law(cycles[:150], synthetic[:150])
    assert fit["a"] > 0 and fit["p"] > 0
    t80, status = power_law_eol(fit, baseline=1.0)
    assert status == "finite_scenario" and 150 < t80 <= CONFIG.eol_max_cycle

    # Constant slopes must not cause division by zero.
    assert robust_slope_scale([0.0, 0.0, 0.0]) == 1e-8

    # Projection must respect the observed anchor and be monotone.
    projected = project_absolute_prediction(np.array([1.01, 1.00, 1.005, 0.99]), anchor=1.0)
    assert projected[0] <= 1.0 and np.all(np.diff(projected) <= 1e-15)

    records, meta, _ = load_records(PROJECT_ROOT)
    complete_ids = meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int).tolist()
    training = [records[i] for i in complete_ids if i not in CONFIG.smoke_battery_ids]
    target = records[CONFIG.smoke_battery_ids[0]]

    # Missing C1 is handled by fold-local imputation; rank-deficient K is clipped.
    transformer = PrefixFeatureTransformer.fit(training, 50)
    transformed = transformer.transform([records[4]], 50)
    assert np.isfinite(transformed).all()
    ridge_pred = predict_trajectory_ridge(training[:3], target, 50, (5, 1.0))
    assert ridge_pred.shape == (50,) and np.isfinite(ridge_pred).all()

    # No same-policy fallback must still produce a finite strategy prediction.
    foreign_training = [record for record in training if record.policy != target.policy]
    transfer_pred, gamma = predict_strategy_transfer(foreign_training, target, 50, 1.0)
    assert transfer_pred.shape == (50,) and np.isfinite(transfer_pred).all() and 0 <= gamma <= 3

    # Prefix invariance: changing target future cannot change features or fixed-model predictions.
    altered_cycles = target.cycles.copy()
    altered_cycles.loc[altered_cycles["cycle"].gt(50), ["SOH_clean", "IR_clean", "Tavg_raw", "chargetime_raw"]] = 9.0
    altered_relative = target.relative_soh.copy()
    altered_relative[50:] = 9.0
    altered = replace(target, cycles=altered_cycles, relative_soh=altered_relative)
    assert np.allclose(prefix_numeric_features(target, 50), prefix_numeric_features(altered, 50), equal_nan=True)
    b1, _ = predict_strategy_transfer(training, target, 50, 1.0)
    b2, _ = predict_strategy_transfer(training, altered, 50, 1.0)
    c1 = predict_trajectory_ridge(training, target, 50, (2, 1.0))
    c2 = predict_trajectory_ridge(training, altered, 50, (2, 1.0))
    assert np.allclose(b1, b2) and np.allclose(c1, c2)
    print("Q3 model boundary and leakage tests passed")


if __name__ == "__main__":
    main()
