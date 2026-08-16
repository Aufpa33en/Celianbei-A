"""Tests for Q2 point sensitivity across frozen Q1 T80 model families."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q2_models.lifetime_family_sensitivity import (  # noqa: E402
    run_lifetime_family_sensitivity,
)


def main() -> None:
    tables = run_lifetime_family_sensitivity(ROOT)
    policy = tables["lifetime_family_policy_t80_summary"]
    design = tables["lifetime_family_strategy_design"]
    metrics = tables["lifetime_family_model_comparison"]
    summary = tables["lifetime_family_selection_summary"]
    assert len(policy) == 27 and policy.groupby("Family")["policy"].nunique().eq(9).all()
    assert len(design) == 24 and design.groupby("Family")["policy"].nunique().eq(8).all()
    assert design.groupby("Family")["explicit_new_structure_cohort"].sum().eq(6).all()
    assert len(metrics) == 18 and metrics.groupby("Family")["model"].nunique().eq(6).all()
    assert len(summary) == 3 and summary["SelectedModel"].eq("linear_J").all()
    assert summary["LinearJSlope"].lt(0).all()
    assert ~summary["HasCrossFamilyCI"].astype(bool).any()
    assert not any("ci95" in column.lower() for column in summary.columns)

    formal = ROOT / "result" / "q2" / "03_formal_validation"
    paper = ROOT / "result" / "q2" / "04_paper_materials" / "tables"
    if formal.is_dir():
        stored = pd.read_csv(formal / "lifetime_family_selection_summary.csv")
        assert len(stored) == 3 and stored["SelectedModel"].eq("linear_J").all()
        bootstrap = pd.read_csv(formal / "lifetime_bootstrap_selection.csv")
        assert bootstrap["bootstrap_repetitions"].eq(2000).all()
        linear = bootstrap.loc[bootstrap["model"].eq("linear_J")].iloc[0]
        assert linear["improvement_ci95_low"] < 0 < linear["improvement_ci95_high"]
        for name in (
            "lifetime_family_policy_t80_summary.csv",
            "lifetime_family_strategy_design.csv",
            "lifetime_family_model_comparison.csv",
            "lifetime_family_selection_summary.csv",
        ):
            assert (paper / name).is_file()
    print("Q2 lifetime-family sensitivity tests passed")


if __name__ == "__main__":
    main()
