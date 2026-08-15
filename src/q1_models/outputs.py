"""Comparison tables, paper-facing report, and dependency-light PNG figures."""

from __future__ import annotations

from pathlib import Path
import platform
import sys
import time

import matplotlib.pyplot as plt
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


def write_authoritative_outputs(
    project_root: Path,
    tables: dict[str, pd.DataFrame],
    command: str,
    inference_seconds: float,
) -> None:
    """Write one traceable Q1 result tree from the authoritative inference context."""
    started = time.perf_counter()
    result_dir = project_root / "result" / "q1"
    paper_dir = result_dir / "paper"
    raw_dir = result_dir / "raw"
    paper_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    for name, table in tables.items():
        table.to_csv(raw_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    paper_tables = {
        "model_comparison": tables["model_comparison"],
        "strategy_scalar_estimates": tables["strategy_scalar_estimates"],
        "strategy_rank_stability": tables["strategy_rank_stability"],
        "authoritative_model_cv_by_policy": tables["authoritative_model_cv_by_policy"],
        "selection_pipeline_summary": tables["selection_pipeline_summary"],
        "q1_conclusions": tables["q1_conclusions"],
        "lifetime_window_validation_summary": tables["lifetime_window_validation_summary"],
        "battery_lifetime_estimates": tables["battery_lifetime_estimates"],
        "strategy_lifetime_summary": tables["strategy_lifetime_summary"],
        "strategy_lifetime_rank_stability": tables["strategy_lifetime_rank_stability"],
        "pairwise_strategy_lifetime_comparison": tables["pairwise_strategy_lifetime_comparison"],
    }
    for name, table in paper_tables.items():
        table.to_csv(paper_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    _draw_final_strategy_curves(tables, paper_dir / "fig_q1_strategy_soh_curves.png")
    _draw_final_model_comparison(tables, paper_dir / "fig_q1_model_comparison.png")
    _draw_final_tradeoff(tables, paper_dir / "fig_q1_strategy_tradeoff.png")
    _write_final_paper_report(paper_dir / "report.md", tables)

    runtime = pd.DataFrame(
        [
            {"Parameter": "command", "Value": command},
            {"Parameter": "inference_seconds", "Value": f"{inference_seconds:.6f}"},
            {"Parameter": "output_seconds", "Value": f"{time.perf_counter() - started:.6f}"},
            {"Parameter": "python", "Value": sys.version.split()[0]},
            {"Parameter": "platform", "Value": platform.platform()},
            {"Parameter": "numpy", "Value": np.__version__},
            {"Parameter": "pandas", "Value": pd.__version__},
        ]
    )
    runtime.to_csv(raw_dir / "runtime_metadata.csv", index=False, encoding="utf-8-sig")

    _write_result_readme(result_dir / "README.md")
    manifest_rows = []
    for path in sorted(p for p in result_dir.rglob("*") if p.is_file()):
        if path.name == "result_manifest.csv":
            continue
        manifest_rows.append(
            {
                "Path": str(path.relative_to(result_dir)),
                "SizeBytes": path.stat().st_size,
                "Role": "paper" if paper_dir in path.parents else "raw_or_supporting",
            }
        )
    pd.DataFrame(manifest_rows).to_csv(
        raw_dir / "result_manifest.csv", index=False, encoding="utf-8-sig"
    )


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": [
                "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                "WenQuanYi Micro Hei", "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
        }
    )


POLICY_LABELS = {
    "3_6C-80PER_3_6C": "3.6C→3.6C（80%）",
    "80PER_3_6C": "0→3.6C（80%）",
    "4_8C_80PER_4_8C": "4.8C→4.8C（80%）",
    "4_8C_80PER_4_8C_NEWSTRUCTURE": "4.8C→4.8C（80%，新）",
    "5C_67PER_4C_NEWSTRUCTURE": "5.0C→4.0C（67%，新）",
    "5_3C_54PER_4C_NEWSTRUCTURE": "5.3C→4.0C（54%，新）",
    "5_6C_36PER_4_3C_NEWSTRUCTURE": "5.6C→4.3C（36%，新）",
    "5_6C_19PER_4_6C_NEWSTRUCTURE": "5.6C→4.6C（19%，新）",
    "3_7C_31PER_5_9C_NEWSTRUCTURE": "3.7C→5.9C（31%，新）",
}


