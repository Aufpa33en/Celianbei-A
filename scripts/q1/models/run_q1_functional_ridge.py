"""Run only the two-stage functional ridge candidate."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from q1_models.experiments import run_candidate  # noqa: E402

run_candidate(ROOT, "functional_ridge", seed=20260814, write_files=True)
