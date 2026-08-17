"""Generate the compact four-question relationship chart used in the paper."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "paper" / "figures" / "flowchart2.png"


def select_chinese_font() -> str:
    """Choose an installed CJK font so labels render consistently on Windows."""
    preferred = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    return next((name for name in preferred if name in installed), "sans-serif")


def add_node(
    ax: plt.Axes,
    center_x: float,
    code: str,
    title: str,
    detail: str,
    *,
    facecolor: str = "#FFFFFF",
) -> None:
    """Draw one fixed-size process node with a stable two-line hierarchy."""
    width, height, bottom = 0.172, 0.255, 0.57
    left = center_x - width / 2
    box = FancyBboxPatch(
        (left, bottom),
        width,
        height,
        boxstyle="round,pad=0.006,rounding_size=0.008",
        linewidth=1.25,
        edgecolor="#374151",
        facecolor=facecolor,
    )
    ax.add_patch(box)

    if code:
        ax.text(
            center_x,
        bottom + 0.198,
            code,
            ha="center",
            va="center",
            fontsize=14.0,
            fontweight="bold",
            color="#1F4E79",
        )
    ax.text(
        center_x,
        bottom + 0.130,
        title,
        ha="center",
        va="center",
        fontsize=13.2,
        fontweight="bold",
        color="#111827",
    )
    ax.text(
        center_x,
        bottom + 0.055,
        detail,
        ha="center",
        va="center",
        fontsize=10.5,
        color="#4B5563",
    )


def add_link(ax: plt.Axes, x0: float, x1: float, label: str) -> None:
    """Connect adjacent nodes without crossing or routing around other nodes."""
    arrow = FancyArrowPatch(
        (x0 + 0.089, 0.697),
        (x1 - 0.089, 0.697),
        arrowstyle="-|>",
        mutation_scale=13,
        linewidth=1.2,
        color="#4B5563",
        shrinkA=0,
        shrinkB=0,
    )
    ax.add_patch(arrow)
    ax.text(
        (x0 + x1) / 2,
        0.747,
        label,
        ha="center",
        va="bottom",
        fontsize=9.5,
        color="#374151",
    )


def build() -> None:
    """Render the paper-ready PNG with a single modeling storyline."""
    plt.rcParams.update(
        {
            "font.family": select_chinese_font(),
            "axes.unicode_minus": False,
        }
    )

    fig, ax = plt.subplots(figsize=(13.8, 4.7), dpi=300)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    centers = [0.13, 0.38, 0.63, 0.88]
    add_node(ax, centers[0], "Q1", "寿命描述", "SOH 曲线 · T80")
    add_node(ax, centers[1], "Q2", "参数效应", "应力坐标 · 混合模型")
    add_node(ax, centers[2], "Q3", "早期预测", "151 至 200 循环 · T80")
    add_node(ax, centers[3], "Q4", "策略优化", "时间-寿命 Pareto", facecolor="#F3F6FA")

    for left, right, label in zip(
        centers[:-1],
        centers[1:],
        ["策略比较", "应力特征", "预测结果"],
        strict=True,
    ):
        add_link(ax, left, right, label)

    data_box = FancyBboxPatch(
        (0.035, 0.175),
        0.31,
        0.175,
        boxstyle="round,pad=0.006,rounding_size=0.006",
        linewidth=1.0,
        edgecolor="#6B7280",
        facecolor="#F8FAFC",
    )
    ax.add_patch(data_box)
    ax.text(
        0.19,
        0.292,
        "数据基础",
        ha="center",
        va="center",
        fontsize=11.0,
        fontweight="bold",
        color="#1F4E79",
    )
    ax.text(
        0.19,
        0.225,
        "49 电池 · 9350 记录 · 9 策略",
        ha="center",
        va="center",
        fontsize=9.8,
        color="#374151",
    )
    ax.text(
        0.19,
        0.187,
        "清洗修复并保留审计标记",
        ha="center",
        va="center",
        fontsize=9.0,
        color="#4B5563",
    )

    validation = FancyBboxPatch(
        (0.39, 0.175),
        0.575,
        0.175,
        boxstyle="round,pad=0.006,rounding_size=0.006",
        linewidth=1.0,
        edgecolor="#6B7280",
        facecolor="#F8FAFC",
    )
    ax.add_patch(validation)
    ax.text(
        0.6775,
        0.292,
        "贯穿验证",
        ha="center",
        va="center",
        fontsize=11.0,
        fontweight="bold",
        color="#1F4E79",
    )
    ax.text(
        0.6775,
        0.222,
        "整块电池分组 · LOBO · bootstrap · 敏感性分析",
        ha="center",
        va="center",
        fontsize=10.0,
        color="#374151",
    )

    ax.plot([centers[0], centers[0]], [0.57, 0.35], color="#6B7280", linewidth=1.0, linestyle=(0, (4, 4)))
    ax.plot([centers[2], centers[2]], [0.57, 0.35], color="#6B7280", linewidth=1.0, linestyle=(0, (4, 4)))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=300, bbox_inches="tight", pad_inches=0.12, facecolor="white")
    plt.close(fig)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
