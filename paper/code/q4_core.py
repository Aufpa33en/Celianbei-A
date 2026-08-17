"""Auditable Q4 discrete Pareto and constrained single-exposure models."""
# ============================================================================
# Q4 的核心逻辑：把每条充电策略（工艺参数组合）映射到“观测时间 − 容量损失”的
# 二维目标，在此基础上做离散 Pareto 前沿分析、bootstrap 稳健性检验，
# 以及单一解释变量（如策略经济性 J）对容量损失的岭回归外推评估（LOSO 交叉验证）。
# ============================================================================

# 启用延迟求值的类型注解（PEP 563），允许在注解中引用尚未定义的类型。
from __future__ import annotations

# 标准库：dataclass 定义观测数据结构、Path 定位数据目录
from dataclasses import dataclass
from pathlib import Path

# 第三方：NumPy 数值计算、pandas 表格处理
import numpy as np
import pandas as pd

# 项目内部：复用 Q3 的数据装载入口 load_records
from q3_models.core import load_records


Q4_VERSION = "q4_smoke_v1"   # 结果版本号：写入输出表，便于论文附录与复现时追踪数据/代码版本
SEED = 20260815              # 全局随机种子：保证 bootstrap 抽样结果完全可复现
LAMBDA_GRID = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
# 加权标量化权重网格：权重 w 越大越侧重“缩短观测时间”，1−w 越侧重“降低容量损失”；
# 0 与 1 两端对应纯损失最优 / 纯时间最优，中间值刻画两个目标之间的折中。


@dataclass(frozen=True)
class PolicyObservation:
    # 一条策略的“观测汇总”（frozen=True 防止误改，因下游会按 dict 语义使用）：
    # 把该策略下所有完整电池按三个维度聚合，供 Pareto 前沿与敏感性分析使用。
    policy: str                    # 策略标识（工艺方案名）
    n_battery: int                 # 该策略下可用（完整历史）电池数，作为可信度/样本量参考
    time_mean: float               # 平均“观测时间”（平均充电时间），衡量策略的观测成本
    time_sd: float                 # 观测时间的标准差（电池间波动），反映该策略的稳健性
    loss_mean: float               # 平均“容量损失”：1 − SOH(200)，即到第 200 循环累计损失的容量比例
    loss_sd: float                 # 容量损失的标准差
    late_slope_mean: float         # 后期（151~200 循环）容量损失线性退化斜率均值，刻画末端劣化速度
    c1: float                      # 策略参数：快充阶段电流（或电压）档位
    q1: float                      # 策略参数：快充容量占比 Q1（百分比）
    c2: float                      # 策略参数：第二阶段（恒压段）电流档位
    j: float                       # 第一周期电池成本 J = q·C1 + (0.8−q)·C2（q = Q1/100）
    h: float                       # 损耗/持有成本 H = 0.5·(C1·q² + C2·(0.8²−q²))
    coordinate: tuple[float, float, float] | None
    # 策略“坐标”(c1, q1, c2)：作为离散策略的唯一指纹，用于 LOSO（留一坐标）交叉验证的分组键。


def _finite_mean(values: pd.Series) -> float:
    # 数值化并忽略缺失值后取均值：数据行可能含空值或非数值，统一在此兜底。
    values = pd.to_numeric(values, errors="coerce").dropna()
    return float(values.mean()) if len(values) else float("nan")   # 全缺失时返回 NaN 而非抛错


