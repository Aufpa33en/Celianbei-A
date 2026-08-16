"""Nested battery-level comparison of monotone T80 extrapolation families."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from .lifetime_candidates import (
    LifetimeCandidate,
    candidate_grid,
    candidate_t80,
    fit_candidate,
    predict_candidate,
)


def _complete_cohort(cycles: pd.DataFrame, required_cycle: int = 200) -> pd.DataFrame:
    last = cycles.groupby("battery_id")["cycle"].max()
    return cycles.loc[cycles["battery_id"].isin(last.loc[last >= required_cycle].index)].copy()


def _battery_validation(
    cycles: pd.DataFrame,
    candidate: LifetimeCandidate,
    origin: int = 150,
    horizon: int = 50,
) -> pd.DataFrame:
    rows = []
    for battery_id, frame in cycles.groupby("battery_id", sort=True):
        intercept, coefficient = fit_candidate(frame, origin, candidate)
        held_out = frame.loc[frame["cycle"].between(origin + 1, origin + horizon)].sort_values("cycle")
        if len(held_out) != horizon:
            raise ValueError(f"battery {battery_id} lacks the requested validation horizon")
        prediction = predict_candidate(
            held_out["cycle"].to_numpy(dtype=float), intercept, coefficient, candidate
        )
        error = prediction - held_out["SOH_clean"].to_numpy(dtype=float)
        rows.append(
            {
                "BatteryId": int(battery_id),
                "Policy": str(frame["policy"].iloc[0]),
                "Family": candidate.family,
                "Candidate": candidate.name,
                "TailWindow": candidate.tail_window,
                "Shape": candidate.shape,
                "Origin": origin,
                "Horizon": horizon,
                "RMSE": float(np.sqrt(np.mean(error**2))),
                "MAE": float(np.mean(np.abs(error))),
                "Bias": float(np.mean(error)),
                "Coefficient": coefficient,
            }
        )
    return pd.DataFrame(rows)


def _summarize(rows: pd.DataFrame) -> dict[str, float]:
    policy_mse = rows.assign(MSE=rows["RMSE"] ** 2).groupby("Policy")["MSE"].mean()
    return {
        "StrategyEqualRMSE": float(np.sqrt(policy_mse.mean())),
        "MeanBatteryRMSE": float(rows["RMSE"].mean()),
        "WorstBatteryRMSE": float(rows["RMSE"].max()),
        "MeanBatteryMAE": float(rows["MAE"].mean()),
        "MeanBias": float(rows["Bias"].mean()),
        "NonDecreasingCount": int((rows["Coefficient"] >= 0).sum()),
    }


def compare_lifetime_families(
    cycles: pd.DataFrame,
    candidates: Iterable[LifetimeCandidate] | None = None,
) -> dict[str, pd.DataFrame]:
    complete = _complete_cohort(cycles)
    grid = tuple(candidate_grid() if candidates is None else candidates)
    by_name = {candidate.name: candidate for candidate in grid}
    validation = pd.concat(
        [_battery_validation(complete, candidate) for candidate in grid], ignore_index=True
    )

    outer_rows = []
    tuning_rows = []
    battery_ids = sorted(complete["battery_id"].unique())
    families = sorted({candidate.family for candidate in grid})
    for outer_id in battery_ids:
        for family in families:
            family_candidates = [candidate for candidate in grid if candidate.family == family]
            scored = []
            for candidate in family_candidates:
                inner = validation.loc[
                    validation["Candidate"].eq(candidate.name)
                    & ~validation["BatteryId"].eq(outer_id)
                ]
                scored.append({"candidate": candidate, **_summarize(inner)})
            selected = min(
                scored,
                key=lambda row: (
                    row["StrategyEqualRMSE"], row["WorstBatteryRMSE"], row["candidate"].name
                ),
            )
            candidate = selected["candidate"]
            target = validation.loc[
                validation["Candidate"].eq(candidate.name)
                & validation["BatteryId"].eq(outer_id)
            ].iloc[0]
            tuning_rows.append(
                {
                    "OuterBatteryId": outer_id,
                    "Family": family,
                    "SelectedCandidate": candidate.name,
                    "InnerStrategyEqualRMSE": selected["StrategyEqualRMSE"],
                    "InnerWorstBatteryRMSE": selected["WorstBatteryRMSE"],
                    "InnerNBattery": len(battery_ids) - 1,
                }
            )
            outer_rows.append(
                {
                    "OuterBatteryId": outer_id,
                    "Policy": target["Policy"],
                    "Family": family,
                    "SelectedCandidate": candidate.name,
                    "RMSE": target["RMSE"],
                    "MAE": target["MAE"],
                    "Bias": target["Bias"],
                }
            )

    outer = pd.DataFrame(outer_rows)
    family_rows = []
    for family, current in outer.groupby("Family", sort=True):
        family_rows.append({"Family": family, **_summarize(current.assign(Coefficient=-1.0))})
    family_summary = pd.DataFrame(family_rows).sort_values(
        ["StrategyEqualRMSE", "WorstBatteryRMSE", "Family"], kind="stable"
    ).reset_index(drop=True)
    family_summary["SelectedFamily"] = family_summary.index.to_numpy() == 0

    frozen_rows = []
    for family in families:
        candidates_in_family = [candidate for candidate in grid if candidate.family == family]
        scored = []
        for candidate in candidates_in_family:
            current = validation.loc[validation["Candidate"].eq(candidate.name)]
            scored.append({"candidate": candidate, **_summarize(current)})
        selected = min(
            scored,
            key=lambda row: (
                row["StrategyEqualRMSE"], row["WorstBatteryRMSE"], row["candidate"].name
            ),
        )
        frozen_rows.append(
            {
                "Family": family,
                "FrozenCandidate": selected["candidate"].name,
                "TailWindow": selected["candidate"].tail_window,
                "Shape": selected["candidate"].shape,
                "FullCohortStrategyEqualRMSE": selected["StrategyEqualRMSE"],
                "SelectedFamily": family_summary.iloc[0]["Family"] == family,
            }
        )
    frozen = pd.DataFrame(frozen_rows).sort_values("Family").reset_index(drop=True)

    origin_rows = []
    for row in frozen.itertuples(index=False):
        candidate = by_name[row.FrozenCandidate]
        for origin in (100, 125, 150):
            current = _battery_validation(complete, candidate, origin=origin, horizon=50)
            origin_rows.append(
                {
                    "Family": row.Family,
                    "FrozenCandidate": row.FrozenCandidate,
                    "Origin": origin,
                    **_summarize(current),
                }
            )

    lifetime_rows = []
    for battery_id, frame in cycles.groupby("battery_id", sort=True):
        for row in frozen.itertuples(index=False):
            candidate = by_name[row.FrozenCandidate]
            intercept, coefficient = fit_candidate(frame, 150, candidate)
            t80, status = candidate_t80(intercept, coefficient, candidate)
            lifetime_rows.append(
                {
                    "BatteryId": int(battery_id),
                    "Policy": str(frame["policy"].iloc[0]),
                    "Family": row.Family,
                    "Candidate": row.FrozenCandidate,
                    "SelectedFamily": bool(row.SelectedFamily),
                    "Intercept": intercept,
                    "Coefficient": coefficient,
                    "EstimatedT80": t80,
                    "T80Status": status,
                    "ExtrapolationMultiple": t80 / 150 if np.isfinite(t80) else np.nan,
                }
            )

    lifetimes = pd.DataFrame(lifetime_rows)
    strategy_rows = []
    for (family, policy), current in lifetimes.groupby(["Family", "Policy"], sort=True):
        finite = current["EstimatedT80"].dropna().to_numpy(dtype=float)
        strategy_rows.append(
            {
                "Family": family,
                "Policy": policy,
                "NBattery": len(current),
                "NFiniteT80": len(finite),
                "MedianEstimatedT80": np.median(finite) if len(finite) else np.nan,
                "MinEstimatedT80": np.min(finite) if len(finite) else np.nan,
                "MaxEstimatedT80": np.max(finite) if len(finite) else np.nan,
            }
        )
    strategy = pd.DataFrame(strategy_rows)
    strategy["RankWithinFamily"] = strategy.groupby("Family")["MedianEstimatedT80"].rank(
        method="first", ascending=False
    ).astype(int)
    strategy_envelope = (
        strategy.groupby("Policy")["MedianEstimatedT80"]
        .agg(ModelFamilyMedianT80Min="min", ModelFamilyMedianT80Max="max")
        .reset_index()
    )
    strategy_envelope["ModelFamilyMedianT80Ratio"] = (
        strategy_envelope["ModelFamilyMedianT80Max"]
        / strategy_envelope["ModelFamilyMedianT80Min"]
    )
    envelope = (
        lifetimes.groupby(["BatteryId", "Policy"])["EstimatedT80"]
        .agg(FiniteFamilyCount="count", ModelFamilyT80Min="min", ModelFamilyT80Max="max")
        .reset_index()
    )
    envelope["ModelFamilyT80Ratio"] = envelope["ModelFamilyT80Max"] / envelope["ModelFamilyT80Min"]
    return {
        "candidate_validation_by_battery": validation,
        "nested_tuning_by_outer_battery": pd.DataFrame(tuning_rows),
        "nested_family_lobo_by_battery": outer,
        "nested_family_summary": family_summary,
        "frozen_family_candidates": frozen,
        "frozen_candidate_origin_sensitivity": pd.DataFrame(origin_rows),
        "battery_t80_by_family": lifetimes,
        "strategy_t80_by_family": strategy,
        "strategy_t80_model_family_envelope": strategy_envelope,
        "battery_t80_model_family_envelope": envelope,
    }
