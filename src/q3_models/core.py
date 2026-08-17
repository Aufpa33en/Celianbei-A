"""Data loading, trajectory utilities, metrics, and constrained extrapolation."""
# ============================================================================
# Q3（电池 SOH 预测）的公共工具层：负责数据装载、轨迹特征统计、预测指标计算，
# 以及带物理约束的外推投影。本文件只提供纯函数与数据结构，不承载具体模型，
# 被 features.py / models/*.py 等上层模块复用，保证全模块口径一致。
# ============================================================================

# 启用延迟求值的类型注解（PEP 563），允许在注解中引用尚未定义的类型。
from __future__ import annotations

# 标准库：dataclass 定义数据结构、Path 处理路径、Iterable 作类型标注
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# 第三方：NumPy 数值计算、pandas 表格数据处理
import numpy as np
import pandas as pd

# 项目内部：Q3 配置（CONFIG 实例、Q3Config 类型），供默认参数与网格/边界取值
from .config import CONFIG, Q3Config


@dataclass
class BatteryRecord:
    # 单个电池的“一行式”聚合记录：把电池的静态属性（策略、工艺参数）与逐循环
    # 数据绑定在一起，作为所有 Q3 模型输入的统一载体，避免用裸 dict 传递导致键名散落。
    battery_id: int          # 电池编号（样本 ID）
    policy: str              # 所属策略/工艺方案名（用于分组、one-hot 编码、分层等）
    meta: pd.Series          # 电池静态汇总行（来自 battery_summary_clean.csv，含 C1/Q1/C2 等工艺参数）
    cycles: pd.DataFrame     # 该电池的逐循环训练数据（cycle、SOH_clean、IR_clean、Tavg_raw 等）
    baseline: float          # 相对 SOH 的基准：前 5 个循环 SOH 的中位数，所有值都以它为除数归一化
    relative_soh: np.ndarray # 归一化后的相对 SOH 序列：relative = SOH / baseline，
                             # 是模型拟合与预测的核心目标量

    def relative_at(self, cycle: int) -> float:
        # 读取“第 cycle 个循环”的相对 SOH。注意索引偏移：数组下标从 0 开始，
        # 因此第 cycle 个循环对应下标 cycle-1（1-based 转 0-based）。
        return float(self.relative_soh[cycle - 1])

    def absolute_future(self, start: int = 151, end: int = 200) -> np.ndarray:
        # 提取 [start, end) 区间（默认 151~200 循环，即“未来观测窗口”）的绝对 SOH 真值。
        # 绝对 SOH = 相对 SOH × baseline；下标从 0 起，第 start 个循环对应下标 start-1。
        # 该真值用于评估外推式模型在绝对尺度上的精度（配合 RMSE 等指标）。
        return self.baseline * self.relative_soh[start - 1 : end]