def collect_policy_observations(project_root: Path) -> tuple[list[PolicyObservation], pd.DataFrame]:
    # Q4 数据装配主入口：把逐电池数据聚合成“策略级观测”，
    # 同时返回逐电池长表（带策略标量回填）供可视化与逐电池复算。
    records, meta, _ = load_records(project_root)                  # 复用 Q3 的统一装载逻辑
    complete_ids = set(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int))
    # 只保留完整历史电池（prediction_test==0），避免用被预留的测试电池“偷看”答案。
    rows = []                                                      # 长表行缓存：每行对应“一条策略 × 一个电池”
    observations: list[PolicyObservation] = []                     # 策略级观测列表（每个策略一个元素）
    for policy, group in meta.loc[meta["battery_id"].isin(complete_ids)].groupby("policy", sort=True):
        # 按策略分组；sort=True 保证策略处理顺序确定，结果可复现。
        metadata_by_battery = group.set_index("battery_id")        # 便于按电池号取静态属性
        battery_rows = []                                          # 该策略下逐电池观测暂存
        for battery_id in sorted(group["battery_id"].astype(int)):  # 遍历该策略下的每个完整电池（按编号有序）
            record = records[battery_id]                           # 取出该电池的聚合记录
            cycles = record.cycles                                 # 取该电池逐循环明细表
            time_column = "chargetime_raw" if "chargetime_raw" in cycles.columns else "chargetime"
            # 优先使用“原始充电时间”列，缺失时回退到旧字段名，保持向后兼容。
            if time_column not in cycles.columns:
                raise KeyError("Q4 requires chargetime_raw (or legacy chargetime) in cleaned cycle data")  # 缺列即抛错，确保观测时间口径可用
            time_series = pd.to_numeric(cycles[time_column], errors="coerce")
            # 转数值并容忍脏数据（非法值变 NaN），保证后续均值不受非数值干扰。
            time_value = float(metadata_by_battery.loc[battery_id, "mean_chargetime"])
            # 观测时间取静态汇总里的平均充电时间（跨循环平均），衡量该策略下观测一次的时间成本。
            cycle_time_value = float(time_series.mean())           # 逐循环数据的均值，用于敏感性对比
            loss_value = float(1.0 - record.relative_at(200))      # 容量损失 = 1 − SOH(200)（相对值即比例）
            late_values = record.relative_soh[150:200]             # 后期窗口：第 151~200 循环的相对 SOH
            x = np.arange(151, 201, dtype=float)                   # 与后期窗口对应的循环下标
            xc = x - x.mean()                                      # 中心化，便于用点积直接求斜率
            slope = float(xc @ (late_values - late_values.mean()) / (xc @ xc))
            # 对后期 SOH 做最小二乘直线拟合求斜率：SOH 下降越快，损失上升越快。
            battery_rows.append({"battery_id": battery_id, "time": time_value,  # 收集该电池的观测行（时间/损失/后期退化速率）
                                 "cycle_time_sensitivity": cycle_time_value,
                                 "loss": loss_value, "late_slope_loss": max(0.0, -slope)})
            # max(0.0, −slope)：把“后期损失退化速率”定义为非负量——
            # 负斜率（SOH 下降）被映射为正的损失斜率，方便比较与聚合。
        values = pd.DataFrame(battery_rows)                        # 该策略下所有电池的逐电池观测表
        first = group.iloc[0]                                      # 取策略组第一行（参数在组内恒定）
        c1, q1, c2 = (float(first[col]) if pd.notna(first[col]) else np.nan for col in ("C1", "Q1", "C2"))
        # 策略参数在同一策略内是常量，取第一行即可；缺值用 NaN 占位。
        q = q1 / 100.0 if np.isfinite(q1) else np.nan              # Q1 为百分数，转成 0~0.8 的小数比例
        j = q * c1 + (0.8 - q) * c2 if np.isfinite([c1, q, c2]).all() else np.nan
        # J：第一周期电池成本（线性项）——量化快充阶段按容量比例加权的电流支出，
        # 是策略经济性的一阶量，之后作为单变量解释电池容量损失。
        h = 0.5 * (c1 * q**2 + c2 * (0.8**2 - q**2)) if np.isfinite([c1, q, c2]).all() else np.nan
        # H：损耗/持有成本（二次项）——来自容量损失与时间关系的积分刻画，
        # 与 J 合起来构成策略的“综合成本”代理变量。
        coordinate = (c1, q1, c2) if np.isfinite([c1, q1, c2]).all() else None
        # 参数完整才构成有效策略坐标；任一缺失则置 None，防止残缺策略被误当作有效离散点。
        # 把该策略的聚合统计（样本量、时间/损失均值与波动、后期退化斜率、工艺参数与成本代理）打包成观测记录：
        observations.append(PolicyObservation(
            policy=str(policy), n_battery=len(values), time_mean=float(values["time"].mean()),
            time_sd=float(values["time"].std(ddof=1)) if len(values) > 1 else 0.0,
            # ddof=1 用样本标准差；只有 1 个电池时无法估计波动，取 0 兜底。
            loss_mean=float(values["loss"].mean()),
            loss_sd=float(values["loss"].std(ddof=1)) if len(values) > 1 else 0.0,
            late_slope_mean=float(values["late_slope_loss"].mean()),
            c1=c1, q1=q1, c2=c2, j=j, h=h, coordinate=coordinate,
        ))
        for row in battery_rows:
            # 把策略级标量回填到每个电池行，形成便于画散点图 / 分组统计的长表。
            row.update({"policy": str(policy), "c1": c1, "q1": q1, "c2": c2, "j": j, "h": h})
            rows.append(row)                                       # 逐电池行追加进长表
    return observations, pd.DataFrame(rows)                        # 返回（策略级观测列表，逐电池长表）


