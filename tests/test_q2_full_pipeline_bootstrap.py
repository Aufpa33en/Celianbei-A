"""Equivalence and boundary tests for the Q2 full-pipeline bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from q2_models.full_pipeline_bootstrap import (  # noqa: E402
    FullPipelineBootstrapSettings,
    compare_backends,
    make_sample_plan,
    run_cached_full_pipeline_bootstrap,
    run_full_pipeline_lifetime_validation,
    run_naive_full_pipeline_bootstrap,
    summarize_full_pipeline_bootstrap,
)
from q2_models.lifetime_validation import prepare_lifetime_design  # noqa: E402
from q2_models.lifetime_validation import LifetimeValidationSettings  # noqa: E402


def main() -> None:
    battery, _, _ = prepare_lifetime_design(ROOT)
    settings = FullPipelineBootstrapSettings(repetitions=3, seed=20260816)
    plan = make_sample_plan(battery, settings)
    assert len(plan) == 3 * 49
    naive = run_naive_full_pipeline_bootstrap(ROOT, settings, plan)
    cached, runtime = run_cached_full_pipeline_bootstrap(ROOT, settings, plan)
    check = compare_backends(naive, cached)
    assert check.iloc[0]["decision_mismatch_count"] == 0
    assert check.iloc[0]["maximum_numeric_difference"] < 1e-10
    summary, window = summarize_full_pipeline_bootstrap(cached)
    assert len(summary) == 6 and window["count"].sum() == 3
    assert runtime.iloc[0]["repetitions"] == 3
    full = run_full_pipeline_lifetime_validation(
        ROOT, LifetimeValidationSettings(bootstrap_repetitions=3, seed=20260816)
    )
    assert "lifetime_fixed_t80_bootstrap_selection" in full
    assert len(full["lifetime_bootstrap_replicates"]) == 18
    assert full["lifetime_bootstrap_window_frequency"]["count"].sum() == 3
    print("Q2 full-pipeline bootstrap tests passed")


if __name__ == "__main__":
    main()
