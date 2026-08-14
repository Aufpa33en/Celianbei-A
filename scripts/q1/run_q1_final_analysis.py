"""Complete Question 1 and write CSV-only authoritative results to result/q1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q1_models.inference import InferenceSettings, file_hashes, run_final_inference  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260814)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_dir = PROJECT_ROOT / "result" / "q1"
    result_dir.mkdir(parents=True, exist_ok=True)
    data_paths = sorted(path for path in (PROJECT_ROOT / "A题").rglob("*") if path.is_file())
    data_paths += sorted(path for path in (PROJECT_ROOT / "data" / "raw").rglob("*") if path.is_file())
    data_paths += sorted(
        path for path in (PROJECT_ROOT / "data" / "processed" / "q1_cleaned").rglob("*") if path.is_file()
    )
    data_paths = list(dict.fromkeys(data_paths))
    program_paths = sorted((PROJECT_ROOT / "scripts" / "q1").rglob("*.py")) + sorted(
        (PROJECT_ROOT / "src" / "q1_models").glob("*.py")
    )
    data_before = file_hashes(data_paths).rename(columns={"SHA256": "SHA256Before", "SizeBytes": "SizeBytesBefore"})
    programs_before = file_hashes(program_paths).rename(columns={"SHA256": "SHA256Before", "SizeBytes": "SizeBytesBefore"})

    settings = InferenceSettings(seed=args.seed, bootstrap_repetitions=args.bootstrap)
    tables = run_final_inference(PROJECT_ROOT, settings)
    for name, table in tables.items():
        table.to_csv(result_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    data_after = file_hashes(data_paths).rename(columns={"SHA256": "SHA256After", "SizeBytes": "SizeBytesAfter"})
    programs_after = file_hashes(program_paths).rename(columns={"SHA256": "SHA256After", "SizeBytes": "SizeBytesAfter"})
    data_check = data_before.merge(data_after, on="Path")
    data_check["Unchanged"] = (
        (data_check["SHA256Before"] == data_check["SHA256After"])
        & (data_check["SizeBytesBefore"] == data_check["SizeBytesAfter"])
    )
    program_check = programs_before.merge(programs_after, on="Path")
    program_check["UnchangedDuringRun"] = (
        (program_check["SHA256Before"] == program_check["SHA256After"])
        & (program_check["SizeBytesBefore"] == program_check["SizeBytesAfter"])
    )
    data_check.to_csv(result_dir / "data_integrity_check.csv", index=False, encoding="utf-8-sig")
    program_check.to_csv(result_dir / "program_integrity_check.csv", index=False, encoding="utf-8-sig")
    if not data_check["Unchanged"].all():
        raise RuntimeError("experimental data changed during Q1 final analysis")
    if not program_check["UnchangedDuringRun"].all():
        raise RuntimeError("an existing experiment program changed during Q1 final analysis")

    manifest_rows = []
    for path in sorted(result_dir.glob("*.csv")):
        if path.name == "result_manifest.csv":
            continue
        frame = pd.read_csv(path)
        manifest_rows.append(
            {
                "File": path.name,
                "Rows": len(frame),
                "Columns": len(frame.columns),
                "SizeBytes": path.stat().st_size,
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    manifest.to_csv(result_dir / "result_manifest.csv", index=False, encoding="utf-8-sig")
    print(f"Q1 final analysis complete: {result_dir}")
    print(f"CSV files: {len(manifest) + 1}")
    print("Experimental data unchanged: true")
    print("Existing experiment programs unchanged during run: true")


if __name__ == "__main__":
    main()
