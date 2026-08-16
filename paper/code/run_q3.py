"""Run complete Q3 nested validation, freeze a model, then predict test cells."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models.config import CONFIG  # noqa: E402
from q3_models.full_outputs import (  # noqa: E402
    directory_hashes,
    final_integrity_checks,
    full_integrity_checks,
    write_final_outputs,
    write_full_outputs,
)
from q3_models.full_validation import (  # noqa: E402
    compare_protected_hashes,
    protected_file_hashes,
    run_final_prediction,
    run_full_validation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=5000)
    parser.add_argument("--resume-final", action="store_true")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "result" / "q3",
        help="Directory containing 02_full_validation and 03_final_predictions.",
    )
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    full_dir = output_root / "02_full_validation"
    final_dir = output_root / "03_final_predictions"
    if args.resume_final:
        if not full_dir.exists() or final_dir.exists():
            raise FileExistsError("--resume-final requires existing 02 and absent 03")
        full = {
            path.name: pd.read_csv(path)
            for path in full_dir.glob("*.csv")
            if path.name not in {"manifest.csv", "integrity_checks.csv", "protected_files_integrity.csv"}
        }
        full_hashes = directory_hashes(full_dir)
        before = protected_file_hashes(PROJECT_ROOT)
        final = run_final_prediction(PROJECT_ROOT, full)
        protected_final = compare_protected_hashes(before, protected_file_hashes(PROJECT_ROOT))
        settings = final["final_hyperparameters.csv"]
        selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
        selected = final["final_predictions.csv"].loc[
            final["final_predictions.csv"]["model"].eq(selected_model)
        ]
        checks = final_integrity_checks(selected, final["final_predictions.csv"], settings, protected_final)
        if not checks["passed"].all():
            raise RuntimeError("Final pre-publication integrity checks failed")
        published_final = write_final_outputs(
            PROJECT_ROOT, final, protected_final, CONFIG.seed, output_root=output_root
        )
        if directory_hashes(full_dir) != full_hashes:
            raise RuntimeError("Published 02_full_validation changed during resumed final prediction")
        print(f"Q3 final predictions published: {published_final}", flush=True)
        return
    if full_dir.exists() or final_dir.exists():
        raise FileExistsError("Q3 authoritative full/final directory already exists; refusing overwrite")

    started = time.perf_counter()
    before = protected_file_hashes(PROJECT_ROOT)
    full = run_full_validation(PROJECT_ROOT, bootstrap_repetitions=args.bootstrap)
    after_full = protected_file_hashes(PROJECT_ROOT)
    protected_full = compare_protected_hashes(before, after_full)
    if not protected_full["unchanged"].all():
        raise RuntimeError("Protected data, programs, or smoke outputs changed during full validation")
    final = run_final_prediction(PROJECT_ROOT, full)
    after_final = protected_file_hashes(PROJECT_ROOT)
    protected_final = compare_protected_hashes(before, after_final)
    if not protected_final["unchanged"].all():
        raise RuntimeError("Protected data, programs, or smoke outputs changed during final prediction")
    # Validate both products before publishing either authoritative directory.
    if not full_integrity_checks(full, protected_full)["passed"].all():
        raise RuntimeError("Full pre-publication integrity checks failed")
    settings = final["final_hyperparameters.csv"]
    selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
    selected = final["final_predictions.csv"].loc[
        final["final_predictions.csv"]["model"].eq(selected_model)
    ]
    if not final_integrity_checks(selected, final["final_predictions.csv"], settings, protected_final)["passed"].all():
        raise RuntimeError("Final pre-publication integrity checks failed")
    published_full = write_full_outputs(
        PROJECT_ROOT, full, protected_full, CONFIG.seed, output_root=output_root
    )
    print(f"Q3 full validation published: {published_full}", flush=True)
    full_hashes = directory_hashes(published_full)
    published_final = write_final_outputs(
        PROJECT_ROOT, final, protected_final, CONFIG.seed, output_root=output_root
    )
    if directory_hashes(published_full) != full_hashes:
        raise RuntimeError("Published 02_full_validation changed during final publication")
    print(f"Q3 final predictions published: {published_final}", flush=True)
    print(f"Q3 complete wall seconds: {time.perf_counter() - started:.3f}", flush=True)


if __name__ == "__main__":
    main()