def _draw_final_strategy_curves(tables: dict[str, pd.DataFrame], path: Path) -> None:
    _configure_matplotlib()
    curves = tables["strategy_curve_confidence_band"].copy()
    policies = tables["strategy_rank_stability"].sort_values("PointSOH200Rank")["Policy"]
    fig, axes = plt.subplots(3, 3, figsize=(12, 9), sharex=True, sharey=True, constrained_layout=True)
    for ax, policy in zip(axes.flat, policies):
        frame = curves.loc[curves["Policy"] == policy].sort_values("Cycle")
        cycle = pd.to_numeric(frame["Cycle"], errors="raise").to_numpy(dtype=float)
        estimate = pd.to_numeric(frame["SOHEstimate"], errors="raise").to_numpy(dtype=float)
        low = pd.to_numeric(frame["CI95Low"], errors="raise").to_numpy(dtype=float)
        high = pd.to_numeric(frame["CI95High"], errors="raise").to_numpy(dtype=float)
        ax.fill_between(cycle, low, high, color="#4C78A8", alpha=0.22)
        ax.plot(cycle, estimate, color="#1F5A99", linewidth=1.8)
        ax.set_title(POLICY_LABELS.get(policy, policy))
        ax.grid(alpha=0.2)
    fig.supxlabel("循环次数")
    fig.supylabel("SOH")
    fig.suptitle("不同快充策略的SOH平均轨迹与95%电池级bootstrap区间", fontsize=14)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def _draw_final_model_comparison(tables: dict[str, pd.DataFrame], path: Path) -> None:
    _configure_matplotlib()
    frame = tables["model_comparison"].sort_values("MeanBatteryRMSE").copy()
    display = {
        "functional_ridge": "函数型曲线",
        "spline_mixed": "惩罚样条",
        "polynomial_mixed": "二次曲线",
    }
    fig, (ax, ax_delta) = plt.subplots(1, 2, figsize=(10.5, 4.6), constrained_layout=True)
    colors = ["#2E7D32" if selected else "#7A8CA5" for selected in frame["Selected"]]
    labels = [display.get(value, value) for value in frame["Model"]]
    ax.errorbar(
        frame["MeanBatteryRMSE"],
        labels,
        xerr=frame["SEBatteryRMSE"],
        fmt="none", ecolor="#444444",
        capsize=4,
        linewidth=1.1,
    )
    ax.scatter(frame["MeanBatteryRMSE"], labels, c=colors, s=70, zorder=3)
    for _, row in frame.iterrows():
        ax.annotate(f"{row['MeanBatteryRMSE']:.6f}",
                    (row["MeanBatteryRMSE"], display.get(row["Model"], row["Model"])),
                    xytext=(5, 7), textcoords="offset points", fontsize=9)
    ax.set_xlabel("嵌套留一电池 RMSE（误差线为电池间标准误）")
    ax.set_title("每个外层折内重新调参：三模型高度重叠")
    ax.grid(axis="x", alpha=0.2)

    paired = tables["model_pairwise_cv_difference"].copy()
    paired = paired.loc[paired["ModelB"].eq("functional_ridge")].reset_index(drop=True)
    delta_labels = [f"{display.get(a, a)} − 函数型曲线" for a in paired["ModelA"]]
    delta = paired["MeanRMSEDifference_AminusB"].to_numpy(dtype=float)
    low = paired["CI95Low"].to_numpy(dtype=float)
    high = paired["CI95High"].to_numpy(dtype=float)
    ax_delta.errorbar(delta, delta_labels, xerr=np.vstack((delta - low, high - delta)),
                      fmt="o", color="#1F5A99", capsize=4)
    ax_delta.axvline(0.0, color="#555555", linewidth=1, linestyle="--")
    ax_delta.set_xlabel("嵌套配对 RMSE 差（正值表示函数型曲线更低）")
    ax_delta.set_title("配对差异：统计可辨，实际量级很小")
    ax_delta.grid(axis="x", alpha=0.2)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def _draw_final_tradeoff(tables: dict[str, pd.DataFrame], path: Path) -> None:
    _configure_matplotlib()
    scalars = tables["strategy_scalar_estimates"]
    rank = tables["strategy_rank_stability"][["Policy", "PointSOH200Rank", "PrimaryGroup"]]
    soh = scalars.loc[scalars["Metric"] == "SOH200", ["Policy", "Estimate", "CI95Low", "CI95High"]]
    charge = scalars.loc[scalars["Metric"] == "MeanChargeTime", ["Policy", "Estimate"]].rename(
        columns={"Estimate": "MeanChargeTime"}
    )
    frame = soh.merge(charge, on="Policy").merge(rank, on="Policy")
    colors = {"typical_long": "#2E7D32", "middle": "#D89000", "typical_short": "#C62828"}
    fig, (ax, key_ax) = plt.subplots(
        1, 2, figsize=(11.2, 5.4), gridspec_kw={"width_ratios": [3.4, 1.6]},
        constrained_layout=True,
    )
    annotation_offsets = {
        1: (6, 6), 2: (-12, 12), 3: (-12, -12), 4: (8, 10), 5: (8, -12),
        6: (6, 6), 7: (6, 6), 8: (6, 6), 9: (6, 6),
    }
    for _, row in frame.iterrows():
        ax.errorbar(
            row["MeanChargeTime"], row["Estimate"],
            yerr=[[row["Estimate"] - row["CI95Low"]], [row["CI95High"] - row["Estimate"]]],
            fmt="o", color=colors[row["PrimaryGroup"]], capsize=3, markersize=7,
        )
        rank_value = int(row["PointSOH200Rank"])
        ax.annotate(f"R{rank_value}", (row["MeanChargeTime"], row["Estimate"]),
                    xytext=annotation_offsets[rank_value], textcoords="offset points", fontsize=9)
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=color, markeredgecolor=color,
                   label=label, markersize=7)
        for label, color in (("典型长寿命代理", colors["typical_long"]),
                             ("中间组", colors["middle"]),
                             ("典型短寿命代理", colors["typical_short"]))
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=3, frameon=False)
    ax.set_xlabel("平均充电时间（min）")
    ax.set_ylabel("第200循环 SOH")
    ax.set_title("充电时间与前200循环健康保持的经验权衡")
    ax.grid(alpha=0.2)
    key_ax.axis("off")
    key_ax.set_title("点位编号（按SOH200排名）", loc="left", fontsize=10)
    ranked = frame.sort_values("PointSOH200Rank")
    mapping = [
        f"R{int(row.PointSOH200Rank)}  {POLICY_LABELS.get(row.Policy, row.Policy)}"
        for row in ranked.itertuples()
    ]
    key_ax.text(0.0, 0.96, "\n\n".join(mapping), va="top", ha="left", fontsize=9)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)


