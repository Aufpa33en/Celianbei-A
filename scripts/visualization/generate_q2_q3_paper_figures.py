"""Generate paper-facing figures for Questions 2 and 3 from frozen CSV results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
Q2_FIGURE_DIR = ROOT / "result" / "q2" / "04_paper_materials" / "figures"
Q3_FIGURE_DIR = ROOT / "result" / "q3" / "03_final_predictions" / "figures"

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

MODEL_LABELS = {
    "P0_persistence": "P0 末值保持",
    "P1_linear": "P1 局部线性",
    "A_power": "A 约束幂律",
    "B_strategy": "B 策略迁移",
    "C_ridge": "C 轨迹岭回归",
    "D_ensemble": "D 组合模型",
}

MODEL_COLORS = {
    "P0_persistence": "#8C8C8C",
    "P1_linear": "#4C78A8",
    "A_power": "#F58518",
    "B_strategy": "#54A24B",
    "C_ridge": "#B22222",
    "D_ensemble": "#9467BD",
}


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.sans-serif": [
                "Microsoft YaHei",
                "SimHei",
                "Noto Sans CJK SC",
                "WenQuanYi Micro Hei",
                "DejaVu Sans",
            ],
            "axes.unicode_minus": False,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
        }
    )


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        result[column] = pd.to_numeric(result[column], errors="raise")
    return result


def _read_csv(relative_path: str) -> pd.DataFrame:
    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def _save(fig: plt.Figure, path: Path, pad_inches: float = 0.10) -> None:
    fig.savefig(path, dpi=300, bbox_inches="tight", pad_inches=pad_inches)
    plt.close(fig)


def draw_q2_strategy_late_rate() -> Path:
    frame = _read_csv(
        "result/q2/05_merged_robustness/paper/strategy_late_rate.csv"
    )
    frame = _numeric(
        frame,
        ["late_degradation_rate", "late_rate_sd", "new_structure", "n_batteries"],
    )
    frame = frame.sort_values("late_degradation_rate", ascending=True).reset_index(drop=True)
    frame["rate_scaled"] = frame["late_degradation_rate"] * 1e4
    frame["sd_scaled"] = frame["late_rate_sd"] * 1e4

    fig, ax = plt.subplots(figsize=(10.8, 5.8), constrained_layout=True)
    colors = np.where(frame["new_structure"].eq(1), "#D97706", "#2563A6")
    y = np.arange(len(frame))
    ax.errorbar(
        frame["rate_scaled"],
        y,
        xerr=frame["sd_scaled"],
        fmt="none",
        ecolor="#555555",
        capsize=3,
        linewidth=1.1,
        zorder=1,
    )
    ax.scatter(frame["rate_scaled"], y, c=colors, s=58, zorder=2)
    ax.set_yticks(y, [POLICY_LABELS.get(value, value) for value in frame["policy"]])
    ax.set_xlabel(r"第151–200循环平均退化速率（×$10^{-4}$ SOH/循环）")
    ax.set_ylabel("快充策略")
    ax.set_title("不同快充策略的末段退化速率（误差线为策略内电池标准差）")
    ax.grid(axis="x", alpha=0.22)
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#2563A6",
                   markeredgecolor="#2563A6", label="原结构", markersize=7),
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#D97706",
                   markeredgecolor="#D97706", label="新结构", markersize=7),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.11),
        ncol=2,
        frameon=False,
        borderaxespad=0.0,
    )
    path = Q2_FIGURE_DIR / "fig_q2_strategy_late_rate.png"
    _save(fig, path)
    return path


def draw_q2_model_stability() -> Path:
    bootstrap = _read_csv(
        "result/q2/03_formal_validation/bootstrap_selection_frequency.csv"
    )
    bootstrap = _numeric(
        bootstrap,
        ["selection_frequency", "n_bootstrap", "both_responses_improve_share"],
    ).sort_values("selection_frequency", ascending=True)
    sensitivity = _read_csv(
        "result/q2/03_formal_validation/sensitivity_model_comparison.csv"
    )
    sensitivity = sensitivity.loc[
        sensitivity["cohort"].eq("explicit_new_structure")
        & sensitivity["exclude_battery41"].astype(str).str.lower().eq("false")
        & sensitivity["model"].isin(
            ["ridge_Jhigh50", "ridge_Jhigh60", "ridge_Jhigh70", "ridge_H"]
        )
    ].copy()
    sensitivity = _numeric(
        sensitivity,
        ["relative_loss_improvement", "soh200_improvement"],
    )
    order = ["ridge_Jhigh50", "ridge_Jhigh60", "ridge_Jhigh70", "ridge_H"]
    sensitivity["order"] = sensitivity["model"].map({name: index for index, name in enumerate(order)})
    sensitivity = sensitivity.sort_values("order")

    labels = {
        "constant_mean": "常数模型",
        "ridge_Jhigh50": "Jhigh50",
        "ridge_Jhigh60": "Jhigh60",
        "ridge_Jhigh70": "Jhigh70",
        "ridge_H": "H",
    }
    fig, (ax_freq, ax_gain) = plt.subplots(
        1, 2, figsize=(11.2, 5.0), constrained_layout=True
    )

    y_freq = np.arange(len(bootstrap))
    freq_colors = ["#2E7D32" if name == "ridge_Jhigh50" else "#6B88A8"
                   for name in bootstrap["model"]]
    bars = ax_freq.barh(
        y_freq,
        bootstrap["selection_frequency"] * 100,
        color=freq_colors,
        height=0.62,
    )
    ax_freq.set_yticks(y_freq, [labels.get(name, name) for name in bootstrap["model"]])
    ax_freq.set_xlabel("bootstrap选择频率（%）")
    ax_freq.set_title("2000次整块电池bootstrap：阈值选择分散")
    ax_freq.grid(axis="x", alpha=0.22)
    for bar, value in zip(bars, bootstrap["selection_frequency"] * 100):
        ax_freq.text(value + 0.7, bar.get_y() + bar.get_height() / 2,
                     f"{value:.1f}%", va="center", fontsize=9)
    ax_freq.set_xlim(0, max(42.0, float((bootstrap["selection_frequency"] * 100).max() + 6)))

    y_gain = np.arange(len(sensitivity))
    height = 0.34
    ax_gain.barh(
        y_gain - height / 2,
        sensitivity["relative_loss_improvement"] * 100,
        height=height,
        color="#4C78A8",
        label="相对损失RMSE改善",
    )
    ax_gain.barh(
        y_gain + height / 2,
        sensitivity["soh200_improvement"] * 100,
        height=height,
        color="#F58518",
        label="SOH200 RMSE改善",
    )
    ax_gain.axvline(0.0, color="#555555", linestyle="--", linewidth=1)
    ax_gain.set_yticks(y_gain, [labels.get(name, name) for name in sensitivity["model"]])
    ax_gain.invert_yaxis()
    ax_gain.set_xlabel("相对常数模型的留一坐标RMSE改善（%）")
    ax_gain.set_title("明确新结构队列：不同响应给出不同优选")
    ax_gain.grid(axis="x", alpha=0.22)
    ax_gain.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.11),
        ncol=2,
        frameon=False,
        borderaxespad=0.0,
    )
    path = Q2_FIGURE_DIR / "fig_q2_model_stability.png"
    _save(fig, path)
    return path


def draw_q3_early_length_rmse() -> Path:
    frame = _read_csv("result/q3/02_full_validation/model_summary.csv")
    frame = frame.loc[frame["prediction_variant"].eq("raw")].copy()
    frame = _numeric(frame, ["L", "strategy_equal_rmse"])

    fig, ax = plt.subplots(figsize=(9.5, 5.2), constrained_layout=True)
    for model in MODEL_LABELS:
        subset = frame.loc[frame["model"].eq(model)].sort_values("L")
        linewidth = 2.8 if model == "C_ridge" else 1.6
        markersize = 7 if model == "C_ridge" else 5
        ax.plot(
            subset["L"],
            subset["strategy_equal_rmse"],
            marker="o",
            linewidth=linewidth,
            markersize=markersize,
            color=MODEL_COLORS[model],
            label=MODEL_LABELS[model],
            zorder=3 if model == "C_ridge" else 2,
        )
    ax.set_xticks([50, 100, 150])
    ax.set_xlabel("可用早期循环长度 L")
    ax.set_ylabel("策略等权 RMSE")
    ax.set_title("早期观测长度增加显著降低第151–200循环预测误差")
    ax.grid(alpha=0.22)
    ax.legend(
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        borderaxespad=0.0,
    )
    path = Q3_FIGURE_DIR / "fig_q3_early_length_rmse.png"
    _save(fig, path, pad_inches=0.12)
    return path


def draw_q3_test_predictions() -> Path:
    observed = _read_csv("data/processed/q1_cleaned/cycle_train_clean.csv")
    observed = observed.loc[observed["prediction_test"].eq(1)].copy()
    observed = _numeric(observed, ["battery_id", "cycle", "SOH_clean"])
    predictions = _read_csv(
        "result/q3/03_final_predictions/test_predictions_long.csv"
    )
    predictions = _numeric(
        predictions,
        [
            "battery_id",
            "cycle",
            "y_pred_raw",
            "y_pred_projected",
            "approx_interval_low",
            "approx_interval_high",
        ],
    )
    battery_order = sorted(predictions["battery_id"].unique())

    fig, axes = plt.subplots(
        3, 3, figsize=(12.0, 9.0), sharex=True, sharey=True, constrained_layout=True
    )
    for ax, battery_id in zip(axes.flat, battery_order):
        history = observed.loc[observed["battery_id"].eq(battery_id)].sort_values("cycle")
        future = predictions.loc[predictions["battery_id"].eq(battery_id)].sort_values("cycle")
        cycle = future["cycle"].to_numpy(dtype=float)
        ax.plot(history["cycle"], history["SOH_clean"], color="#222222", linewidth=1.2)
        ax.fill_between(
            cycle,
            future["approx_interval_low"].to_numpy(dtype=float),
            future["approx_interval_high"].to_numpy(dtype=float),
            color="#4C78A8",
            alpha=0.18,
        )
        ax.plot(
            cycle,
            future["y_pred_raw"],
            color="#E07A1F",
            linestyle="--",
            linewidth=1.1,
        )
        ax.plot(
            cycle,
            future["y_pred_projected"],
            color="#1F5A99",
            linewidth=1.8,
        )
        ax.axvline(150, color="#777777", linestyle=":", linewidth=1)
        policy = str(future["policy"].iloc[0])
        ax.set_title(f"电池{int(battery_id)} · {POLICY_LABELS.get(policy, policy)}")
        ax.grid(alpha=0.18)
    for ax in axes.flat[len(battery_order):]:
        ax.axis("off")
    fig.supxlabel("循环次数")
    fig.supylabel("SOH")
    fig.suptitle("9块测试电池：前150循环观测与第151–200循环预测", fontsize=14)
    fig.legend(
        handles=[
            Line2D([0], [0], color="#222222", linewidth=1.2, label="已观测SOH"),
            Line2D([0], [0], color="#E07A1F", linestyle="--", linewidth=1.1,
                   label="raw预测"),
            Line2D([0], [0], color="#1F5A99", linewidth=1.8, label="单调投影预测"),
            Patch(facecolor="#4C78A8", alpha=0.18, label="逐循环近似区间"),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=4,
        frameon=False,
        borderaxespad=0.0,
    )
    path = Q3_FIGURE_DIR / "fig_q3_test_predictions.png"
    _save(fig, path, pad_inches=0.12)
    return path


def draw_q3_t80_sensitivity() -> Path:
    eol = _read_csv("result/q3/03_final_predictions/eol_sensitivity.csv")
    eol = eol.loc[eol["model"].eq("C_ridge")].copy()
    eol["battery_id"] = pd.to_numeric(eol["battery_id"], errors="raise")
    eol["t80"] = pd.to_numeric(eol["t80"], errors="coerce")
    summary = _read_csv("result/q3/03_final_predictions/test_battery_summary.csv")
    summary = _numeric(summary, ["battery_id", "scenario_T80_default"])
    rows = []
    for battery_id, group in eol.groupby("battery_id", sort=True):
        finite = group.loc[group["status"].eq("finite_scenario"), "t80"].dropna()
        rows.append(
            {
                "battery_id": int(battery_id),
                "minimum": float(finite.min()),
                "maximum": float(finite.max()),
                "beyond": int(group["status"].eq("beyond_5000").sum()),
                "total": int(len(group)),
            }
        )
    frame = pd.DataFrame(rows).merge(
        summary[["battery_id", "scenario_T80_default"]], on="battery_id", how="left"
    )
    frame = frame.sort_values("scenario_T80_default", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(9.6, 5.6), constrained_layout=True)
    y = np.arange(len(frame))
    ax.hlines(y, frame["minimum"], frame["maximum"], color="#7088A3", linewidth=4, alpha=0.75)
    ax.scatter(frame["minimum"], y, color="#7088A3", s=28, zorder=2)
    ax.scatter(frame["maximum"], y, color="#7088A3", s=28, zorder=2)
    ax.scatter(frame["scenario_T80_default"], y, color="#B22222", marker="D", s=48, zorder=3)
    for index, row in frame.iterrows():
        if row["beyond"]:
            ax.annotate(
                f"{int(row['beyond'])}/{int(row['total'])}种设置>5000",
                (row["maximum"], index),
                xytext=(7, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )
    ax.set_yticks(y, [f"电池{int(value)}" for value in frame["battery_id"]])
    ax.invert_yaxis()
    ax.set_xlabel("T80情景循环数")
    ax.set_ylabel("测试电池")
    ax.set_title("C_ridge在不同拟合起点与预测口径下的T80敏感性")
    ax.grid(axis="x", alpha=0.22)
    ax.legend(
        handles=[
            Line2D([0], [0], color="#7088A3", linewidth=4, label="有限情景范围"),
            Line2D([0], [0], marker="D", color="none", markerfacecolor="#B22222",
                   markeredgecolor="#B22222", label="默认情景", markersize=7),
        ],
        loc="lower center",
        bbox_to_anchor=(0.5, 1.10),
        ncol=2,
        frameon=False,
        borderaxespad=0.0,
    )
    path = Q3_FIGURE_DIR / "fig_q3_t80_sensitivity.png"
    _save(fig, path)
    return path


def main() -> None:
    _configure_matplotlib()
    Q2_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    Q3_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        draw_q2_strategy_late_rate(),
        draw_q2_model_stability(),
        draw_q3_early_length_rmse(),
        draw_q3_test_predictions(),
        draw_q3_t80_sensitivity(),
    ]
    for path in outputs:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