def observation_frame(observations: list[PolicyObservation]) -> pd.DataFrame:
    # 把 PolicyObservation 列表转成宽表（每个策略一行）——
    # 用 __dict__ 取全部字段，便于后续筛选、画表与进一步计算。
    return pd.DataFrame([obs.__dict__ for obs in observations])


def _normalise(values: np.ndarray) -> np.ndarray:
    # 最小-最大归一化到 [0,1]：把量纲不同的“时间”与“损失”拉到同一尺度，
    # 这样加权标量化（见 choose_scalar）中的权重才有可解释性。
    values = np.asarray(values, dtype=float)                       # 统一转 float 数组
    lo, hi = np.nanmin(values), np.nanmax(values)                  # 取非缺失最小/最大值作为归一化端点
    return np.zeros_like(values) if hi - lo < 1e-12 else (values - lo) / (hi - lo)
    # 区间长度接近 0（所有值几乎相同）时返回全 0，避免除零。


def pareto_mask(time: np.ndarray, loss: np.ndarray) -> np.ndarray:
    # 计算“Pareto 非支配”标记：在（时间, 损失）双目标下，若存在另一个策略在
    # 两项上都不更差、且至少一项严格更优，则该策略被支配（应从前沿中排除）。
    time, loss = np.asarray(time, float), np.asarray(loss, float)  # 统一转 float 数组
    mask = np.ones(len(time), dtype=bool)                          # 先默认全部非支配，再逐点判定剔除
    for i in range(len(time)):                                     # 对每个策略点 i 判断是否存在支配它的点
        dominated = (time <= time[i] + 1e-12) & (loss <= loss[i] + 1e-12)
        # 加 1e-12 容差，避免浮点相等被误判为“不差于”。
        strictly = (time < time[i] - 1e-12) | (loss < loss[i] - 1e-12)
        # “至少一项严格更优”的条件（时间或损失其一严格更小）。
        mask[i] = not bool(np.any(dominated & strictly))   # 存在同时满足两条件的点 ⇒ 被支配 ⇒ 非前沿
    return mask                                             # 返回非支配标记数组（True = 位于 Pareto 前沿）


def choose_scalar(time: np.ndarray, loss: np.ndarray, policies: list[str], weight: float) -> int:
    # 加权标量化选优：score = w·(归一化时间) + (1−w)·(归一化损失)，
    # 返回得分最小（最优）的策略索引。这是把双目标问题化为单目标做折中决策的标准做法。
    score = weight * _normalise(time) + (1.0 - weight) * _normalise(loss)  # 加权得分：越小越优
    order = sorted(range(len(score)), key=lambda i: (score[i], loss[i], time[i], policies[i]))
    # 排序键依次为 score、loss、time、策略名：score 并列时优先损失小 → 时间少 → 名字字典序，
    # 保证“平局”下的选择是确定且可复现的。
    return order[0]