def _write_final_paper_report(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    comparison = tables["model_comparison"].sort_values("MeanBatteryRMSE")
    ranks = tables["strategy_rank_stability"].sort_values("PointSOH200Rank")
    residual = tables["residual_diagnostics_overall"].iloc[0]
    significant = tables["pairwise_strategy_scalar_comparison"].query(
        "Metric == 'SOH200' and SignificantAfterHolm"
    )
    bootstrap_excluding_zero = tables["pairwise_strategy_scalar_comparison"].query(
        "Metric == 'SOH200' and BootstrapCIExcludesZero"
    )
    selected = comparison.iloc[0]
    selection_pipeline = tables["selection_pipeline_summary"].iloc[0]
    top = "、".join(ranks.head(3)["Policy"])
    bottom = "、".join(ranks.tail(3)["Policy"])
    lines = [
        "# 第一问：数据整理与快充策略寿命影响初步分析",
        "",
        "## 数据边界",
        "",
        "附件包含49块电池、9种快充策略和9350条循环记录。正式周期200比较只使用40块完整电池；9块仅观测至周期150的测试电池留给第三问。附件中没有任何电池达到80% SOH，因此本文将SOH200、周期1—200损失和末段斜率作为早期寿命代理，不把局部线性L80外推称为观测寿命。",
        "",
        "## 模型",
        "",
        "主模型采用两阶段函数型曲线。令 $x=t/200$，以 $B(x)=[1,x,x^2,x^3,(x-0.25)_+^3,(x-0.50)_+^3,(x-0.75)_+^3]$ 为基函数。对电池 $i$ 估计",
        "",
        "$$\\hat\\beta_i=\\arg\\min_{\\beta}\u2009\\lVert y_i-B_i\\beta\\rVert_2^2+\\lambda\\beta^{\\mathsf T}P\\beta,$$",
        "",
        "其中截距和一次项不惩罚，二次及以上项施加岭惩罚。策略 $s$ 的总体曲线为",
        "",
        "$$\\hat\\mu_s(t)=B(t)\\left(\\frac{1}{n_s}\\sum_{i\\in s}\\hat\\beta_i\\right),$$",
        "",
        "从而保证每块电池而不是每条循环记录等权。该模型与二次曲线模型、带电池随机截距和随机斜率的惩罚样条模型按相同划分比较。每个外层留一电池折都只在其余电池上用策略分层三折重新选择超参数；若外层训练集内某策略只剩一块电池，该策略保留在内层训练中、不参与内层验证。另在每个外层折内同时选择模型家族和超参数，用于估计完整选择流水线的泛化误差。",
        "",
        "## 模型选择结果",
        "",
        f"在外层留一电池、内层重新调参的候选家族比较中，函数型曲线RMSE为 {selected['MeanBatteryRMSE']:.6f}，样条基线为 {comparison.iloc[1]['MeanBatteryRMSE']:.6f}。在更完整的外层验证中，每折连模型家族也只由训练电池选择，选择流水线RMSE为 {selection_pipeline['MeanBatteryRMSE']:.6f}。全体40块电池三折调参选择的最终曲线惩罚为 {selected['LambdaCurve']:g}；这表示当前网格支持无惩罚端点，不能继续称为正则化岭解。候选家族误差用于比较，选择流水线误差用于报告部署流程的外推性能，二者不可混称。三种最终拟合模型给出的SOH200策略排序一致。",
        "",
        "## 策略比较",
        "",
        f"SOH200点估计前三位为：{top}。后三位为：{bottom}。排名稳定性应结合 `strategy_rank_stability.csv` 中的Top/Bottom概率判断，不能只报告点排名。",
        "",
        f"对任意两策略，以电池级SOH200均值差为统计量，枚举合并样本的全部分组方式构造双侧精确置换检验；对36组策略对作Holm校正后，SOH200差异显著的策略对为 {len(significant)} 组。另有 {len(bootstrap_excluding_zero)} 组策略对的策略内整块电池bootstrap 95%区间不跨0，但这些区间没有作多重比较校正，不是同时置信区间，不能据此改报为 {len(bootstrap_excluding_zero)} 组确证差异。精确置换在每策略仅2—7块完整电池时分辨率较粗，因此两种不确定性摘要应并列报告；0组Holm确证差异既不等于所有策略真实相同，也不构成等价性证据。",
        "",
        "## 解释与限制",
        "",
        f"主模型训练残差平均一阶相关为 {residual['BatteryMeanLag1Correlation']:.3f}，说明平滑后仍存在循环内序列相关；策略不确定性采用整块电池bootstrap处理，但模型没有显式估计AR(1)协方差。基线校正和剔除电池41的敏感性分析表明，中上游名次会交换，因此最可靠的是长/短寿命代理组，而不是组内精确名次。充电时间、温度和内阻关联仅有9个策略级样本，只作描述性机制线索，不作因果解释。",
        "",
        "## 论文取舍",
        "",
        "第一问最终回答限定为前200循环的健康保持、充电时间分布和典型策略分组。真实80% SOH寿命留待第三问作为带敏感性分析的外推任务，并明确其无法由当前附件直接验证。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_result_readme(path: Path) -> None:
    path.write_text(
        "# 第一问权威结果\n\n"
        "`result/q1/` 是第一问当前唯一权威结果目录。\n\n"
        "- `paper/`：论文入口；保存报告、核心汇总表和300 dpi图片。\n"
        "- `raw/`：审计入口；保存完整推断表、逐电池/逐循环结果、参数、运行环境和清单。\n"
        "- `00_overview/`—`05_integrity_audit/`：上一轮Excel查看包，仅作辅助浏览；若与 `paper/` 或 `raw/` 冲突，以后两者为准。\n"
        "- `original_q1_csv_archive.zip`：上一轮CSV归档，仅用于历史审计。\n\n"
        "## 输入、模型与结论边界\n\n"
        "- 输入：`data/processed/q1_cleaned/cycle_train_clean.csv`和"
        "`battery_summary_clean.csv`；响应变量为`SOH_clean`。\n"
        "- 队列：40块完整电池用于正式推断；9块`prediction_test=1`电池留给第三问。\n"
        "- 主模型：两阶段函数型曲线（超参数网格包含无惩罚端点）；2000次策略内整块电池bootstrap用于区间和排名稳定性。\n"
        "- 显著性：以整块电池为单位执行双侧精确置换，并按指标作Holm校正。\n\n"
        "正式运行：`python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`；"
        "也可用当前系统虚拟环境中的Python替换`python`。\n"
        "当前附件没有观测到80% SOH终点，所有L80均为未验证外推代理；"
        "可靠结论限定于1—200循环内的健康状态差异。\n",
        encoding="utf-8",
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
