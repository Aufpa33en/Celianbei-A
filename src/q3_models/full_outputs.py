"""Validated, atomic writers for Q3 full validation and final prediction."""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .full_validation import FULL_VERSION, MODELS


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    check = pd.read_csv(path)
    if check.shape != frame.shape or list(check.columns) != list(frame.columns):
        raise RuntimeError(f"CSV round-trip validation failed: {path.name}")


def _manifest(directory: Path, project_root: Path, seed: int) -> pd.DataFrame:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
        ).strip()
    except Exception:
        commit = "unavailable"
    rows = []
    for path in sorted(p for p in directory.iterdir() if p.is_file() and p.name != "manifest.csv"):
        if path.suffix == ".csv":
            frame = pd.read_csv(path)
            n_rows, n_columns = frame.shape
        else:
            n_rows, n_columns = len(path.read_text(encoding="utf-8").splitlines()), 1
        rows.append(
            {
                "path": path.name,
                "rows": n_rows,
                "columns": n_columns,
                "size_bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "version": FULL_VERSION,
                "seed": seed,
                "git_commit_at_run": commit,
            }
        )
    return pd.DataFrame(rows)


def _publish(temp: Path, target: Path) -> None:
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite authoritative directory: {target}")
    os.replace(temp, target)


def directory_hashes(directory: Path) -> dict[str, str]:
    """Return a stable content hash map for a published authoritative directory."""
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def full_integrity_checks(
    results: dict[str, pd.DataFrame], protected: pd.DataFrame
) -> pd.DataFrame:
    pred = results["predictions_long.csv"]
    selector = results["nested_selector_predictions.csv"]
    tuning = results["outer_tuning.csv"]
    selection = results["selection_decision.csv"]
    checks: list[tuple[str, bool, str]] = []
    checks.append(("candidate_prediction_rows", len(pred) == 36000, f"observed={len(pred)} expected=36000"))
    group_sizes = pred.groupby(["model", "L", "battery_id"])["cycle"].nunique()
    checks.append(("candidate_groups_50_cycles", len(group_sizes) == 720 and group_sizes.eq(50).all(),
                   f"groups={len(group_sizes)}"))
    checks.append(("candidate_models_lengths_batteries",
                   set(pred["model"]) == set(MODELS) and set(pred["L"]) == {50, 100, 150}
                   and pred["battery_id"].nunique() == 40, "6 models; 3 lengths; 40 batteries"))
    checks.append(("no_test_battery_in_validation", set(pred["battery_id"]).isdisjoint({2, 5, 9, 10, 11, 14, 16, 24, 25}),
                   "full validation must contain prediction_test=0 only"))
    checks.append(("finite_candidate_predictions", np.isfinite(pred[["y_true", "y_pred_raw", "y_pred_projected"]]).all().all(),
                   "truth/raw/projected finite"))
    monotone = pred.sort_values("cycle").groupby(["model", "L", "battery_id"])["y_pred_projected"].apply(
        lambda values: bool(np.all(np.diff(values.to_numpy()) <= 1e-12))
    )
    checks.append(("projected_monotone", monotone.all(), f"passed={int(monotone.sum())}/{len(monotone)}"))
    selector_groups = selector.groupby(["model", "L", "battery_id"])["cycle"].agg(["size", "nunique"])
    selector_unique = not selector.duplicated(["model", "L", "battery_id", "cycle"]).any()
    checks.append(("nested_selector_groups_complete",
                   len(selector) == 6000 and len(selector_groups) == 120
                   and selector_groups["size"].eq(50).all() and selector_groups["nunique"].eq(50).all()
                   and selector_unique and set(selector["L"]) == {50, 100, 150}
                   and set(selector["cycle"]) == set(range(151, 201)),
                   f"rows={len(selector)} groups={len(selector_groups)} unique_keys={selector_unique}"))
    checks.append(("outer_train_isolation", len(tuning) == 120 and tuning["n_outer_train"].eq(39).all()
                   and ~tuning["outer_id_in_train"].astype(bool).any(), f"fold_rows={len(tuning)}"))
    checks.append(("single_candidate_comparison_winner", selection["selected"].astype(bool).sum() == 1,
                   f"selected={selection.loc[selection['selected'].astype(bool), 'model'].tolist()}"))
    checks.append(("single_deployment_freeze", len(results["deployment_freeze.csv"]) == 1,
                   str(results["deployment_freeze.csv"]["selected_model"].tolist())))
    frozen_model = str(results["deployment_freeze.csv"]["selected_model"].iloc[0])
    comparison_model = str(selection.loc[selection["selected"].astype(bool), "model"].iloc[0])
    checks.append(("deployment_family_from_outer_lobo", frozen_model == comparison_model,
                   f"freeze={frozen_model} outer_lobo={comparison_model}"))
    frozen = results["deployment_freeze.csv"].iloc[0]
    tuning150 = results["deployment_tuning.csv"].loc[results["deployment_tuning.csv"]["L"].eq(150)].iloc[0]
    freeze_matches = (
        float(frozen["lambda_gamma_L150"]) == float(tuning150["lambda_gamma"])
        and int(frozen["K_L150"]) == int(tuning150["K"])
        and float(frozen["alpha_L150"]) == float(tuning150["alpha"])
        and float(frozen["w_strategy_L150"]) == float(tuning150["w_strategy"])
    )
    checks.append(("deployment_hyperparameters_frozen", freeze_matches, "freeze row equals L=150 tuning row"))
    checks.append(("record_shapes", len(results["record_shape_checks.csv"]) == 49
                   and results["record_shape_checks.csv"]["continuous_unique_cycles"].astype(bool).all(), "49/49"))
    checks.append(("protected_files_unchanged", protected["unchanged"].astype(bool).all(),
                   f"passed={int(protected['unchanged'].sum())}/{len(protected)}"))
    # Verify D equals the fold-specific convex combination of B and C.
    wide = pred.pivot(index=["L", "battery_id", "cycle"], columns="model", values="y_pred_raw")
    weight = tuning.set_index(["L", "held_out_battery_id"])["w_strategy"]
    max_error = 0.0
    for (L, battery_id, _), row in wide.iterrows():
        w = float(weight.loc[(L, battery_id)])
        max_error = max(max_error, abs(row["D_ensemble"] - (w * row["B_strategy"] + (1 - w) * row["C_ridge"])))
    checks.append(("ensemble_identity", max_error < 1e-12, f"max_abs_error={max_error:.3e}"))
    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def _full_report(results: dict[str, pd.DataFrame], checks: pd.DataFrame) -> str:
    selection = results["selection_decision.csv"].sort_values("final_rank")
    raw = results["model_summary.csv"].query("prediction_variant == 'raw'")
    nested = results["nested_selector_summary.csv"].query("prediction_variant == 'raw'")
    freeze = results["deployment_freeze.csv"].iloc[0]
    pair = results["pairwise_selection.csv"].iloc[0]
    lines = [
        "# 第三问40电池全量嵌套LOBO报告", "",
        "## 验证边界", "",
        "40块完整电池逐块作为外层目标；每折只用其余39块重新选择B的λ、C的K/α、D的权重，并同时在39块内部选择模型族。9块真实测试电池未参与本阶段任何拟合、标准化、PCA、调参或区间校准。误差均在还原后的绝对SOH上计算，raw为唯一选模口径。", "",
        "## 六模型共同比较", "",
        "| 排名 | 模型 | 加权策略等权RMSE | L=150策略等权RMSE | 加权最差电池RMSE |", "|---:|---|---:|---:|---:|",
    ]
    for row in selection.itertuples(index=False):
        lines.append(f"| {row.final_rank} | {row.model} | {row.weighted_score:.6f} | {row.L150_strategy_equal_rmse:.6f} | {row.weighted_worst_battery_rmse:.6f} |")
    lines.extend(["", "## 嵌套模型族选择器", ""])
    for row in nested.sort_values("L").itertuples(index=False):
        lines.append(f"- L={row.L}：策略等权RMSE={row.strategy_equal_rmse:.6f}，池化RMSE={row.pooled_rmse:.6f}，最差电池RMSE={row.worst_battery_rmse:.6f}。")
    lines.extend([
        "", "## 不确定性和冻结", "",
        f"候选比较前两名为{pair.model_a}与{pair.model_b}；分层整块电池bootstrap的加权分数差95%区间为[{pair.bootstrap_ci95_low:.6f}, {pair.bootstrap_ci95_high:.6f}]。该区间用于判断领先是否稳定，不把模型差异写成逐循环独立的显著性。",
        f"依据40次真正外层LOBO的冻结规则，部署模型为`{freeze.selected_model}`；模型族冻结后，才用全部40块电池内部OOF确定其部署超参数。最终9电池预测只能使用该冻结模型，不能查看预测曲线后改选。", "",
        "## C模型特征消融", "",
        "消融固定为描述性分析，不参与模型族选择：比较仅早期动态特征、加入连续策略特征、再加入策略独热编码。结果位于`c_ablation_summary.csv`。", "",
        "## 完整性门", "",
        f"完整性检查{int(checks['passed'].sum())}/{len(checks)}项通过。只有全部通过才允许发布本目录并进入9块真实测试电池预测。", "",
        "## EOL边界", "",
        "80%终点没有真实标签，未参与上述模型选择。最终T80只作为真实1—150与预测151—200拼接后的情景外推，并单列raw/projected、拟合窗口和模型形式敏感性。",
    ])
    return "\n".join(lines) + "\n"


