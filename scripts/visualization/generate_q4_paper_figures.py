"""Generate paper-facing Q4 figures from frozen q4_full_v4 CSV artifacts."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "result" / "q4" / "02_full_validation"
FIGURE_DIR = RESULT / "figures"

POLICY_LABELS = {
    "3_6C-80PER_3_6C": "3.6C→3.6C（80%）",
    "80PER_3_6C": "0→3.6C（80%）",
    "4_8C_80PER_4_8C": "4.8C→4.8C（80%，旧）",
    "4_8C_80PER_4_8C_NEWSTRUCTURE": "4.8C→4.8C（80%，新）",
    "5C_67PER_4C_NEWSTRUCTURE": "5.0C→4.0C（67%，新）",
    "5_3C_54PER_4C_NEWSTRUCTURE": "5.3C→4.0C（54%，新）",
    "5_6C_19PER_4_6C_NEWSTRUCTURE": "5.6C→4.6C（19%，新）",
    "5_6C_36PER_4_3C_NEWSTRUCTURE": "5.6C→4.3C（36%，新）",
    "3_7C_31PER_5_9C_NEWSTRUCTURE": "3.7C→5.9C（31%，新）",
}


def _configure() -> None:
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
    })


def _read(name: str) -> pd.DataFrame:
    path = RESULT / name
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _save(fig: plt.Figure, name: str) -> Path:
    path = FIGURE_DIR / name
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return path


def draw_pareto_uncertainty() -> Path:
    summary = _read("policy_summary.csv")
    uncertainty = _read("policy_uncertainty.csv")
    frequency = _read("selection_frequency.csv")[["policy", "pareto_frequency"]]
    frame = summary.merge(uncertainty, on=["policy", "n_battery"]).merge(frequency, on="policy")
    for column in ("time_mean", "loss_mean", "time_p025", "time_p975", "loss_p025", "loss_p975", "pareto_frequency"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")

    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4), constrained_layout=True)
    panels = [
        (axes[0], None, None, "全部9个观测策略"),
        (axes[1], (10.05, 11.30), (-0.0003, 0.0050), "快速低退化区域放大"),
    ]
    for ax, xlim, ylim, title in panels:
        for row in frame.itertuples(index=False):
            color = (
                "#B22222" if row.policy == "5_3C_54PER_4C_NEWSTRUCTURE"
                else "#D89000" if row.policy == "5C_67PER_4C_NEWSTRUCTURE"
                else "#2563A6" if bool(row.pareto) else "#8C8C8C"
            )
            marker = (
                "D" if row.policy == "5_3C_54PER_4C_NEWSTRUCTURE"
                else "s" if row.policy == "5C_67PER_4C_NEWSTRUCTURE"
                else "o"
            )
            ax.errorbar(
                row.time_mean, row.loss_mean,
                xerr=[[row.time_mean - row.time_p025], [row.time_p975 - row.time_mean]],
                yerr=[[row.loss_mean - row.loss_p025], [row.loss_p975 - row.loss_mean]],
                fmt=marker, color=color, ecolor=color, alpha=0.86, capsize=2.5,
                markersize=5.5 + 5.0 * row.pareto_frequency, linewidth=1.0,
            )
            if xlim is not None and xlim[0] <= row.time_mean <= xlim[1] and ylim[0] <= row.loss_mean <= ylim[1]:
                offset = {
                    "5C_67PER_4C_NEWSTRUCTURE": (7, 7),
                    "5_3C_54PER_4C_NEWSTRUCTURE": (7, -13),
                }.get(row.policy, (5, 5))
                ax.annotate(POLICY_LABELS[row.policy], (row.time_mean, row.loss_mean),
                            xytext=offset, textcoords="offset points", fontsize=8)
        ax.set_title(title)
        ax.set_xlabel("平均充电时间（min）")
        ax.grid(alpha=0.22)
        if xlim:
            ax.set_xlim(*xlim)
        if ylim:
            ax.set_ylim(*ylim)
    axes[0].set_ylabel("第200循环相对SOH损失")
    axes[0].annotate("3.6C基准", (13.3880, 0.000520), xytext=(-42, 10), textcoords="offset points", fontsize=8)
    fig.suptitle("Q4观测策略Pareto点与整块电池bootstrap区间", fontsize=14)
    fig.legend(handles=[
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#2563A6", markeredgecolor="#2563A6", label="点估计Pareto"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#8C8C8C", markeredgecolor="#8C8C8C", label="非前沿"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#B22222", markeredgecolor="#B22222", label="点Pareto快速推荐"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#D89000", markeredgecolor="#D89000", label="非前沿近似并列敏感性"),
    ], loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=4, frameon=False)
    return _save(fig, "fig_q4_pareto_uncertainty.png")


def draw_fast_pair_comparison() -> Path:
    row = _read("fast_pair_comparison.csv").iloc[0]
    metrics = [
        ("时间差（min）", float(row["pair_time_difference_first_minus_second_p50"]),
         float(row["pair_time_difference_first_minus_second_p025"]),
         float(row["pair_time_difference_first_minus_second_p975"])),
        ("第200循环相对SOH损失差", float(row["pair_loss_difference_first_minus_second_p50"]),
         float(row["pair_loss_difference_first_minus_second_p025"]),
         float(row["pair_loss_difference_first_minus_second_p975"])),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.8), constrained_layout=True)
    for ax, (label, median, low, high) in zip(axes, metrics):
        ax.hlines(0, low, high, color="#4C78A8", linewidth=5, alpha=0.8)
        ax.scatter([low, high], [0, 0], color="#4C78A8", s=34, zorder=2)
        ax.scatter(median, 0, color="#B22222", marker="D", s=62, zorder=3)
        ax.axvline(0, color="#333333", linestyle="--", linewidth=1.2)
        ax.set_yticks([])
        ax.set_xlabel(label)
        ax.grid(axis="x", alpha=0.22)
        ax.set_title(f"中位差={median:.6f}\n95%区间=[{low:.6f}, {high:.6f}]")
    fig.suptitle("5.3C减5.0C：时间差与退化差均无法排除0", fontsize=14)
    fig.text(0.5, -0.02,
             f"5.3C退化更低概率={float(row['probability_lower_loss_than_pair']):.4f}；"
             f"时间不慢超过0.01 min概率={float(row['probability_not_slower_by_more_than_0_01_min']):.4f}；唯一推荐门槛=0.95",
             ha="center", fontsize=10)
    return _save(fig, "fig_q4_fast_pair_comparison.png")


def draw_m1_validation() -> Path:
    frame = _read("m1_coordinate_loso.csv")
    frame["rmse"] = pd.to_numeric(frame["rmse"], errors="raise")
    frame["constant_rmse"] = pd.to_numeric(frame["constant_rmse"], errors="raise")
    frame = frame.sort_values("rmse", ascending=True).reset_index(drop=True)
    y = np.arange(len(frame))
    fig, ax = plt.subplots(figsize=(10.0, 5.2), constrained_layout=True)
    ax.hlines(y, frame["constant_rmse"], frame["rmse"], color="#A6A6A6", linewidth=2)
    ax.scatter(frame["constant_rmse"], y, color="#4C78A8", s=52, label="常数基线RMSE", zorder=2)
    ax.scatter(frame["rmse"], y, color="#B22222", marker="D", s=52, label="单J岭RMSE", zorder=3)
    ax.set_yticks(y, frame["held_out_coordinate"])
    ax.set_xlabel("留一坐标RMSE")
    ax.set_ylabel("留出策略坐标 (C1, Q1, C2)")
    ax.set_title("单J岭代理仅1/7个留一坐标优于常数基线")
    ax.grid(axis="x", alpha=0.22)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.08), ncol=2, frameon=False)
    worst = frame.loc[frame["worst_fold"].astype(bool)].iloc[0]
    remaining = frame.loc[~frame["worst_fold"].astype(bool)]
    fig.text(
        0.5, -0.02,
        f"最差折位于训练J范围外且预测退化<0，贡献{float(worst['squared_error_share']):.1%}总平方误差；"
        f"剔除后单J岭RMSE={remaining['rmse'].mean():.6f}，常数基线={remaining['constant_rmse'].mean():.6f}",
        ha="center", fontsize=9,
    )
    return _save(fig, "fig_q4_m1_validation.png")


def main() -> None:
    _configure()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for path in (draw_pareto_uncertainty(), draw_fast_pair_comparison(), draw_m1_validation()):
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
