"""Shared numerical core for Question 2 smoke tests.

The strategy parameter coordinate, rather than a cycle row or a battery, is the
independent design unit.  All parameter-response regressions therefore average
within strategy first and validate by leaving an entire parameter coordinate out.
"""

# ======================================================================
# 模块职责
# 本文件是第二问"冒烟测试(smoke test)"的共享数值核心。
# 核心设计原则：把"策略参数坐标" (C1, q, C2) —— 而不是某个充放电循环行或某块
# 电池 —— 作为独立的统计设计单元。因此所有"参数-响应"回归都先在同一个策略内部
# 对多块电池求平均（见 strategy_summary），再通过"留出整个参数坐标"的方式做交叉
# 验证，从而保证训练/测试之间不存在同策略样本泄漏。
# ======================================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# ===== 全局常量 =====
# SEED：固定随机种子以保证结果可复现。
# LAMBDA_GRID：岭回归惩罚系数 λ 的候选网格，从小到大覆盖"几乎不惩罚"到"强收缩"，
#   供留一坐标交叉验证在 select_lambda_inner 中择优。
# CHECKPOINTS：绘制/评估退化曲线用的标准循环检查点（第 25~200 圈）。
SEED = 20260814
LAMBDA_GRID = (0.0, 0.01, 0.1, 1.0, 10.0, 100.0)
CHECKPOINTS = np.array([25, 50, 75, 100, 125, 150, 175, 200], dtype=int)


# ===== 候选模型描述结构 =====
# name：候选模型的唯一标识，用于记录结果与对齐预测。
# features：用于预测响应的协议特征列名元组（可为空元组，表示"不使用任何特征"）。
# family：拟合器的种类，取值 constant / nearest / ridge / hierarchical，
#   决定调用哪一类训练-预测函数。
# quadratic_cycle：仅对 hierarchical 族生效，为 True 时在固定效应里额外加入 cycle^2
#   二次项，允许退化趋势弯曲（刻画加速退化）。
# frozen=True 使候选定义不可变，可被多处代码安全共享而不会意外被改写。
@dataclass(frozen=True)
class Candidate:
    name: str
    features: tuple[str, ...]
    family: str = "ridge"
    quadratic_cycle: bool = False


# ================= 第一层：策略级响应候选模型 =================
# 因变量是每个"策略坐标"聚合出的老化响应（如 soh200、relative_loss200、curve_loss200），
# 自变量为协议特征。各候选特征组合的物理含义：
#   - 空特征            ：常数均值基线，评估"不借助任何协议信息"能达到的精度下限；
#   - C1, q, C2         ：原始协议参数坐标（首段倍率 / 切换SOC点 / 二段倍率），最直接的输入表示；
#   - E1, E2            ：两阶段各自的实际充入电量代理（"分阶段能量"）；
#   - J  = E1+E2        ：整次充电的总能量吞吐代理；
#   - H                 ：按 SOC 加权的"高SOC停留"发热/应力代理；
#   - J_high_50/60/70   ：SOC 高于 50%/60%/70% 后充入的电量，刻画"高压区间"充电应力。
# 这些特征覆盖了"原始坐标 -> 能量吞吐 -> 高SOC阈值应力"三类不同机理的输入假设。
STRATEGY_CANDIDATES = (
    # 常数均值基线：不使用任何协议特征，直接预测训练响应的平均值。
    Candidate("constant_mean", (), "constant"),
    # 最近邻法：在 (C1, q, C2) 参数空间用最邻近策略的观测响应做预测，作为非参数基线。
    Candidate("nearest_coordinate", ("C1", "q", "C2"), "nearest"),
    # 岭回归：直接以三个原始协议参数为特征。
    Candidate("ridge_raw_C1_q_C2", ("C1", "q", "C2")),
    # 岭回归：只用分阶段能量 E1、E2，考察"分阶段能量"是否比原始坐标更有解释力。
    Candidate("ridge_stage_E1_E2", ("E1", "E2")),
    # 岭回归：只用总能量吞吐 J。
    Candidate("ridge_J", ("J",)),
    # 岭回归：只用高SOC加权发热代理 H。
    Candidate("ridge_H", ("H",)),
    # 岭回归：J 与 H 联合，同时纳入"能量总量"与"高SOC效应"两种应力。
    Candidate("ridge_J_H", ("J", "H")),
    # 岭回归：只用 SOC 高于 50%/60%/70% 时充入的电量，检验"高SOC阈值应力"假设。
    Candidate("ridge_Jhigh50", ("J_high_50",)),
    Candidate("ridge_Jhigh60", ("J_high_60",)),
    Candidate("ridge_Jhigh70", ("J_high_70",)),
)


