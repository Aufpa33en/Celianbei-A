"""Lightweight integrity tests for Question 2 smoke-test outputs."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.core import add_protocol_features, load_clean_data  # noqa: E402


def main() -> None:
    sample = pd.DataFrame(
        {
            "policy": ["test"],
            "C1": [4.8],
            "Q1": [80.0],
            "C2": [4.8],
        }
    )
    featured = add_protocol_features(sample)
    assert np.isclose(featured.loc[0, "T0"], 10.0)
    assert np.isclose(featured.loc[0, "E2"], 0.0)
    assert np.isclose(featured.loc[0, "J_high_70"], 0.48)

    cycles, summary = load_clean_data(PROJECT_ROOT)
    assert cycles["battery_id"].nunique() == 40
    assert len(summary) == 40
    assert cycles.groupby("battery_id")["cycle"].nunique().eq(200).all()

    audit = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "00_design" / "design_audit.csv")
    assert len(audit) == 8
    assert audit["coordinate_id"].nunique() == 7
    assert audit["equal_time_cohort"].sum() == 7
    assert audit.loc[audit["equal_time_cohort"].eq(1), "coordinate_id"].nunique() == 6
    assert audit["explicit_new_structure_cohort"].sum() == 6
    assert audit.loc[audit["explicit_new_structure_cohort"].eq(1), "coordinate_id"].nunique() == 6

    selection = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "02_model_selection" / "smoke_model_selection.csv")
    assert selection["selected_explanatory_smoke_model"].sum() == 1
    assert selection["best_predictive_benchmark"].sum() == 1
    manifest = pd.read_csv(PROJECT_ROOT / "result" / "q2" / "result_manifest.csv")
    assert len(manifest) == 12
    print("Q2 smoke tests passed")


if __name__ == "__main__":
    main()
