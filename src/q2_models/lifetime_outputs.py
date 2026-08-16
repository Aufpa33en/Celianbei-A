"""Paper-facing outputs for the T80-primary Question 2 analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SHORT_LABELS = {
    "3_7C_31PER_5_9C_NEWSTRUCTURE": "3.7C→5.9C",
    "4_8C_80PER_4_8C_NEWSTRUCTURE": "4.8C→4.8C（新）",
    "5C_67PER_4C_NEWSTRUCTURE": "5.0C→4.0C",
    "5_3C_54PER_4C_NEWSTRUCTURE": "5.3C→4.0C",
    "5_6C_19PER_4_6C_NEWSTRUCTURE": "5.6C→4.6C",
    "5_6C_36PER_4_3C_NEWSTRUCTURE": "5.6C→4.3C",
}


def _configure() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
        }
    )


def draw_lifetime_evidence(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    _configure()
    design = tables["lifetime_strategy_design"].loc[
        tables["lifetime_strategy_design"]["explicit_new_structure_cohort"].astype(bool)
    ].copy()
    metrics = tables["lifetime_model_comparison"].copy()
    bootstrap = tables["lifetime_bootstrap_selection"].copy()
    comparison = metrics.merge(bootstrap, on="model", how="left")

    fig, (ax, ax_validation) = plt.subplots(1, 2, figsize=(12.2, 5.2), constrained_layout=True)
    x = pd.to_numeric(design["J"], errors="raise").to_numpy(dtype=float)
    y = pd.to_numeric(design["median_t80"], errors="raise").to_numpy(dtype=float)
    ax.scatter(x, y, s=58, color="#1F5A99", zorder=3)
    selected = metrics.loc[metrics["selected_primary_explanatory"].astype(bool)].iloc[0]
    grid = np.linspace(x.min(), x.max(), 200)
    fitted_geometric_mean = np.exp(
        float(selected["full_intercept"]) + float(selected["full_slope_original_scale"]) * grid
    )
    ax.plot(grid, fitted_geometric_mean, color="#C43C39", linewidth=1.8, linestyle="--")
    mapping = []
    for point_id, row in enumerate(design.sort_values(["J", "median_t80"], ascending=[True, False]).itertuples(), start=1):
        ax.annotate(
            f"S{point_id}",
            (row.J, row.median_t80),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8.5,
            fontweight="bold",
        )
        mapping.append(f"S{point_id}  {SHORT_LABELS.get(row.policy, row.policy)}")
    ax.set_yscale("log")
    ax.set_xlabel(r"总倍率应力 $J$")
    ax.set_ylabel(r"策略电池预测寿命中位数 $T_{80}$（cycle，对数轴）")
    ax.set_title(r"6个新结构策略：$J$ 与预测寿命")
    ax.grid(alpha=0.22, which="both")
    ax.text(
        0.02,
        0.03,
        "\n".join(mapping),
        transform=ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=8.2,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#BBBBBB", "alpha": 0.92},
    )

    plotted = comparison.loc[comparison["model"].ne("constant_mean")].copy()
    plotted["label"] = plotted["feature"].replace(
        {"J_high_50": r"$J_{high,50}$", "J_high_60": r"$J_{high,60}$", "J_high_70": r"$J_{high,70}$"}
    )
    plotted = plotted.sort_values("relative_rmse_improvement_vs_constant")
    point = 100 * plotted["relative_rmse_improvement_vs_constant"].to_numpy(dtype=float)
    low = 100 * plotted["improvement_ci95_low"].to_numpy(dtype=float)
    high = 100 * plotted["improvement_ci95_high"].to_numpy(dtype=float)
    colors = ["#2E7D32" if value else "#7A8CA5" for value in plotted["selected_primary_explanatory"]]
    ax_validation.errorbar(
        point,
        plotted["label"],
        xerr=np.vstack((point - low, high - point)),
        fmt="none",
        ecolor="#555555",
        capsize=4,
        linewidth=1.1,
    )
    ax_validation.scatter(point, plotted["label"], c=colors, s=58, zorder=3)
    ax_validation.axvline(0, color="#333333", linewidth=1, linestyle="--")
    ax_validation.set_xlabel("相对常数模型的LOCO RMSE改善（%）")
    ax_validation.set_title("点估计与整块电池bootstrap 95%区间")
    ax_validation.grid(axis="x", alpha=0.22)
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)


def write_lifetime_conclusion(path: Path, tables: dict[str, pd.DataFrame]) -> None:
    selected = tables["lifetime_model_comparison"].loc[
        tables["lifetime_model_comparison"]["selected_primary_explanatory"].astype(bool)
    ].iloc[0]
    boot = tables["lifetime_bootstrap_selection"].set_index("model").loc[selected["model"]]
    deletion = tables["lifetime_deletion_diagnostics"]
    extreme = deletion.loc[deletion["excluded_policy"].eq("3_7C_31PER_5_9C_NEWSTRUCTURE")].iloc[0]
    permutation = tables["lifetime_permutation_diagnostic"].iloc[0]
    family = tables["lifetime_family_selection_summary"]
    family_summary = "、".join(
        f"{row.Family}:{row.SelectedModel}({100*row.LinearJImprovementVsConstant:.2f}%)"
        for row in family.itertuples(index=False)
    )
    lines = [
        "# 第二问T80寿命主分析正式结论",
        "",
        "## 最终判定",
        "",
        "问题2以每块电池前150循环预测的T80作为主要寿命响应；SOH200、相对损失和末段衰减率降为辅助稳健性指标。参数效应分析限定在6个明确新结构策略，并对策略内电池的log(T80)取均值。",
        "",
        f"点估计选择`{selected['model']}`：留一策略坐标RMSE为{selected['loco_rmse_log_t80']:.4f}，较常数模型改善{100*selected['relative_rmse_improvement_vs_constant']:.2f}%，系数方向为总倍率应力增加、预测寿命缩短。该模型只能作为探索性解释模型。",
        "",
        "## 不支持确认性参数效应的证据",
        "",
        f"- {int(boot['bootstrap_repetitions'])}次全流水线bootstrap中，每次重新抽取整块电池、重选寿命窗口、重算T80并重选参数模型；该模型入选频率为{100*boot['selected_frequency']:.2f}%，RMSE改善95%区间为[{100*boot['improvement_ci95_low']:.2f}%, {100*boot['improvement_ci95_high']:.2f}%]。",
        "- 上述bootstrap区间条件于Q1已选局部线性T80族；它没有传播寿命模型族形式不确定性。",
        f"- 另以三种冻结T80模型族做点敏感性，结果为{family_summary}。三族均选择`linear_J`且斜率为负，但该比较没有跨族联合置信区间，不能升级为显著或因果证据。",
        f"- 删除3.7C-31%-5.9C策略后，模型选择状态为`{extreme['selection_status']}`，说明主要关联由单个极端设计点支撑。",
        f"- 五个预定义暴露量的最大方向统计量在720种标签排列下尾部比例为{permutation['tail_fraction']:.4f}。策略并非随机分配且策略均值异方差，因此该比例只是交换性诊断，不是确认性p值。",
        "- C1、Q1、C2在现有策略中联合变化；同一(4.8,80%,4.8)参数坐标的新旧结构寿命差异又与批次完全混杂，无法识别三个参数的独立因果效应。",
        "",
        "## 可保留的论文结论",
        "",
        "现有数据支持“总倍率应力较大时预测T80倾向缩短”的探索性关联，并支持中高SOC高倍率暴露需要重点控制的机制解释。但不能声称J、某个SOC阈值或C1、Q1、C2中的单一参数具有经确认的显著独立效应。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
