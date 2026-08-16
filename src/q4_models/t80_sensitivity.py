"""Supporting Q4 Pareto sensitivity using predicted T80 rather than SOH200 loss."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .core import pareto_mask


def prepare_t80_pareto_inputs(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    battery_q4 = pd.read_csv(
        project_root / "result" / "q4" / "02_full_validation" / "battery_observations.csv"
    )
    family = pd.read_csv(
        project_root
        / "result"
        / "q1"
        / "02_lifetime_model_comparison"
        / "raw"
        / "battery_t80_by_family.csv"
    )
    joined = family.merge(
        battery_q4[["battery_id", "policy", "time", "loss", "late_slope_loss"]],
        left_on=["BatteryId", "Policy"],
        right_on=["battery_id", "policy"],
        how="inner",
        validate="many_to_one",
    )
    if joined["BatteryId"].nunique() != 40 or len(joined) != 120:
        raise AssertionError("Q4 T80 sensitivity requires 40 complete batteries × 3 model families")
    joined = joined.drop(columns=["battery_id", "policy"])

    rows = []
    for (family_name, policy), current in joined.groupby(["Family", "Policy"], sort=True):
        t80 = current["EstimatedT80"].dropna().to_numpy(dtype=float)
        rows.append(
            {
                "Family": family_name,
                "Policy": policy,
                "NBattery": len(current),
                "NFiniteT80": len(t80),
                "TimeMean": float(current["time"].mean()),
                "T80Median": float(np.median(t80)),
                "T80Mean": float(np.mean(t80)),
                "T80Min": float(np.min(t80)),
                "T80Max": float(np.max(t80)),
            }
        )
    summary = pd.DataFrame(rows)
    parts = []
    for family_name, current in summary.groupby("Family", sort=True):
        current = current.copy()
        current["ParetoTimeMaxT80"] = pareto_mask(
            current["TimeMean"].to_numpy(dtype=float),
            -current["T80Median"].to_numpy(dtype=float),
        )
        current["T80Rank"] = current["T80Median"].rank(
            method="first", ascending=False
        ).astype(int)
        parts.append(current)
    return joined, pd.concat(parts, ignore_index=True)


def bootstrap_t80_pareto(
    joined: pd.DataFrame,
    repetitions: int = 5000,
    seed: int = 20260816,
) -> pd.DataFrame:
    selected = joined.loc[joined["Family"].eq("linear")].copy()
    policies = sorted(selected["Policy"].unique())
    records = {
        policy: selected.loc[selected["Policy"].eq(policy)].reset_index(drop=True)
        for policy in policies
    }
    rng = np.random.default_rng(seed)
    rows = []
    for replicate in range(repetitions):
        point = []
        for policy in policies:
            current = records[policy]
            sampled = current.iloc[rng.integers(0, len(current), size=len(current))]
            point.append(
                (
                    policy,
                    float(sampled["time"].mean()),
                    float(sampled["EstimatedT80"].median()),
                )
            )
        time = np.asarray([row[1] for row in point], dtype=float)
        negative_lifetime = -np.asarray([row[2] for row in point], dtype=float)
        front = pareto_mask(time, negative_lifetime)
        for (policy, time_mean, t80_median), is_front in zip(point, front):
            rows.append(
                {
                    "replicate": replicate,
                    "Policy": policy,
                    "TimeMean": time_mean,
                    "T80Median": t80_median,
                    "ParetoTimeMaxT80": bool(is_front),
                    "seed": seed,
                }
            )
    return pd.DataFrame(rows)


def summarize_t80_bootstrap(
    summary: pd.DataFrame,
    bootstrap: pd.DataFrame,
    early_proxy_summary: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    linear = summary.loc[summary["Family"].eq("linear")].copy()
    rows = []
    for row in linear.itertuples(index=False):
        current = bootstrap.loc[bootstrap["Policy"].eq(row.Policy)]
        rows.append(
            {
                "Policy": row.Policy,
                "NBattery": row.NBattery,
                "TimeMean": row.TimeMean,
                "TimeP025": float(current["TimeMean"].quantile(0.025)),
                "TimeP975": float(current["TimeMean"].quantile(0.975)),
                "T80Median": row.T80Median,
                "T80P025": float(current["T80Median"].quantile(0.025)),
                "T80P975": float(current["T80Median"].quantile(0.975)),
                "PointParetoTimeMaxT80": bool(row.ParetoTimeMaxT80),
                "BootstrapParetoFrequency": float(current["ParetoTimeMaxT80"].mean()),
            }
        )
    paper = pd.DataFrame(rows).sort_values(
        ["PointParetoTimeMaxT80", "T80Median"], ascending=[False, False]
    )
    early = early_proxy_summary[["policy", "pareto"]].rename(
        columns={"policy": "Policy", "pareto": "PointParetoTimeMinSOH200Loss"}
    )
    comparison = paper[["Policy", "PointParetoTimeMaxT80"]].merge(
        early, on="Policy", how="left", validate="one_to_one"
    )
    comparison["FrontAgreement"] = (
        comparison["PointParetoTimeMaxT80"].astype(bool)
        == comparison["PointParetoTimeMinSOH200Loss"].astype(bool)
    )
    return paper.reset_index(drop=True), comparison


def run_t80_pareto_sensitivity(
    project_root: Path,
    repetitions: int = 5000,
    seed: int = 20260816,
) -> dict[str, pd.DataFrame]:
    joined, family_summary = prepare_t80_pareto_inputs(project_root)
    bootstrap = bootstrap_t80_pareto(joined, repetitions, seed)
    early = pd.read_csv(
        project_root / "result" / "q4" / "02_full_validation" / "policy_summary.csv"
    )
    paper, comparison = summarize_t80_bootstrap(family_summary, bootstrap, early)
    family_front = family_summary.pivot(
        index="Policy", columns="Family", values="ParetoTimeMaxT80"
    ).reset_index()
    family_front["ParetoInAllFamilies"] = family_front[
        [column for column in family_front if column != "Policy"]
    ].astype(bool).all(axis=1)
    family_front["ParetoFamilyCount"] = family_front[
        [column for column in family_front if column not in ("Policy", "ParetoInAllFamilies")]
    ].astype(bool).sum(axis=1)
    metadata = pd.DataFrame(
        [
            {"parameter": "status", "value": "supporting_sensitivity_not_primary_q4_replacement"},
            {"parameter": "primary_lifetime_family", "value": "linear_w40_s1"},
            {"parameter": "bootstrap_repetitions", "value": repetitions},
            {"parameter": "seed", "value": seed},
            {"parameter": "bootstrap_unit", "value": "whole_battery_within_policy_joint_time_and_T80"},
            {"parameter": "paper_main_modified", "value": False},
        ]
    )
    return {
        "battery_t80_observations": joined,
        "policy_t80_by_model_family": family_summary,
        "t80_pareto_bootstrap": bootstrap,
        "policy_t80_pareto_summary": paper,
        "early_proxy_t80_front_comparison": comparison,
        "t80_pareto_model_family_sensitivity": family_front,
        "run_metadata": metadata,
    }