# ================= 第二层：层次(混合效应)候选模型 =================
# 这些候选使用"循环级"数据拟合 Model C 的线性化代理（见 fit_hierarchical_penalized），
# 结构为 y = 截距 + β_x*x + Σ β_k * ((z_k - mean)/scale) * x + [可选 β_q*x^2]
#           + 电池随机效应(a_i + u_i*x) + 策略随机效应(v_p*x)。
# 注意：这里的 features 指"与循环数 x 交互"的应力协变量，而不是独立的主效应项；
#       它们以乘 x 的形式影响退化速率（斜率），是混合效应模型中"斜率随策略变化"的来源。
HIERARCHICAL_CANDIDATES = (
    # 无应力协变量：只有循环趋势 + 两层随机效应，作为层次模型基线。
    Candidate("hier_cycle_no_stress", (), "hierarchical", False),
    # 加入 J 作为线性应力协变量（与循环数交互），刻画能量吞吐对退化速率的影响。
    Candidate("hier_cycle_J_linear", ("J",), "hierarchical", False),
    # 加入 H 作为线性应力协变量，刻画高SOC发热对退化速率的影响。
    Candidate("hier_cycle_H_linear", ("H",), "hierarchical", False),
    # 同时加入 J 与 H 两个应力协变量。
    Candidate("hier_cycle_J_H_linear", ("J", "H"), "hierarchical", False),
    # 在 J 的基础上再额外加入 cycle^2 二次项，检验退化曲线是否呈下凸(加速退化)形态。
    Candidate("hier_cycle_J_quadratic", ("J",), "hierarchical", True),
)


