"""Comparison tables, paper-facing report, and dependency-light PNG figures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from .core import fit_population_model
from .experiments import (
    CandidateResult,
    _extract_outputs,
    load_clean_data,
    observed_battery_metrics,
    strategy_distribution,
)


def compare_and_write(project_root: Path, results: list[CandidateResult], seed: int = 20260814) -> pd.DataFrame:
    summary_dir = project_root / "outputs" / "summary" / "q1_models"
    figure_dir = project_root / "figures" / "q1_models"
    summary_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    comparison_rows = []
    for result in results:
        policy_error = result.lobo.groupby("Policy", sort=False)["RMSE"].mean()
        curve_matrix = result.curves.pivot(index="Cycle", columns="Policy", values="SOHPred")
        increments = np.diff(curve_matrix.to_numpy(), axis=0)
        comparison_rows.append(
            {
                "Model": result.model_type,
                "MeanBatteryRMSE": result.lobo["RMSE"].mean(),
                "SEBatteryRMSE": result.lobo["RMSE"].std(ddof=1) / np.sqrt(len(result.lobo)),
                "MeanBatteryMAE": result.lobo["MAE"].mean(),
                "MedianBatteryRMSE": result.lobo["RMSE"].median(),
                "WorstPolicyRMSE": policy_error.max(),
                "MaxBatteryError": result.lobo["MaxAbsError"].max(),
                "InvalidTrendFractionAfter20": np.mean(increments[19:] > 1e-4),
                "LambdaRandom": result.best_config.lambda_random,
                "LambdaCurve": result.best_config.lambda_curve,
            }
        )
    comparison = pd.DataFrame(comparison_rows)
    best_index = int(comparison["MeanBatteryRMSE"].idxmin())
    comparison["Selected"] = False
    comparison.loc[best_index, "Selected"] = True
    best = results[best_index]

    agreement, ranks = _model_agreement(results)
    paired = _paired_cv_differences(results, seed)
    all_curves = pd.concat([r.curves for r in results], ignore_index=True)
    all_strategy = pd.concat([r.strategy_summary for r in results], ignore_index=True)
    cycles, batteries = load_clean_data(project_root)
    battery_metrics = observed_battery_metrics(cycles, batteries)
    distributions = strategy_distribution(battery_metrics)
    authoritative = _classify_strategies(best.strategy_summary)
    sensitivity = _baseline_sensitivity(cycles, batteries, best)
    policy_cv = (
        best.lobo.groupby("Policy", sort=False)
        .agg(NBattery=("BatteryId", "size"), MeanRMSE=("RMSE", "mean"), MedianRMSE=("RMSE", "median"), MaxRMSE=("RMSE", "max"))
        .reset_index()
        .sort_values("MeanRMSE", ascending=False)
    )

    comparison.to_csv(summary_dir / "model_comparison.csv", index=False)
    agreement.to_csv(summary_dir / "model_agreement.csv", index=False)
    paired.to_csv(summary_dir / "model_pairwise_cv_difference.csv", index=False)
    ranks.to_csv(summary_dir / "strategy_rank_by_model.csv", index=False)
    all_curves.to_csv(summary_dir / "all_model_strategy_curves.csv", index=False)
    all_strategy.to_csv(summary_dir / "all_model_strategy_summary.csv", index=False)
    authoritative.to_csv(summary_dir / "authoritative_strategy_summary.csv", index=False)
    best.curves.to_csv(summary_dir / "authoritative_strategy_curves.csv", index=False)
    battery_metrics.to_csv(summary_dir / "battery_observed_window_metrics.csv", index=False)
    distributions.to_csv(summary_dir / "strategy_lifetime_proxy_distribution.csv", index=False)
    sensitivity.to_csv(summary_dir / "baseline_sensitivity_strategy_rank.csv", index=False)
    policy_cv.to_csv(summary_dir / "authoritative_model_cv_by_policy.csv", index=False)

    _draw_strategy_panels(best, figure_dir / "q1_best_model_strategy_curves.png")
    _draw_model_bars(comparison, figure_dir / "q1_model_cv_comparison.png")
    _draw_tradeoff(authoritative, figure_dir / "q1_strategy_time_soh_tradeoff.png")
    _write_report(
        project_root / "reports" / "q1_model_comparison.md",
        comparison,
        agreement,
        paired,
        authoritative,
        distributions,
        sensitivity,
        policy_cv,
    )
    return comparison


def _model_agreement(results: list[CandidateResult]) -> tuple[pd.DataFrame, pd.DataFrame]:
    policies = results[0].strategy_summary["Policy"].tolist()
    rank_table = pd.DataFrame({"Policy": policies})
    values: dict[str, np.ndarray] = {}
    for result in results:
        frame = result.strategy_summary.set_index("Policy").loc[policies]
        values[result.model_type] = frame["SOH200"].to_numpy()
        rank_table[f"{result.model_type}_rank"] = _rank_descending(values[result.model_type])

    rows = []
    for first in results:
        for second in results:
            left = first.curves.sort_values(["Policy", "Cycle"])["SOHPred"].to_numpy()
            right = second.curves.sort_values(["Policy", "Cycle"])["SOHPred"].to_numpy()
            rank_a = _rank_descending(values[first.model_type])
            rank_b = _rank_descending(values[second.model_type])
            rows.append(
                {
                    "ModelA": first.model_type,
                    "ModelB": second.model_type,
                    "CurveRMSE": np.sqrt(np.mean((left - right) ** 2)),
                    "RankSpearman": np.corrcoef(rank_a, rank_b)[0, 1],
                }
            )
    return pd.DataFrame(rows), rank_table


def _paired_cv_differences(results: list[CandidateResult], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            left = results[i].lobo[["BatteryId", "RMSE"]].rename(columns={"RMSE": "A"})
            right = results[j].lobo[["BatteryId", "RMSE"]].rename(columns={"RMSE": "B"})
            difference = left.merge(right, on="BatteryId")["A"].to_numpy() - left.merge(right, on="BatteryId")["B"].to_numpy()
            samples = rng.choice(difference, size=(5000, len(difference)), replace=True).mean(axis=1)
            rows.append(
                {
                    "ModelA": results[i].model_type,
                    "ModelB": results[j].model_type,
                    "MeanRMSEDifference_AminusB": difference.mean(),
                    "CI95Low": np.quantile(samples, 0.025),
                    "CI95High": np.quantile(samples, 0.975),
                    "AHasLowerRMSE": bool(np.quantile(samples, 0.975) < 0),
                    "BHasLowerRMSE": bool(np.quantile(samples, 0.025) > 0),
                }
            )
    return pd.DataFrame(rows)


def _rank_descending(values: np.ndarray) -> np.ndarray:
    order = np.argsort(-np.asarray(values), kind="stable")
    ranks = np.empty(len(order), dtype=int)
    ranks[order] = np.arange(1, len(order) + 1)
    return ranks


def _classify_strategies(summary: pd.DataFrame) -> pd.DataFrame:
    output = summary.sort_values("SOH200", ascending=False).reset_index(drop=True).copy()
    output["SOH200Rank"] = np.arange(1, len(output) + 1)
    output["LifeGroup"] = "middle"
    output.loc[:2, "LifeGroup"] = "typical_long"
    output.loc[len(output) - 3 :, "LifeGroup"] = "typical_short"
    return output


def _baseline_sensitivity(cycles: pd.DataFrame, batteries: pd.DataFrame, best: CandidateResult) -> pd.DataFrame:
    variants = {
        "primary_soh_clean": cycles.copy(),
        "relative_soh": cycles.assign(SOH_clean=cycles["SOH_relative_clean"]),
        "exclude_battery_41": cycles.loc[cycles["battery_id"] != 41].copy(),
    }
    parts = []
    for name, frame in variants.items():
        model = fit_population_model(frame, best.model_type, best.best_config)
        _, summary = _extract_outputs(model, batteries)
        summary = summary.sort_values("SOH200", ascending=False).reset_index(drop=True)
        summary["Rank"] = np.arange(1, len(summary) + 1)
        summary.insert(0, "SensitivityVariant", name)
        parts.append(summary[["SensitivityVariant", "Policy", "SOH200", "Rank"]])
    return pd.concat(parts, ignore_index=True)


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _draw_strategy_panels(result: CandidateResult, path: Path) -> None:
    width, height = 1800, 1200
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((width // 2, 28), f"第一问主模型：{result.model_type} 策略平均SOH轨迹", font=_font(34, True), fill="#172033", anchor="ma")
    colors = ["#2364AA", "#3DA35D", "#F28E2B", "#D1495B", "#7B2CBF", "#008C95", "#A66A00", "#52616B", "#C43E96"]
    margin_x, top, gap_x, gap_y = 80, 100, 35, 45
    panel_w = (width - 2 * margin_x - 2 * gap_x) // 3
    panel_h = (height - top - 80 - 2 * gap_y) // 3
    for index, policy in enumerate(result.final_model.policy_names):
        row, col = divmod(index, 3)
        left = margin_x + col * (panel_w + gap_x)
        upper = top + row * (panel_h + gap_y)
        right, lower = left + panel_w, upper + panel_h
        plot_left, plot_top, plot_right, plot_bottom = left + 58, upper + 48, right - 18, lower - 44
        draw.rectangle((plot_left, plot_top, plot_right, plot_bottom), outline="#7A8494", width=2)
        draw.text(((left + right) // 2, upper + 8), policy, font=_font(17), fill="#172033", anchor="ma")
        for value in (0.95, 0.97, 0.99, 1.01):
            y = _map(value, 0.94, 1.01, plot_bottom, plot_top)
            draw.line((plot_left, y, plot_right, y), fill="#E4E8EF", width=1)
            draw.text((plot_left - 8, y), f"{value:.2f}", font=_font(12), fill="#4A5568", anchor="rm")
        for value in (1, 50, 100, 150, 200):
            x = _map(value, 1, 200, plot_left, plot_right)
            draw.line((x, plot_top, x, plot_bottom), fill="#F0F2F6", width=1)
            draw.text((x, plot_bottom + 7), str(value), font=_font(12), fill="#4A5568", anchor="ma")
        frame = result.curves[result.curves["Policy"] == policy]
        points = [
            (_map(cycle, 1, 200, plot_left, plot_right), _map(soh, 0.94, 1.01, plot_bottom, plot_top))
            for cycle, soh in zip(frame["Cycle"], frame["SOHPred"])
        ]
        draw.line(points, fill=colors[index], width=4, joint="curve")
    image.save(path, dpi=(300, 300))


def _draw_model_bars(comparison: pd.DataFrame, path: Path) -> None:
    width, height = 1300, 760
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((width // 2, 35), "三种模型的留一电池泛化误差", font=_font(34, True), fill="#172033", anchor="ma")
    left, top, right, bottom = 120, 120, 1230, 620
    maximum = comparison["MeanBatteryRMSE"].max() * 1.25
    draw.line((left, top, left, bottom), fill="#4A5568", width=2)
    draw.line((left, bottom, right, bottom), fill="#4A5568", width=2)
    colors = ["#2364AA", "#3DA35D", "#F28E2B"]
    slot = (right - left) / len(comparison)
    for i, row in comparison.reset_index(drop=True).iterrows():
        center = left + slot * (i + 0.5)
        bar_width = slot * 0.48
        bar_top = _map(row["MeanBatteryRMSE"], 0, maximum, bottom, top)
        draw.rectangle((center - bar_width / 2, bar_top, center + bar_width / 2, bottom), fill=colors[i])
        error_y = abs(_map(row["SEBatteryRMSE"], 0, maximum, bottom, top) - bottom)
        draw.line((center, bar_top - error_y, center, bar_top + error_y), fill="#111827", width=3)
        draw.line((center - 14, bar_top - error_y, center + 14, bar_top - error_y), fill="#111827", width=3)
        draw.text((center, bar_top - error_y - 12), f"{row['MeanBatteryRMSE']:.5f}", font=_font(18, True), fill="#172033", anchor="ms")
        draw.text((center, bottom + 22), row["Model"], font=_font(18), fill="#172033", anchor="ma")
    draw.text((38, (top + bottom) // 2), "RMSE", font=_font(21), fill="#172033", anchor="mm")
    image.save(path, dpi=(300, 300))


def _draw_tradeoff(summary: pd.DataFrame, path: Path) -> None:
    width, height = 1750, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((width // 2, 34), "充电时间与第200循环SOH（主模型）", font=_font(34, True), fill="#172033", anchor="ma")
    left, top, right, bottom = 135, 120, 1160, 820
    xmin, xmax = summary["MeanChargeTime"].min() - 0.4, summary["MeanChargeTime"].max() + 0.4
    ymin, ymax = summary["SOH200"].min() - 0.003, summary["SOH200"].max() + 0.003
    draw.rectangle((left, top, right, bottom), outline="#697386", width=2)
    colors = {"typical_long": "#238636", "middle": "#D97706", "typical_short": "#CF222E"}
    for value in np.linspace(xmin, xmax, 5):
        x = _map(value, xmin, xmax, left, right)
        draw.line((x, top, x, bottom), fill="#E7EAF0", width=1)
        draw.text((x, bottom + 10), f"{value:.1f}", font=_font(16), fill="#4A5568", anchor="ma")
    for value in np.linspace(ymin, ymax, 5):
        y = _map(value, ymin, ymax, bottom, top)
        draw.line((left, y, right, y), fill="#E7EAF0", width=1)
        draw.text((left - 10, y), f"{value:.3f}", font=_font(16), fill="#4A5568", anchor="rm")
    for point_id, (_, row) in enumerate(summary.iterrows(), start=1):
        x = _map(row["MeanChargeTime"], xmin, xmax, left, right)
        y = _map(row["SOH200"], ymin, ymax, bottom, top)
        color = colors[row["LifeGroup"]]
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color, outline="white", width=2)
        offsets = {1: (-4, -34), 2: (10, -12), 4: (10, 12), 5: (10, 32)}
        dx, dy = offsets.get(point_id, (12, -12))
        draw.text((x + dx, y + dy), f"S{point_id}", font=_font(17, True), fill="#172033")
        legend_y = 135 + (point_id - 1) * 72
        draw.ellipse((1215, legend_y, 1231, legend_y + 16), fill=color)
        draw.text((1245, legend_y - 3), f"S{point_id}  {row['Policy']}", font=_font(16), fill="#172033")
    draw.text(((left + right) // 2, bottom + 50), "平均充电时间", font=_font(23), fill="#172033", anchor="ma")
    draw.text((left, top - 35), "SOH200", font=_font(21), fill="#172033", anchor="ls")
    image.save(path, dpi=(300, 300))


def _map(value, source_min, source_max, target_min, target_max):
    return target_min + (float(value) - source_min) * (target_max - target_min) / (source_max - source_min)


def _write_report(path: Path, comparison, agreement, paired, authoritative, distributions, sensitivity, policy_cv) -> None:
    best = comparison.loc[comparison["Selected"]].iloc[0]
    lines = [
        "# A题第一问模型比较与主模型选择",
        "",
        "## 选择结论",
        "",
        f"主模型为 `{best['Model']}`，留一电池平均RMSE为 {best['MeanBatteryRMSE']:.6f}，MAE为 {best['MeanBatteryMAE']:.6f}。",
        "",
        "选择只依据0—200循环内的电池级验证误差；80% SOH没有真实标签，其外推值不参与模型选择。",
        "",
        "## 三模型比较",
        "",
        "| 模型 | RMSE | RMSE标准误 | MAE | 最差策略RMSE | 20循环后明显回升比例 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['Model']} | {row['MeanBatteryRMSE']:.6f} | {row['SEBatteryRMSE']:.6f} | "
            f"{row['MeanBatteryMAE']:.6f} | {row['WorstPolicyRMSE']:.6f} | {row['InvalidTrendFractionAfter20']:.4f} |"
        )
    lines += ["", "## 模型一致性", ""]
    for _, row in agreement.iterrows():
        if row["ModelA"] < row["ModelB"]:
            lines.append(
                f"- `{row['ModelA']}` 与 `{row['ModelB']}`：策略曲线RMSE {row['CurveRMSE']:.6f}，"
                f"SOH200排序Spearman系数 {row['RankSpearman']:.3f}。"
            )
    lines += ["", "配对电池bootstrap的模型RMSE差异：", ""]
    for _, row in paired.iterrows():
        lines.append(
            f"- `{row['ModelA']} - {row['ModelB']}`：均值 {row['MeanRMSEDifference_AminusB']:.6f}，"
            f"95%区间 [{row['CI95Low']:.6f}, {row['CI95High']:.6f}]。"
        )
    lines += [
        "",
        "## 主模型策略结果",
        "",
        "| 策略 | SOH200 | 排名 | 分组 | 1—200损失 | 平均充电时间 | 局部线性L80外推 |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for _, row in authoritative.iterrows():
        lines.append(
            f"| {row['Policy']} | {row['SOH200']:.6f} | {int(row['SOH200Rank'])} | {row['LifeGroup']} | "
            f"{row['Loss1to200']:.6f} | {row['MeanChargeTime']:.3f} | {row['ProjectedL80LocalLinear']:.1f} |"
        )
    lines += [
        "",
        "## 寿命分布口径",
        "",
        f"49块电池中真实达到80% SOH的数量为 {int(distributions['ObservedEOL80Count'].sum())}。",
        "因此 `ProjectedL80LocalLinear` 及策略分布均只是第151循环以后局部斜率外推，不能写成观测寿命或验证寿命。",
        "",
        "## 电池41基准敏感性",
        "",
        "主模型分别使用原SOH、相对SOH以及剔除电池41重新拟合。完整排名见 `outputs/summary/q1_models/baseline_sensitivity_strategy_rank.csv`。",
    ]
    for variant, frame in sensitivity.groupby("SensitivityVariant", sort=False):
        ordered = frame.sort_values("Rank")
        top = "、".join(ordered.head(3)["Policy"])
        bottom = "、".join(ordered.tail(3)["Policy"])
        lines.append(f"- `{variant}`：前三名为 {top}；后三名为 {bottom}。")
    lines += [
        "",
        f"主模型最难泛化的策略是 `{policy_cv.iloc[0]['Policy']}`，策略平均RMSE为 {policy_cv.iloc[0]['MeanRMSE']:.6f}；该策略包含基准异常的电池41，因此不能把这一误差完全解释为曲线模型不足。",
        "三种口径下，5C_67PER_4C_NEWSTRUCTURE、5_3C_54PER_4C_NEWSTRUCTURE、3_6C-80PER_3_6C始终位于前四；80PER_3_6C、4_8C_80PER_4_8C、3_7C_31PER_5_9C_NEWSTRUCTURE始终位于后三，可作为较稳健的长寿命组和短寿命组。组内精确名次不作稳健结论。",
        "",
        "## 如何解释模型不一致",
        "",
        "不同模型只要回答相同的策略平均轨迹问题，主要趋势和明显优劣策略通常应一致。数值不完全相同并不意味着推导错误；样条平滑、随机效应收缩和电池等权汇总会产生正常差异。若出现大范围排序反转，同时伴随较差的留一电池误差、明显非单调振荡或对单块电池高度敏感，才应优先检查模型设定和程序实现。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
