"""Integrity checks for generated Q4 paper figures."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "fig_q4_pareto_uncertainty.png": (2800, 1200),
    "fig_q4_fast_pair_comparison.png": (2600, 850),
    "fig_q4_m1_validation.png": (2400, 1200),
}


def main() -> None:
    root = ROOT / "result" / "q4" / "02_full_validation" / "figures"
    for name, minimum in EXPECTED.items():
        path = root / name
        assert path.exists(), path
        assert path.stat().st_size > 50_000, (path, path.stat().st_size)
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= minimum[0], (path, image.size)
            assert image.height >= minimum[1], (path, image.size)
    print("Q4 paper figure integrity tests passed")


if __name__ == "__main__":
    main()