def load_clean_data(project_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    # 载入第一问清洗后的两类数据：循环级数据(每圈一条)与电池级汇总数据(每块电池一条)。
    cycle_path = project_root / "data" / "processed" / "q1_cleaned" / "cycle_train_clean.csv"
    summary_path = project_root / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv"
    cycles = pd.read_csv(cycle_path)
    summary = pd.read_csv(summary_path)
    # 统计每块电池实际记录的循环圈数：若某块电池缺失部分循环，其退化曲线不完整，
    # 会破坏后续的曲线拟合与策略级聚合，因此只保留完整跑到 200 圈的"完整子队列"。
    counts = cycles.groupby("battery_id", observed=True)["cycle"].nunique()
    complete_ids = counts[counts.eq(200)].index
    cycles = cycles[cycles["battery_id"].isin(complete_ids)].copy()
    summary = summary[summary["battery_id"].isin(complete_ids)].copy()
    # SOH_clean 是层次模型的目标变量：一旦含缺失值，后续正规方程的 rhs/矩阵运算会
    # 产生 NaN 并静默污染所有系数，因此必须在此显式拦截并报错。
    if cycles["SOH_clean"].isna().any():
        raise ValueError("SOH_clean contains missing values in the complete cohort")
    return cycles, summary


def coordinate_id(frame: pd.DataFrame) -> pd.Series:
    # 把 (C1, q, C2) 三个参数各保留 3 位小数后拼成"|"分隔的字符串，作为策略坐标 ID。
    # 目的：把连续参数空间离散化为互不相同的分组键，供"按策略聚合"与"留一坐标验证"使用。
    # 统一格式化到 3 位小数，可避免浮点尾数误差导致同一策略被误判为两个不同坐标。
    return (
        frame["C1"].map(lambda value: f"{value:.3f}")
        + "|"
        + frame["q"].map(lambda value: f"{value:.3f}")
        + "|"
        + frame["C2"].map(lambda value: f"{value:.3f}")
    )


def add_protocol_features(frame: pd.DataFrame) -> pd.DataFrame:
    # 从原始协议参数派生出建模所需的应力特征。这些派生量全部是确定性的代数计算，
    # 不含任何随机成分，因此可以在训练/测试上直接复用同一个表达式。
    result = frame.copy()
    # q = Q1/100：Q1 是"切换点 SOC 百分比"，除以 100 换算成 0~1 的小数，
    # 便于与 0.8（充电目标 SOC）及 0.5/0.6/0.7 等阈值在同尺度下比较。
    result["q"] = result["Q1"] / 100.0
    # structure_batch：策略名中若含 "NEWSTRUCTURE" 标记则记为 1，否则为 0，
    # 用于刻画"新结构批次"这一批次层面的系统差异（可作混淆变量或分层依据）。
    result["structure_batch"] = result["policy"].astype(str).str.contains("NEWSTRUCTURE").astype(int)
    # T0：估算把电池充到 80% SOC 的总充电时间(分钟)。第 1 段从 0 充到 q、历时 60*q/C1
    # 分钟；第 2 段从 q 充到 0.8、历时 60*(0.8-q)/C2 分钟；两段相加即总时长。
    result["T0"] = 60.0 * (result["q"] / result["C1"] + (0.8 - result["q"]) / result["C2"])
    # E1、E2：两段各自的实际充入电量代理（充电倍率 × 相应 SOC 跨度），
    # 作为"分阶段能量"特征输入模型。
    result["E1"] = result["q"] * result["C1"]
    result["E2"] = (0.8 - result["q"]) * result["C2"]
    # J = E1 + E2：整次充电的总能量吞吐代理，衡量单次充电对电池的"总负荷"。
    result["J"] = result["E1"] + result["E2"]
    # H：按 SOC 加权的"高SOC停留"发热/应力代理，形如 ∫ SOC dSOC 的分段积分：
    # 0.5*C1*q^2 是第 1 段(0→q)、0.5*C2*(0.8^2-q^2) 是第 2 段(q→0.8)，
    # 系数 0.5 来自 ∫ s ds = s^2/2。它刻画充电过程中在高 SOC 区间停留的加权时间/热积累，
    # 是电池老化建模中典型的高应力项。
    result["H"] = 0.5 * (
        result["C1"] * result["q"] ** 2
        + result["C2"] * (0.8**2 - result["q"] ** 2)
    )
    # J_high_50/60/70：SOC 高于某阈值(0.5/0.6/0.7)之后充入的电量，直接刻画"高SOC压力"。
    # 若切换点 q 高于阈值：从阈值充到 q 用 C1 倍率、从 q 充到 0.8 用 C2 倍率；
    # 若 q 不高于阈值：从阈值到 0.8 整段都以 C2 倍率充电，故用 np.where 分支计算。
    for threshold in (0.5, 0.6, 0.7):
        result[f"J_high_{int(threshold * 100)}"] = np.where(
            threshold < result["q"],
            result["C1"] * (result["q"] - threshold)
            + result["C2"] * (0.8 - result["q"]),
            result["C2"] * (0.8 - threshold),
        )
    # 追加策略坐标 ID，供后续按策略聚合与留一坐标交叉验证使用。
    result["coordinate_id"] = coordinate_id(result)
    return result


def battery_degradation_summary(cycles: pd.DataFrame, battery_meta: pd.DataFrame) -> pd.DataFrame:
    # 把每块电池的循环级数据压缩成一行"电池级老化汇总"：返回的每一行代表一块电池，
    # 既保留原始协议参数(C1/Q1/C2)与运行工况均值，也加入从退化曲线拟合出的衰减特征。
    records: list[dict[str, float | int | str]] = []
    # 把电池元数据以 battery_id 为索引，方便在循环内逐电池快速查取策略参数与基线。
    meta = battery_meta.set_index("battery_id")
    for battery_id, group in cycles.groupby("battery_id", observed=True):
        # 先按循环圈数排序，保证后续"前5圈/后5圈"切片与真实时间顺序一致。
        group = group.sort_values("cycle")
        row = meta.loc[battery_id]
        # baseline：元数据里给出的"前 1~5 圈 SOH 基线"（单位与 SOH 相同）。
        baseline = float(row["baseline_soh_cycles_1_5"])
        # 一致性校验：用循环数据自身第 1~5 圈 SOH 的中位数与元数据基线比对。
        # 若不一致，说明数据在不同阶段的定义/口径有出入，所有依赖基线的特征都会失真，
        # 因此直接抛错以暴露数据问题。
        expected_baseline = float(group.loc[group["cycle"].between(1, 5), "SOH_clean"].median())
        if not np.isclose(baseline, expected_baseline, rtol=0.0, atol=1e-12):
            raise ValueError(f"Battery {battery_id} has an inconsistent first-five-cycle SOH baseline")
        # soh200：末段(第 196~200 圈)SOH 均值，代表电池在 200 圈结束后的健康状态。
        end_soh = float(group.loc[group["cycle"].between(196, 200), "SOH_clean"].mean())
        # 将循环圈数归一化到 [0,1]（cycle/200），避免原始数值(最大 200)过大、
        # 而二次项 x^2 过小，导致设计矩阵数值病态、最小二乘不稳定。
        x = group["cycle"].to_numpy(dtype=float) / 200.0
        # 定义退化量 degradation = 1 - SOH_relative_clean，即"累计健康损失"，
        # 方向与 SOH 相反（退化越大损失越大），用它作为二次多项式拟合的目标。
        degradation = 1.0 - group["SOH_relative_clean"].to_numpy(dtype=float)
        # 二次多项式设计矩阵 [1, x, x^2]；lstsq 给出最小二乘解，
        # 系数依次对应 截距/线性/二次 三项，用于刻画损失曲线的整体形态。
        design = np.column_stack((np.ones_like(x), x, x**2))
        coef = np.linalg.lstsq(design, degradation, rcond=None)[0]
        records.append(
            {
                "battery_id": int(battery_id),
                "policy": str(row["policy"]),
                # C1 可能缺测，缺测时记 NaN；后续 strategy_summary 会按 C1 非空过滤掉这些电池。
                "C1": float(row["C1"]) if np.isfinite(row["C1"]) else np.nan,
                "Q1": float(row["Q1"]),
                "C2": float(row["C2"]),
                "baseline_soh": baseline,
                "soh200": end_soh,
                # 相对损失：200 圈后相对初始 SOH 的下降比例（0~1 之间）。
                "relative_loss200": 1.0 - end_soh / baseline,
                # 曲线总损失 = 三系数之和，即拟合曲线在 x=1(第 200 圈)处的累计退化量。
                "curve_loss200": float(coef.sum()),
                "curve_linear": float(coef[1]),
                "curve_quadratic": float(coef[2]),
                # 平均充电时间、内阻、平均温度：作为可能影响老化的运行工况协变量。
                "mean_chargetime": float(row["mean_chargetime"]),
                "mean_IR": float(row["mean_IR"]),
                "mean_Tavg": float(row["mean_Tavg"]),
                # 是否为编号 41 的电池：该电池疑似为已知的异常/关注样本，
                # 显式给出哑变量便于在分析中隔离并检验它的影响。
                "flag_battery41": int(battery_id == 41),
            }
        )
    # 所有电池汇总完毕后，统一补上协议派生特征(q、T0、E1、E2、J、H、J_high_*、coordinate_id)。
    return add_protocol_features(pd.DataFrame.from_records(records))


def strategy_summary(battery: pd.DataFrame) -> pd.DataFrame:
    # 把"电池级"数据按策略聚合为"策略坐标级"数据——这是本模块所有参数-响应回归的
    # 训练单元：返回的每一行代表一个策略坐标，其协议特征取"first"、响应取均值。
    # 先剔除 C1 缺失的电池：C1 缺失会导致协议特征无法计算，也无法参与坐标匹配。
    complete = battery[battery["C1"].notna()].copy()
    # 协议特征列：同一策略内这些参数理论上是常数（同策略共享同一协议），
    # 因此聚合方式取 "first"（策略内第一条记录的值即可代表整组）。
    feature_columns = [
        "C1", "Q1", "C2", "q", "T0", "E1", "E2", "J", "H",
        "J_high_50", "J_high_60", "J_high_70", "structure_batch",
    ]
    # 响应列：同一策略内多块电池的老化响应存在自然波动（电池间异质性），
    # 因此取均值作为该策略的代表响应，以降低单体随机误差的影响。
    response_columns = [
        "soh200", "relative_loss200", "curve_loss200", "curve_linear", "curve_quadratic",
        "mean_chargetime", "mean_IR", "mean_Tavg",
    ]
    aggregations: dict[str, str | tuple[str, str]] = {column: "first" for column in feature_columns}
    aggregations.update({column: "mean" for column in response_columns})
    # 额外统计该策略下纳入聚合的电池数量 n_batteries，作为样本量/可信度参考。
    aggregations["n_batteries"] = ("battery_id", "size")
    # 一次性完成分组聚合：特征列取 first、响应列取 mean、电池数取 size。
    # 三元组形式(value)已含列名，元组形式则需补 (key, value) 使列名与键一致。
    result = complete.groupby("policy", as_index=False, observed=True).agg(**{
        key: value if isinstance(value, tuple) else (key, value) for key, value in aggregations.items()
    })
    result["coordinate_id"] = coordinate_id(result)
    # 两个队列哑变量：
    # equal_time_cohort：是否非 3_6C-80PER_3_6C 的均衡时间策略（该策略是时间均衡基准）；
    # explicit_new_structure_cohort：是否属于"新结构批次"。二者用于检验批次/策略类别差异。
    result["equal_time_cohort"] = result["policy"].ne("3_6C-80PER_3_6C").astype(int)
    result["explicit_new_structure_cohort"] = result["structure_batch"].eq(1).astype(int)
    # 按策略名排序并重置行索引，保证输出行序稳定、可复现。
    return result.sort_values("policy").reset_index(drop=True)


def standardized(train: pd.DataFrame, test: pd.DataFrame, features: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # 用"训练集"的均值与标准差对训练/测试特征做 Z-score 标准化。
    # 关键点：mean 与 scale 只能从训练集估计，测试集必须复用同一套参数，
    # 否则会把测试信息泄漏进标准化过程，破坏留一验证的无偏性。
    if not features:
        # 无特征时返回空矩阵与空参数，供常数均值等模型使用；
        # 空矩阵保证了与有特征路径相同的形状，下游矩阵乘法维度才能自洽。
        return np.empty((len(train), 0)), np.empty((len(test), 0)), np.array([]), np.array([])
    mean = train.loc[:, features].mean(axis=0).to_numpy(dtype=float, copy=True)
    # ddof=0 表示用总体标准差(除以 n)，保持与交叉验证中误差计算的口径一致。
    scale = train.loc[:, features].std(axis=0, ddof=0).to_numpy(dtype=float, copy=True)
    # 若某特征在训练集中近似零方差(标准差 < 1e-12)，直接相除会产生除零/NaN，
    # 此时把其 scale 强制置为 1，等价于"对该特征不做缩放"。
    scale[scale < 1e-12] = 1.0
    return (
        (train.loc[:, features].to_numpy(dtype=float) - mean) / scale,
        (test.loc[:, features].to_numpy(dtype=float) - mean) / scale,
        mean,
        scale,
    )


def ridge_fit(x: np.ndarray, y: np.ndarray, ridge_lambda: float) -> np.ndarray:
    # 岭回归：最小化 ||y - [1, X]w||^2 + lambda * ||w||^2。
    # 先拼接常数项列 1，得到含截距的完整设计矩阵 [1, X]。
    design = np.column_stack((np.ones(len(x)), x))
    # 惩罚矩阵：diag(lambda) 的对角阵，只在每个系数对应位置加惩罚，实现 L2 收缩。
    penalty = np.eye(design.shape[1]) * ridge_lambda
    # 截距项(第 0 个系数)不做惩罚：这是岭回归的标准做法，
    # 保证预测结果对特征的平移变换保持不变。
    penalty[0, 0] = 0.0
    # 解正规方程 (X^T X + lambda*I) w = X^T y，其解即为岭回归系数。
    lhs = design.T @ design + penalty
    return np.linalg.lstsq(lhs, design.T @ y, rcond=None)[0]


def ridge_predict(coef: np.ndarray, x: np.ndarray) -> np.ndarray:
    # 用 ridge_fit 返回的系数做预测；设计矩阵必须与拟合时完全一致(1 + x 列)。
    return np.column_stack((np.ones(len(x)), x)) @ coef


def select_lambda_inner(train: pd.DataFrame, response: str, features: tuple[str, ...]) -> float:
    # 在内层"留一策略坐标"交叉验证上为岭回归挑选最优惩罚系数 λ。
    # 做法：对每个策略坐标依次当测试集、其余坐标训练，得到该 λ 下所有留出误差的均值；
    # 遍历完整个 λ 网格后，以"最小误差的 1.01 倍 + 1e-15"为容差，在精度几乎不损失的
    # 前提下选择最大的 λ（相当于"1SE/一标准误差规则"式的稳健选择：惩罚更强、模型更平滑，
    # 更不容易过拟合单体噪声）。
    groups = train["coordinate_id"].unique().tolist()
    # 策略坐标太少(≤3)时留一验证极不稳定，直接返回较大的 λ=10 作为兜底。
    if len(groups) <= 3:
        return 10.0
    scores: list[tuple[float, float]] = []
    for ridge_lambda in LAMBDA_GRID:
        errors: list[float] = []
        for group in groups:
            inner_train = train[train["coordinate_id"].ne(group)]
            inner_test = train[train["coordinate_id"].eq(group)]
            # 标准化参数只从 inner_train 估计并复用到 inner_test，确保无泄漏。
            x_train, x_test, _, _ = standardized(inner_train, inner_test, features)
            coef = ridge_fit(x_train, inner_train[response].to_numpy(dtype=float), ridge_lambda)
            prediction = ridge_predict(coef, x_test)
            # 记录该"被留出的坐标"上的均方误差。
            errors.append(float(np.mean((prediction - inner_test[response].to_numpy(dtype=float)) ** 2)))
        # 一个 λ 的整体得分 = 各留出坐标误差的平均值。
        scores.append((float(np.mean(errors)), ridge_lambda))
    minimum = min(value for value, _ in scores)
    tolerance = minimum * 1.01 + 1e-15
    # 在所有"误差不超过容差"的 λ 中取最大者：越大的惩罚收缩越强、越平滑稳健。
    return max(ridge_lambda for value, ridge_lambda in scores if value <= tolerance)


def nearest_prediction(train: pd.DataFrame, test: pd.DataFrame, response: str) -> np.ndarray:
    # 最近邻基线：不做任何参数化建模，直接取 (C1, q, C2) 参数空间上
    # 距离最近策略的观测响应作为预测。
    features = ("C1", "q", "C2")
    # 同样用训练集标准化，使三个参数在欧氏距离计算中量纲统一、权重可比。
    x_train, x_test, _, _ = standardized(train, test, features)
    y = train[response].to_numpy(dtype=float)
    output = np.empty(len(test), dtype=float)
    for index, row in enumerate(x_test):
        # 平方欧氏距离：逐样本求 sum((x_train - row)^2)，由于已标准化，直接累加即可。
        distance = np.sum((x_train - row) ** 2, axis=1)
        # 取距离最近样本的响应值作为预测(最近邻回归，k=1)。
        output[index] = y[int(np.argmin(distance))]
    return output


def fit_hierarchical_penalized(
    train_cycles: pd.DataFrame,
    train_strategy: pd.DataFrame,
    features: tuple[str, ...],
    quadratic: bool,
    lambda_fixed: float = 1.0,
    lambda_battery: float = 1.0,
    lambda_policy: float = 10.0,
) -> tuple[np.ndarray, dict[str, object]]:
    """Fit a linearized smoke surrogate of Model C by penalized least squares.

    y_it = beta0 + beta_x*x + sum beta_k*z_pk*x + beta_q*x^2
           + a_i + u_i*x + v_p*x + error.

    For runtime, this smoke fit uses cycle 1 and every fifth cycle. The formal
    nonlinear exponential-link/AR(1) likelihood is intentionally not claimed
    here. This surrogate answers whether the additional hierarchy has enough
    predictive signal to justify a later full Model C fit.
    """
    # ===== 拟合 Model C 的线性化"冒烟"代理(惩罚最小二乘) =====
    # 混合效应结构：固定效应含 截距 + 循环主趋势 x + "应力×x"交互 + (可选)x^2，
    # 随机效应含 电池截距/斜率(a_i, u_i) 与 策略斜率(v_p)；全部随机效应用 L2 惩罚
    # 收缩实现，故称"岭型混合效应"。以下注释逐块说明设计矩阵与惩罚的构造。

    # 建立 policy -> 策略级特征值的查找表，便于从循环级帧按策略取应力协变量。
    strategy_lookup = train_strategy.set_index("policy")
    # 出于运行时间考虑，本"冒烟拟合"只保留第 1 圈与每第 5 圈的循环行
    # (cycle ∈ {1,5,10,...})：既保留了下降趋势与随机效应的可识别性，又把样本量
    # 压缩到约 1/5，使整个候选搜索在竞赛时限内可跑完。
    frame = train_cycles[
        train_cycles["policy"].isin(strategy_lookup.index)
        & (train_cycles["cycle"].eq(1) | train_cycles["cycle"].mod(5).eq(0))
    ].copy()
    # 收集全部策略与电池的唯一取值，并映射为从 0 开始的稠密整数索引，
    # 供构造哑变量形式的随机效应设计矩阵使用。
    policies = sorted(frame["policy"].unique().tolist())
    batteries = sorted(frame["battery_id"].unique().tolist())
    p_index = {name: index for index, name in enumerate(policies)}
    b_index = {value: index for index, value in enumerate(batteries)}
    # 应力协变量同样只在策略级训练集上估计 mean/scale(与 standardized 相同的防泄漏原则)。
    means = train_strategy.loc[:, features].mean(axis=0).to_numpy(dtype=float, copy=True) if features else np.array([])
    scales = train_strategy.loc[:, features].std(axis=0, ddof=0).to_numpy(dtype=float, copy=True) if features else np.array([])
    if len(scales):
        # 零方差特征令 scale=1，避免后续标准化除零。
        scales[scales < 1e-12] = 1.0
    # 循环数归一化到 [0,1]，与策略级回归使用相同的比例尺。
    x = frame["cycle"].to_numpy(dtype=float) / 200.0
    # 固定效应设计矩阵的起始两列：截距 1 与循环主趋势 x。
    fixed_columns = [np.ones(len(frame)), x]
    for feature, mean, scale in zip(features, means, scales):
        # 每个应力协变量 z 先标准化，再与 x 相乘，构成"应力×循环"交互项：
        # 由于该项以 x 为系数的一部分，等价于让退化速率(斜率)线性依赖该策略应力，
        # 这正是"不同策略的退化速率不同"这一核心假设的体现。
        z = frame["policy"].map(strategy_lookup[feature]).to_numpy(dtype=float)
        fixed_columns.append(((z - mean) / scale) * x)
    if quadratic:
        # quadratic=True 时额外加入 x^2，允许退化趋势弯曲，用于刻画加速退化形态。
        fixed_columns.append(x**2)
    fixed = np.column_stack(fixed_columns)
    # 随机效应设计矩阵：每块电池对应两列"截距+斜率"(a_i, u_i)，
    # 每个策略对应一列斜率 v_p。u_i 与 v_p 列都乘以 x，
    # 表示"电池个体偏差"与"策略影响"都作用于退化速率而非退化水平。
    random_battery = np.zeros((len(frame), 2 * len(batteries)))
    random_policy = np.zeros((len(frame), len(policies)))
    rows = np.arange(len(frame))
    bidx = frame["battery_id"].map(b_index).to_numpy(dtype=int)
    pidx = frame["policy"].map(p_index).to_numpy(dtype=int)
    # 电池随机截距列：命中该电池的行置 1，其余为 0(哑变量)。
    random_battery[rows, 2 * bidx] = 1.0
    # 电池随机斜率列：命中该电池的行置为 x，使该电池的退化速率偏离整体。
    random_battery[rows, 2 * bidx + 1] = x
    # 策略随机斜率列：命中该策略的行置为 x，使该策略的退化速率偏离整体。
    random_policy[rows, pidx] = x
    # 把三部分横向拼接成完整设计矩阵 D = [固定效应 | 电池随机 | 策略随机]。
    design = np.column_stack((fixed, random_battery, random_policy))
    # 惩罚向量：对不同类型的系数施加不同强度的 L2 收缩(岭型混合效应)，
    # 用先验控制各随机效应组的复杂度，避免每组单独估计时过拟合。
    penalty = np.zeros(design.shape[1])
    # 固定效应中"应力×循环"交互系数位于索引 2 起，施加 lambda_fixed 惩罚。
    penalty[2 : 2 + len(features)] = lambda_fixed
    # 电池随机效应的 2*n_battery 个系数施加 lambda_battery。
    penalty[fixed.shape[1] : fixed.shape[1] + random_battery.shape[1]] = lambda_battery
    # 策略随机效应的 n_policy 个系数施加最强的 lambda_policy 惩罚：
    # 策略个数相对样本量偏少，更强的收缩可防止策略层过拟合。
    penalty[fixed.shape[1] + random_battery.shape[1] :] = lambda_policy
    # 正规方程：求解 (D^T D + diag(penalty)) w = D^T y，得到惩罚最小二乘解。
    lhs = design.T @ design
    # 只给对角线加惩罚；再加 1e-10 的极小数值稳定项，防止某些对角元素为 0 时矩阵奇异。
    lhs.flat[:: lhs.shape[0] + 1] += penalty + 1e-10
    rhs = design.T @ frame["SOH_clean"].to_numpy(dtype=float)
    try:
        coef = np.linalg.solve(lhs, rhs)
    except np.linalg.LinAlgError:
        # 若 (D^T D + diag(penalty)) 仍不可逆(数值奇异)，回退到最小二乘的稳健解法
        # (lstsq 通过奇异值分解保证在奇异时也能给出最小范数解)。
        coef = np.linalg.lstsq(lhs, rhs, rcond=None)[0]
    # 计算拟合值与残差，供训练 RMSE 与残差诊断使用。
    fitted = design @ coef
    residual = frame["SOH_clean"].to_numpy(dtype=float) - fitted
    residual_frame = pd.DataFrame({"battery_id": frame["battery_id"].to_numpy(), "cycle": frame["cycle"].to_numpy(), "residual": residual})
    # 逐电池计算"相邻循环残差的相关系数"(lag-1 自相关)：若残差仍有明显正自相关，
    # 说明线性模型没有解释完时间结构，未来可能需要引入 AR(1) 等误差过程。
    pairs = []
    for _, group in residual_frame.groupby("battery_id", observed=True):
        values = group.sort_values("cycle")["residual"].to_numpy()
        if len(values) > 1:
            pairs.append(np.corrcoef(values[:-1], values[1:])[0, 1])
    # 汇总诊断信息：固定效应系数、标准化参数、训练 RMSE、残差一阶自相关均值、
    # 策略/电池组规模。这些信息既供 predict_hierarchical 复现预测，
    # 也供上层比较各层次候选的拟合质量与残差结构。
    info = {
        "fixed_coef": coef[: fixed.shape[1]],
        "feature_mean": means,
        "feature_scale": scales,
        "features": features,
        "quadratic": quadratic,
        "train_rmse": float(np.sqrt(np.mean(residual**2))),
        "lag1_residual_correlation": float(np.nanmean(pairs)),
        "n_policy": len(policies),
        "n_battery": len(batteries),
    }
    return coef, info


def predict_hierarchical(info: dict[str, object], test_strategy: pd.DataFrame, cycles: np.ndarray) -> np.ndarray:
    # 用 fit_hierarchical_penalized 返回的信息对新策略做预测。
    # 注意：预测时只使用固定效应(fixed_coef)，随机效应在预测期不可观测、按 0 处理，
    # 等价于对随机效应取"无条件期望"，得到每个策略在给定应力下的确定性预测曲线。
    features = tuple(info["features"])
    means = np.asarray(info["feature_mean"], dtype=float)
    scales = np.asarray(info["feature_scale"], dtype=float)
    fixed_coef = np.asarray(info["fixed_coef"], dtype=float)
    predictions: list[dict[str, float | int | str]] = []
    x = cycles.astype(float) / 200.0
    for _, row in test_strategy.iterrows():
        # 每个策略独立重建与拟合阶段完全一致的固定效应设计矩阵。
        columns = [np.ones(len(x)), x]
        for feature, mean, scale in zip(features, means, scales):
            # 策略特征值标准化后与循环数 x 相乘，生成"应力×循环"交互列。
            columns.append(np.repeat((float(row[feature]) - mean) / scale, len(x)) * x)
        if bool(info["quadratic"]):
            columns.append(x**2)
        value = np.column_stack(columns) @ fixed_coef
        # 把该策略在各检查点循环处的预测逐行展开为"长表"，
        # 每行是 (policy, cycle, prediction)，便于与真实循环数据对齐比较。
        for cycle, prediction in zip(cycles, value):
            predictions.append({"policy": row["policy"], "cycle": int(cycle), "prediction": float(prediction)})
    return pd.DataFrame(predictions)
