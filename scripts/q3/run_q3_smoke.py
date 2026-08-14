"""Run Question 3 model smoke tests only; does not run full LOBO validation."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models import run_smoke_test  # noqa: E402
from q3_models.outputs import write_smoke_outputs  # noqa: E402


def main() -> None:
    results = run_smoke_test(PROJECT_ROOT)
    output_dir = write_smoke_outputs(PROJECT_ROOT, results)
    print(f"Q3 smoke test completed: {output_dir}")
    print("STOP: full validation and final test-battery prediction were not run.")


if __name__ == "__main__":
    main()
