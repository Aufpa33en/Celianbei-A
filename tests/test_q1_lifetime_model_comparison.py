"""Tests for monotone Q1 lifetime-family comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q1_models.lifetime_candidates import LifetimeCandidate, candidate_t80, fit_candidate  # noqa: E402
from q1_models.lifetime_model_selection import compare_lifetime_families  # noqa: E402


def synthetic_cycles() -> pd.DataFrame:
    rows = []
    for battery_id in range(1, 7):
        policy = "a" if battery_id <= 3 else "b"
        rate = 0.00005 if policy == "a" else 0.00009
        for cycle in range(1, 201):
            rows.append(
                {
                    "battery_id": battery_id,
                    "cycle": cycle,
                    "policy": policy,
                    "SOH_clean": 1.0 - rate * cycle - 2e-7 * cycle**2,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    cycles = synthetic_cycles()
    candidate = LifetimeCandidate("power", 80, 2.0)
    intercept, coefficient = fit_candidate(cycles.loc[cycles["battery_id"].eq(1)], 150, candidate)
    t80, status = candidate_t80(intercept, coefficient, candidate)
    assert status == "finite_extrapolation" and t80 > 150

    candidates = (
        LifetimeCandidate("linear", 40, 1.0),
        LifetimeCandidate("power", 80, 1.0),
        LifetimeCandidate("power", 80, 2.0),
        LifetimeCandidate("exponential", 80, 0.005),
    )
    result = compare_lifetime_families(cycles, candidates)
    summary = result["nested_family_summary"]
    assert len(summary) == 3 and summary["SelectedFamily"].sum() == 1
    outer = result["nested_family_lobo_by_battery"]
    assert len(outer) == 18 and outer.groupby("Family")["OuterBatteryId"].nunique().eq(6).all()
    lifetimes = result["battery_t80_by_family"]
    assert len(lifetimes) == 18 and lifetimes["EstimatedT80"].notna().all()
    strategy = result["strategy_t80_by_family"]
    assert len(strategy) == 6 and strategy.groupby("Family")["RankWithinFamily"].nunique().eq(2).all()
    assert result["battery_t80_model_family_envelope"]["FiniteFamilyCount"].eq(3).all()
    print("Q1 lifetime model comparison tests passed")


if __name__ == "__main__":
    main()
