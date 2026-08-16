"""Run the exploratory monotone T80 model-family comparison."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from q1_models.lifetime_model_outputs import write_lifetime_model_comparison  # noqa: E402
from q1_models.lifetime_model_selection import compare_lifetime_families  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "result" / "q1" / "02_lifetime_model_comparison",
    )
    parser.add_argument("--seed", type=int, default=20260816)
    args = parser.parse_args()
    cycles = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "cycle_train_clean.csv")
    started = time.perf_counter()
    tables = compare_lifetime_families(cycles)
    write_lifetime_model_comparison(
        tables, args.output_dir.resolve(), args.seed, time.perf_counter() - started
    )
    selected = tables["nested_family_summary"].loc[
        tables["nested_family_summary"]["SelectedFamily"].astype(bool)
    ].iloc[0]
    print(
        f"selected_family={selected['Family']} "
        f"strategy_equal_rmse={selected['StrategyEqualRMSE']:.6f} "
        f"output={args.output_dir.resolve()}"
    )


if __name__ == "__main__":
    main()
