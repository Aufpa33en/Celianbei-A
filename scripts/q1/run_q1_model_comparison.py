"""Run all Question 1 candidates and select the best by battery-level CV."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q1_models.core import MODEL_TYPES  # noqa: E402
from q1_models.experiments import run_candidate  # noqa: E402
from q1_models.outputs import compare_and_write  # noqa: E402


def main() -> None:
    seed = 20260814
    results = []
    for model_type in MODEL_TYPES:
        print(f"[Q1] running {model_type}...", flush=True)
        results.append(run_candidate(PROJECT_ROOT, model_type, seed=seed, write_files=True))
    comparison = compare_and_write(PROJECT_ROOT, results, seed=seed)
    print("\n[Q1] model comparison")
    print(comparison.to_string(index=False))
    selected = comparison.loc[comparison["Selected"], "Model"].iloc[0]
    print(f"\n[Q1] selected model: {selected}")
    print(f"[Q1] authoritative output: {PROJECT_ROOT / 'outputs' / 'summary' / 'q1_models'}")


if __name__ == "__main__":
    main()
