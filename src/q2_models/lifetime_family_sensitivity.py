"""Point sensitivity of Q2 exposure conclusions across frozen Q1 T80 families."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .lifetime_validation import evaluate_exposure_models, prepare_lifetime_design


FAMILIES = ("linear", "power", "exponential")


def run_lifetime_family_sensitivity(project_root: Path) -> dict[str, pd.DataFrame]:
    source = project_root / "result" / "q1" / "raw" / "lifetime_family_battery_t80.csv"
    if not source.is_file():
        raise FileNotFoundError(
            "Q1 authoritative lifetime-family table is missing; run "
            "scripts/q1/run_q1_final_analysis.py first"
        )
    battery_t80 = pd.read_csv(source)
    if len(battery_t80) != 49 * len(FAMILIES):
        raise ValueError("Q2 family sensitivity requires 49 batteries in each of three T80 families")
    if set(battery_t80["Family"]) != set(FAMILIES):
        raise ValueError("unexpected Q1 lifetime family set")
    if not battery_t80.groupby("BatteryId")["Family"].nunique().eq(len(FAMILIES)).all():
        raise ValueError("each battery must have one T80 estimate from every family")
    if not np.isfinite(battery_t80["EstimatedT80"]).all():
        raise ValueError("family sensitivity requires finite T80 estimates")

    _, template, selected_window = prepare_lifetime_design(project_root)
    response_columns = {
        "n_batteries", "mean_log_t80", "median_t80", "mean_t80",
        "minimum_t80", "maximum_t80",
    }
    features = template.drop(columns=[column for column in response_columns if column in template])
    policy_rows, design_parts, prediction_parts, metric_parts, selection_rows = [], [], [], [], []
    for family in FAMILIES:
        current = battery_t80.loc[battery_t80["Family"].eq(family)].copy()
        current["log_t80"] = np.log(current["EstimatedT80"])
        policy = (
            current.groupby("Policy", as_index=False)
            .agg(
                n_batteries=("BatteryId", "size"),
                mean_log_t80=("log_t80", "mean"),
                median_t80=("EstimatedT80", "median"),
                mean_t80=("EstimatedT80", "mean"),
                minimum_t80=("EstimatedT80", "min"),
                maximum_t80=("EstimatedT80", "max"),
            )
            .rename(columns={"Policy": "policy"})
        )
        policy.insert(0, "Family", family)
        policy_rows.append(policy)
        design = features.merge(
            policy.drop(columns="Family"), on="policy", how="left", validate="one_to_one"
        )
        if design["mean_log_t80"].isna().any():
            raise ValueError(f"family {family} is missing a parameterized policy")
        design.insert(0, "Family", family)
        design["lifetime_tail_window"] = selected_window
        predictions, metrics = evaluate_exposure_models(design)
        predictions.insert(0, "Family", family)
        metrics.insert(0, "Family", family)
        design_parts.append(design)
        prediction_parts.append(predictions)
        metric_parts.append(metrics)
        selected = metrics.loc[metrics["selected_primary_explanatory"].astype(bool)]
        if len(selected) != 1:
            raise AssertionError(f"family {family} must have one selected point explanatory model")
        selected = selected.iloc[0]
        linear_j = metrics.loc[metrics["model"].eq("linear_J")].iloc[0]
        selection_rows.append(
            {
                "Family": family,
                "SelectedModel": selected["model"],
                "SelectedLOCORMSE": selected["loco_rmse_log_t80"],
                "SelectedImprovementVsConstant": selected[
                    "relative_rmse_improvement_vs_constant"
                ],
                "SelectedSlope": selected["full_slope_original_scale"],
                "LinearJImprovementVsConstant": linear_j[
                    "relative_rmse_improvement_vs_constant"
                ],
                "LinearJSlope": linear_j["full_slope_original_scale"],
                "SensitivityType": "point_estimate_across_frozen_T80_families",
                "HasCrossFamilyCI": False,
            }
        )
    return {
        "lifetime_family_policy_t80_summary": pd.concat(policy_rows, ignore_index=True),
        "lifetime_family_strategy_design": pd.concat(design_parts, ignore_index=True),
        "lifetime_family_loco_predictions": pd.concat(prediction_parts, ignore_index=True),
        "lifetime_family_model_comparison": pd.concat(metric_parts, ignore_index=True),
        "lifetime_family_selection_summary": pd.DataFrame(selection_rows),
    }
