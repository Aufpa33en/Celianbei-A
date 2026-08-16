"""Run the supporting Q4 time-versus-predicted-T80 Pareto analysis."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from q4_models.t80_outputs import write_t80_sensitivity_outputs  # noqa: E402
from q4_models.t80_sensitivity import run_t80_pareto_sensitivity  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260816)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "result" / "q4" / "03_t80_pareto_sensitivity",
    )
    args = parser.parse_args()
    started = time.perf_counter()
    tables = run_t80_pareto_sensitivity(ROOT, args.bootstrap, args.seed)
    tables["runtime"] = pd.DataFrame(
        [
            {
                "stage": "q4_t80_pareto_sensitivity",
                "bootstrap_repetitions": args.bootstrap,
                "seed": args.seed,
                "runtime_seconds": time.perf_counter() - started,
            }
        ]
    )
    write_t80_sensitivity_outputs(tables, args.output_dir.resolve())
    print(f"Q4 T80 Pareto sensitivity complete: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
