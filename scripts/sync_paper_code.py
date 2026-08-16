#!/usr/bin/env python3
"""Keep paper/code in sync with the single source of truth in src/ and scripts/.

Usage:
    python scripts/sync_paper_code.py            # copy source files into paper/code
    python scripts/sync_paper_code.py --check    # verify paper/code matches source
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_CODE = ROOT / "paper" / "code"

SOURCES: dict[str, str] = {
    "src/clean_a_battery_data.m": "clean_a_battery_data.m",
    "src/q1_models/core.py": "q1_core.py",
    "src/q2_models/core.py": "q2_core.py",
    "src/q3_models/core.py": "q3_core.py",
    "src/q4_models/core.py": "q4_core.py",
    "scripts/q1/run_q1_final_analysis.py": "run_q1.py",
    "scripts/q2/run_q2_merged_robustness.py": "run_q2.py",
    "scripts/q3/run_q3_full_validation.py": "run_q3.py",
    "scripts/q4/run_q4_full_validation.py": "run_q4.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="only verify, do not copy")
    args = parser.parse_args()

    missing_source = [src for src in SOURCES if not (ROOT / src).is_file()]
    if missing_source:
        print("missing source files:")
        for src in missing_source:
            print(f"  {src}")
        return 1

    PAPER_CODE.mkdir(parents=True, exist_ok=True)
    mismatched = []
    for src, dst in SOURCES.items():
        source = ROOT / src
        target = PAPER_CODE / dst
        if not target.is_file() or sha256(source) != sha256(target):
            mismatched.append((source, target))

    if not mismatched:
        print(f"OK: {len(SOURCES)} files in paper/code match src/ and scripts/")
        return 0

    if args.check:
        print("MISMATCHED files (run without --check to sync):")
        for source, target in mismatched:
            print(f"  {target.name} <- {source.relative_to(ROOT)}")
        return 1

    for source, target in mismatched:
        shutil.copy2(source, target)
        print(f"synced {target.name} <- {source.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
