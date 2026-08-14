"""CSV writers for Question 2 smoke-test results."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


OUTPUT_MAP = {
    "design_audit": ("00_design", "design_audit.csv"),
    "battery_summary": ("01_smoke_test", "battery_degradation_summary.csv"),
    "strategy_summary": ("01_smoke_test", "strategy_degradation_summary.csv"),
    "scalar_predictions": ("01_smoke_test", "scalar_fold_predictions.csv"),
    "hierarchical_predictions": ("01_smoke_test", "hierarchical_fold_predictions.csv"),
    "scalar_metrics": ("02_model_selection", "scalar_model_comparison.csv"),
    "coefficient_stability": ("02_model_selection", "coefficient_stability.csv"),
    "hierarchical_metrics": ("02_model_selection", "hierarchical_model_comparison.csv"),
    "hierarchical_diagnostics": ("02_model_selection", "hierarchical_diagnostics.csv"),
    "model_selection": ("02_model_selection", "smoke_model_selection.csv"),
    "selected_model_fit": ("02_model_selection", "selected_model_fit.csv"),
    "selected_model_predictions": ("02_model_selection", "selected_model_predictions.csv"),
}


def write_outputs(project_root: Path, outputs: dict[str, pd.DataFrame]) -> None:
    root = project_root / "result" / "q2"
    for key, frame in outputs.items():
        folder, filename = OUTPUT_MAP[key]
        destination = root / folder
        destination.mkdir(parents=True, exist_ok=True)
        frame.to_csv(destination / filename, index=False, encoding="utf-8-sig")
    manifest_rows = []
    for key, frame in outputs.items():
        folder, filename = OUTPUT_MAP[key]
        manifest_rows.append(
            {
                "output_key": key,
                "relative_path": f"result/q2/{folder}/{filename}",
                "rows": len(frame),
                "columns": len(frame.columns),
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    manifest_path = root / "result_manifest.csv"
    if manifest_path.exists():
        existing = pd.read_csv(manifest_path)
        retained = existing[~existing["relative_path"].isin(manifest["relative_path"])]
        manifest = pd.concat((manifest, retained), ignore_index=True)
    manifest.to_csv(manifest_path, index=False, encoding="utf-8-sig")
