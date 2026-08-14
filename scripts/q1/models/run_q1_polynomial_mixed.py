"""Run only the quadratic mixed-effects approximation candidate."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from q1_models.experiments import run_candidate  # noqa: E402

run_candidate(ROOT, "polynomial_mixed", seed=20260814, write_files=True)
