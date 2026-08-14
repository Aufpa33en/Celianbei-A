"""Complete Question 1 and write CSV-only authoritative results to result/q1."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q1_models.inference import InferenceSettings, file_hashes, run_final_inference  # noqa: E402
from q1_models.outputs import write_authoritative_outputs  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260814)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result_dir = PROJECT_ROOT / "result" / "q1"
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
    inference_started = time.perf_counter()
    tables = run_final_inference(PROJECT_ROOT, settings)
    inference_seconds = time.perf_counter() - inference_started

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
    if not data_check["Unchanged"].all():
        raise RuntimeError("experimental data changed during Q1 final analysis")
    if not program_check["UnchangedDuringRun"].all():
        raise RuntimeError("an existing experiment program changed during Q1 final analysis")
    tables["data_integrity_check"] = data_check
    tables["program_integrity_check"] = program_check
    command = (
        f"{Path(sys.executable).resolve()} scripts/q1/run_q1_final_analysis.py "
        f"--bootstrap {args.bootstrap} --seed {args.seed}"
    )
    write_authoritative_outputs(PROJECT_ROOT, tables, command, inference_seconds)
    print(f"Q1 final analysis complete: {result_dir}")
    print(f"Inference tables: {len(tables)}")
    print("Experimental data unchanged: true")
    print("Existing experiment programs unchanged during run: true")


if __name__ == "__main__":
    main()