def load_records(project_root: Path) -> tuple[dict[int, BatteryRecord], pd.DataFrame, pd.DataFrame]:
    # 统一装载入口：从预处理后的 q1_cleaned 目录读入全部电池数据并做一致性审计，
    # 返回 (records, meta, cycles)。records 按 battery_id 索引，后续模型直接按电池号取用。
    data_dir = project_root / "data" / "processed" / "q1_cleaned"
    meta = pd.read_csv(data_dir / "battery_summary_clean.csv")   # 电池静态属性表（每电池一行）
    cycles = pd.read_csv(data_dir / "cycle_train_clean.csv")     # 逐循环明细表（每电池多行）
    records: dict[int, BatteryRecord] = {}                       # 结果字典：battery_id → BatteryRecord
    for battery_id, frame in cycles.groupby("battery_id", sort=True):
        # 按电池分组遍历；sort=True 保证字典按电池号有序，便于调试与结果可复现。
        row = meta.loc[meta["battery_id"].eq(battery_id)].iloc[0]  # 取该电池在静态表中的对应行（唯一行）
        frame = frame.sort_values("cycle").reset_index(drop=True)  # 按循环号升序并重置索引，使下标与循环号对齐
        baseline = float(row["baseline_soh_cycles_1_5"])           # 预处理阶段已算好的前5循环 SOH 基准
        expected_baseline = float(
            frame.loc[frame["cycle"].between(1, 5), "SOH_clean"].median()
        )  # 用原始 SOH 直接重算前5循环中位数，作为基线的交叉校验
        if not np.isclose(baseline, expected_baseline, rtol=0.0, atol=1e-12):   # 基线一致性审计（不通过则抛错）
            raise ValueError(f"Battery {battery_id} has an inconsistent first-five-cycle SOH baseline")
        # 数据审计：若汇总表给的 baseline 与明细表重算值不一致，说明清洗有误，
        # 宁可抛错也不能让错误基线污染后续所有相对 SOH（rtol=0、atol=1e-12 表示要求完全一致）。
        relative_soh = frame["SOH_relative_clean"].to_numpy(float)  # 预处理已给出的相对 SOH 序列
        if not np.allclose(relative_soh, frame["SOH_clean"].to_numpy(float) / baseline,  # 相对 SOH 一致性审计（不通过则抛错）
                           rtol=0.0, atol=1e-12):
            raise ValueError(f"Battery {battery_id} has an inconsistent relative SOH series")
        # 再审计：相对 SOH 必须严格等于 SOH/baseline，防止“相对/绝对”两条口径漂移。
        records[int(battery_id)] = BatteryRecord(               # 构造该电池的聚合记录并存入字典
            battery_id=int(battery_id),
            policy=str(row["policy"]),
            meta=row,
            cycles=frame,
            baseline=baseline,
            relative_soh=relative_soh,
        )
    return records, meta, cycles                               # 返回（records 字典, 静态表, 逐循环表）三元组


def complete_battery_ids(meta: pd.DataFrame) -> list[int]:
    # 返回“完整历史”电池的编号列表：prediction_test == 0 表示该电池整个循环历史
    # 都可用于训练/验证（而非被预留用于测试）；排序后保证顺序稳定、结果可复现。
    return sorted(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int).tolist())


def slope(values: np.ndarray, cycles: np.ndarray | None = None) -> float:
    # 用最小二乘直线拟合 values~cycles 的斜率（等价于 np.polyfit(x, y, 1) 的斜率项）。
    # 用于刻画 SOH 退化速率、内阻/温度等特征的走向，作为后续回归的候选特征。
    values = np.asarray(values, dtype=float)                   # 统一转 float 数组，避免整型/列表混入
    if cycles is None:                                        # 未给循环号：用 1..n 自然下标
        cycles = np.arange(1, len(values) + 1, dtype=float)  # 未给循环号时用 1,2,... 自然下标
    else:                                                     # 已显式给出循环号时原样使用
        cycles = np.asarray(cycles, dtype=float)              # 显式给定的循环号同样转 float
    good = np.isfinite(values) & np.isfinite(cycles)          # 剔除缺失点，防止 NaN 污染回归
    if good.sum() < 2:                                        # 有效点不足 2 个则无法估计斜率
        return 0.0                                            # 有效点不足 2 个无法拟合，返回 0（中性斜率）
    x = cycles[good]                                          # 取有效点对应的横坐标（循环数）
    y = values[good]                                          # 取有效点对应的纵坐标（指标值）
    xc = x - x.mean()                                         # 中心化：便于用点积一步求出斜率
    denom = float(xc @ xc)                                    # Σ(x-mean)^2，即最小二乘的分母
    # 分子为 Σ(x-mean)(y-mean)；denom<=0（所有点重合）时斜率无定义，防御性返回 0。
    return 0.0 if denom <= 0 else float(xc @ (y - y.mean()) / denom)


def robust_slope_scale(slopes: Iterable[float]) -> float:
    # 对一组斜率估计“稳健尺度”，用于把不同电池的斜率特征归一化到可比量纲，
    # 或作为后续正则化/置信区间的尺度参考。
    values = np.asarray(list(slopes), dtype=float)            # 迭代器先转列表再成 float 数组（只能消费一次）
    values = values[np.isfinite(values)]                      # 丢弃缺失斜率
    if values.size == 0:                                      # 全部为缺失/空集：给出兜底尺度
        return 1e-8                                           # 空集兜底：返回极小正值，避免后续除以 0
    median = float(np.median(values))                         # 中位数作为位置中心
    # 1.4826 = 1/Φ⁻¹(0.75)，使 MAD（绝对偏差中位数）在正态假设下成为 σ 的一致估计；
    # 相比标准差，MAD 对离群斜率更稳健（个别异常电池不会把尺度拉爆）。
    scale = 1.4826 * float(np.median(np.abs(values - median)))
    if scale < 1e-8:
        # MAD 退化（如所有斜率相同）时退回样本标准差；仍极小则用 1e-8 兜底，防止除零。
        scale = max(float(np.std(values, ddof=1)) if values.size > 1 else 0.0, 1e-8)
    return scale                                              # 返回稳健尺度（MAD 或退化后的 std 兜底）