def write_full_outputs(
    project_root: Path,
    results: dict[str, pd.DataFrame],
    protected: pd.DataFrame,
    seed: int,
) -> Path:
    target = project_root / "result" / "q3" / "02_full_validation"
    temp = target.with_name(target.name + ".tmp_q3_full_v1")
    if temp.exists() or target.exists():
        raise FileExistsError(f"Refusing to overwrite existing full output path: {temp if temp.exists() else target}")
    temp.mkdir(parents=True)
    checks = full_integrity_checks(results, protected)
    if not checks["passed"].all():
        failed = checks.loc[~checks["passed"], "check"].tolist()
        raise RuntimeError(f"Full validation integrity failed: {failed}")
    write_started = time.perf_counter()
    for name, frame in results.items():
        if name == "runtime.csv":
            continue
        _write_csv(frame, temp / name)
    runtime = results["runtime.csv"].copy()
    runtime.loc[len(runtime)] = {
        "version": FULL_VERSION, "scope": "run", "outer_battery_id": np.nan,
        "model": "ALL", "L": np.nan, "stage": "write_outputs_except_runtime",
        "seconds": time.perf_counter() - write_started,
    }
    _write_csv(runtime, temp / "runtime.csv")
    _write_csv(protected, temp / "protected_files_integrity.csv")
    _write_csv(checks, temp / "integrity_checks.csv")
    (temp / "full_validation_report.md").write_text(_full_report(results, checks), encoding="utf-8")
    _write_csv(_manifest(temp, project_root, seed), temp / "manifest.csv")
    _publish(temp, target)
    return target


