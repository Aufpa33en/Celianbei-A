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
)
from q2_models.full_pipeline_bootstrap import run_full_pipeline_lifetime_validation  # noqa: E402
from q2_models.lifetime_family_sensitivity import run_lifetime_family_sensitivity  # noqa: E402
from q2_models.lifetime_outputs import draw_lifetime_evidence, write_lifetime_conclusion  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260816)
    args = parser.parse_args()
    tables = run_full_pipeline_lifetime_validation(
        PROJECT_ROOT,
        LifetimeValidationSettings(args.bootstrap, args.seed),
    )
    tables.update(run_lifetime_family_sensitivity(PROJECT_ROOT))
    output_dir = PROJECT_ROOT / "result" / "q2" / "03_formal_validation"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
    write_lifetime_conclusion(output_dir / "正式验证结论.md", tables)
    paper_figure_dir = PROJECT_ROOT / "result" / "q2" / "04_paper_materials" / "figures"
    paper_figure_dir.mkdir(parents=True, exist_ok=True)
    draw_lifetime_evidence(paper_figure_dir / "fig_q2_t80_parameter_evidence.png", tables)
    paper_table_dir = PROJECT_ROOT / "result" / "q2" / "04_paper_materials" / "tables"
    paper_table_dir.mkdir(parents=True, exist_ok=True)
    paper_table_keys = (
        "lifetime_family_policy_t80_summary",
        "lifetime_family_strategy_design",
        "lifetime_family_model_comparison",
        "lifetime_family_selection_summary",
    )
    for name in paper_table_keys:
        tables[name].to_csv(paper_table_dir / f"{name}.csv", index=False, encoding="utf-8-sig")
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
    paper_manifest_rows = pd.DataFrame(
        [
            {
                "output_key": f"paper_{name}",
                "relative_path": f"result/q2/04_paper_materials/tables/{name}.csv",
                "rows": len(tables[name]),
                "columns": len(tables[name].columns),
            }
            for name in paper_table_keys
        ]
    )
    manifest_rows = pd.concat((manifest_rows, paper_manifest_rows), ignore_index=True)
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