def fit_power_law(
    cycles: np.ndarray,
    relative_soh: np.ndarray,
    config: Q3Config = CONFIG,
) -> dict[str, float]:
    # 核心外推模型：假设相对 SOH 随循环数按“幂律”衰减 y = β0 - a·t^p
    # （β0 为初始相对 SOH，a 为退化系数，p 为幂指数）。
    # 在 power_grid 上网格搜索 p，用加权最小二乘选 SSE 最小的组合；
    # 这是 Q3 判断“寿命轨迹外推”的基准物理模型。
    t = np.asarray(cycles, dtype=float)                       # 循环数转 float 数组
    y = np.asarray(relative_soh, dtype=float)                 # 相对 SOH 转 float 数组
    good = np.isfinite(t) & np.isfinite(y)                    # 有效点掩码：横纵坐标都非缺失才算有效
    t, y = t[good], y[good]                                   # 剔除缺失点，保证矩阵运算不出现 NaN
    if t.size < 5:
        # 数据太少不做拟合：返回退化结果——a=0 表示“不衰减”，p=1 为线性名义值，
        # SSE=inf 保证该解永远不会被当作最优选中。
        return {"beta0": float(np.nanmean(y)), "a": 0.0, "p": 1.0, "sse": np.inf}
    L = float(t.max())                                        # 观测最末循环，作为权重归一化基准
    weights = 1.0 + 2.0 * (t / L) ** 2                        # 远端（大循环）权重更大：优先拟合近期/末端退化，提升外推质量
    root_w = np.sqrt(weights)                                 # 加权最小二乘等价于对数据乘 sqrt(w)，见下方 lstsq
    best: dict[str, float] | None = None                      # 最优候选缓存；None 表示尚未比较（首轮直接入选）
    for p in config.power_grid:                               # 在幂指数网格上穷举搜索
        z = t**p                                              # 幂变换后的设计变量 t^p
        design = np.column_stack([np.ones_like(t), -z])       # 设计矩阵 [1, -t^p]：对应模型 β0 + (-a)·z
        coef, *_ = np.linalg.lstsq(design * root_w[:, None], y * root_w, rcond=None)
        # 加权最小二乘：把设计矩阵与目标同乘 sqrt(w)，等价于最小化 Σw·(y-β0+a·z)²；
        # 返回 [β0, a]，lstsq 的其余返回值用 *_ 丢弃。
        beta0, a = float(coef[0]), float(coef[1])             # 解包并转 Python 标量：β0 截距、a 退化系数
        if a < 0:
            # 物理约束：SOH 不允许“越用越高”，负退化系数没有物理意义；
            # 强制 a=0 并用加权均值估计 β0，保证模型轨迹单调不增。
            a = 0.0
            beta0 = float(np.average(y, weights=weights))     # 用加权均值重估初始值，作为无退化系数时的合理起点
        pred = beta0 - a * z                                  # 该 (p,a,β0) 组合下的模型预测
        sse = float(np.sum(weights * (y - pred) ** 2))        # 加权残差平方和，作为拟合优度
        candidate = {"beta0": beta0, "a": a, "p": float(p), "sse": sse}  # 打包本幂指数的拟合结果
        if best is None or sse < best["sse"]:                 # 首轮或 SSE 更小则更新最优
            best = candidate                                  # 保留当前 SSE 最小的参数组合
    assert best is not None                                   # power_grid 非空，best 必然已被赋值
    return best                                               # 返回 SSE 最小的参数组合（β0, a, p, sse）


