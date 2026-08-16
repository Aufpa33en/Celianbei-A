"""Integrity checks for authoritative Q1 lifetime-family sensitivity outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    paper = ROOT / "result" / "q1" / "paper"
    raw = ROOT / "result" / "q1" / "raw"
    validation = pd.read_csv(paper / "lifetime_family_validation_summary.csv")
    assert set(validation["Family"]) == {"linear", "power", "exponential"}
    selected = validation.loc[validation["SelectedFamily"].astype(bool)]
    assert len(selected) == 1 and selected.iloc[0]["Family"] == "linear"

    battery = pd.read_csv(raw / "lifetime_family_battery_t80.csv")
    strategy = pd.read_csv(paper / "lifetime_family_strategy_t80.csv")
    assert len(battery) == 49 * 3 and battery["BatteryId"].nunique() == 49
    assert battery.groupby("BatteryId")["Family"].nunique().eq(3).all()
    assert len(strategy) == 9 * 3 and strategy["Policy"].nunique() == 9

    main_t80 = pd.read_csv(raw / "battery_lifetime_estimates.csv")
    linear = battery.loc[battery["Family"].eq("linear"), ["BatteryId", "EstimatedT80"]]
    matched = main_t80[["BatteryId", "EstimatedT80"]].merge(
        linear, on="BatteryId", suffixes=("_main", "_family"), validate="one_to_one"
    )
    assert np.allclose(
        matched["EstimatedT80_main"], matched["EstimatedT80_family"], rtol=0.0, atol=1e-10
    )

    for name, ratio in (
        ("lifetime_family_battery_envelope.csv", "ModelFamilyT80Ratio"),
        ("lifetime_family_strategy_envelope.csv", "ModelFamilyMedianT80Ratio"),
    ):
        envelope = pd.read_csv(paper / name)
        assert np.isfinite(envelope[ratio]).all() and envelope[ratio].ge(1.0).all()
    assert (paper / "fig_q1_lifetime_family_comparison.png").stat().st_size > 100_000
    assert (paper / "fig_q1_lifetime_family_strategy_mapping.csv").is_file()
    report = (paper / "report.md").read_text(encoding="utf-8")
    assert "模型形式敏感性，不是置信区间" in report
    assert "主bootstrap区间条件于已选局部线性族" in report
    print("Q1 authoritative lifetime-family tests passed")


if __name__ == "__main__":
    main()
