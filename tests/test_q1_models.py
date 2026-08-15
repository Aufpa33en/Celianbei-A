"""Synthetic and real-data smoke tests for the Q1 Python models."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q1_models.core import MODEL_TYPES, ModelConfig, candidate_configs, fit_population_model  # noqa: E402
from q1_models.experiments import load_clean_data  # noqa: E402
from q1_models.inference import _exact_permutation_p_value, _run_candidate_on_data  # noqa: E402
from q1_models.lifetime import (  # noqa: E402
    LifetimeSettings,
    bootstrap_strategy_lifetimes,
    estimate_battery_lifetimes,
    validate_lifetime_windows,
)


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
    polynomial_grid = candidate_configs("polynomial_mixed")
    functional_grid = candidate_configs("functional_ridge")
    assert min(config.lambda_random for config in polynomial_grid) == 0.001
    assert max(config.lambda_random for config in polynomial_grid) == 1000.0
    assert min(config.lambda_curve for config in functional_grid) == 0.0
    assert any(config.lambda_curve == 0.000001 for config in functional_grid)

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

    small = synthetic_data()
    small_batteries = pd.DataFrame(
        {
            "battery_id": small["battery_id"].drop_duplicates(),
            "policy": small.drop_duplicates("battery_id")["policy"].to_numpy(),
            "mean_chargetime": 10.0,
        }
    )
    nested = _run_candidate_on_data(small, small_batteries, "functional_ridge", 20260814)
    assert len(nested.lobo) == small["battery_id"].nunique()
    assert nested.lobo["InnerValidationNBattery"].lt(len(nested.lobo)).all()
    assert nested.lobo["InnerSelectedLambdaCurve"].notna().all()

    lifetime_rows = []
    for battery_id, frame in small.groupby("battery_id", sort=False):
        policy = frame["policy"].iloc[0]
        for cycle in range(101, 201):
            x = cycle / 200
            loss = {"long": 0.020, "middle": 0.035, "short": 0.055}[policy]
            lifetime_rows.append((battery_id, cycle, policy, 1 - loss * x - 0.006 * x**2))
    lifetime_data = pd.concat(
        [small, pd.DataFrame(lifetime_rows, columns=small.columns)], ignore_index=True
    ).sort_values(["battery_id", "cycle"])
    lifetime_settings = LifetimeSettings(candidate_windows=(30, 40, 50))
    _, validation_summary, selected_window = validate_lifetime_windows(
        lifetime_data, lifetime_settings
    )
    assert selected_window in lifetime_settings.candidate_windows
    assert validation_summary["Selected"].sum() == 1
    lifetimes = estimate_battery_lifetimes(lifetime_data, selected_window, lifetime_settings)
    assert lifetimes["EstimatedT80"].notna().all()
    policy_lifetime, lifetime_rank = bootstrap_strategy_lifetimes(
        lifetimes, repetitions=200, seed=20260814
    )
    ordered = policy_lifetime.set_index("Policy")["MedianEstimatedT80"]
    assert ordered["long"] > ordered["middle"] > ordered["short"]
    assert lifetime_rank.set_index("Policy").loc["long", "PointT80Rank"] == 1

    pairwise_path = ROOT / "result" / "q1" / "raw" / "pairwise_strategy_scalar_comparison.csv"
    if pairwise_path.exists():
        pairwise = pd.read_csv(pairwise_path)
        expected = (pairwise["CI95Low"] > 0) | (pairwise["CI95High"] < 0)
        assert "BootstrapCIExcludesZero" in pairwise.columns
        assert pairwise["BootstrapCIExcludesZero"].astype(bool).equals(expected)
        soh200 = pairwise.loc[pairwise["Metric"] == "SOH200"]
        assert not soh200["SignificantAfterHolm"].astype(bool).any()
        assert soh200["BootstrapCIExcludesZero"].astype(bool).any()
        selection = pd.read_csv(ROOT / "result" / "q1" / "raw" / "selection_pipeline_lobo_by_battery.csv")
        assert selection["BatteryId"].nunique() == 40
        assert selection["SelectedModel"].eq("functional_ridge").all()
        assert selection["InnerValidationNBattery"].isin([38, 39]).all()
        lifetime_summary = pd.read_csv(
            ROOT / "result" / "q1" / "raw" / "lifetime_window_validation_summary.csv"
        )
        assert lifetime_summary.loc[lifetime_summary["Selected"].astype(bool), "Window"].tolist() == [40]
        battery_lifetime = pd.read_csv(
            ROOT / "result" / "q1" / "raw" / "battery_lifetime_estimates.csv"
        )
        assert len(battery_lifetime) == 49
        assert battery_lifetime["LifetimePrefixCycle"].eq(150).all()
        assert battery_lifetime["EstimatedT80"].notna().all()
    print("Q1 model tests passed")


if __name__ == "__main__":
    main()
