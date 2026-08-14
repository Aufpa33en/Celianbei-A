"""Integrity checks for generated Q3 smoke outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = PROJECT_ROOT / "result" / "q3" / "01_smoke_test"
    required = {
        "predictions_long.csv",
        "battery_metrics.csv",
        "model_summary.csv",
        "runtime.csv",
        "selection_decision.csv",
        "manifest.csv",
        "smoke_report.md",
    }
    assert required == {path.name for path in output.iterdir() if path.is_file()}
    pred = pd.read_csv(output / "predictions_long.csv")
    assert pred["battery_id"].nunique() == 9
    assert set(pred["L"]) == {50, 100, 150}
    assert pred["model"].nunique() == 6
    assert pred.groupby(["model", "L", "battery_id"])["cycle"].nunique().eq(50).all()
    decision = pd.read_csv(output / "selection_decision.csv")
    assert decision["final_model_selected"].eq(False).all()
    assert decision["selection_variant"].eq("raw").all()
    assert decision.loc[decision["engineering_pass"], "must_enter_full_validation"].all()
    print("Q3 smoke output integrity tests passed")


if __name__ == "__main__":
    main()
