"""Integrity checks for generated Q4 paper figures."""

import hashlib
from pathlib import Path

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "fig_q4_pareto_uncertainty.png": (2800, 1200),
    "fig_q4_fast_pair_comparison.png": (2600, 850),
    "fig_q4_m1_validation.png": (2400, 1200),
}


def main() -> None:
    root = ROOT / "result" / "q4" / "02_full_validation" / "figures"
    manifest = pd.read_csv(root / "figure_manifest.csv")
    assert set(manifest["figure"]) == set(EXPECTED)
    for name, minimum in EXPECTED.items():
        path = root / name
        assert path.exists(), path
        assert path.stat().st_size > 50_000, (path, path.stat().st_size)
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= minimum[0], (path, image.size)
            assert image.height >= minimum[1], (path, image.size)
        row = manifest.loc[manifest["figure"].eq(name)].iloc[0]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["figure_sha256"]
        source_names = row["source_files"].split(";")
        source_hashes = row["source_sha256"].split(";")
        assert len(source_names) == len(source_hashes)
        result_root = root.parent
        for source_name, expected_hash in zip(source_names, source_hashes):
            assert hashlib.sha256((result_root / source_name).read_bytes()).hexdigest() == expected_hash
        generator = ROOT / row["generator"]
        assert hashlib.sha256(generator.read_bytes()).hexdigest() == row["generator_sha256"]
    print("Q4 paper figure integrity tests passed")


if __name__ == "__main__":
    main()