def final_integrity_checks(
    selected: pd.DataFrame, all_predictions: pd.DataFrame, settings: pd.DataFrame,
    protected: pd.DataFrame,
) -> pd.DataFrame:
    selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
    expected_ids = {2, 5, 9, 10, 11, 14, 16, 24, 25}
    selected_groups = selected.groupby(["battery_id", "model"])["cycle"].agg(["size", "nunique"])
    selected_unique = not selected.duplicated(["battery_id", "model", "cycle"]).any()
    all_groups = all_predictions.groupby(["battery_id", "model"])["cycle"].agg(["size", "nunique"])
    all_unique = not all_predictions.duplicated(["battery_id", "model", "cycle"]).any()
    checks = [
        ("selected_prediction_rows", len(selected) == 450, f"observed={len(selected)} expected=450"),
        ("nine_frozen_test_batteries", set(selected["battery_id"]) == expected_ids,
         str(sorted(selected["battery_id"].unique()))),
        ("selected_groups_complete", len(selected_groups) == 9 and selected_groups["size"].eq(50).all()
         and selected_groups["nunique"].eq(50).all() and selected_unique
         and set(selected["cycle"]) == set(range(151, 201)),
         f"groups={len(selected_groups)} unique_keys={selected_unique}"),
        ("selected_model_frozen", selected["model"].eq(selected_model).all(), selected_model),
        ("no_truth_or_error_columns", not any(c in selected.columns for c in ("y_true", "rmse", "mae")), "test labels unavailable"),
        ("all_six_models_audited", len(all_predictions) == 2700
         and set(all_predictions["battery_id"]) == expected_ids
         and set(all_predictions["model"]) == set(MODELS) and len(all_groups) == 54
         and all_groups["size"].eq(50).all() and all_groups["nunique"].eq(50).all()
         and all_unique and set(all_predictions["cycle"]) == set(range(151, 201)),
         f"rows={len(all_predictions)} groups={len(all_groups)} unique_keys={all_unique}"),
        ("finite_final_predictions", np.isfinite(selected[["y_pred_raw", "y_pred_projected"]]).all().all(), "raw/projected finite"),
        ("intervals_present", selected[["approx_interval_low", "approx_interval_high"]].notna().all().all(), "selected model only"),
        ("protected_files_unchanged", protected["unchanged"].astype(bool).all(),
         f"passed={int(protected['unchanged'].sum())}/{len(protected)}"),
    ]
    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def _final_summary(predictions: pd.DataFrame, eol: pd.DataFrame, selected_model: str) -> pd.DataFrame:
    selected = predictions.loc[predictions["model"].eq(selected_model)]
    default = eol.loc[
        eol["model"].eq(selected_model) & eol["variant"].eq("raw")
        & eol["method"].eq("stitched_power_start_1")
    ].set_index("battery_id")
    rows = []
    for (battery_id, policy), group in selected.groupby(["battery_id", "policy"]):
        group = group.sort_values("cycle")
        eol_row = default.loc[battery_id]
        rows.append({"version": FULL_VERSION, "battery_id": battery_id, "policy": policy,
                     "selected_model": selected_model, "predicted_SOH200_raw": group["y_pred_raw"].iloc[-1],
                     "predicted_SOH200_projected": group["y_pred_projected"].iloc[-1],
                     "interval_low_cycle200": group["approx_interval_low"].iloc[-1],
                     "interval_high_cycle200": group["approx_interval_high"].iloc[-1],
                     "scenario_T80_default": eol_row["t80"], "scenario_T80_status": eol_row["status"]})
    return pd.DataFrame(rows)


