"""Writers for the exploratory Q1 lifetime-family comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


FAMILY_LABELS = {"linear": "局部线性", "power": "幂律", "exponential": "加速指数"}


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": [
                "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"
            ],
            "axes.unicode_minus": False,
            "font.size": 10,
        }
    )


def _draw_comparison(tables: dict[str, pd.DataFrame], path: Path) -> None:
    _configure_matplotlib()
    origin = tables["frozen_candidate_origin_sensitivity"].copy()
    origin["Origin"] = pd.to_numeric(origin["Origin"], errors="raise")
    origin["StrategyEqualRMSE"] = pd.to_numeric(
        origin["StrategyEqualRMSE"], errors="raise"
    )
    strategy = tables["strategy_t80_by_family"].copy()
    strategy["MedianEstimatedT80"] = pd.to_numeric(
        strategy["MedianEstimatedT80"], errors="raise"
    )
    selected_family = str(
        tables["nested_family_summary"].loc[
            tables["nested_family_summary"]["SelectedFamily"].astype(bool), "Family"
        ].iloc[0]
    )
    selected_order = (
        strategy.loc[strategy["Family"].eq(selected_family)]
        .sort_values("MedianEstimatedT80", ascending=False)["Policy"]
        .tolist()
    )
    policy_codes = {policy: f"S{index + 1}" for index, policy in enumerate(selected_order)}
    colors = {"linear": "#1565C0", "power": "#2E7D32", "exponential": "#C62828"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    for family in ("linear", "power", "exponential"):
        current = origin.loc[origin["Family"].eq(family)].sort_values("Origin")
        axes[0].plot(
            current["Origin"], current["StrategyEqualRMSE"], marker="o",
            linewidth=2, color=colors[family], label=FAMILY_LABELS[family],
        )
        values = strategy.loc[strategy["Family"].eq(family)].set_index("Policy")
        axes[1].plot(
            np.arange(len(selected_order)),
            values.loc[selected_order, "MedianEstimatedT80"].to_numpy(dtype=float),
            marker="o", linewidth=2, color=colors[family], label=FAMILY_LABELS[family],
        )
    axes[0].set_xlabel("截断循环")
    axes[0].set_ylabel("策略等权 RMSE")
    axes[0].set_title("近端预测误差随截断点变化")
    axes[0].set_xticks([100, 125, 150])
    axes[0].grid(alpha=0.25)
    axes[1].set_xlabel("策略编号（按局部线性 T80 排序）")
    axes[1].set_ylabel(r"策略预测 $T_{80}$ 中位数（cycle）")
    axes[1].set_title("寿命外推的模型形式敏感性")
    axes[1].set_yscale("log")
    axes[1].set_xticks(np.arange(len(selected_order)))
    axes[1].set_xticklabels([policy_codes[policy] for policy in selected_order])
    axes[1].grid(alpha=0.25)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels, loc="upper center", bbox_to_anchor=(0.5, 1.05),
        ncol=3, frameon=False,
    )
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)

    mapping = pd.DataFrame(
        [{"StrategyCode": policy_codes[policy], "Policy": policy} for policy in selected_order]
    )
    mapping.to_csv(path.with_name("fig_q1_lifetime_family_strategy_mapping.csv"), index=False,
                   encoding="utf-8-sig")


def draw_lifetime_family_comparison(
    tables: dict[str, pd.DataFrame], path: Path
) -> None:
    """Public paper-figure entrypoint shared by exploratory and authoritative writers."""
    _draw_comparison(tables, path)


def write_lifetime_model_comparison(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
    seed: int,
    runtime_seconds: float,
) -> None:
    raw = output_dir / "raw"
    paper = output_dir / "paper"
    raw.mkdir(parents=True, exist_ok=False)
    paper.mkdir(parents=True, exist_ok=False)
    for name, frame in tables.items():
        frame.to_csv(raw / f"{name}.csv", index=False, encoding="utf-8-sig")
    for name in (
        "nested_family_summary",
        "frozen_family_candidates",
        "frozen_candidate_origin_sensitivity",
        "strategy_t80_by_family",
        "strategy_t80_model_family_envelope",
        "battery_t80_model_family_envelope",
    ):
        tables[name].to_csv(paper / f"{name}.csv", index=False, encoding="utf-8-sig")
    _draw_comparison(tables, paper / "fig_q1_lifetime_family_comparison.png")

    family = tables["nested_family_summary"]
    selected = family.loc[family["SelectedFamily"].astype(bool)].iloc[0]
    envelope = tables["battery_t80_model_family_envelope"]
    report = (
        "# Q1 单调寿命外推模型族比较\n\n"
        "状态：支持性生成记录；权威副本已接入 `result/q1/raw` 与 `result/q1/paper`。\n\n"
        f"嵌套留一电池比较选择 `{selected['Family']}`，策略等权 151—200 RMSE "
        f"为 {selected['StrategyEqualRMSE']:.6f}，最坏电池 RMSE 为 "
        f"{selected['WorstBatteryRMSE']:.6f}。\n\n"
        f"三模型族 T80 包络的电池级最大跨度比中位数为 "
        f"{envelope['ModelFamilyT80Ratio'].median():.2f}，最大值为 "
        f"{envelope['ModelFamilyT80Ratio'].max():.2f}。该跨度是模型形式敏感性，不是置信区间。\n"
    )
    (paper / "report.md").write_text(report, encoding="utf-8")
    metadata = {
        "status": "supporting_generation_record_canonical_copies_in_q1_authoritative",
        "seed": seed,
        "selection_metric": "nested_outer_LOBO_strategy_equal_RMSE_cycles_151_200",
        "families": ["linear", "power", "exponential"],
        "paper_main_modified": False,
    }
    (raw / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(
        [
            {
                "stage": "nested_family_comparison_and_output",
                "runtime_seconds": runtime_seconds,
                "seed": seed,
                "candidate_count": len(tables["candidate_validation_by_battery"]["Candidate"].unique()),
                "outer_battery_count": len(tables["nested_family_lobo_by_battery"]["OuterBatteryId"].unique()),
            }
        ]
    ).to_csv(raw / "runtime_metadata.csv", index=False, encoding="utf-8-sig")
    manifest_rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            manifest_rows.append(
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    pd.DataFrame(manifest_rows).to_csv(
        output_dir / "manifest.csv", index=False, encoding="utf-8-sig"
    )
    (output_dir / "README.md").write_text(
        "# Q1 寿命模型族比较\n\n"
        "本目录保留模型族比较的支持性生成记录。经审查后，局部线性族继续作为主模型，"
        "核心表和图的权威副本已接入`result/q1/paper/`与`result/q1/raw/`；"
        "本目录不再作为论文取数入口。\n",
        encoding="utf-8",
    )
