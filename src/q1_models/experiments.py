"""Battery-level tuning, cross-validation, and real-data summaries for Q1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .core import ModelConfig, candidate_configs, fit_population_model


@dataclass
class CandidateResult:
    model_type: str
    seed: int
    tuning: pd.DataFrame
    best_config: ModelConfig
    lobo: pd.DataFrame
    final_model: object
    curves: pd.DataFrame
    strategy_summary: pd.DataFrame


def load_clean_data(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = project_root / "data" / "processed" / "q1_cleaned"
    cycles = pd.read_csv(data_dir / "cycle_train_clean.csv")
    batteries = pd.read_csv(data_dir / "battery_summary_clean.csv")
    cycles["policy"] = cycles["policy"].astype(str)
    batteries["policy"] = batteries["policy"].astype(str)
    cycles = cycles.loc[
        cycles["SOH_clean"].notna() & cycles["cycle"].between(1, 200)
    ].copy()
    if cycles["battery_id"].nunique() != 49 or cycles["policy"].nunique() != 9:
        raise AssertionError("cleaned Q1 data no longer has the expected 49 batteries and 9 policies")
    return cycles, batteries


def run_candidate(
    project_root: Path, model_type: str, seed: int = 20260814, write_files: bool = True
) -> CandidateResult:
    cycles, batteries = load_clean_data(project_root)
    configs = candidate_configs(model_type)
    fold_map = _stratified_three_fold_map(cycles, seed)
    tuning_rows: list[dict] = []
    for config_id, config in enumerate(configs, start=1):
        parts = []
        for fold in (1, 2, 3):
            held_out = [battery for battery, assigned in fold_map.items() if assigned == fold]
            train = cycles.loc[~cycles["battery_id"].isin(held_out)]
            test = cycles.loc[cycles["battery_id"].isin(held_out)]
            model = fit_population_model(train, model_type, config)
            parts.append(_evaluate_batteries(model, test))
        metrics = pd.concat(parts, ignore_index=True)
        policy_rmse = metrics.groupby("Policy", sort=False)["RMSE"].mean()
        tuning_rows.append(
            {
                "ConfigId": config_id,
                "LambdaRandom": config.lambda_random,
                "LambdaCurve": config.lambda_curve,
                "MeanBatteryRMSE": metrics["RMSE"].mean(),
                "MeanBatteryMAE": metrics["MAE"].mean(),
                "WorstPolicyRMSE": policy_rmse.max(),
            }
        )
    tuning = pd.DataFrame(tuning_rows)
    best_row = tuning.loc[tuning["MeanBatteryRMSE"].idxmin()]
    best_config = configs[int(best_row["ConfigId"]) - 1]

    lobo_parts = []
    for battery_id in pd.unique(cycles["battery_id"]):
        train = cycles.loc[cycles["battery_id"] != battery_id]
        test = cycles.loc[cycles["battery_id"] == battery_id]
        model = fit_population_model(train, model_type, best_config)
        lobo_parts.append(_evaluate_batteries(model, test))
    lobo = pd.concat(lobo_parts, ignore_index=True)
    final_model = fit_population_model(cycles, model_type, best_config)
    curves, strategy_summary = _extract_outputs(final_model, batteries)
    result = CandidateResult(
        model_type, seed, tuning, best_config, lobo, final_model, curves, strategy_summary
    )
    if write_files:
        output_dir = project_root / "outputs" / "raw" / "q1_models" / model_type
        output_dir.mkdir(parents=True, exist_ok=True)
        tuning.to_csv(output_dir / "tuning.csv", index=False)
        lobo.to_csv(output_dir / "lobo_by_battery.csv", index=False)
        curves.to_csv(output_dir / "strategy_curves.csv", index=False)
        strategy_summary.to_csv(output_dir / "strategy_summary.csv", index=False)
    return result


def observed_battery_metrics(cycles: pd.DataFrame, batteries: pd.DataFrame) -> pd.DataFrame:
    rows = []
    summary = batteries.set_index("battery_id")
    for battery_id, frame in cycles.groupby("battery_id", sort=False):
        frame = frame.sort_values("cycle")
        tail = frame.tail(min(50, len(frame)))
        design = np.column_stack((np.ones(len(tail)), tail["cycle"].to_numpy(dtype=float)))
        intercept, slope = np.linalg.lstsq(design, tail["SOH_clean"], rcond=None)[0]
        last_cycle = int(frame["cycle"].iloc[-1])
        last_soh = float(frame["SOH_clean"].iloc[-1])
        projected_l80 = (0.8 - intercept) / slope if slope < -1e-7 else np.nan
        rows.append(
            {
                "BatteryId": int(battery_id),
                "Policy": frame["policy"].iloc[0],
                "LastObservedCycle": last_cycle,
                "LastObservedSOH": last_soh,
                "SlopeLast50": slope,
                "ProjectedL80LocalLinear": projected_l80,
                "ObservedEOL80": bool((frame["SOH_clean"] <= 0.8).any()),
                "MeanChargeTime": float(summary.loc[battery_id, "mean_chargetime"]),
                "PredictionTest": int(summary.loc[battery_id, "prediction_test"]),
            }
        )
    return pd.DataFrame(rows)


def strategy_distribution(battery_metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for policy, frame in battery_metrics.groupby("Policy", sort=False):
        life = frame["ProjectedL80LocalLinear"].dropna().to_numpy()
        rows.append(
            {
                "Policy": policy,
                "NBattery": len(frame),
                "ObservedEOL80Count": int(frame["ObservedEOL80"].sum()),
                "ChargeTimeMean": frame["MeanChargeTime"].mean(),
                "ChargeTimeSD": frame["MeanChargeTime"].std(ddof=1),
                "LocalL80Median": np.median(life) if len(life) else np.nan,
                "LocalL80Q25": np.quantile(life, 0.25) if len(life) else np.nan,
                "LocalL80Q75": np.quantile(life, 0.75) if len(life) else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _stratified_three_fold_map(data: pd.DataFrame, seed: int) -> dict[int, int]:
    meta = data[["battery_id", "policy"]].drop_duplicates()
    rng = np.random.default_rng(seed)
    mapping: dict[int, int] = {}
    for _, frame in meta.groupby("policy", sort=False):
        ids = frame["battery_id"].to_numpy(dtype=int).copy()
        rng.shuffle(ids)
        for position, battery_id in enumerate(ids):
            mapping[int(battery_id)] = position % 3 + 1
    return mapping


def _evaluate_batteries(model, test: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for battery_id, frame in test.groupby("battery_id", sort=False):
        y = frame["SOH_clean"].to_numpy(dtype=float)
        prediction = model.predict(frame["policy"].iloc[0], frame["cycle"].to_numpy())
        error = prediction - y
        rows.append(
            {
                "BatteryId": int(battery_id),
                "Policy": frame["policy"].iloc[0],
                "NObs": len(frame),
                "RMSE": np.sqrt(np.mean(error**2)),
                "MAE": np.mean(np.abs(error)),
                "Bias": np.mean(error),
                "MaxAbsError": np.max(np.abs(error)),
            }
        )
    return pd.DataFrame(rows)


def _extract_outputs(model, batteries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cycles = np.arange(1, 201, dtype=float)
    curve_parts = []
    summary_rows = []
    for policy in model.policy_names:
        prediction = model.predict(policy, cycles)
        curve_parts.append(
            pd.DataFrame(
                {"Model": model.model_type, "Policy": policy, "Cycle": cycles.astype(int), "SOHPred": prediction}
            )
        )
        slope = np.linalg.lstsq(
            np.column_stack((np.ones(50), cycles[-50:])), prediction[-50:], rcond=None
        )[0][1]
        projected = 200.0 + (prediction[-1] - 0.8) / (-slope) if slope < -1e-7 else np.nan
        charge_time = batteries.loc[batteries["policy"] == policy, "mean_chargetime"].mean()
        summary_rows.append(
            {
                "Model": model.model_type,
                "Policy": policy,
                "SOH1": prediction[0],
                "SOH50": prediction[49],
                "SOH100": prediction[99],
                "SOH150": prediction[149],
                "SOH200": prediction[199],
                "Loss1to200": prediction[0] - prediction[199],
                "MeanSOH1to200": np.trapezoid(prediction, cycles) / 199.0,
                "Slope151to200": slope,
                "ProjectedL80LocalLinear": projected,
                "MeanChargeTime": charge_time,
            }
        )
    return pd.concat(curve_parts, ignore_index=True), pd.DataFrame(summary_rows)
