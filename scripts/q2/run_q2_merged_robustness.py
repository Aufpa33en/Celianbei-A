#!/usr/bin/env python3
"""Run the merged Q2 robustness analysis."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.merged_robustness import run_merged_robustness, write_merged_robustness  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--permutations", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260814)
    args = parser.parse_args()
    outputs = run_merged_robustness(PROJECT_ROOT, args.permutations, args.seed)
    write_merged_robustness(PROJECT_ROOT, outputs)
    print("Merged Q2 robustness analysis complete")


if __name__ == "__main__":
    main()
