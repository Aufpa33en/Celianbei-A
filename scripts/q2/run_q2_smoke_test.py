"""Run Question 2 design audit and candidate-model smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models import run_smoke_test  # noqa: E402


def main() -> None:
    outputs = run_smoke_test(PROJECT_ROOT)
    audit = outputs["design_audit"]
    equal_time = audit[audit["equal_time_cohort"].eq(1)]
    print("[Q2] design audit")
    print(
        f"complete parameterized policies={len(audit)}, unique coordinates={audit['coordinate_id'].nunique()}"
    )
    print(
        f"non-baseline equal-T0 policies={len(equal_time)}, unique coordinates={equal_time['coordinate_id'].nunique()}, "
        f"T0 range={equal_time['T0'].min():.4f}-{equal_time['T0'].max():.4f} min"
    )
    print(
        f"observed mean charge-time range={equal_time['mean_chargetime'].min():.4f}-"
        f"{equal_time['mean_chargetime'].max():.4f} min"
    )
    selection = outputs["model_selection"]
    print("\n[Q2] smoke model selection")
    print(selection.to_string(index=False))
    selected = selection.loc[selection["selected_explanatory_smoke_model"], "model"].iloc[0]
    benchmark = selection.loc[selection["best_predictive_benchmark"], "model"].iloc[0]
    print(f"\n[Q2] selected explanatory smoke model: {selected}")
    print(f"[Q2] best predictive benchmark: {benchmark}")
    print(f"[Q2] authoritative smoke outputs: {PROJECT_ROOT / 'result' / 'q2'}")


if __name__ == "__main__":
    main()