def predict_power_law(fit: dict[str, float], cycles: np.ndarray) -> np.ndarray:
    # 用 fit_power_law 的拟合结果在任意循环序列上外推相对 SOH：ŷ = β0 - a·t^p。
    t = np.asarray(cycles, dtype=float)                        # 目标循环序列转 float 数组
    return fit["beta0"] - fit["a"] * t ** fit["p"]             # 按幂律公式逐点预测相对 SOH


def power_law_eol(fit: dict[str, float], baseline: float, config: Q3Config = CONFIG) -> tuple[float, str]:
    # 求解“寿命终点 EOL”：即绝对 SOH 首次跌破 0.8 阈值对应的循环数。
    # 由于绝对 SOH = baseline × 相对 SOH，等价于相对 SOH 跌破 0.8/baseline。
    threshold = 0.8 / baseline                                # 换算到相对尺度：绝对阈值 0.8 除以基线
    beta0, a, p = fit["beta0"], fit["a"], fit["p"]            # 解包幂律参数供判断与反解
    if not np.isfinite([beta0, a, p]).all() or a <= 0 or beta0 <= threshold or p <= 0:  # 反解前提检查（参数有限、a>0、起点高于阈值、p>0）
        return np.nan, "no_finite_intersection"
    # 不满足反解前提（参数无效 / 不衰减 / 起点已低于阈值 / 幂指数非正），
    # 返回 NaN 并附状态码说明原因，便于调用方分类处理。
    cycle = float(((beta0 - threshold) / a) ** (1.0 / p))     # 由 β0 - a·t^p = threshold 反解 t
    if not np.isfinite(cycle) or cycle > config.eol_max_cycle:   # EOL 无意义或超出关注上限则判为“未失效”
        return np.nan, "beyond_5000"                           # EOL 超出关心范围（默认 5000 循环）→ 视为“未失效”
    if cycle <= 150:                                          # EOL 落在观测期内（观测至 150 循环）则标注该情形
        return cycle, "before_or_at_observation"               # EOL 落在观测窗口内：外推意义有限，仍给数值并标注
    return cycle, "finite_scenario"                            # 正常外推情景：观测期之后才达到 EOL


def project_absolute_prediction(raw: np.ndarray, anchor: float, config: Q3Config = CONFIG) -> np.ndarray:
    # 对原始外推预测施加两条物理约束，输出“可用”的绝对 SOH 轨迹：
    clipped = np.clip(np.asarray(raw, dtype=float), *config.soh_bounds)
    # ① 夹取到合理区间 soh_bounds=[0.75, 1.05]，防止数值溢出到无物理意义的值；
    return np.minimum.accumulate(np.concatenate([[float(anchor)], clipped]))[1:]
    # ② 用“前缀最小值”强制轨迹单调不增（电池 SOH 不可能回升）：把锚点（最后一个观测值）
    #    拼在最前面做累计最小值后再去掉锚点，保证每个时刻的预测 ≤ 之前所有值且以观测值为上界。


def prediction_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    # 预测误差的统一度量，返回 RMSE / MAE / 末点误差，供所有 Q3 模型在同口径下比较。
    residual = np.asarray(y_pred) - np.asarray(y_true)         # 残差向量（预测 − 真值）
    return {
        "rmse": float(np.sqrt(np.mean(residual**2))),          # 均方根误差：对大幅偏差更敏感
        "mae": float(np.mean(np.abs(residual))),               # 平均绝对误差：对离群点更稳健
        "error_cycle200": float(residual[-1]),                 # 第 200 循环的符号误差：直接反映“远端外推”偏乐观/悲观
    }


def strategy_parameters(record: BatteryRecord) -> np.ndarray:
    # 提取该电池对应的充电策略参数向量 [C1, Q1, C2]：
    row = record.meta                                          # 取该电池的静态汇总行，作为策略参数来源
    # C1（快充阶段电流档位）、Q1（快充容量占比）、C2（恒压/二阶段电流档位）三个工艺参数
    # 将作为解释变量进入“策略参数 → SOH 预测”的迁移模型；
    # 用 Series.get(..., np.nan) 保证缺参时以 NaN 占位而不是抛 KeyError。
    return np.asarray([row.get("C1", np.nan), row.get("Q1", np.nan), row.get("C2", np.nan)], dtype=float)
