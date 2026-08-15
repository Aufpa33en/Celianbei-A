"""Run optimized formal validation for Question 2."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.formal_validation import run_formal_validation  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    outputs = run_formal_validation(
        PROJECT_ROOT,
        n_bootstrap=args.bootstrap,
        seed=args.seed,
        workers=args.workers,
    )
    frequency = outputs["bootstrap_selection_frequency"]
    permutation = outputs["permutation_test_summary"]
    decision = outputs["formal_model_decision"]["decision"].iloc[0]
    print("[Q2 formal] bootstrap selection frequency")
    print(frequency.to_string(index=False))
    print("\n[Q2 formal] hypothetical policy-mean exchangeability diagnostic (not a confirmatory test)")
    print(permutation.to_string(index=False))
    print(f"\n[Q2 formal] decision: {decision}")
    print(f"[Q2 formal] output: {PROJECT_ROOT / 'result' / 'q2' / '03_formal_validation'}")


if __name__ == "__main__":
    main()
