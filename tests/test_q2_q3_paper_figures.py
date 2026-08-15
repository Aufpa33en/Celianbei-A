"""Integrity checks for generated Question 2 and Question 3 paper figures."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "result/q2/04_paper_materials/figures/fig_q2_strategy_late_rate.png": (2400, 1200),
    "result/q2/04_paper_materials/figures/fig_q2_model_stability.png": (2400, 1200),
    "result/q3/03_final_predictions/figures/fig_q3_early_length_rmse.png": (2400, 1200),
    "result/q3/03_final_predictions/figures/fig_q3_test_predictions.png": (3000, 2200),
    "result/q3/03_final_predictions/figures/fig_q3_t80_sensitivity.png": (2400, 1200),
}


def main() -> None:
    for relative_path, minimum_size in EXPECTED.items():
        path = ROOT / relative_path
        assert path.exists(), relative_path
        assert path.stat().st_size > 50_000, (relative_path, path.stat().st_size)
        with Image.open(path) as image:
            assert image.format == "PNG", (relative_path, image.format)
            assert image.width >= minimum_size[0], (relative_path, image.size)
            assert image.height >= minimum_size[1], (relative_path, image.size)
    print("Q2/Q3 paper figure integrity tests passed")


if __name__ == "__main__":
    main()
