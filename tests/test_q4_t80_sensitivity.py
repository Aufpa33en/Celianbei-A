"""Tests for Q4 predicted-T80 Pareto sensitivity."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q4_models.t80_sensitivity import run_t80_pareto_sensitivity  # noqa: E402


def main() -> None:
    tables = run_t80_pareto_sensitivity(ROOT, repetitions=20, seed=20260816)
    battery = tables["battery_t80_observations"]
    assert len(battery) == 120 and battery["BatteryId"].nunique() == 40
    summary = tables["policy_t80_pareto_summary"]
    assert len(summary) == 9 and summary["PointParetoTimeMaxT80"].astype(bool).any()
    boot = tables["t80_pareto_bootstrap"]
    assert len(boot) == 180 and boot.groupby("replicate").size().eq(9).all()
    family = tables["t80_pareto_model_family_sensitivity"]
    assert {"linear", "power", "exponential"}.issubset(family.columns)
    assert tables["early_proxy_t80_front_comparison"]["FrontAgreement"].isin([True, False]).all()
    print("Q4 T80 sensitivity tests passed")


if __name__ == "__main__":
    main()
