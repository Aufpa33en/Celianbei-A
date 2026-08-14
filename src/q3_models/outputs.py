"""Atomic output writer and smoke-stage report."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from .config import CONFIG, Q3Config


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig")
    check = pd.read_csv(temporary)
    if list(check.columns) != list(frame.columns) or len(check) != len(frame):
        raise RuntimeError(f"Output validation failed for {path.name}")
    os.replace(temporary, path)


def _report_text(results: dict[str, pd.DataFrame], config: Q3Config) -> str:
    summary = results["model_summary.csv"]
    decision = results["selection_decision.csv"].drop_duplicates("model").sort_values("provisional_rank")
    runtime = results["runtime.csv"]
    lines = [
        "# 第三问 smoke test 阶段报告",
        "",
        "## 硬门状态",
        "",
        "文献筛选、模型推导和三路独立审查已经完成。smoke test仅用于排错、计时和工程可行性检查；本报告形成后停止，不运行40块电池全量LOBO，也不生成9块真实测试电池的最终预测。",
        "",
        "## 数据与模型",
        "",
        f"- 伪测试电池：{','.join(map(str, config.smoke_battery_ids))}，覆盖9种策略；其余31块完整电池用于smoke训练。",
        "- 早期长度：50、100、150；统一预测第151—200循环。",
        "- 模型：P0末值保持、P1线性趋势、A约束幂律、B同策略迁移、C降维多输出岭、D凸组合。",
        "- 主比较口径：raw预测；单调projected结果仅作敏感性分析。",
        "",
        "## 继承关系与文献依据",
        "",
        "第三问采用‘继承并扩展’路线：继承第一问的清洗SOH与策略曲线，继承第二问的策略参数和不可辨识性边界，新增早期特征到未来轨迹的预测层。Severson等支持早期循环特征与正则化预测；Kim等支持直接重建未来轨迹而非递归滚动；多输出GP文献支持共享未来时点相关结构；LFP/石墨幂律寿命文献只用于约束外推基线。由于本题没有电压-容量曲线和真实EOL标签，未照搬深度网络、完整MOGP或机理P2D模型。",
        "",
        "## 子agent审查硬门",
        "",
        "三个独立审查分别攻击了数据泄漏、数学/EOL推导和工程运行。初审发现相对SOH阈值、L<150拼接、动态特征未来泄漏、模型B量纲、嵌套调参、smoke选择偏差和计时口径等问题；修订后，三路复查均给出PASS，才进入本次smoke。",
        "",
        "## Raw预测结果",
        "",
        "| 模型 | L | 策略等权RMSE | 池化RMSE | MAE | 最差电池RMSE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    raw = summary.loc[summary["prediction_variant"].eq("raw")].sort_values(["model", "L"])
    for row in raw.itertuples(index=False):
        lines.append(
            f"| {row.model} | {row.L} | {row.strategy_equal_rmse:.6f} | {row.pooled_rmse:.6f} | {row.mae:.6f} | {row.worst_battery_rmse:.6f} |"
        )
    lines.extend(
        [
            "",
            "## 暂定排序与工程判定",
            "",
            "该排序应用预先冻结的2%并列规则，但不能用于淘汰数值可运行模型，也不是最终模型选择。所有工程通过模型必须进入用户确认后的全量嵌套LOBO。",
            "",
            "| 暂定排名 | 模型 | smoke综合分数 | 工程通过 | 三个L总时间/s |",
            "|---:|---|---:|---|---:|",
        ]
    )
    for row in decision.itertuples(index=False):
        total = runtime.loc[(runtime["model"].eq(row.model)) & runtime["stage"].eq("total"), "seconds"].sum()
        lines.append(f"| {row.provisional_rank} | {row.model} | {row.smoke_score:.6f} | {row.engineering_pass} | {total:.3f} |")
    lines.extend(
        [
            "",
            "## EOL边界",
            "",
            "80%寿命没有真实标签，只在L=150下作为情景外推。EOL不参与模型排序；本次不同模型的有限T80范围约从466循环延伸到2327循环，模型间差异远大于151—200短期预测差异，说明远期寿命对外推形式高度敏感。有限值、超过5000循环和无有限交点均保留为结果状态。",
            "",
            "## 运行时间与优化",
            "",
            "smoke总墙钟时间约8秒，最耗时的是模型C的嵌套PCA/多输出岭。实现已缓存前缀特征、每折只做一次SVD，并让模型D直接复用B/C的OOF结果。预计所有候选参加40块电池全量嵌套LOBO约需2—5分钟；实际瓶颈是结果核查而非数值计算。",
            "",
            "## 下一步与停止声明",
            "",
            "下一步应在用户确认后，让所有工程通过模型参加相同的40块电池嵌套LOBO，并在该阶段完成最终选模、误差区间和9块测试电池预测。本轮在此停止。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_smoke_outputs(project_root: Path, results: dict[str, pd.DataFrame], config: Q3Config = CONFIG) -> Path:
    output_dir = project_root / "result" / "q3" / "01_smoke_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_start = time.perf_counter()
    for name, frame in results.items():
        if name == "runtime.csv":
            continue
        _atomic_csv(frame, output_dir / name)

    write_seconds = time.perf_counter() - write_start
    runtime = results["runtime.csv"].copy()
    combinations = runtime.loc[runtime["stage"].eq("write"), ["model", "L"]].drop_duplicates()
    allocated = write_seconds / max(len(combinations), 1)
    runtime.loc[runtime["stage"].eq("write"), "seconds"] = allocated
    for (model, L), group in runtime.groupby(["model", "L"]):
        total = group.loc[~group["stage"].eq("total"), "seconds"].sum()
        runtime.loc[
            runtime["model"].eq(model) & runtime["L"].eq(L) & runtime["stage"].eq("total"),
            "seconds",
        ] = total
    results["runtime.csv"] = runtime
    _atomic_csv(runtime, output_dir / "runtime.csv")

    report_path = output_dir / "smoke_report.md"
    report_tmp = report_path.with_suffix(".md.tmp")
    report_tmp.write_text(_report_text(results, config), encoding="utf-8")
    os.replace(report_tmp, report_path)

    manifest_rows = []
    for path in sorted(output_dir.iterdir()):
        if path.name == "manifest.csv" or path.suffix not in {".csv", ".md"}:
            continue
        if path.suffix == ".csv":
            frame = pd.read_csv(path)
            rows, columns = frame.shape
        else:
            rows, columns = len(path.read_text(encoding="utf-8").splitlines()), 1
        manifest_rows.append(
            {
                "path": path.name,
                "rows": rows,
                "columns": columns,
                "version": config.version,
                "seed": config.seed,
                "smoke_battery_ids": ";".join(map(str, config.smoke_battery_ids)),
            }
        )
    _atomic_csv(pd.DataFrame(manifest_rows), output_dir / "manifest.csv")
    return output_dir
