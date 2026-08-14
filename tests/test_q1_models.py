"""Synthetic and real-data smoke tests for the Q1 Python models."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q1_models.core import MODEL_TYPES, ModelConfig, fit_population_model  # noqa: E402
from q1_models.experiments import load_clean_data  # noqa: E402
from q1_models.inference import _exact_permutation_p_value  # noqa: E402


def synthetic_data() -> pd.DataFrame:
    rng = np.random.default_rng(20260814)
    rows = []
    policy_loss = {"long": 0.020, "middle": 0.035, "short": 0.055}
    battery = 0
    for policy, loss in policy_loss.items():
        for _ in range(4):
            battery += 1
            random_intercept = rng.normal(0, 0.0015)
            random_slope = rng.normal(0, 0.002)
            for cycle in range(1, 101):
                x = cycle / 200
                soh = 1 + random_intercept - (loss + random_slope) * x - 0.006 * x**2
                soh += rng.normal(0, 0.0005)
                rows.append((battery, cycle, policy, soh))
    return pd.DataFrame(rows, columns=["battery_id", "cycle", "policy", "SOH_clean"])


def main() -> None:
    data = synthetic_data()
    configs = {
        "polynomial_mixed": ModelConfig(0.1, 0),
        "spline_mixed": ModelConfig(0.3, 0.1),
        "functional_ridge": ModelConfig(0, 0.1),
    }
    for model_type in MODEL_TYPES:
        model = fit_population_model(data, model_type, configs[model_type])
        prediction = {name: model.predict(name, [100])[0] for name in ("long", "middle", "short")}
        assert prediction["long"] > prediction["middle"] > prediction["short"], (model_type, prediction)
        assert all(0.9 < value < 1.02 for value in prediction.values())

    separated_p = _exact_permutation_p_value(
        np.array([0.99, 0.991, 0.992, 0.993]),
        np.array([0.95, 0.951, 0.952, 0.953]),
    )
    assert np.isclose(separated_p, 2 / 70), separated_p
    tied_p = _exact_permutation_p_value(np.array([1.0, 1.0]), np.array([1.0, 1.0]))
    assert tied_p == 1.0, tied_p

    cycles, _ = load_clean_data(ROOT)
    assert len(cycles) == 9350
    assert cycles["battery_id"].nunique() == 49
    assert cycles["policy"].nunique() == 9
    print("Q1 model tests passed")


if __name__ == "__main__":
    main()