def bootstrap_pareto(
    frame: pd.DataFrame,
    repetitions: int = 2000,
    seed: int = SEED,
    lambda_grid: np.ndarray | None = None,
    loss_limits: tuple[float, ...] = (),
) -> pd.DataFrame:
    # Bootstrap 稳健性检验：对电池样本重抽样多次，观察“Pareto 前沿与最优选择”
    # 在抽样噪声下是否稳定。若某策略在绝大多数重复中仍被选中，说明结论可靠、
    # 不是被个别极端电池左右。
    rng = np.random.default_rng(seed)          # 用 NumPy 新式 Generator，配合固定 seed 完全可复现
    lambda_grid = LAMBDA_GRID if lambda_grid is None else np.asarray(lambda_grid, dtype=float)
    # 权重网格可覆盖传入；默认用全局 LAMBDA_GRID。
    policies = sorted(frame["policy"].unique())            # 有序策略列表，保证结果列顺序稳定
    records = {policy: frame.loc[frame["policy"].eq(policy)].reset_index(drop=True) for policy in policies}
    # 按策略切分，供分层抽样：bootstrap 在“策略内”有放回抽样，保持各策略的样本量结构。
    rows = []                                              # 长表行缓存：每行对应“一次重复 × 一条策略”
    for rep in range(repetitions):                         # 外层：重复抽样 repetitions 次
        summary = []                                       # 本次重复各策略的汇总暂存
        for policy in policies:                            # 内层：逐策略做有放回抽样并汇总
            data = records[policy]                         # 取该策略的电池池
            idx = rng.integers(0, len(data), size=len(data))   # 有放回抽样（长度不变、允许重复）——bootstrap 的核心
            sample = data.iloc[idx]                        # 按抽样索引取出行，构成本次 bootstrap 样本
            late_slope = float(sample["late_slope_loss"].mean()) if "late_slope_loss" in sample else np.nan  # 后期损失退化斜率均值；缺列时记 NaN
            summary.append((policy, float(sample["time"].mean()), float(sample["loss"].mean()), late_slope))
        # 本次重复中每个策略的汇总（时间 / 损失 / 后期斜率均值）。
        t = np.array([row[1] for row in summary]); d = np.array([row[2] for row in summary])
        front = pareto_mask(t, d)                              # 本次重复的 Pareto 前沿标记
        choices = {w: summary[choose_scalar(t, d, policies, w)][0] for w in lambda_grid}
        # 对每个权重 w，选出加权标量化最优的策略名。
        constrained_choices = {}                               # 记录每个损失上限下的受限最优策略
        for limit in loss_limits:                              # 遍历用户给定的损失上限
            feasible = np.flatnonzero(d <= limit)              # 容量损失不超过上限的策略（可行集）
            # 在可行集中选 (时间, 损失) 字典序最小者（时间优先、其次损失），
            # 作为“损失受限”约束下的最优策略。
            constrained_choices[limit] = (
                min(feasible, key=lambda i: (t[i], d[i], policies[i])) if len(feasible) else None
            )   # 可行集为空时记 None，表示本次重复没有策略能满足该损失上限。
        for index, ((policy, time_value, loss_value, late_slope), is_front) in enumerate(zip(summary, front)):
            # 把每个策略的本次结果写成一行：含 Pareto 标记与各权重/损失上限下的选中标记。
            rows.append({"version": Q4_VERSION, "replicate": rep, "policy": policy,
                         "time": time_value, "loss": loss_value, "late_slope_loss": late_slope,
                         "pareto": bool(is_front),
                         **{f"selected_lambda_{w:.2f}": choices[w] == policy for w in lambda_grid},
                         # 每列是一个权重 w 下的“是否被选中”布尔值，宽表便于统计选中频率。
                         **{f"selected_loss_limit_{limit:.4f}": constrained_choices[limit] == index
                            for limit in loss_limits}})
            # 同样对每个损失上限生成“是否被选中”的布尔列。
    return pd.DataFrame(rows)


def fit_single_exposure(train: pd.DataFrame, exposure: str, lam: float) -> tuple[float, float, float, float]:
    # 拟合“单一解释变量 exposure（如 J）→ 容量损失”的岭回归（带截距、自变量标准化）。
    # 返回 (intercept, slope, mean, scale)：mean/scale 用于把新数据的 exposure 标准化到同尺度。
    loss_column = "loss" if "loss" in train.columns else "loss_mean"   # 兼容两种损失字段命名
    train = train.dropna(subset=[exposure, loss_column])               # 丢弃解释变量或目标缺失的行
    if len(train) < 2 or train[exposure].std(ddof=0) < 1e-8:
        # 样本过少或 exposure 几乎无变化时无法估计斜率：退化为常数模型
        #（斜率 0、scale 取 1），此时预测恒为训练损失均值。
        return float(train[loss_column].mean()), 0.0, float(train[exposure].mean()), 1.0
    mean, scale = float(train[exposure].mean()), float(train[exposure].std(ddof=0))  # 训练集 exposure 的均值与标准差，用于标准化
    z = (train[exposure].to_numpy(float) - mean) / scale               # 标准化：消除 exposure 的量纲影响
    x = np.column_stack([np.ones(len(z)), z]); y = train[loss_column].to_numpy(float)
    # 拼出设计矩阵 [1, z] 与目标 y，准备解岭回归的正规方程。
    penalty = np.diag([0.0, lam]); coef = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    # 岭惩罚矩阵中截距项不惩罚、斜率项惩罚 λ，解正规方程 (XᵀX + λI)β = Xᵀy 得回归系数；
    # 返回截距、斜率、均值、尺度（后两者供新数据标准化复用）。
    return float(coef[0]), float(coef[1]), mean, scale


