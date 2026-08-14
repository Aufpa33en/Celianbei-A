"""Pre-run and post-run checks for the additive Q3 full protocol."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models.config import CONFIG  # noqa: E402
from q3_models.core import complete_battery_ids, load_records  # noqa: E402
from q3_models.full_validation import (  # noqa: E402
    _choose_ensemble_weight,
    protected_file_hashes,
    validate_record_shapes,
)


def main() -> None:
    records, meta, _ = load_records(PROJECT_ROOT)
    shapes = validate_record_shapes(records, meta)
    assert len(shapes) == 49 and shapes["continuous_unique_cycles"].all()
    complete = [records[battery_id] for battery_id in complete_battery_ids(meta)]
    assert len(complete) == 40
    test_ids = set(meta.loc[meta["prediction_test"].eq(1), "battery_id"].astype(int))
    assert test_ids == {2, 5, 9, 10, 11, 14, 16, 24, 25}
    assert all(len(records[battery_id].relative_soh) == 150 for battery_id in test_ids)

    subset = complete[:4]
    identical = {record.battery_id: np.full(50, record.relative_at(150)) for record in subset}
    weight, _ = _choose_ensemble_weight(subset, identical, identical, CONFIG)
    assert weight == 1.0

    hashes = protected_file_hashes(PROJECT_ROOT)
    assert not hashes.empty and hashes["path"].is_unique

    full_dir = PROJECT_ROOT / "result" / "q3" / "02_full_validation"
    final_dir = PROJECT_ROOT / "result" / "q3" / "03_final_predictions"
    if full_dir.exists():
        pred = pd.read_csv(full_dir / "predictions_long.csv")
        assert len(pred) == 36000
        assert pred.groupby(["model", "L", "battery_id"])["cycle"].nunique().eq(50).all()
        assert pd.read_csv(full_dir / "integrity_checks.csv")["passed"].astype(bool).all()
    if final_dir.exists():
        pred = pd.read_csv(final_dir / "test_predictions_long.csv")
        assert len(pred) == 450 and pred["battery_id"].nunique() == 9
        assert "y_true" not in pred and set(pred["cycle"]) == set(range(151, 201))
        assert pd.read_csv(final_dir / "integrity_checks.csv")["passed"].astype(bool).all()
    print("Q3 full protocol tests passed")


if __name__ == "__main__":
    main()
