"""Numerical core for the three comparable Question 1 curve models."""
# 问题一三种可比曲线模型（多项式混合/样条混合/函数型岭）的数值核心。
# 统一约定：以整块电池为推断单位，x=t/200 归一化循环数。

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


# 三种候选模型的类型常量，后续分支判断都依赖这些字符串标识
MODEL_POLYNOMIAL = "polynomial_mixed"
MODEL_SPLINE = "spline_mixed"
MODEL_FUNCTIONAL = "functional_ridge"
MODEL_TYPES = (MODEL_POLYNOMIAL, MODEL_SPLINE, MODEL_FUNCTIONAL)


@dataclass(frozen=True)
class ModelConfig:
    # lambda_random：电池随机截距/斜率的岭惩罚强度；lambda_curve：曲线（样条高次项）惩罚强度
    lambda_random: float = 0.1
    lambda_curve: float = 0.01


@dataclass
class PopulationCurveModel:
    # 拟合结果的容器：保存策略级固定系数、电池级随机系数与逐电池曲线系数，便于预测与可视化
    model_type: str
    config: ModelConfig
    policy_names: tuple[str, ...]
    fixed_coef: np.ndarray
    battery_ids: np.ndarray
    random_coef: np.ndarray | None = None
    cell_coef: np.ndarray | None = None
    cell_policy: np.ndarray | None = None

    def predict(self, policy: str | Iterable[str], cycle: Iterable[float]) -> np.ndarray:
        # 给定策略名与循环数，返回对应的 SOH 预测值；支持单个策略或策略序列
        cycles = np.asarray(cycle, dtype=float).reshape(-1)  # 循环数转一维数组
        policies = np.asarray([policy] * len(cycles) if isinstance(policy, str) else policy, dtype=str)  # 展开为与循环等长的策略数组
        if len(policies) != len(cycles):
            raise ValueError("policy and cycle must have the same length")  # 策略与循环数量必须一一对应
        basis = make_basis(self.model_type, cycles)  # 按模型类型构造样条/多项式基
        output = np.full(len(cycles), np.nan, dtype=float)  # 初始化输出，默认 NaN 便于发现未覆盖的策略
        policy_to_index = {name: i for i, name in enumerate(self.policy_names)}  # 策略名→固定系数行号
        for name in np.unique(policies):  # 按策略逐组预测，避免重复计算
            if name not in policy_to_index:
                raise KeyError(f"policy absent from training data: {name}")  # 训练数据里没有的策略直接报错
            use = policies == name  # 标记属于当前策略的样本
            output[use] = basis[use] @ self.fixed_coef[policy_to_index[name]]  # 基函数 × 策略系数 = 预测值
        return output


def make_basis(model_type: str, cycle: Iterable[float]) -> np.ndarray:
    """Return the explicitly specified cycle basis, using x=t/200."""
    # 构造显式的循环数基函数，x=t/200 归一化
    x = np.asarray(cycle, dtype=float).reshape(-1) / 200.0
    if model_type == MODEL_POLYNOMIAL:
        return np.column_stack((np.ones_like(x), x, x**2))  # 多项式：1, x, x^2
    if model_type in (MODEL_SPLINE, MODEL_FUNCTIONAL):
        # 三次截断幂基：1,x,x^2,x^3 加上在 0.25/0.50/0.75 处截断的三次项，允许曲线分段平滑
        columns = [np.ones_like(x), x, x**2, x**3]
        columns.extend(np.maximum(x - knot, 0.0) ** 3 for knot in (0.25, 0.50, 0.75))
        return np.column_stack(columns)
    raise ValueError(f"unknown model type: {model_type}")


def candidate_configs(model_type: str) -> list[ModelConfig]:
    # 返回各模型的超参数网格；留一验证时逐组比较选择最优
    if model_type == MODEL_POLYNOMIAL:
        # 多项式：只扫 lambda_random（离散随机惩罚），曲线惩罚恒为 0
        return [ModelConfig(value, 0.0) for value in (0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)]
    if model_type == MODEL_SPLINE:
        # 样条混合：lambda_random 与 lambda_curve 双惩罚组合
        return [
            ModelConfig(random_penalty, curve_penalty)
            for random_penalty in (0.03, 0.3, 3.0)
            for curve_penalty in (0.001, 0.01, 0.1, 1.0)
        ]
    if model_type == MODEL_FUNCTIONAL:
        # 函数型岭：lambda_random 固定为 0，只扫 lambda_curve（含 0，即最终选中的无惩罚解）
        return [
            ModelConfig(0.0, value)
            for value in (0.0, 0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0)
        ]
    raise ValueError(f"unknown model type: {model_type}")