def _final_report(summary: pd.DataFrame, settings: pd.DataFrame, eol: pd.DataFrame) -> str:
    model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
    finite = eol.loc[eol["model"].eq(model) & eol["status"].eq("finite_scenario"), "t80"].dropna()
    lines = [
        "# 第三问完整回答与最终预测说明", "",
        "## 最终方法", "",
        f"40块完整电池经过外层留一、折内调参和嵌套模型族选择后，冻结部署模型为`{model}`。随后只用全部40块完整电池重新调参/拟合，并读取9块测试电池的1—150循环前缀预测151—200循环。测试电池没有真实未来标签，因此不报告测试RMSE。", "",
        "## 九块测试电池结果", "",
        "| 电池 | 策略 | 预测SOH200(raw) | 预测SOH200(projected) | SOH200近似95%区间 | 默认情景T80 | 状态 |", "|---:|---|---:|---:|---|---:|---|",
    ]
    for row in summary.itertuples(index=False):
        t80 = "—" if pd.isna(row.scenario_T80_default) else f"{row.scenario_T80_default:.1f}"
        lines.append(f"| {row.battery_id} | {row.policy} | {row.predicted_SOH200_raw:.6f} | {row.predicted_SOH200_projected:.6f} | [{row.interval_low_cycle200:.6f}, {row.interval_high_cycle200:.6f}] | {t80} | {row.scenario_T80_status} |")
    lines.extend([
        "", "## 预测区间", "",
        "区间由40块训练电池的外层交叉拟合绝对残差逐循环校准，是模型选择后的小样本近似区间，不是独立测试集覆盖率，也不能延伸解释为T80置信区间。", "",
        "## EOL情景外推", "",
        (f"所有模型、raw/projected和多个拟合起点均保存在`eol_sensitivity.csv`。有限情景值范围为{finite.min():.1f}—{finite.max():.1f}循环；"
         if len(finite) else "当前设置没有稳定有限的T80；")
        + "由于49块电池均未观测到80% SOH，T80只表示模型情景，不具有实证寿命精度。跨窗口或模型差异较大时，应报告范围和状态而不是单一寿命。", "",
        "## 可用结论", "",
        "第三问能够用前50/100/150循环预测统一的151—200短期轨迹，并量化早期长度、策略信息和模型复杂度的作用；真正80%寿命仍受短观测窗口限制。论文中应把短期LOBO误差与远期T80不确定性分开陈述。",
    ])
    return "\n".join(lines) + "\n"


