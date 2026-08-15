"""Full nested-LOBO validation and final Q3 prediction.

This module is intentionally additive: the frozen smoke implementation and its
outputs remain unchanged.  Every outer fold retunes B/C/D using only the other
complete batteries; the nine prediction-test batteries are used only after
model selection is frozen.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CONFIG, Q3Config
from .core import (
    BatteryRecord,
    complete_battery_ids,
    fit_power_law,
    load_records,
    power_law_eol,
    prediction_metrics,
    project_absolute_prediction,
    slope,
)
from .experiments import MODELS, _summary_tables
from .features import prefix_numeric_features
from .models import (
    predict_individual_power,
    predict_linear_trend,
    predict_persistence,
    predict_strategy_transfer,
    predict_trajectory_ridge,
    select_strategy_lambda,
    select_trajectory_hyperparameters,
)


FULL_VERSION = "q3_full_v2"
SCORE_WEIGHTS = {50: 0.15, 100: 0.25, 150: 0.60}
ABLATION_MODES = ("dynamic_only", "dynamic_plus_strategy", "full_with_policy")


def _full_config(config: Q3Config) -> Q3Config:
    return replace(config, version=FULL_VERSION)


def protected_file_hashes(project_root: Path) -> pd.DataFrame:
    """Hash data, existing programs and frozen smoke outputs."""
    roots = [
        project_root / "A题",
        project_root / "data",
        project_root / "scripts",
        project_root / "src",
        project_root / "tests",
        project_root / "result" / "q3" / "01_smoke_test",
    ]
    rows: list[dict[str, object]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            rows.append(
                {
                    "path": str(path.relative_to(project_root)),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return pd.DataFrame(rows)


def compare_protected_hashes(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    merged = before.merge(after, on="path", how="outer", suffixes=("_before", "_after"), indicator=True)
    merged["unchanged"] = (
        merged["_merge"].eq("both")
        & merged["size_bytes_before"].eq(merged["size_bytes_after"])
        & merged["sha256_before"].eq(merged["sha256_after"])
    )
    return merged


def validate_record_shapes(records: dict[int, BatteryRecord], meta: pd.DataFrame) -> pd.DataFrame:
    """Enforce the cycle-index assumptions used by every Q3 model."""
    rows = []
    for row in meta.itertuples(index=False):
        battery_id = int(row.battery_id)
        expected_end = 150 if int(row.prediction_test) == 1 else 200
        record = records[battery_id]
        observed = record.cycles["cycle"].to_numpy(dtype=int)
        valid = len(observed) == expected_end and np.array_equal(
            observed, np.arange(1, expected_end + 1)
        )
        rows.append({"battery_id": battery_id, "prediction_test": int(row.prediction_test),
                     "expected_end": expected_end, "observed_rows": len(observed),
                     "continuous_unique_cycles": valid})
    result = pd.DataFrame(rows)
    if len(result) != 49 or not result["continuous_unique_cycles"].all():
        raise AssertionError("Q3 requires 40 complete 1-200 and nine test 1-150 trajectories")
    return result


def _strategy_equal_score(
    records: list[BatteryRecord], predictions: dict[int, np.ndarray], config: Q3Config
) -> tuple[float, float]:
    """Nine-strategy equal RMSE and worst-battery RMSE on OOF predictions."""
    policy_mse: dict[str, list[float]] = {}
    battery_rmse = []
    for record in records:
        pred_abs = record.baseline * predictions[record.battery_id]
        truth = record.absolute_future(config.future_start, config.future_end)
        mse = float(np.mean((pred_abs - truth) ** 2))
        policy_mse.setdefault(record.policy, []).append(mse)
        battery_rmse.append(np.sqrt(mse))
    score = float(np.mean([np.sqrt(np.mean(values)) for values in policy_mse.values()]))
    return score, float(np.max(battery_rmse))


def _select_strategy_equal(
    records: list[BatteryRecord], L: int, config: Q3Config
) -> tuple[float, dict[float, dict[int, np.ndarray]], dict[float, float]]:
    _, candidates = select_strategy_lambda(records, L, config)
    scores = {value: _strategy_equal_score(records, pred, config)[0] for value, pred in candidates.items()}
    selected = min(scores, key=lambda value: (scores[value], -value))
    return float(selected), candidates, scores


def _select_trajectory_equal(
    records: list[BatteryRecord], L: int, config: Q3Config
) -> tuple[tuple[int, float], dict[tuple[int, float], dict[int, np.ndarray]], dict[tuple[int, float], float]]:
    _, candidates = select_trajectory_hyperparameters(records, L, config)
    scores = {key: _strategy_equal_score(records, pred, config)[0] for key, pred in candidates.items()}
    selected = min(scores, key=lambda key: (scores[key], -key[1], key[0]))
    return selected, candidates, scores


def _choose_ensemble_weight(
    records: list[BatteryRecord],
    b_oof: dict[int, np.ndarray],
    c_oof: dict[int, np.ndarray],
    config: Q3Config,
) -> tuple[float, dict[float, float]]:
    scores: dict[float, float] = {}
    for weight in config.ensemble_weight_grid:
        combined = {
            record.battery_id: weight * b_oof[record.battery_id]
            + (1.0 - weight) * c_oof[record.battery_id]
            for record in records
        }
        scores[float(weight)] = _strategy_equal_score(records, combined, config)[0]
    best = min(scores.values())
    tied = [w for w, value in scores.items() if np.isclose(value, best, rtol=0, atol=1e-12)]
    # Frozen rule: prefer a boundary (simpler single model), and prefer B at equal distance.
    tied.sort(key=lambda w: (min(w, 1.0 - w), -w))
    return float(tied[0]), scores


def _predict_models(
    train: list[BatteryRecord],
    target: BatteryRecord,
    L: int,
    selected_lambda: float,
    selected_c: tuple[int, float],
    selected_weight: float,
    config: Q3Config,
) -> tuple[dict[str, np.ndarray], dict[str, dict[str, float] | None]]:
    p0 = predict_persistence(target, L, config)
    p1 = predict_linear_trend(target, L, config)
    power, power_fit = predict_individual_power(target, L, config)
    strategy, _ = predict_strategy_transfer(train, target, L, selected_lambda, config)
    ridge = predict_trajectory_ridge(train, target, L, selected_c, config)
    ensemble = selected_weight * strategy + (1.0 - selected_weight) * ridge
    return (
        {
            "P0_persistence": p0,
            "P1_linear": p1,
            "A_power": power,
            "B_strategy": strategy,
            "C_ridge": ridge,
            "D_ensemble": ensemble,
        },
        {"A_power": power_fit},
    )


def _inner_family_oof(
    records: list[BatteryRecord], L: int, config: Q3Config
) -> tuple[
    dict[str, dict[int, np.ndarray]], dict[str, float], dict[str, float],
    float, tuple[int, float], float,
]:
    """Generate training-only OOF predictions for all six model families."""
    selected_lambda, b_candidates, _ = _select_strategy_equal(records, L, config)
    selected_c, c_candidates, _ = _select_trajectory_equal(records, L, config)
    b_oof = b_candidates[selected_lambda]
    c_oof = c_candidates[selected_c]
    selected_weight, _ = _choose_ensemble_weight(records, b_oof, c_oof, config)
    maps: dict[str, dict[int, np.ndarray]] = {
        "P0_persistence": {}, "P1_linear": {}, "A_power": {},
        "B_strategy": b_oof, "C_ridge": c_oof,
        "D_ensemble": {
            record.battery_id: selected_weight * b_oof[record.battery_id]
            + (1.0 - selected_weight) * c_oof[record.battery_id]
            for record in records
        },
    }
    for target in records:
        maps["P0_persistence"][target.battery_id] = predict_persistence(target, L, config)
        maps["P1_linear"][target.battery_id] = predict_linear_trend(target, L, config)
        maps["A_power"][target.battery_id] = predict_individual_power(target, L, config)[0]
    scores, worst = {}, {}
    for model in MODELS:
        scores[model], worst[model] = _strategy_equal_score(records, maps[model], config)
    return maps, scores, worst, selected_lambda, selected_c, selected_weight


def _choose_family(
    scores_by_l: dict[int, dict[str, float]],
    worst_by_l: dict[int, dict[str, float]],
    config: Q3Config,
) -> tuple[str, dict[str, float], dict[str, float]]:
    scores = {
        model: sum(SCORE_WEIGHTS[L] * scores_by_l[L][model] for L in config.early_lengths)
        for model in MODELS
    }
    worst = {
        model: sum(SCORE_WEIGHTS[L] * worst_by_l[L][model] for L in config.early_lengths)
        for model in MODELS
    }
    best = min(scores.values())
    tied = [model for model in MODELS if (scores[model] - best) / max(best, 1e-15) <= config.tie_relative_tolerance]
    tied.sort(key=lambda model: (worst[model], MODELS.index(model)))
    return tied[0], scores, worst


def _prediction_rows(
    target: BatteryRecord,
    L: int,
    predictions: dict[str, np.ndarray],
    config: Q3Config,
) -> list[dict[str, object]]:
    truth = target.absolute_future(config.future_start, config.future_end)
    rows: list[dict[str, object]] = []
    anchor = target.baseline * target.relative_at(L)
    for model, relative in predictions.items():
        raw = target.baseline * relative
        projected = project_absolute_prediction(raw, anchor, config)
        for offset, cycle in enumerate(range(config.future_start, config.future_end + 1)):
            rows.append(
                {
                    "version": config.version,
                    "model": model,
                    "L": L,
                    "battery_id": target.battery_id,
                    "policy": target.policy,
                    "cycle": cycle,
                    "y_true": truth[offset],
                    "y_pred_raw": raw[offset],
                    "y_pred_projected": projected[offset],
                    "t80_raw": np.nan,
                    "eol_status_raw": "not_used_for_validation_selection",
                    "t80_projected": np.nan,
                    "eol_status_projected": "not_used_for_validation_selection",
                }
            )
    return rows


def _select_from_summary(
    summary: pd.DataFrame, battery: pd.DataFrame, config: Q3Config
) -> pd.DataFrame:
    raw = summary.loc[summary["prediction_variant"].eq("raw")]
    scores: dict[str, float] = {}
    worst: dict[str, float] = {}
    for model in MODELS:
        current = raw.loc[raw["model"].eq(model)].set_index("L")
        scores[model] = sum(
            SCORE_WEIGHTS[L] * float(current.loc[L, "strategy_equal_rmse"])
            for L in config.early_lengths
        )
        worst[model] = sum(
            SCORE_WEIGHTS[L] * float(current.loc[L, "worst_battery_rmse"])
            for L in config.early_lengths
        )
    remaining = sorted(MODELS, key=lambda model: (scores[model], MODELS.index(model)))
    order: list[str] = []
    while remaining:
        best = scores[remaining[0]]
        tied = [m for m in remaining if (scores[m] - best) / max(best, 1e-15) <= config.tie_relative_tolerance]
        tied.sort(key=lambda m: (worst[m], MODELS.index(m)))
        order.extend(tied)
        remaining = [m for m in remaining if m not in tied]
    ranks = {model: rank + 1 for rank, model in enumerate(order)}
    rows = []
    for model in MODELS:
        l150 = raw.loc[raw["model"].eq(model) & raw["L"].eq(150)].iloc[0]
        rows.append(
            {
                "version": config.version,
                "model": model,
                "selection_variant": "raw",
                "weighted_score": scores[model],
                "weighted_worst_battery_rmse": worst[model],
                "L150_strategy_equal_rmse": l150["strategy_equal_rmse"],
                "L150_pooled_rmse": l150["pooled_rmse"],
                "final_rank": ranks[model],
                "selected": ranks[model] == 1,
                "decision_role": "multi_length_robustness_sensitivity_not_deployment",
            }
        )
    return pd.DataFrame(rows).sort_values("final_rank")


def _bootstrap_selection(
    battery_metrics: pd.DataFrame,
    selection: pd.DataFrame,
    repetitions: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = battery_metrics.loc[battery_metrics["prediction_variant"].eq("raw")].copy()
    raw["mse"] = raw["rmse"] ** 2
    policies = sorted(raw["policy"].unique())
    rng = np.random.default_rng(seed)
    score_samples = {model: np.empty(repetitions) for model in MODELS}
    worst_samples = {model: np.empty(repetitions) for model in MODELS}
    winners = {model: 0 for model in MODELS}
    grouped_ids = {
        policy: sorted(raw.loc[raw["policy"].eq(policy), "battery_id"].unique()) for policy in policies
    }
    indexed = raw.set_index(["model", "L", "battery_id"])["mse"]
    for rep in range(repetitions):
        sampled = {
            policy: rng.choice(ids, size=len(ids), replace=True).tolist()
            for policy, ids in grouped_ids.items()
        }
        for model in MODELS:
            score = 0.0
            weighted_worst = 0.0
            for L, weight in SCORE_WEIGHTS.items():
                policy_rmse = []
                battery_rmse = []
                for policy in policies:
                    values = [float(indexed.loc[(model, L, int(battery_id))]) for battery_id in sampled[policy]]
                    policy_rmse.append(float(np.sqrt(np.mean(values))))
                    battery_rmse.extend(float(np.sqrt(value)) for value in values)
                score += weight * float(np.mean(policy_rmse))
                weighted_worst += weight * max(battery_rmse)
            score_samples[model][rep] = score
            worst_samples[model][rep] = weighted_worst
        best_score = min(score_samples[model][rep] for model in MODELS)
        tied = [
            model for model in MODELS
            if score_samples[model][rep] <= best_score * (1.0 + CONFIG.tie_relative_tolerance)
        ]
        winner = min(tied, key=lambda m: (worst_samples[m][rep], MODELS.index(m)))
        winners[winner] += 1
    rows = []
    point = selection.set_index("model")["weighted_score"]
    for model in MODELS:
        values = score_samples[model]
        rows.append(
            {
                "version": FULL_VERSION,
                "model": model,
                "point_score": point.loc[model],
                "bootstrap_median": np.median(values),
                "ci95_low": np.quantile(values, 0.025),
                "ci95_high": np.quantile(values, 0.975),
                "frozen_rule_winner_frequency": winners[model] / repetitions,
                "repetitions": repetitions,
                "seed": seed,
            }
        )
    best_two = selection.sort_values("final_rank").head(2)["model"].tolist()
    difference = score_samples[best_two[0]] - score_samples[best_two[1]]
    pair = pd.DataFrame(
        [
            {
                "version": FULL_VERSION,
                "model_a": best_two[0],
                "model_b": best_two[1],
                "difference_a_minus_b": point.loc[best_two[0]] - point.loc[best_two[1]],
                "bootstrap_ci95_low": np.quantile(difference, 0.025),
                "bootstrap_ci95_high": np.quantile(difference, 0.975),
                "probability_a_lower": np.mean(difference < 0),
                "repetitions": repetitions,
            }
        ]
    )
    return pd.DataFrame(rows), pair


@dataclass
class _AblationTransformer:
    medians: np.ndarray
    means: np.ndarray
    scales: np.ndarray
    keep: np.ndarray
    policies: tuple[str, ...]
    mode: str

    @classmethod
    def fit(cls, records: list[BatteryRecord], L: int, mode: str, config: Q3Config):
        raw = np.vstack([prefix_numeric_features(record, L, config) for record in records])
        if mode == "dynamic_only":
            raw = raw[:, :-9]
        medians = np.nanmedian(raw, axis=0)
        medians = np.where(np.isfinite(medians), medians, 0.0)
        filled = np.where(np.isfinite(raw), raw, medians)
        means = filled.mean(axis=0)
        scales = filled.std(axis=0, ddof=1) if len(records) > 1 else np.ones(raw.shape[1])
        keep = np.isfinite(scales) & (scales > 1e-12)
        scales = np.where(keep, scales, 1.0)
        policies = tuple(sorted({record.policy for record in records})) if mode == "full_with_policy" else ()
        return cls(medians, means, scales, keep, policies, mode)

    def transform(self, records: list[BatteryRecord], L: int, config: Q3Config) -> np.ndarray:
        raw = np.vstack([prefix_numeric_features(record, L, config) for record in records])
        if self.mode == "dynamic_only":
            raw = raw[:, :-9]
        filled = np.where(np.isfinite(raw), raw, self.medians)
        numeric = ((filled - self.means) / self.scales)[:, self.keep]
        if not self.policies:
            return numeric
        one_hot = np.zeros((len(records), len(self.policies)))
        positions = {policy: index for index, policy in enumerate(self.policies)}
        for row, record in enumerate(records):
            if record.policy in positions:
                one_hot[row, positions[record.policy]] = 1.0
        return np.column_stack((numeric, one_hot))


def _c_mode_candidates(
    train: list[BatteryRecord], target: BatteryRecord, L: int, mode: str, config: Q3Config
) -> dict[tuple[int, float], np.ndarray]:
    transformer = _AblationTransformer.fit(train, L, mode, config)
    X = transformer.transform(train, L, config)
    x = transformer.transform([target], L, config)
    Y = np.vstack([
        record.relative_soh[config.future_start - 1 : config.future_end] - record.relative_at(L)
        for record in train
    ])
    mean = Y.mean(axis=0)
    centered = Y - mean
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    max_rank = max(1, min(len(train) - 1, centered.shape[1], vt.shape[0]))
    xtx = X.T @ X
    eye = np.eye(X.shape[1])
    output = {}
    for requested_k in config.k_grid:
        k = min(requested_k, max_rank)
        basis = vt[:k].T
        scores = centered @ basis
        for alpha in config.alpha_grid:
            coef = np.linalg.solve(xtx + alpha * eye, X.T @ scores)
            output[(requested_k, float(alpha))] = target.relative_at(L) + (mean + (x @ coef @ basis.T).ravel())
    return output


def _select_c_mode(records: list[BatteryRecord], L: int, mode: str, config: Q3Config):
    predictions: dict[tuple[int, float], dict[int, np.ndarray]] = {}
    for target in records:
        train = [record for record in records if record.battery_id != target.battery_id]
        candidates = _c_mode_candidates(train, target, L, mode, config)
        for key, pred in candidates.items():
            predictions.setdefault(key, {})[target.battery_id] = pred
    scores = {key: _strategy_equal_score(records, value, config)[0] for key, value in predictions.items()}
    ranked = sorted(scores, key=lambda key: (scores[key], -key[1], key[0]))
    return ranked[0], predictions[ranked[0]]


def run_c_ablation(
    complete: list[BatteryRecord], main_predictions: pd.DataFrame, config: Q3Config
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    # Reuse the already nested full-feature C predictions.
    full = main_predictions.loc[
        main_predictions["model"].eq("C_ridge"),
        ["L", "battery_id", "policy", "y_true", "y_pred_raw"],
    ]
    for (L, battery_id, policy), group in full.groupby(["L", "battery_id", "policy"]):
        metrics = prediction_metrics(group["y_true"].to_numpy(), group["y_pred_raw"].to_numpy())
        rows.append({"version": config.version, "mode": "full_with_policy", "L": L,
                     "battery_id": battery_id, "policy": policy, **metrics})
    for mode in ("dynamic_only", "dynamic_plus_strategy"):
        for L in config.early_lengths:
            for target in complete:
                outer_train = [record for record in complete if record.battery_id != target.battery_id]
                selected, _ = _select_c_mode(outer_train, L, mode, config)
                pred = _c_mode_candidates(outer_train, target, L, mode, config)[selected]
                truth = target.absolute_future(config.future_start, config.future_end)
                rows.append({"version": config.version, "mode": mode, "L": L,
                             "battery_id": target.battery_id, "policy": target.policy,
                             **prediction_metrics(truth, target.baseline * pred)})
    battery = pd.DataFrame(rows)
    summary_rows = []
    for (mode, L), group in battery.groupby(["mode", "L"]):
        policy_rmse = [float(np.sqrt(np.mean(policy["rmse"] ** 2))) for _, policy in group.groupby("policy")]
        summary_rows.append({"version": config.version, "mode": mode, "L": L,
                             "strategy_equal_rmse": np.mean(policy_rmse),
                             "battery_equal_rmse": np.sqrt(np.mean(group["rmse"] ** 2)),
                             "mae": group["mae"].mean(), "worst_battery_rmse": group["rmse"].max()})
    return battery, pd.DataFrame(summary_rows)


def _deployment_candidates(summary: pd.DataFrame, config: Q3Config) -> pd.DataFrame:
    rows = []
    fixed = summary.loc[
        summary["prediction_variant"].eq("raw") & summary["L"].eq(150)
    ]
    for row in fixed.itertuples(index=False):
        rows.append({"model": row.model, "source": "fixed_family_outer_LOBO",
                     "strategy_equal_rmse": row.strategy_equal_rmse,
                     "worst_battery_rmse": row.worst_battery_rmse})
    result = pd.DataFrame(rows)
    best = float(result["strategy_equal_rmse"].min())
    result["within_tie_tolerance"] = (
        (result["strategy_equal_rmse"] - best) / max(best, 1e-15)
        <= config.tie_relative_tolerance
    )
    tied = result.loc[result["within_tie_tolerance"]].sort_values(
        ["worst_battery_rmse", "strategy_equal_rmse", "model"]
    )
    selected = str(tied.iloc[0]["model"])
    result["selected_for_L150_deployment"] = result["model"].eq(selected)
    result["version"] = config.version
    result["selection_scope"] = "L150_only_matches_final_prediction_information"
    return result.sort_values(["selected_for_L150_deployment", "strategy_equal_rmse"], ascending=[False, True])


def run_full_validation(
    project_root: Path,
    config: Q3Config = CONFIG,
    bootstrap_repetitions: int = 5000,
) -> dict[str, pd.DataFrame]:
    run_started = time.perf_counter()
    config = _full_config(config)
    load_started = time.perf_counter()
    records, meta, _ = load_records(project_root)
    shape_checks = validate_record_shapes(records, meta)
    complete = [records[battery_id] for battery_id in complete_battery_ids(meta)]
    if len(complete) != 40:
        raise AssertionError("Full validation requires exactly 40 complete batteries")
    runtime_rows = [{"version": config.version, "scope": "run", "outer_battery_id": np.nan,
                     "model": "ALL", "L": np.nan, "stage": "load_and_validate",
                     "seconds": time.perf_counter() - load_started}]
    prediction_rows = []
    selector_prediction_rows = []
    selector_fold_rows = []
    tuning_rows = []
    for fold, target in enumerate(complete, start=1):
        scores_by_l: dict[int, dict[str, float]] = {}
        worst_by_l: dict[int, dict[str, float]] = {}
        target_predictions: dict[int, dict[str, np.ndarray]] = {}
        fold_tuning: dict[int, tuple[float, tuple[int, float], float]] = {}
        outer_train = [record for record in complete if record.battery_id != target.battery_id]
        if len(outer_train) != 39 or target.battery_id in {r.battery_id for r in outer_train}:
            raise AssertionError("Outer LOBO isolation failed")
        for L in config.early_lengths:
            started = time.perf_counter()
            (
                _, inner_scores, inner_worst, selected_lambda,
                selected_c, selected_weight,
            ) = _inner_family_oof(outer_train, L, config)
            nested_seconds = time.perf_counter() - started
            scores_by_l[L] = inner_scores
            worst_by_l[L] = inner_worst
            fold_tuning[L] = (selected_lambda, selected_c, selected_weight)
            started_predict = time.perf_counter()
            predictions, _ = _predict_models(
                outer_train, target, L, selected_lambda, selected_c, selected_weight, config
            )
            target_predictions[L] = predictions
            prediction_rows.extend(_prediction_rows(target, L, predictions, config))
            predict_seconds = time.perf_counter() - started_predict
            tuning_rows.append(
                {
                    "version": config.version,
                    "L": L,
                    "outer_fold": fold,
                    "held_out_battery_id": target.battery_id,
                    "lambda_gamma": selected_lambda,
                    "K": selected_c[0],
                    "alpha": selected_c[1],
                    "w_strategy": selected_weight,
                    "inner_B_strategy_equal_rmse": inner_scores["B_strategy"],
                    "inner_C_strategy_equal_rmse": inner_scores["C_ridge"],
                    "inner_D_strategy_equal_rmse": inner_scores["D_ensemble"],
                    "n_outer_train": len(outer_train),
                    "outer_id_in_train": False,
                }
            )
            runtime_rows.extend(
                [
                    {"version": config.version, "L": L, "outer_fold": fold,
                     "model": "B_C_D_inclusive", "stage": "nested_fit", "seconds": nested_seconds},
                    {"version": config.version, "L": L, "outer_fold": fold,
                     "model": "all_models", "stage": "outer_predict", "seconds": predict_seconds},
                ]
            )
        chosen, family_scores, family_worst = _choose_family(scores_by_l, worst_by_l, config)
        selector_fold_rows.append(
            {
                "version": config.version,
                "outer_fold": fold,
                "held_out_battery_id": target.battery_id,
                "held_out_policy": target.policy,
                "n_outer_train": 39,
                "selected_family": chosen,
                **{f"score_{model}": family_scores[model] for model in MODELS},
                **{f"worst_{model}": family_worst[model] for model in MODELS},
            }
        )
        for L in config.early_lengths:
            selected_rows = _prediction_rows(
                target, L, {"NESTED_selector": target_predictions[L][chosen]}, config
            )
            for row in selected_rows:
                row["selected_base_model"] = chosen
            selector_prediction_rows.extend(selected_rows)
        if fold % 5 == 0 or fold == len(complete):
            print(f"Q3 full validation outer folds: {fold}/{len(complete)}", flush=True)
    predictions = pd.DataFrame(prediction_rows)
    selector_predictions = pd.DataFrame(selector_prediction_rows)
    battery, summary = _summary_tables(predictions, config)
    selector_battery, selector_summary = _summary_tables(selector_predictions, config)
    selection = _select_from_summary(summary, battery, config)
    stage_started = time.perf_counter()
    bootstrap, pairwise = _bootstrap_selection(
        battery, selection, bootstrap_repetitions, config.seed
    )
    runtime_rows.append({"version": config.version, "scope": "run", "outer_battery_id": np.nan,
                         "model": "ALL", "L": np.nan, "stage": "bootstrap",
                         "seconds": time.perf_counter() - stage_started})
    stage_started = time.perf_counter()
    ablation_battery, ablation_summary = run_c_ablation(complete, predictions, config)
    deployment_candidates = _deployment_candidates(summary, config)
    runtime_rows.append({"version": config.version, "scope": "run", "outer_battery_id": np.nan,
                         "model": "C_ridge", "L": np.nan, "stage": "c_ablation",
                         "seconds": time.perf_counter() - stage_started})
    print("Q3 C-feature ablation complete", flush=True)
    # Final prediction always observes 150 cycles, so deployment is frozen from
    # honest L=150 outer-LOBO candidates. Multi-length scoring remains a
    # robustness sensitivity and must not override the deployment information set.
    deployment_model = str(deployment_candidates.loc[
        deployment_candidates["selected_for_L150_deployment"].astype(bool), "model"
    ].iloc[0])
    deployment_scores_by_l, deployment_worst_by_l = {}, {}
    deployment_tuning_rows = []
    stage_started = time.perf_counter()
    for L in config.early_lengths:
        _, scores, worst, selected_lambda, selected_c, selected_weight = _inner_family_oof(
            complete, L, config
        )
        deployment_scores_by_l[L] = scores
        deployment_worst_by_l[L] = worst
        deployment_tuning_rows.append(
            {"version": config.version, "L": L, "lambda_gamma": selected_lambda,
             "K": selected_c[0], "alpha": selected_c[1], "w_strategy": selected_weight,
             "inner_D_strategy_equal_rmse": scores["D_ensemble"]}
        )
    runtime_rows.append({"version": config.version, "scope": "run", "outer_battery_id": np.nan,
                         "model": deployment_model, "L": np.nan, "stage": "deployment_tuning",
                         "seconds": time.perf_counter() - stage_started})
    selection_index = selection.set_index("model")
    frozen_l150 = next(row for row in deployment_tuning_rows if row["L"] == 150)
    deployment_freeze = pd.DataFrame(
        [{"version": config.version, "selected_model": deployment_model,
          "selection_variant": "raw_absolute_SOH", "L_final_prediction": 150,
          "tie_relative_tolerance": config.tie_relative_tolerance,
          "lambda_gamma_L150": frozen_l150["lambda_gamma"],
          "K_L150": frozen_l150["K"], "alpha_L150": frozen_l150["alpha"],
          "w_strategy_L150": frozen_l150["w_strategy"],
          "freeze_source": "L150_outer_LOBO_deployment_candidates",
          "deployment_strategy_equal_rmse_L150": float(
              deployment_candidates.loc[
                  deployment_candidates["selected_for_L150_deployment"],
                  "strategy_equal_rmse",
              ].iloc[0]
          ),
          "deployment_worst_battery_rmse_L150": float(
              deployment_candidates.loc[
                  deployment_candidates["selected_for_L150_deployment"],
                  "worst_battery_rmse",
              ].iloc[0]
          ),
          **{f"score_{model}": float(selection_index.loc[model, "weighted_score"]) for model in MODELS},
          **{f"worst_{model}": float(selection_index.loc[model, "weighted_worst_battery_rmse"]) for model in MODELS}}]
    )
    runtime_rows.append({"version": config.version, "scope": "run", "outer_battery_id": np.nan,
                         "model": "ALL", "L": np.nan, "stage": "full_compute_total",
                         "seconds": time.perf_counter() - run_started})
    print(f"Q3 deployment family frozen: {deployment_model}", flush=True)
    return {
        "predictions_long.csv": predictions,
        "battery_metrics.csv": battery,
        "model_summary.csv": summary,
        "outer_tuning.csv": pd.DataFrame(tuning_rows),
        "runtime.csv": pd.DataFrame(runtime_rows),
        "selection_decision.csv": selection,
        "selection_bootstrap.csv": bootstrap,
        "pairwise_selection.csv": pairwise,
        "c_ablation_by_battery.csv": ablation_battery,
        "c_ablation_summary.csv": ablation_summary,
        "deployment_candidate_comparison.csv": deployment_candidates,
        "nested_selector_predictions.csv": selector_predictions,
        "nested_selector_battery_metrics.csv": selector_battery,
        "nested_selector_summary.csv": selector_summary,
        "nested_selector_folds.csv": pd.DataFrame(selector_fold_rows),
        "deployment_tuning.csv": pd.DataFrame(deployment_tuning_rows),
        "deployment_freeze.csv": deployment_freeze,
        "record_shape_checks.csv": shape_checks,
    }


def _calibration_table(full: dict[str, pd.DataFrame], selected_model: str) -> pd.DataFrame:
    use = full["predictions_long.csv"]
    use = use.loc[use["L"].eq(150) & use["model"].eq(selected_model)].copy()
    use["absolute_residual"] = np.abs(use["y_true"] - use["y_pred_raw"])
    rows = []
    for cycle, group in use.groupby("cycle"):
        n = group["battery_id"].nunique()
        target_coverage = 0.95
        order = min(n, int(np.ceil((n + 1) * target_coverage)))
        empirical_order_level = order / n
        signed_residual = group["y_true"] - group["y_pred_raw"]
        radius = float(np.sort(group["absolute_residual"].to_numpy())[order - 1])
        rows.append({"version": FULL_VERSION, "model": selected_model, "cycle": cycle,
                     "n_outer_residuals": n, "target_marginal_coverage": target_coverage,
                     "order_statistic_rank": order, "empirical_order_level": empirical_order_level,
                     "signed_residual_mean": float(signed_residual.mean()),
                     "signed_residual_median": float(signed_residual.median()),
                     "interval_radius": radius,
                     "calibration_reuses_model_selection_residuals": True,
                     "interval_status": "post_selection_diagnostic_not_independent_coverage"})
    return pd.DataFrame(rows)


def _linear_eol(record: BatteryRecord, L: int = 150) -> tuple[float, str]:
    window = min(50, L)
    s = min(0.0, slope(record.relative_soh[L - window : L]))
    threshold = 0.8 / record.baseline
    if s >= 0:
        return np.nan, "no_finite_intersection"
    cycle = L + (threshold - record.relative_at(L)) / s
    if cycle <= L:
        return float(cycle), "before_or_at_observation"
    if cycle > CONFIG.eol_max_cycle:
        return np.nan, "beyond_5000"
    return float(cycle), "finite_scenario"


def _eol_sensitivity(
    record: BatteryRecord,
    model: str,
    raw_relative: np.ndarray,
    projected_relative: np.ndarray,
    native_power_fit: dict[str, float] | None,
    config: Q3Config,
) -> list[dict[str, object]]:
    rows = []
    if model == "P0_persistence":
        for variant in ("raw", "projected"):
            rows.append({"version": config.version, "battery_id": record.battery_id,
                         "policy": record.policy, "model": model, "variant": variant,
                         "method": "stitched_power_start_1", "t80": np.nan,
                         "status": "not_applicable_constant", "p": np.nan, "a": np.nan})
        return rows
    series = {"raw": raw_relative, "projected": projected_relative}
    grids = {
        "default": config,
        "low_p": replace(config, power_grid=tuple(p for p in config.power_grid if p <= 1.5)),
        "high_p": replace(config, power_grid=tuple(p for p in config.power_grid if p >= 0.75)),
    }
    for variant, future in series.items():
        stitched = np.concatenate((record.relative_soh[:150], future))
        for grid_name, grid_config in grids.items():
            for start in (1, 51, 101):
                cycles = np.arange(start, 201, dtype=float)
                fit = fit_power_law(cycles, stitched[start - 1 :], grid_config)
                t80, status = power_law_eol(fit, record.baseline, grid_config)
                if status == "before_or_at_observation":
                    t80 = np.nan
                method = f"stitched_power_start_{start}" if grid_name == "default" else f"stitched_power_{grid_name}_start_{start}"
                rows.append({"version": config.version, "battery_id": record.battery_id,
                             "policy": record.policy, "model": model, "variant": variant,
                             "method": method, "t80": t80, "status": status,
                             "p": fit["p"], "a": fit["a"]})
    if model == "A_power" and native_power_fit is not None:
        t80, status = power_law_eol(native_power_fit, record.baseline, config)
        if status == "before_or_at_observation":
            t80 = np.nan
        rows.append({"version": config.version, "battery_id": record.battery_id,
                     "policy": record.policy, "model": model, "variant": "raw",
                     "method": "native_prefix_power", "t80": t80, "status": status,
                     "p": native_power_fit["p"], "a": native_power_fit["a"]})
    if model == "P1_linear":
        t80, status = _linear_eol(record)
        if status == "before_or_at_observation":
            t80 = np.nan
        rows.append({"version": config.version, "battery_id": record.battery_id,
                     "policy": record.policy, "model": model, "variant": "raw",
                     "method": "native_prefix_linear", "t80": t80, "status": status,
                     "p": np.nan, "a": np.nan})
    return rows


def run_final_prediction(
    project_root: Path,
    full: dict[str, pd.DataFrame],
    config: Q3Config = CONFIG,
) -> dict[str, pd.DataFrame]:
    final_started = time.perf_counter()
    config = _full_config(config)
    load_started = time.perf_counter()
    records, meta, _ = load_records(project_root)
    validate_record_shapes(records, meta)
    complete = [records[battery_id] for battery_id in complete_battery_ids(meta)]
    test_ids = sorted(meta.loc[meta["prediction_test"].eq(1), "battery_id"].astype(int).tolist())
    if len(test_ids) != 9 or any(len(records[battery_id].relative_soh) != 150 for battery_id in test_ids):
        raise AssertionError("Final prediction requires nine isolated 150-cycle test batteries")
    runtime_rows = [{"version": config.version, "scope": "final", "stage": "load_and_validate",
                     "seconds": time.perf_counter() - load_started}]
    selected_model = str(full["deployment_freeze.csv"]["selected_model"].iloc[0])
    frozen = full["deployment_tuning.csv"].loc[full["deployment_tuning.csv"]["L"].eq(150)]
    if len(frozen) != 1:
        raise AssertionError("Exactly one frozen L=150 deployment setting is required")
    frozen_row = frozen.iloc[0]
    selected_lambda = float(frozen_row["lambda_gamma"])
    selected_c = (int(frozen_row["K"]), float(frozen_row["alpha"]))
    selected_weight = float(frozen_row["w_strategy"])
    # The nested selector estimates the full selection workflow; a fixed-family
    # interval uses that family's outer residuals after the family is frozen.
    calibration_started = time.perf_counter()
    calibration = _calibration_table(full, selected_model)
    runtime_rows.append({"version": config.version, "scope": "final", "stage": "interval_calibration",
                         "seconds": time.perf_counter() - calibration_started})
    radii = calibration.set_index("cycle")["interval_radius"]
    prediction_rows = []
    eol_rows = []
    predict_started = time.perf_counter()
    for battery_id in test_ids:
        target = records[battery_id]
        predictions, direct = _predict_models(
            complete, target, 150, selected_lambda, selected_c, selected_weight, config
        )
        for model, relative in predictions.items():
            raw = target.baseline * relative
            projected = project_absolute_prediction(raw, target.baseline * target.relative_at(150), config)
            for offset, cycle in enumerate(range(151, 201)):
                radius = float(radii.loc[cycle]) if model == selected_model else np.nan
                prediction_rows.append(
                    {
                        "version": config.version,
                        "battery_id": battery_id,
                        "policy": target.policy,
                        "model": model,
                        "selected_model": model == selected_model,
                        "cycle": cycle,
                        "y_pred_raw": raw[offset],
                        "y_pred_projected": projected[offset],
                        "approx_interval_low": raw[offset] - radius if np.isfinite(radius) else np.nan,
                        "approx_interval_high": raw[offset] + radius if np.isfinite(radius) else np.nan,
                    }
                )
            eol_rows.extend(
                _eol_sensitivity(
                    target, model, relative, projected / target.baseline,
                    direct.get(model), config,
                )
            )
    runtime_rows.append({"version": config.version, "scope": "final", "stage": "refit_predict_and_eol",
                         "seconds": time.perf_counter() - predict_started})
    hyper = pd.DataFrame(
        [
            {"version": config.version, "parameter": "selected_model", "value": selected_model,
             "parameter_role": "deployment_identity"},
            {"version": config.version, "parameter": "P1_linear_trend_window", "value": 50,
             "parameter_role": "used_by_selected_model"},
            {"version": config.version, "parameter": "D_lambda_gamma", "value": selected_lambda,
             "parameter_role": "frozen_nonselected_candidate"},
            {"version": config.version, "parameter": "C_K", "value": selected_c[0],
             "parameter_role": "frozen_nonselected_candidate"},
            {"version": config.version, "parameter": "C_alpha", "value": selected_c[1],
             "parameter_role": "frozen_nonselected_candidate"},
            {"version": config.version, "parameter": "D_w_strategy", "value": selected_weight,
             "parameter_role": "frozen_nonselected_candidate"},
            {"version": config.version, "parameter": "B_slope_window", "value": 20,
             "parameter_role": "frozen_nonselected_candidate"},
            {"version": config.version, "parameter": "D_inner_strategy_equal_rmse", "value": frozen_row["inner_D_strategy_equal_rmse"],
             "parameter_role": "nonselected_candidate_diagnostic"},
        ]
    )
    runtime_rows.append({"version": config.version, "scope": "final", "stage": "final_compute_total",
                         "seconds": time.perf_counter() - final_started})
    return {
        "final_predictions.csv": pd.DataFrame(prediction_rows),
        "prediction_interval_calibration.csv": calibration,
        "eol_sensitivity.csv": pd.DataFrame(eol_rows),
        "final_hyperparameters.csv": hyper,
        "final_runtime.csv": pd.DataFrame(runtime_rows),
    }
