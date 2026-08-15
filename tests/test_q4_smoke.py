from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_q4_smoke_protocol() -> None:
    target = ROOT / "result" / "q4" / "01_smoke_test_v2"
    if not target.exists():
        return
    checks = pd.read_csv(target / "integrity_checks.csv")
    assert checks["passed"].astype(bool).all()
    summary = pd.read_csv(target / "policy_summary.csv")
    assert len(summary) == 9 and summary["pareto"].any()
    boot = pd.read_csv(target / "bootstrap_pareto.csv")
    assert len(boot) == 18000


if __name__ == "__main__":
    test_q4_smoke_protocol()
    print("Q4 smoke protocol tests passed")
