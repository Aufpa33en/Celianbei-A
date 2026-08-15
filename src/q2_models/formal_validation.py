"""Optimized formal validation for the selected Question 2 model family.

The implementation keeps the parameter coordinate as the validation unit and
the whole battery as the bootstrap unit. Battery summaries are deterministic
functions of each cleaned trajectory, so resampling the precomputed summaries
is exactly equivalent to resampling whole trajectories and recomputing those
same summaries, while avoiding repeated CSV parsing and curve compression.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from itertools import permutations
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from .core import LAMBDA_GRID, battery_degradation_summary, load_clean_data, strategy_summary


EXPOSURE_NAMES = ("J_high_50", "J_high_60", "J_high_70", "H")
MODEL_NAMES = ("ridge_Jhigh50", "ridge_Jhigh60", "ridge_Jhigh70", "ridge_H")
EXPECTED_SIGN = np.array([1.0, -1.0])


@dataclass(frozen=True)
class CohortArrays:
    policy: tuple[str, ...]
    coordinate: tuple[str, ...]
    groups: np.ndarray
    response: np.ndarray
    exposure: np.ndarray
    nearest_features: np.ndarray
    battery_values: tuple[np.ndarray, ...]


def _factorize(values: list[str]) -> np.ndarray:
    mapping: dict[str, int] = {}
    output = []
    for value in values:
        if value not in mapping:
            mapping[value] = len(mapping)
        output.append(mapping[value])
    return np.asarray(output, dtype=int)


def make_cohort_arrays(
    battery: pd.DataFrame,
    strategy: pd.DataFrame,
    cohort: str,
    exclude_battery41: bool = False,
) -> CohortArrays:
    if cohort == "explicit_new_structure":
        selected = strategy[strategy["explicit_new_structure_cohort"].eq(1)].copy()
    elif cohort == "equal_T0_nonbaseline":
        selected = strategy[strategy["equal_time_cohort"].eq(1)].copy()
    elif cohort == "all_complete":
        selected = strategy.copy()
    elif cohort == "explicit_new_without_3_7C":
        selected = strategy[
            strategy["explicit_new_structure_cohort"].eq(1)
            & ~strategy["policy"].str.startswith("3_7C")
        ].copy()
    else:
        raise ValueError(f"unknown cohort: {cohort}")
    if exclude_battery41:
        battery = battery[battery["battery_id"].ne(41)].copy()
    policies = selected["policy"].tolist()
    values = []
    response_rows = []
    for policy in policies:
        group = battery[battery["policy"].eq(policy)]
        array = group[["relative_loss200", "soh200"]].to_numpy(dtype=float)
        if len(array) == 0:
            raise ValueError(f"no batteries remain for policy {policy}")
        values.append(array)
        response_rows.append(array.mean(axis=0))
    return CohortArrays(
        policy=tuple(policies),
        coordinate=tuple(selected["coordinate_id"].tolist()),
        groups=_factorize(selected["coordinate_id"].tolist()),
        response=np.vstack(response_rows),
        exposure=selected.loc[:, EXPOSURE_NAMES].to_numpy(dtype=float),
        nearest_features=selected.loc[:, ["C1", "q", "C2"]].to_numpy(dtype=float),
        battery_values=tuple(values),
    )


def _standardize(train: np.ndarray, test: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float]:
    mean = float(np.mean(train))
    scale = float(np.std(train))
    if scale < 1e-12:
        scale = 1.0
    return (train - mean) / scale, (test - mean) / scale, mean, scale


def _ridge_univariate_fit(x: np.ndarray, y: np.ndarray, ridge_lambda: float) -> tuple[float, float]:
    x_centered = x - np.mean(x)
    y_mean = float(np.mean(y))
    denominator = float(x_centered @ x_centered + ridge_lambda)
    slope = 0.0 if denominator <= 1e-15 else float(x_centered @ (y - y_mean) / denominator)
    intercept = y_mean - slope * float(np.mean(x))
    return intercept, slope


def _select_lambda(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    unique_groups = np.unique(groups)
    scores = []
    for ridge_lambda in LAMBDA_GRID:
        fold_errors = []
        for heldout in unique_groups:
            train = groups != heldout
            test = ~train
            z_train, z_test, _, _ = _standardize(x[train], x[test])
            intercept, slope = _ridge_univariate_fit(z_train, y[train], ridge_lambda)
            fold_errors.append(float(np.mean((intercept + slope * z_test - y[test]) ** 2)))
        scores.append(float(np.mean(fold_errors)))
    minimum = min(scores)
    tolerance = minimum * 1.01 + 1e-15
    eligible = [value for value, score in zip(LAMBDA_GRID, scores) if score <= tolerance]
    return float(max(eligible))


def _fit_full_feature(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> tuple[float, float, float, float]:
    ridge_lambda = _select_lambda(x, y, groups)
    z, _, mean, scale = _standardize(x, x)
    intercept, slope = _ridge_univariate_fit(z, y, ridge_lambda)
    return intercept, slope, ridge_lambda, slope / scale


def _group_equal_metrics(error: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    group_mse = []
    group_mae = []
    for group in np.unique(groups):
        use = groups == group
        group_mse.append(float(np.mean(error[use] ** 2)))
        group_mae.append(float(np.mean(np.abs(error[use]))))
    return float(np.sqrt(np.mean(group_mse))), float(np.mean(group_mae))


def _constant_cv(y: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rmse = np.zeros(y.shape[1])
    mae = np.zeros(y.shape[1])
    for response_index in range(y.shape[1]):
        predictions = np.zeros(len(y))
        for group in np.unique(groups):
            train = groups != group
            predictions[~train] = float(np.mean(y[train, response_index]))
        rmse[response_index], mae[response_index] = _group_equal_metrics(
            predictions - y[:, response_index], groups
        )
    return rmse, mae


def _nearest_cv(y: np.ndarray, features: np.ndarray, groups: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    predictions = np.zeros_like(y)
    for group in np.unique(groups):
        train = groups != group
        test = ~train
        mean = features[train].mean(axis=0)
        scale = features[train].std(axis=0)
        scale[scale < 1e-12] = 1.0
        x_train = (features[train] - mean) / scale
        x_test = (features[test] - mean) / scale
        train_y = y[train]
        for local_index, row in zip(np.flatnonzero(test), x_test):
            nearest = int(np.argmin(np.sum((x_train - row) ** 2, axis=1)))
            predictions[local_index] = train_y[nearest]
    rmse = np.zeros(y.shape[1])
    mae = np.zeros(y.shape[1])
    for response_index in range(y.shape[1]):
        rmse[response_index], mae[response_index] = _group_equal_metrics(
            predictions[:, response_index] - y[:, response_index], groups
        )
    return rmse, mae


def evaluate_exposure_models(y: np.ndarray, exposure: np.ndarray, groups: np.ndarray) -> dict[str, object]:
    constant_rmse, constant_mae = _constant_cv(y, groups)
    model_rows = []
    for feature_index, model in enumerate(MODEL_NAMES):
        predictions = np.zeros_like(y)
        for group in np.unique(groups):
            train = groups != group
            test = ~train
            for response_index in range(y.shape[1]):
                ridge_lambda = _select_lambda(
                    exposure[train, feature_index], y[train, response_index], groups[train]
                )
                z_train, z_test, _, _ = _standardize(
                    exposure[train, feature_index], exposure[test, feature_index]
                )
                intercept, slope = _ridge_univariate_fit(
                    z_train, y[train, response_index], ridge_lambda
                )
                predictions[test, response_index] = intercept + slope * z_test
        rmse = np.zeros(y.shape[1])
        mae = np.zeros(y.shape[1])
        coefficients = np.zeros(y.shape[1])
        lambdas = np.zeros(y.shape[1])
        original_coefficients = np.zeros(y.shape[1])
        for response_index in range(y.shape[1]):
            rmse[response_index], mae[response_index] = _group_equal_metrics(
                predictions[:, response_index] - y[:, response_index], groups
            )
            _, coefficients[response_index], lambdas[response_index], original_coefficients[response_index] = _fit_full_feature(
                exposure[:, feature_index], y[:, response_index], groups
            )
        model_rows.append(
            {
                "model": model,
                "rmse": rmse,
                "mae": mae,
                "improvement": 1.0 - rmse / constant_rmse,
                "coef_standardized": coefficients,
                "coef_original": original_coefficients,
                "lambda": lambdas,
            }
        )
    ranks = np.zeros((len(model_rows), y.shape[1]))
    for response_index in range(y.shape[1]):
        order = np.argsort([row["rmse"][response_index] for row in model_rows])
        ranks[order, response_index] = np.arange(1, len(model_rows) + 1)
    eligible = [
        index
        for index, row in enumerate(model_rows)
        if np.all(np.asarray(row["improvement"]) > 0)
    ]
    if eligible:
        selected_index = min(
            eligible,
            key=lambda index: (float(np.mean(ranks[index])), float(model_rows[index]["rmse"][0])),
        )
        selected = MODEL_NAMES[selected_index]
    else:
        selected = "constant_mean"
    return {
        "constant_rmse": constant_rmse,
        "constant_mae": constant_mae,
        "models": model_rows,
        "selected": selected,
        "ranks": ranks,
    }


def _bootstrap_means(values: tuple[np.ndarray, ...], rng: np.random.Generator) -> np.ndarray:
    rows = []
    for array in values:
        indices = rng.integers(0, len(array), size=len(array))
        rows.append(array[indices].mean(axis=0))
    return np.vstack(rows)


def _bootstrap_chunk(payload: tuple[int, np.ndarray, CohortArrays]) -> list[dict[str, object]]:
    start_index, seeds, cohort = payload
    records = []
    for offset, seed in enumerate(seeds):
        rng = np.random.default_rng(int(seed))
        y = _bootstrap_means(cohort.battery_values, rng)
        result = evaluate_exposure_models(y, cohort.exposure, cohort.groups)
        nearest_rmse, _ = _nearest_cv(y, cohort.nearest_features, cohort.groups)
        for model_index, row in enumerate(result["models"]):
            records.append(
                {
                    "replicate": start_index + offset,
                    "model": row["model"],
                    "selected": row["model"] == result["selected"],
                    "relative_loss_rmse": row["rmse"][0],
                    "soh200_rmse": row["rmse"][1],
                    "relative_loss_improvement": row["improvement"][0],
                    "soh200_improvement": row["improvement"][1],
                    "relative_loss_coef_standardized": row["coef_standardized"][0],
                    "soh200_coef_standardized": row["coef_standardized"][1],
                    "relative_loss_coef_original": row["coef_original"][0],
                    "soh200_coef_original": row["coef_original"][1],
                    "relative_loss_lambda": row["lambda"][0],
                    "soh200_lambda": row["lambda"][1],
                    "constant_relative_loss_rmse": result["constant_rmse"][0],
                    "constant_soh200_rmse": result["constant_rmse"][1],
                    "nearest_relative_loss_rmse": nearest_rmse[0],
                    "nearest_soh200_rmse": nearest_rmse[1],
                }
            )
    return records


def run_bootstrap(
    cohort: CohortArrays,
    n_bootstrap: int,
    seed: int,
    workers: int,
    checkpoint_path: Path,
    chunk_size: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    seeds = np.random.SeedSequence(seed).generate_state(n_bootstrap, dtype=np.uint64)
    chunks = []
    for start in range(0, n_bootstrap, chunk_size):
        chunks.append((start, seeds[start : start + chunk_size], cohort))
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    runtime_rows = []
    records = []
    start_time = perf_counter()
    if workers == 1:
        iterator = ((payload[0], _bootstrap_chunk(payload)) for payload in chunks)
        for chunk_index, (start, chunk_records) in enumerate(iterator, start=1):
            records.extend(chunk_records)
            pd.DataFrame(chunk_records).to_csv(
                checkpoint_path,
                mode="a",
                header=not checkpoint_path.exists(),
                index=False,
                encoding="utf-8-sig" if not checkpoint_path.exists() else "utf-8",
            )
            runtime_rows.append(
                {"completed_replicates": min(start + chunk_size, n_bootstrap), "elapsed_seconds": perf_counter() - start_time}
            )
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_bootstrap_chunk, payload): payload[0] for payload in chunks}
            completed = 0
            for future in as_completed(futures):
                chunk_records = future.result()
                records.extend(chunk_records)
                pd.DataFrame(chunk_records).to_csv(
                    checkpoint_path,
                    mode="a",
                    header=not checkpoint_path.exists(),
                    index=False,
                    encoding="utf-8-sig" if not checkpoint_path.exists() else "utf-8",
                )
                completed += len(chunk_records) // len(MODEL_NAMES)
                runtime_rows.append(
                    {"completed_replicates": completed, "elapsed_seconds": perf_counter() - start_time}
                )
    frame = pd.DataFrame(records).sort_values(["replicate", "model"]).reset_index(drop=True)
    frame.to_csv(checkpoint_path, index=False, encoding="utf-8-sig")
    return frame, pd.DataFrame(runtime_rows).sort_values("completed_replicates")


def summarize_bootstrap(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = []
    frequencies = []
    n_replicates = frame["replicate"].nunique()
    for model, group in frame.groupby("model", observed=True):
        frequencies.append(
            {
                "model": model,
                "selection_count": int(group["selected"].sum()),
                "selection_frequency": float(group["selected"].mean()),
                "n_bootstrap": n_replicates,
            }
        )
        for column in (
            "relative_loss_improvement", "soh200_improvement",
            "relative_loss_coef_standardized", "soh200_coef_standardized",
            "relative_loss_coef_original", "soh200_coef_original",
        ):
            values = group[column].to_numpy(dtype=float)
            summaries.append(
                {
                    "model": model,
                    "metric": column,
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "q025": float(np.quantile(values, 0.025)),
                    "q975": float(np.quantile(values, 0.975)),
                    "positive_share": float(np.mean(values > 0)),
                    "negative_share": float(np.mean(values < 0)),
                    "n_bootstrap": n_replicates,
                }
            )
        both_improve = (
            group["relative_loss_improvement"].gt(0)
            & group["soh200_improvement"].gt(0)
        )
        frequencies[-1]["both_responses_improve_share"] = float(both_improve.mean())
        frequencies[-1]["expected_sign_both_share"] = float(
            (
                group["relative_loss_coef_standardized"].gt(0)
                & group["soh200_coef_standardized"].lt(0)
            ).mean()
        )
    selected_total = sum(row["selection_count"] for row in frequencies)
    frequencies.append(
        {
            "model": "constant_mean",
            "selection_count": int(n_replicates - selected_total),
            "selection_frequency": float((n_replicates - selected_total) / n_replicates),
            "n_bootstrap": n_replicates,
            "both_responses_improve_share": np.nan,
            "expected_sign_both_share": np.nan,
        }
    )
    return pd.DataFrame(summaries), pd.DataFrame(frequencies).sort_values("selection_frequency", ascending=False)


def _direction_score(y: np.ndarray, x: np.ndarray, groups: np.ndarray) -> float:
    scores = []
    y_scale = np.std(y, axis=0)
    y_scale[y_scale < 1e-12] = 1.0
    for response_index in range(2):
        _, slope, _, _ = _fit_full_feature(x, y[:, response_index], groups)
        scores.append(EXPECTED_SIGN[response_index] * slope / y_scale[response_index])
    return float(min(scores))


def run_exchangeability_sensitivity(cohort: CohortArrays) -> tuple[pd.DataFrame, pd.DataFrame]:
    observed_scores = np.array(
        [_direction_score(cohort.response, cohort.exposure[:, index], cohort.groups) for index in range(len(MODEL_NAMES))]
    )
    observed_max = float(np.max(observed_scores))
    rows = []
    for permutation_index, order in enumerate(permutations(range(len(cohort.policy)))):
        permuted = cohort.response[np.asarray(order, dtype=int)]
        scores = np.array(
            [_direction_score(permuted, cohort.exposure[:, index], cohort.groups) for index in range(len(MODEL_NAMES))]
        )
        rows.append(
            {
                "permutation": permutation_index,
                "max_direction_score": float(np.max(scores)),
                "selected_by_score": MODEL_NAMES[int(np.argmax(scores))],
                **{f"score_{model}": float(score) for model, score in zip(MODEL_NAMES, scores)},
            }
        )
    distribution = pd.DataFrame(rows)
    adjusted_tail_fraction = float(np.mean(distribution["max_direction_score"] >= observed_max))
    diagnostic_fields = {
        "artifact_role": "diagnostic_not_confirmatory_test",
        "exchangeability_assumption": "six_policy_means_exchangeable_despite_unequal_n_and_variance",
        "confirmatory_p_value_available": False,
    }
    summary_rows = [
        {
            "diagnostic": "max_over_four_exposures",
            "model": "selected_family",
            "observed_score": observed_max,
            "hypothetical_exchangeability_tail_fraction": adjusted_tail_fraction,
            "n_label_permutations": len(distribution),
            **diagnostic_fields,
        }
    ]
    for model, observed in zip(MODEL_NAMES, observed_scores):
        values = distribution[f"score_{model}"].to_numpy(dtype=float)
        summary_rows.append(
            {
                "diagnostic": "single_exposure_unadjusted",
                "model": model,
                "observed_score": float(observed),
                "hypothetical_exchangeability_tail_fraction": float(np.mean(values >= observed)),
                "n_label_permutations": len(values),
                **diagnostic_fields,
            }
        )
    return distribution, pd.DataFrame(summary_rows)


def sensitivity_table(battery: pd.DataFrame, strategy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specifications = (
        ("explicit_new_structure", False),
        ("equal_T0_nonbaseline", False),
        ("all_complete", False),
        ("explicit_new_without_3_7C", False),
        ("explicit_new_structure", True),
    )
    for cohort_name, exclude_battery41 in specifications:
        cohort = make_cohort_arrays(battery, strategy, cohort_name, exclude_battery41=exclude_battery41)
        result = evaluate_exposure_models(cohort.response, cohort.exposure, cohort.groups)
        nearest_rmse, nearest_mae = _nearest_cv(cohort.response, cohort.nearest_features, cohort.groups)
        rows.append(
            {
                "cohort": cohort_name,
                "exclude_battery41": exclude_battery41,
                "model": "constant_mean",
                "relative_loss_rmse": result["constant_rmse"][0],
                "soh200_rmse": result["constant_rmse"][1],
                "relative_loss_improvement": 0.0,
                "soh200_improvement": 0.0,
                "selected_explanatory": result["selected"] == "constant_mean",
                "n_policy": len(cohort.policy),
                "n_coordinate": len(np.unique(cohort.groups)),
            }
        )
        rows.append(
            {
                "cohort": cohort_name,
                "exclude_battery41": exclude_battery41,
                "model": "nearest_coordinate",
                "relative_loss_rmse": nearest_rmse[0],
                "soh200_rmse": nearest_rmse[1],
                "relative_loss_improvement": 1.0 - nearest_rmse[0] / result["constant_rmse"][0],
                "soh200_improvement": 1.0 - nearest_rmse[1] / result["constant_rmse"][1],
                "selected_explanatory": False,
                "n_policy": len(cohort.policy),
                "n_coordinate": len(np.unique(cohort.groups)),
            }
        )
        for row in result["models"]:
            rows.append(
                {
                    "cohort": cohort_name,
                    "exclude_battery41": exclude_battery41,
                    "model": row["model"],
                    "relative_loss_rmse": row["rmse"][0],
                    "soh200_rmse": row["rmse"][1],
                    "relative_loss_improvement": row["improvement"][0],
                    "soh200_improvement": row["improvement"][1],
                    "relative_loss_coef_standardized": row["coef_standardized"][0],
                    "soh200_coef_standardized": row["coef_standardized"][1],
                    "selected_explanatory": row["model"] == result["selected"],
                    "n_policy": len(cohort.policy),
                    "n_coordinate": len(np.unique(cohort.groups)),
                }
            )
    return pd.DataFrame(rows)


def formal_decision(
    frequency: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> pd.DataFrame:
    exposure_frequency = frequency[frequency["model"].isin(MODEL_NAMES)].sort_values(
        "selection_frequency", ascending=False
    )
    top = exposure_frequency.iloc[0]
    without_extreme = sensitivity[
        sensitivity["cohort"].eq("explicit_new_without_3_7C")
        & sensitivity["selected_explanatory"].astype(bool)
    ].iloc[0]
    without_battery41 = sensitivity[
        sensitivity["cohort"].eq("explicit_new_structure")
        & sensitivity["exclude_battery41"].astype(bool)
        & sensitivity["selected_explanatory"].astype(bool)
    ].iloc[0]
    criteria = {
        "top_exposure_selection_frequency_ge_0_50": bool(top["selection_frequency"] >= 0.50),
        "top_exposure_both_improve_share_ge_0_80": bool(top["both_responses_improve_share"] >= 0.80),
        "top_exposure_expected_sign_share_ge_0_90": bool(top["expected_sign_both_share"] >= 0.90),
        "confirmatory_randomization_basis_available": False,
        "high_SOC_family_survives_excluding_3_7C": str(without_extreme["model"]).startswith("ridge_"),
        "high_SOC_family_survives_excluding_battery41": str(without_battery41["model"]).startswith("ridge_"),
    }
    decision = "do_not_claim_independent_parameter_effect; descriptive_association_only"
    rows = [
        {
            "decision": decision,
            "top_bootstrap_model": top["model"],
            "criterion": key,
            "passed": value,
        }
        for key, value in criteria.items()
    ]
    return pd.DataFrame(rows)


def run_formal_validation(
    project_root: Path,
    n_bootstrap: int = 2000,
    seed: int = 20260814,
    workers: int = 8,
) -> dict[str, pd.DataFrame]:
    start = perf_counter()
    cycles, meta = load_clean_data(project_root)
    battery = battery_degradation_summary(cycles, meta)
    strategy = strategy_summary(battery)
    main = make_cohort_arrays(battery, strategy, "explicit_new_structure")
    output_root = project_root / "result" / "q2" / "03_formal_validation"
    output_root.mkdir(parents=True, exist_ok=True)
    bootstrap, runtime = run_bootstrap(
        main,
        n_bootstrap=n_bootstrap,
        seed=seed,
        workers=workers,
        checkpoint_path=output_root / "bootstrap_replicates.csv",
    )
    summary, frequency = summarize_bootstrap(bootstrap)
    permutation_distribution, permutation_summary = run_exchangeability_sensitivity(main)
    sensitivity = sensitivity_table(battery, strategy)
    decision = formal_decision(frequency, sensitivity)
    runtime = pd.concat(
        [
            runtime,
            pd.DataFrame(
                [{"completed_replicates": n_bootstrap, "elapsed_seconds": perf_counter() - start, "stage": "all_complete"}]
            ),
        ],
        ignore_index=True,
    )
    outputs = {
        "bootstrap_summary": summary,
        "bootstrap_selection_frequency": frequency,
        "permutation_distribution": permutation_distribution,
        "permutation_test_summary": permutation_summary,
        "sensitivity_model_comparison": sensitivity,
        "formal_model_decision": decision,
        "runtime_checkpoints": runtime,
    }
    for name, frame in outputs.items():
        frame.to_csv(output_root / f"{name}.csv", index=False, encoding="utf-8-sig")
    manifest = [
        {"file": "bootstrap_replicates.csv", "rows": len(bootstrap), "columns": len(bootstrap.columns)},
        *[
            {"file": f"{name}.csv", "rows": len(frame), "columns": len(frame.columns)}
            for name, frame in outputs.items()
        ],
    ]
    pd.DataFrame(manifest).to_csv(output_root / "result_manifest.csv", index=False, encoding="utf-8-sig")
    return {"bootstrap_replicates": bootstrap, **outputs}