def fit_population_model(data: pd.DataFrame, model_type: str, config: ModelConfig) -> PopulationCurveModel:
    """Fit a strategy population curve with equal inferential units at battery level.
    # 拟合策略总体曲线，推断单位是整块电池（而非循环行）。

    The two mixed candidates minimize
        ||y - F beta - Z b||^2 + lambda_curve ||P beta||^2
                                   + lambda_random ||b||^2,
    where Z contains a random intercept and slope for each battery.  The
    functional candidate first smooths each battery, then averages cell
    coefficients within strategy so batteries receive equal weight.
    # 两个混合候选最小化上述岭目标（F=固定效应，Z=每电池随机截距/斜率，
    # P=曲线高次项惩罚）；函数型候选先逐电池平滑、再在策略内等权平均电池系数。
    """
    required = {"battery_id", "cycle", "policy", "SOH_clean"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")  # 缺列直接报错，避免后续静默出错
    frame = data.loc[np.isfinite(data["SOH_clean"]) & np.isfinite(data["cycle"])].copy()  # 只保留 SOH 与循环均有效的行
    frame["policy"] = frame["policy"].astype(str)  # 策略名统一转字符串，避免类型不一致
    policy_names = tuple(pd.unique(frame["policy"]).tolist())  # 所有策略名的有序集合
    battery_ids = pd.unique(frame["battery_id"]).astype(int)  # 所有电池 id
    policy_index = {name: i for i, name in enumerate(policy_names)}  # 策略名→整数下标
    battery_index = {int(value): i for i, value in enumerate(battery_ids)}  # 电池 id→整数下标
    basis = make_basis(model_type, frame["cycle"].to_numpy())  # 循环基函数矩阵
    n_rows, n_basis = basis.shape  # 行数=样本数，列数=基函数个数

    if model_type in (MODEL_POLYNOMIAL, MODEL_SPLINE):
        # ---- 混合模型分支：固定效应（策略级）+ 随机效应（电池级）一起解 ----
        fixed = np.zeros((n_rows, len(policy_names) * n_basis), dtype=float)  # 固定效应设计矩阵：每策略占 n_basis 列
        pidx = frame["policy"].map(policy_index).to_numpy(dtype=int)  # 每行的策略下标
        rows = np.arange(n_rows)
        for j in range(n_basis):
            # 把第 j 个基函数放进对应策略的第 j 列
            fixed[rows, pidx * n_basis + j] = basis[:, j]

        random = np.zeros((n_rows, 2 * len(battery_ids)), dtype=float)  # 随机效应设计矩阵：每电池 2 列（截距+斜率）
        bidx = frame["battery_id"].map(battery_index).to_numpy(dtype=int)  # 每行的电池下标
        x = frame["cycle"].to_numpy(dtype=float) / 200.0  # 归一化循环数用于随机斜率
        random[rows, 2 * bidx] = 1.0  # 随机截距列：属该电池的行置 1
        random[rows, 2 * bidx + 1] = x  # 随机斜率列：置归一化循环数
        design = np.column_stack((fixed, random))  # 合并成完整设计矩阵

        penalty = np.zeros(design.shape[1], dtype=float)  # 对角惩罚向量，长度=总列数
        if model_type == MODEL_SPLINE:
            # 样条模型：对每个策略的 x^2 及以上列施加曲线惩罚
            for p in range(len(policy_names)):
                start = p * n_basis
                penalty[start + 2 : start + n_basis] = config.lambda_curve
        penalty[len(policy_names) * n_basis :] = config.lambda_random  # 后半段（随机效应）施加随机惩罚
        coefficient = _penalized_solve(design, frame["SOH_clean"].to_numpy(), penalty)  # 岭回归求解
        fixed_coef = coefficient[: len(policy_names) * n_basis].reshape(len(policy_names), n_basis)  # 拆出策略固定系数
        random_coef = coefficient[len(policy_names) * n_basis :].reshape(len(battery_ids), 2)  # 拆出电池随机系数
        return PopulationCurveModel(
            model_type, config, policy_names, fixed_coef, battery_ids, random_coef=random_coef
        )

    if model_type == MODEL_FUNCTIONAL:
        # ---- 函数型分支：先逐电池独立平滑，再策略内等权平均 ----
        cell_coef = np.empty((len(battery_ids), n_basis), dtype=float)  # 每电池一条曲线系数
        cell_policy = np.empty(len(battery_ids), dtype=object)  # 记录每电池所属策略
        penalty = np.zeros(n_basis, dtype=float)
        penalty[2:] = config.lambda_curve  # 只惩罚 x^2 及以上样条系数（对角选择矩阵 diag(0,0,1..1)）
        for i, battery_id in enumerate(battery_ids):
            use = frame["battery_id"].to_numpy() == battery_id  # 选出该电池的样本
            cell_coef[i] = _penalized_solve(basis[use], frame.loc[use, "SOH_clean"].to_numpy(), penalty)  # 单电池岭拟合
            cell_policy[i] = frame.loc[use, "policy"].iloc[0]  # 记录该电池的策略
        fixed_coef = np.vstack([cell_coef[cell_policy == name].mean(axis=0) for name in policy_names])  # 策略内电池系数等权平均
        return PopulationCurveModel(
            model_type,
            config,
            policy_names,
            fixed_coef,
            battery_ids,
            cell_coef=cell_coef,
            cell_policy=cell_policy,
        )
    raise ValueError(f"unknown model type: {model_type}")


def _penalized_solve(design: np.ndarray, response: np.ndarray, penalty: np.ndarray) -> np.ndarray:
    # 带对角岭惩罚的最小二乘求解：最小化 ||design·β - response||² + penalty·β²
    lhs = design.T @ design  # 正规方程左端 X'X
    scale = max(float(np.trace(lhs)) / max(lhs.shape[0], 1), 1.0)  # 用迹缩放惩罚，保证数值稳定
    lhs.flat[:: lhs.shape[0] + 1] += penalty + 1e-12 * scale  # 对角线加惩罚（+极小正则项防止奇异）
    rhs = design.T @ response  # 正规方程右端 X'y
    try:
        return np.linalg.solve(lhs, rhs)  # 直接求解
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(lhs, rhs, rcond=1e-12)[0]  # 奇异时退化为最小二乘（近似）
