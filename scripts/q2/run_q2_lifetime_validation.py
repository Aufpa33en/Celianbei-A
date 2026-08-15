"""Run the Question 2 T80-primary validation and write authoritative tables."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q2_models.lifetime_validation import (  # noqa: E402
    LifetimeValidationSettings,
    run_lifetime_validation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260815)
    args = parser.parse_args()
    tables = run_lifetime_validation(
        PROJECT_ROOT,
        LifetimeValidationSettings(args.bootstrap, args.seed),
    )
    output_dir = PROJECT_ROOT / "result" / "q2" / "03_formal_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
    manifest_rows = pd.DataFrame(
        [
            {
                "output_key": name,
                "relative_path": f"result/q2/03_formal_validation/{name}.csv",
                "rows": len(table),
                "columns": len(table.columns),
            }
            for name, table in tables.items()
        ]
    )
    manifest_path = PROJECT_ROOT / "result" / "q2" / "result_manifest.csv"
    if manifest_path.exists():
        existing = pd.read_csv(manifest_path)
        existing = existing.loc[~existing["output_key"].isin(manifest_rows["output_key"])]
        manifest_rows = pd.concat((existing, manifest_rows), ignore_index=True)
    manifest_rows.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    selected = tables["lifetime_model_comparison"].loc[
        tables["lifetime_model_comparison"]["selected_primary_explanatory"].astype(bool)
    ]
    status = selected.iloc[0]["model"] if len(selected) else "no_eligible_explanatory_model"
    print(f"Q2 lifetime validation complete: {output_dir}")
    print(f"Primary selection: {status}")


if __name__ == "__main__":
    main()