def loso_single_exposure(
    frame: pd.DataFrame,
    exposure: str = "j",
    ridge_grid: tuple[float, ...] = (0.01, 0.1, 1.0, 10.0),
) -> pd.DataFrame:
    # Leave-One-Coordinate-Out（留一坐标）验证：以“策略坐标 (c1, q1, c2)”为分组单位，
    # 每次留出一整条策略作为测试集。由于离散策略参数范围有限，被留出的坐标常落在
    # 训练范围之外，由此测出“外推压力”下的泛化能力——这正是用策略参数预测损失的真正难点。
    usable = frame.dropna(subset=[exposure, "coordinate", "loss_mean"]).copy()
    # 剔除三列任缺的行并拷贝，避免对原帧的链式赋值警告。
    usable["coordinate_key"] = usable["coordinate"].astype(str)        # 坐标转字符串作为分组键
    rows = []                                                          # 长表行缓存：每个留一坐标折叠一行
    for held_out in sorted(usable["coordinate_key"].unique()):  # 遍历每个策略坐标作为留出组
        train = usable.loc[usable["coordinate_key"].ne(held_out)]      # 除该坐标外全部作训练
        test = usable.loc[usable["coordinate_key"].eq(held_out)]       # 该坐标的电池作测试
        best = None                                                    # 当前折叠的最优候选（RMSE 最小者）
        for lam in ridge_grid:                                         # 在岭系数网格上选最优
            intercept, slope, mean, scale = fit_single_exposure(train, exposure, lam)
            # 用训练集拟合该 λ 下的岭回归，得到系数与标准化参数。
            if len(test) == 0 or scale < 1e-8:
                pred = np.full(len(test), intercept)                   # 无可预测性或 scale 退化：仅用截距预测
            else:                                                # 测试集有效且 scale 正常：用标准化线性式预测
                pred = intercept + slope * (test[exposure].to_numpy(float) - mean) / scale
                # 把测试 exposure 用训练集的 mean/scale 标准化后再线性预测，口径必须与训练一致。
            rmse = float(np.sqrt(np.mean((pred - test["loss_mean"].to_numpy(float)) ** 2))) if len(test) else np.nan
            # 计算测试集 RMSE；测试集为空时记 NaN。
            candidate = (rmse, -lam, intercept, slope, mean, scale, pred)
            # 元组第一项 RMSE 最小即最优；第二项存 −λ 仅作并列时的次级排序（λ 小者优先）。
            if best is None or candidate[:2] < best[:2]: best = candidate
        assert best is not None                                        # ridge_grid 非空，best 必被赋值
        baseline_rmse = float(np.sqrt(np.mean((test["loss_mean"].to_numpy(float) - train["loss_mean"].mean()) ** 2))) if len(test) else np.nan
        # 常数基线模型：只用训练集损失均值预测，作为“不做任何外推”的对照 RMSE。
        test_exposure = test[exposure].to_numpy(float)                 # 测试集 exposure，供记录范围与外推判断
        train_exposure = train[exposure].to_numpy(float)               # 训练集 exposure 范围，作为“已知区间”
        prediction = np.asarray(best[6], dtype=float)                  # 最优候选的预测向量（best[6] 存的是 pred）
        rows.append({"version": Q4_VERSION, "exposure": exposure, "held_out_coordinate": held_out,
                     "n_test_policy": len(test), "rmse": best[0], "lambda": -best[1],
                     "constant_rmse": baseline_rmse, "improvement": baseline_rmse - best[0],
                     # improvement > 0 说明岭回归优于常数模型，量化外推带来的增益。
                     "intercept": best[2], "slope": best[3], "train_mean": best[4],
                     "train_scale": best[5],
                     "train_exposure_min": float(train_exposure.min()),
                     "train_exposure_max": float(train_exposure.max()),
                     "test_exposure_min": float(test_exposure.min()),
                     "test_exposure_max": float(test_exposure.max()),
                     # 上述四列量化“测试 exposure 是否越出训练范围”，即外推距离。
                     "outside_train_exposure_range": bool(
                         test_exposure.min() < train_exposure.min()
                         or test_exposure.max() > train_exposure.max()
                     ),
                     # 布尔标记：测试集越出训练区间，说明该折确实在测“外推”。
                     "prediction_mean": float(prediction.mean()),
                     "prediction_below_zero": bool((prediction < 0).any()),
                     # 损失预测出现负值说明模型被外推到不物理区间，标记以便审阅。
                     "observed_loss_mean": float(test["loss_mean"].mean()),
                     "sum_squared_error": float(np.sum((prediction - test["loss_mean"].to_numpy(float)) ** 2)),
                     "validation_type": "coordinate_LOSO_extrapolation_pressure"})
    result = pd.DataFrame(rows)                                # 组装成结果宽表
    result["squared_error_share"] = result["sum_squared_error"] / result["sum_squared_error"].sum()
    # 每个折叠的平方误差占总量占比：用于定位“哪条策略最难外推”。
    result["worst_fold"] = result["sum_squared_error"].eq(result["sum_squared_error"].max())
    # 标记误差最大的折（最差折叠），便于论文集中讨论外推失败的典型案例。
    return result
