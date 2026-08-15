"""Merged Q2 robustness checks retained after comparing local and remote analyses.

The formal high-SOC exposure validation remains the primary parameter analysis.
This module adds two independent diagnostics from the local branch and audits
whether the discarded two-feature J+H log-rate model survives stricter cohort
and parameter-coordinate validation.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
import platform
import sys
import time

import numpy as np
import pandas as pd

from q1_models.core import MODEL_FUNCTIONAL, make_basis


SEED = 20260814


def extract_late_rate(cycles: pd.DataFrame, batteries: pd.DataFrame) -> pd.DataFrame:
    """Return cycles-151--200 decline rates and an auditable log-model eligibility flag."""
    meta = batteries.set_index("battery_id")
    rows = []
    expected = np.arange(1, 201)
    basis = make_basis(MODEL_FUNCTIONAL, expected)
    penalty = np.zeros(basis.shape[1])
    penalty[2:] = 0.0001
    late_design = np.column_stack((np.ones(50), expected[-50:]))
    for battery_id, original in cycles.groupby("battery_id", observed=True):
        frame = original.sort_values("cycle")
        observed = frame["cycle"].to_numpy(dtype=int)
        if len(observed) != 200 or not np.array_equal(observed, expected):
            continue
        lhs = basis.T @ basis
        lhs.flat[:: lhs.shape[0] + 1] += penalty + 1e-12
        coefficient = np.linalg.solve(
            lhs, basis.T @ frame["SOH_relative_clean"].to_numpy(dtype=float)
        )
        fitted = basis @ coefficient
        rate = -float(np.linalg.lstsq(late_design, fitted[-50:], rcond=None)[0][1])
        valid_for_log = bool(rate > 0)
        item = meta.loc[battery_id]
        rows.append(
            {
                "battery_id": int(battery_id),
                "policy": str(item["policy"]),
                "dataset_id": int(item["dataset_id"]),
                "C1": item["C1"],
                "q": float(item["Q1"]) / 100.0,
                "C2": float(item["C2"]),
                "new_structure": int("NEWSTRUCTURE" in str(item["policy"])),
                "late_degradation_rate": rate,
                "late_rate_valid_for_log_model": valid_for_log,
                "late_rate_exclusion_reason": "" if valid_for_log else "nonpositive_rate",
                "log_late_degradation_rate": np.log(rate) if valid_for_log else np.nan,
            }
        )
    return pd.DataFrame(rows)


def strategy_late_rate(battery: pd.DataFrame) -> pd.DataFrame:
    """Average cells equally within strategy and add J/H exposure descriptors."""
    result = (
        battery.groupby("policy", as_index=False, observed=True, dropna=False)
        .agg(
            n_batteries=("battery_id", "size"),
            dataset_id=("dataset_id", "first"),
            C1=("C1", "first"),
            q=("q", "first"),
            C2=("C2", "first"),
            new_structure=("new_structure", "first"),
            late_degradation_rate=("late_degradation_rate", "mean"),
            late_rate_sd=("late_degradation_rate", "std"),
        )
        .sort_values("policy")
        .reset_index(drop=True)
    )
    result["log_late_degradation_rate"] = np.log(result["late_degradation_rate"])
    valid = result["C1"].notna()
    result["J"] = np.nan
    result["H"] = np.nan
    result.loc[valid, "J"] = (
        result.loc[valid, "q"] * result.loc[valid, "C1"]
        + (0.8 - result.loc[valid, "q"]) * result.loc[valid, "C2"]
    )
    result.loc[valid, "H"] = 0.5 * (
        result.loc[valid, "C1"] * result.loc[valid, "q"] ** 2
        + result.loc[valid, "C2"] * (0.8**2 - result.loc[valid, "q"] ** 2)
    )
    result["coordinate_id"] = "missing_C1"
    result.loc[valid, "coordinate_id"] = result.loc[valid].apply(
        lambda row: f"{row.C1:.3f}|{row.q:.3f}|{row.C2:.3f}", axis=1
    )
    return result


def global_strategy_permutation(
    battery: pd.DataFrame, repetitions: int = 20000, seed: int = SEED
) -> pd.DataFrame:
    """Diagnostic label permutation under a hypothetical exchangeability assumption."""
    values = battery["log_late_degradation_rate"].to_numpy(dtype=float)
    labels = battery["policy"].to_numpy(dtype=str)

    def statistic(current: np.ndarray) -> float:
        unique = np.unique(current)
        grand = values.mean()
        between = sum(
            np.sum(current == label) * (values[current == label].mean() - grand) ** 2
            for label in unique
        )
        within = sum(
            np.sum((values[current == label] - values[current == label].mean()) ** 2)
            for label in unique
        )
        return (between / (len(unique) - 1)) / (within / (len(values) - len(unique)))

    observed = statistic(labels)
    rng = np.random.default_rng(seed)
    exceed = sum(statistic(rng.permutation(labels)) >= observed for _ in range(repetitions))
    return pd.DataFrame(
        [
            {
                "test": "global_strategy_log_late_rate",
                "statistic_F": observed,
                "hypothetical_exchangeability_tail_fraction": (exceed + 1)
                / (repetitions + 1),
                "n_permutations": repetitions,
                "seed": seed,
                "n_strategies": battery["policy"].nunique(),
                "n_batteries": len(battery),
                "artifact_role": "diagnostic_not_confirmatory_test",
                "exchangeability_assumption": (
                    "all_battery_labels_exchangeable_despite_fixed_protocol_groups_unequal_n_and_variance"
                ),
                "confirmatory_p_value_available": False,
            }
        ]
    )


def matched_4p8_comparison(battery: pd.DataFrame) -> pd.DataFrame:
    """Exact descriptive comparison at the duplicated 4.8C coordinate."""
    old_policy = "4_8C_80PER_4_8C"
    new_policy = "4_8C_80PER_4_8C_NEWSTRUCTURE"
    old = battery.loc[battery["policy"].eq(old_policy), "late_degradation_rate"].to_numpy()
    new = battery.loc[battery["policy"].eq(new_policy), "late_degradation_rate"].to_numpy()
    combined = np.concatenate((old, new))
    observed = float(new.mean() - old.mean())
    null = []
    for old_indices in combinations(range(len(combined)), len(old)):
        mask = np.zeros(len(combined), dtype=bool)
        mask[list(old_indices)] = True
        null.append(float(combined[~mask].mean() - combined[mask].mean()))
    exact_p = float(np.mean(np.abs(null) >= abs(observed) - 1e-15))
    attainable_p = [float(np.mean(np.abs(null) >= abs(value) - 1e-15)) for value in null]
    minimum_attainable_p = min(attainable_p)
    return pd.DataFrame(
        [
            {
                "old_policy": old_policy,
                "new_policy": new_policy,
                "n_old": len(old),
                "n_new": len(new),
                "old_mean_rate": old.mean(),
                "new_mean_rate": new.mean(),
                "new_minus_old_rate": observed,
                "relative_change": observed / old.mean(),
                "exact_permutation_p": exact_p,
                "n_label_assignments": len(null),
                "minimum_attainable_two_sided_p": minimum_attainable_p,
                "p_at_minimum_resolution": bool(np.isclose(exact_p, minimum_attainable_p)),
                "causal_status": "not_identified_structure_is_confounded_with_dataset_batch",
            }
        ]
    )


def jh_coordinate_sensitivity(
    strategy: pd.DataFrame, return_folds: bool = False
) -> pd.DataFrame | tuple[pd.DataFrame, pd.DataFrame]:
    """Audit the J+H candidate and expose the sample size of every held-coordinate fold."""
    complete = strategy[strategy["C1"].notna()].copy()
    cohorts = {
        "all_complete": complete,
        "explicit_new_structure": complete[complete["new_structure"].eq(1)],
        "explicit_new_without_3_7C": complete[
            complete["new_structure"].eq(1) & ~complete["policy"].str.startswith("3_7C")
        ],
    }
    rows = []
    fold_rows = []
    for cohort_name, frame in cohorts.items():
        frame = frame.reset_index(drop=True)
        for model, features in (("constant_mean", ()), ("log_rate_J_H", ("J", "H"))):
            prediction = np.zeros(len(frame))
            for coordinate in frame["coordinate_id"].unique():
                train = frame[frame["coordinate_id"].ne(coordinate)]
                test = frame[frame["coordinate_id"].eq(coordinate)]
                y = train["log_late_degradation_rate"].to_numpy(dtype=float)
                if not features:
                    predicted_log = np.repeat(y.mean(), len(test))
                else:
                    mean = train[list(features)].mean().to_numpy(dtype=float)
                    scale = train[list(features)].std(ddof=0).to_numpy(dtype=float, copy=True)
                    scale[scale < 1e-12] = 1.0
                    design = np.column_stack(
                        (np.ones(len(train)), (train[list(features)].to_numpy() - mean) / scale)
                    )
                    test_design = np.column_stack(
                        (np.ones(len(test)), (test[list(features)].to_numpy() - mean) / scale)
                    )
                    predicted_log = test_design @ np.linalg.lstsq(design, y, rcond=None)[0]
                prediction[test.index] = np.exp(predicted_log)
                n_parameters = 1 + len(features)
                residual_df_proxy = len(train) - n_parameters
                fold_rows.append(
                    {
                        "cohort": cohort_name,
                        "model": model,
                        "held_coordinate": coordinate,
                        "n_train_policy_rows": len(train),
                        "n_test_policy_rows": len(test),
                        "n_parameters_including_intercept": n_parameters,
                        "residual_df_proxy": residual_df_proxy,
                        "validation_support": (
                            "very_low_df_diagnostic_only"
                            if residual_df_proxy <= 2
                            else "limited_coordinate_validation"
                        ),
                    }
                )
            log_mse = []
            rate_mse = []
            for coordinate in frame["coordinate_id"].unique():
                use = frame["coordinate_id"].eq(coordinate)
                observed = frame.loc[use, "late_degradation_rate"].to_numpy(dtype=float)
                log_mse.append(np.mean((np.log(prediction[use]) - np.log(observed)) ** 2))
                rate_mse.append(np.mean((prediction[use] - observed) ** 2))
            rows.append(
                {
                    "cohort": cohort_name,
                    "model": model,
                    "n_policy_labels": len(frame),
                    "n_unique_coordinates": frame["coordinate_id"].nunique(),
                    "coordinate_equal_log_RMSE": np.sqrt(np.mean(log_mse)),
                    "coordinate_equal_rate_RMSE": np.sqrt(np.mean(rate_mse)),
                }
            )
    result = pd.DataFrame(rows)
    baseline = result[result["model"].eq("constant_mean")].set_index("cohort")
    result["log_RMSE_improvement_vs_constant"] = result.apply(
        lambda row: 1.0
        - row["coordinate_equal_log_RMSE"]
        / baseline.loc[row["cohort"], "coordinate_equal_log_RMSE"],
        axis=1,
    )
    if return_folds:
        return result, pd.DataFrame(fold_rows)
    return result


def run_merged_robustness(
    project_root: Path, repetitions: int = 20000, seed: int = SEED
) -> dict[str, pd.DataFrame]:
    started = time.perf_counter()
    source = project_root / "data" / "processed" / "q1_cleaned"
    cycles = pd.read_csv(source / "cycle_train_clean.csv")
    batteries = pd.read_csv(source / "battery_summary_clean.csv")
    battery = extract_late_rate(cycles, batteries)
    valid_battery = battery.loc[battery["late_rate_valid_for_log_model"]].copy()
    if valid_battery.empty:
        raise ValueError("No positive late degradation rates are available for the log-rate diagnostics")
    strategy = strategy_late_rate(valid_battery)
    jh_summary, jh_folds = jh_coordinate_sensitivity(strategy, return_folds=True)
    outputs = {
        "battery_late_rate": battery,
        "strategy_late_rate": strategy,
        "global_strategy_permutation": global_strategy_permutation(valid_battery, repetitions, seed),
        "matched_4p8_comparison": matched_4p8_comparison(valid_battery),
        "jh_coordinate_sensitivity": jh_summary,
        "jh_coordinate_fold_diagnostics": jh_folds,
    }
    outputs["runtime_metadata"] = pd.DataFrame(
        [
            {"parameter": "command", "value": f"python scripts/q2/run_q2_merged_robustness.py --permutations {repetitions} --seed {seed}"},
            {"parameter": "seed", "value": seed},
            {"parameter": "permutations", "value": repetitions},
            {"parameter": "wall_seconds", "value": f"{time.perf_counter() - started:.6f}"},
            {"parameter": "python", "value": sys.version.split()[0]},
            {"parameter": "platform", "value": platform.platform()},
            {"parameter": "numpy", "value": np.__version__},
            {"parameter": "pandas", "value": pd.__version__},
            {"parameter": "n_late_rate_total", "value": len(battery)},
            {"parameter": "n_late_rate_valid_for_log", "value": len(valid_battery)},
            {"parameter": "n_late_rate_excluded_nonpositive", "value": len(battery) - len(valid_battery)},
        ]
    )
    return outputs


def write_merged_robustness(project_root: Path, outputs: dict[str, pd.DataFrame]) -> None:
    root = project_root / "result" / "q2" / "05_merged_robustness"
    paper = root / "paper"
    raw = root / "raw"
    paper.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    outputs["battery_late_rate"].to_csv(raw / "battery_late_rate.csv", index=False, encoding="utf-8-sig")
    outputs["runtime_metadata"].to_csv(raw / "runtime_metadata.csv", index=False, encoding="utf-8-sig")
    for name in (
        "strategy_late_rate", "global_strategy_permutation", "matched_4p8_comparison",
        "jh_coordinate_sensitivity", "jh_coordinate_fold_diagnostics",
    ):
        outputs[name].to_csv(paper / f"{name}.csv", index=False, encoding="utf-8-sig")
    root.joinpath("README.md").write_text(
        "# Q2合并稳健性分析\n\n"
        "本目录补充远程正式验证，但不替代`03_formal_validation/`。\n\n"
        "- `paper/`：末段退化率策略汇总、假设标签可交换的全局诊断、4.8C匹配诊断，以及J+H坐标留出汇总和逐折样本量。\n"
        "- `raw/`：40块完整电池的末段退化率、对数模型资格/排除原因和运行环境/参数。非正速率保留原值但不进入对数诊断。\n\n"
        "全局标签置换因协议组固定、样本数和方差不等而不提供确认性p值。正式参数结论仍以高SOC暴露族的选择校正诊断及其边界为准。J+H模型在当前6策略同结构队列中每折仅5个训练点拟合3个系数，无法获得可信验证；"
        "4.8C匹配结果只反映结构/批次联合差异；n=2对n=5仅有21种标签分配，当前双侧p值已处于可达分辨率下界。\n",
        encoding="utf-8",
    )
    q2_root = project_root / "result" / "q2"
    manifest = []
    for path in sorted(q2_root.rglob("*.csv")):
        if path.name == "result_manifest.csv":
            continue
        frame = pd.read_csv(path)
        relative = path.relative_to(project_root)
        relative_posix = relative.as_posix()
        manifest.append(
            {
                "output_key": relative.with_suffix("").as_posix().replace("/", "__"),
                "relative_path": relative_posix,
                "rows": len(frame),
                "columns": len(frame.columns),
            }
        )
    pd.DataFrame(manifest).to_csv(
        q2_root / "result_manifest.csv", index=False, encoding="utf-8-sig"
    )
