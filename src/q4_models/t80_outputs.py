"""Paper-facing writers for Q4 predicted-T80 Pareto sensitivity."""

from __future__ import annotations

import hashlib
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _configure() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
        }
    )


def _draw(path: Path, summary: pd.DataFrame) -> pd.DataFrame:
    _configure()
    ordered = summary.sort_values("T80Median", ascending=False).reset_index(drop=True)
    ordered["StrategyCode"] = [f"S{index + 1}" for index in range(len(ordered))]
    fig, ax = plt.subplots(figsize=(8.8, 5.4), constrained_layout=True)
    colors = np.where(ordered["PointParetoTimeMaxT80"].astype(bool), "#2E7D32", "#547AA5")
    sizes = 55 + 180 * ordered["BootstrapParetoFrequency"].to_numpy(dtype=float)
    ax.errorbar(
        ordered["TimeMean"], ordered["T80Median"],
        xerr=np.vstack((ordered["TimeMean"] - ordered["TimeP025"], ordered["TimeP975"] - ordered["TimeMean"])),
        yerr=np.vstack((ordered["T80Median"] - ordered["T80P025"], ordered["T80P975"] - ordered["T80Median"])),
        fmt="none", ecolor="#777777", linewidth=1.0, capsize=3, alpha=0.8,
    )
    ax.scatter(ordered["TimeMean"], ordered["T80Median"], c=colors, s=sizes, zorder=3)
    offsets = {
        "S1": (5, 5), "S2": (5, 5), "S3": (-16, 12), "S4": (8, -9),
        "S5": (8, 10), "S6": (8, -10), "S7": (5, 5), "S8": (5, 5), "S9": (5, 5),
    }
    for row in ordered.itertuples(index=False):
        ax.annotate(row.StrategyCode, (row.TimeMean, row.T80Median),
                    xytext=offsets[row.StrategyCode],
                    textcoords="offset points", fontsize=8.5, fontweight="bold")
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="#2E7D32",
                   markeredgecolor="#2E7D32", label="T80 点 Pareto", markersize=7),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor="#547AA5",
                   markeredgecolor="#547AA5", label="非点 Pareto", markersize=7),
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.02),
              ncol=2, frameon=False)
    ax.set_xlabel("平均充电时间（min）")
    ax.set_ylabel(r"预测 $T_{80}$ 中位数（cycle）")
    ax.set_title("观测策略的充电时间—预测寿命敏感性")
    ax.set_yscale("log")
    ax.grid(alpha=0.22, which="both")
    ax.text(
        0.02, 0.03, "点大小 ∝ bootstrap Pareto 频率",
        transform=ax.transAxes, fontsize=8.5, color="#555555",
    )
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)
    return ordered[["StrategyCode", "Policy"]]


def write_t80_sensitivity_outputs(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    raw = output_dir / "raw"
    paper = output_dir / "paper"
    raw.mkdir(parents=True, exist_ok=False)
    paper.mkdir(parents=True, exist_ok=False)
    for name, frame in tables.items():
        frame.to_csv(raw / f"{name}.csv", index=False, encoding="utf-8-sig")
    for name in (
        "policy_t80_pareto_summary",
        "early_proxy_t80_front_comparison",
        "t80_pareto_model_family_sensitivity",
        "run_metadata",
    ):
        tables[name].to_csv(paper / f"{name}.csv", index=False, encoding="utf-8-sig")
    mapping = _draw(paper / "fig_q4_time_t80_pareto_sensitivity.png",
                    tables["policy_t80_pareto_summary"])
    mapping.to_csv(paper / "fig_q4_time_t80_strategy_mapping.csv", index=False,
                   encoding="utf-8-sig")
    point = tables["policy_t80_pareto_summary"]
    front = point.loc[point["PointParetoTimeMaxT80"].astype(bool), "Policy"].tolist()
    agreement = tables["early_proxy_t80_front_comparison"]["FrontAgreement"].mean()
    stable = tables["t80_pareto_model_family_sensitivity"].loc[
        tables["t80_pareto_model_family_sensitivity"]["ParetoInAllFamilies"].astype(bool), "Policy"
    ].tolist()
    report = (
        "# Q4 充电时间—预测 T80 Pareto 敏感性\n\n"
        "本结果是对正式 SOH200/末段斜率 Pareto 的支持性敏感性，不替代 Q4 主结果。\n\n"
        f"局部线性 T80 点 Pareto 策略为：{'; '.join(front)}。"
        f"与早期退化代理的逐策略前沿成员一致率为 {agreement:.1%}。\n\n"
        "图中点大小随整块电池 bootstrap Pareto 频率增加；误差线为联合重采样的 2.5%—97.5% 分位区间。\n\n"
        f"在线性、幂律、加速指数三种 T80 模型族下始终位于点 Pareto 的策略为："
        f"{'; '.join(stable) if stable else '无'}。模型族敏感性不是置信区间。\n"
    )
    (paper / "report.md").write_text(report, encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Q4 T80 Pareto 支持性敏感性\n\n"
        "`paper/`包含可直接用于论文的图、表和短报告；`raw/`包含40块完整电池的三模型族T80、"
        "5000次整块电池联合重采样和运行元数据。本目录不替代`result/q4/02_full_validation/`。\n",
        encoding="utf-8",
    )
    manifest = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "manifest.csv":
            manifest.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    pd.DataFrame(manifest).to_csv(output_dir / "manifest.csv", index=False, encoding="utf-8-sig")