def write_final_outputs(
    project_root: Path,
    final: dict[str, pd.DataFrame],
    protected: pd.DataFrame,
    seed: int,
) -> Path:
    target = project_root / "result" / "q3" / "03_final_predictions"
    temp = target.with_name(target.name + ".tmp_q3_full_v1")
    if temp.exists() or target.exists():
        raise FileExistsError(f"Refusing to overwrite existing final output path: {temp if temp.exists() else target}")
    temp.mkdir(parents=True)
    all_predictions = final["final_predictions.csv"]
    settings = final["final_hyperparameters.csv"]
    selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
    selected = all_predictions.loc[all_predictions["model"].eq(selected_model)].copy()
    selected = selected.drop(columns=["selected_model"])
    checks = final_integrity_checks(selected, all_predictions, settings, protected)
    if not checks["passed"].all():
        raise RuntimeError(f"Final prediction integrity failed: {checks.loc[~checks['passed'], 'check'].tolist()}")
    summary = _final_summary(all_predictions, final["eol_sensitivity.csv"], selected_model)
    write_started = time.perf_counter()
    _write_csv(selected, temp / "test_predictions_long.csv")
    _write_csv(summary, temp / "test_battery_summary.csv")
    _write_csv(settings, temp / "final_model_settings.csv")
    _write_csv(final["prediction_interval_calibration.csv"], temp / "prediction_interval_calibration.csv")
    _write_csv(final["eol_sensitivity.csv"], temp / "eol_sensitivity.csv")
    final_runtime = final["final_runtime.csv"].copy()
    final_runtime.loc[len(final_runtime)] = {
        "version": FULL_VERSION, "scope": "final", "stage": "write_outputs_except_runtime",
        "seconds": time.perf_counter() - write_started,
    }
    _write_csv(final_runtime, temp / "runtime.csv")
    _write_csv(all_predictions, temp / "all_model_test_predictions.csv")
    _write_csv(protected, temp / "protected_files_integrity.csv")
    _write_csv(checks, temp / "integrity_checks.csv")
    (temp / "q3_complete_answer.md").write_text(
        _final_report(summary, settings, final["eol_sensitivity.csv"]), encoding="utf-8"
    )
    _write_csv(_manifest(temp, project_root, seed), temp / "manifest.csv")
    _publish(temp, target)
    return target
