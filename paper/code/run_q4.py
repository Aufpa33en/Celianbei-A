"""Run and atomically publish the complete Q4 observed-policy protocol.
Q4 全量验证入口：基于观测到的 9 个充放电策略执行离散 Pareto 优化协议——
整块电池 bootstrap 不确定度、加权/约束决策、时间口径敏感性、M1 单 J 岭模型压力测试，
全部完整性校验通过后原子发布权威结果目录（先写 .tmp 再整体改名）。"""

from __future__ import annotations  # 使用延迟求值的类型注解（兼容旧版 Python）

import argparse  # 命令行参数解析（--bootstrap / --output-root）
import hashlib  # 计算文件 SHA-256，用于产物与受保护文件的完整性核对
import json  # 序列化运行配置快照（run_config.json）
import sys  # 修改模块搜索路径，导入项目 src 下的包
import time  # 统计整个流程耗时
from pathlib import Path  # 跨平台路径处理

import numpy as np  # 数值计算（分位数、数组运算等）
import pandas as pd  # 表格数据处理与分组统计

ROOT = Path(__file__).resolve().parents[2]  # 项目根目录（scripts/q4/... 上溯两级）
sys.path.insert(0, str(ROOT / "src"))  # 把 src 加入模块搜索路径，导入 q4_models 包
from q4_models.core import (  # noqa: E402  # Q4 核心算法
    SEED,                       # 全局随机种子，保证 bootstrap 可复现
    bootstrap_pareto,           # 整块电池 bootstrap 重采样 + 每个重复内做 λ 加权/约束策略选择
    choose_scalar,              # 对"时间-退化"两目标加权打分后选出一个策略
    collect_policy_observations,  # 汇总 9 个观测策略的逐电池数据（时间、退化、循环特征）
    loso_single_exposure,       # M1 单 J 岭模型的"单次暴露"留一验证（oracle 坐标压力测试）
    observation_frame,          # 把原始观测整理成按策略聚合的表格（每策略一行）
    pareto_mask,                # 计算两目标下的 Pareto 前沿掩码（时间、退化）
)

# ---------- 协议级常量：固化口径并写入全部产物，保证任何结果都可复核复现 ----------
FORMAL_VERSION = "q4_full_v4"  # 正式协议版本号，标记所有输出文件
FORMAL_LAMBDAS = np.arange(0.0, 1.000001, 0.1)  # 加权系数 λ 网格：0, 0.1, ..., 1.0（共 11 个）
RIDGE_GRID = (0.01, 0.1, 1.0, 10.0)  # M1 岭回归的候选正则化强度（搜索网格）
LOSS_LIMITS = (0.0005, 0.0010, 0.0015, 0.0017)  # 四个退化率上限场景（仅演示决策规则，非工程安全标准）
TIME_EQUIVALENCE_MINUTES = 0.01  # 时间等价阈值：两策略时间差 ≤0.01 分钟即视为近似并列
SUPERIORITY_PROBABILITY = 0.95  # 判定唯一胜出所需的最低胜出概率
FAST_PAIR = (  # 实际充电最快的两个策略，做"不强制分出胜者"的成对对比
    "5_3C_54PER_4C_NEWSTRUCTURE",
    "5C_67PER_4C_NEWSTRUCTURE",
)


def _sha256(path: Path) -> str:
    """计算文件的 SHA-256 十六进制摘要（分块读取，避免大文件一次性占用内存）。"""
    digest = hashlib.sha256()  # 初始化摘要对象
    with path.open("rb") as handle:  # 以二进制模式打开文件
        # 每次读取 1 MiB 分块更新摘要，直到读到空块（文件末尾）为止
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_hashes() -> dict[str, str]:
    """计算"受保护文件"的哈希快照：数据、Q4 源码、Q4 脚本、两版 smoke 测试产物。
    验证全程这些文件都不得被改动，否则判定流程失效。"""
    # 受保护根目录列表：数据、源码、脚本、smoke 测试产物（两版）
    roots = [ROOT / "data", ROOT / "src" / "q4_models", ROOT / "scripts" / "q4",
             ROOT / "result" / "q4" / "01_smoke_test",
             ROOT / "result" / "q4" / "01_smoke_test_v2"]
    files = []  # 收集所有待保护的普通文件路径
    for root in roots:
        if root.exists():  # 目录不存在则跳过（如某版 smoke 产物尚未生成时）
            # 递归列出所有文件，并排除 __pycache__ 缓存目录（缓存内容不稳定，不算受保护对象）
            files.extend(path for path in root.rglob("*")
                         if path.is_file() and "__pycache__" not in path.parts)
    # 返回 {相对仓库根目录的路径: sha256} 字典；sorted 保证遍历顺序稳定可复现
    return {str(path.relative_to(ROOT)): _sha256(path) for path in sorted(files)}


def policy_uncertainty(battery: pd.DataFrame, boot: pd.DataFrame) -> pd.DataFrame:
    """按策略汇总整块电池 bootstrap 的不确定度：对每个策略的
    time/loss/late_slope_loss 指标给出 2.5%、50%、97.5% 分位数（即 95% 区间）。"""
    rows = []
    # 按策略名分组电池观测，sort=True 让分组顺序稳定
    for policy, group in battery.groupby("policy", sort=True):
        row = {"policy": policy, "n_battery": len(group),  # 该策略下的电池样本数
               "interval_type": "strategy_mean_whole_battery_bootstrap"}  # 区间口径标注
        # 取出该策略在 bootstrap 结果中的所有重复
        boot_group = boot.loc[boot["policy"].eq(policy)]
        for metric in ("time", "loss", "late_slope_loss"):  # 三个指标统一处理
            # 转数值并丢弃缺失值（缺失的重复不应污染分位数）
            values = pd.to_numeric(boot_group[metric], errors="coerce").dropna()
            row[f"{metric}_p025"] = float(values.quantile(0.025))  # 95% 区间下界
            row[f"{metric}_p50"] = float(values.quantile(0.5))     # 中位数
            row[f"{metric}_p975"] = float(values.quantile(0.975))  # 95% 区间上界
        rows.append(row)
    return pd.DataFrame(rows)


def point_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    """生成点估计推荐表，含两类规则：
    1) 加权 min-max 打分（对每个 λ 选一个策略）——明确标注为诊断敏感性，非主推荐；
    2) 每个退化上限约束下选"最短时间可行策略"——说明决策规则用，非安全标准。"""
    rows = []
    # 归一化口径说明：加权打分只是诊断敏感性分析；归一化采用包含全部 9 个
    # 观测策略（含被支配点）的 min-max 范围，并记录各指标的取值范围
    normalization = {
        "decision_role": "diagnostic_weight_sensitivity_not_primary_recommendation",
        "normalization_method": "minmax",
        "normalization_scope": "all_9_observed_policies_including_dominated",
        "normalization_n_policies": len(summary),
        "normalization_time_min": float(summary["time_mean"].min()),
        "normalization_time_max": float(summary["time_mean"].max()),
        "normalization_loss_min": float(summary["loss_mean"].min()),
        "normalization_loss_max": float(summary["loss_mean"].max()),
    }
    # 加权打分：对每个 λ，用 choose_scalar 在"时间-退化"两目标加权后选一个策略
    for weight in FORMAL_LAMBDAS:
        idx = choose_scalar(summary["time_mean"].to_numpy(), summary["loss_mean"].to_numpy(),
                            summary["policy"].astype(str).tolist(), float(weight))
        selected = summary.iloc[idx]  # 当前 λ 选出的策略行
        rows.append({"rule": "weighted_minmax_all_policies_diagnostic", "lambda": float(weight),
                     "threshold_type": "not_applicable", "policy": str(selected["policy"]),
                     "time_mean": float(selected["time_mean"]),
                     "loss_mean": float(selected["loss_mean"]), **normalization,
                     "pareto": bool(selected["pareto"])})
    # 约束决策：对每个退化上限，选择"损失满足约束下时间最短"的策略（说明规则用）
    for limit in LOSS_LIMITS:
        feasible = summary.loc[summary["loss_mean"] <= limit]  # 损失在约束内的策略
        if feasible.empty:  # 没有可行策略时，显式记录 NO_FEASIBLE_POLICY 占位
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                         "decision_role": "illustrative_constraint_sensitivity_not_primary_recommendation",
                         "policy": "NO_FEASIBLE_POLICY"})
        else:
            # 按 (时间, 损失, 策略名) 排序取第一个：时间最短，其次损失最小，策略名作稳定并列键
            selected = feasible.sort_values(["time_mean", "loss_mean", "policy"]).iloc[0]
            rows.append({"rule": "shortest_time_under_loss_limit_sensitivity", "loss_limit": limit,
                         "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                         "decision_role": "illustrative_constraint_sensitivity_not_primary_recommendation",
                         "policy": str(selected["policy"]), "time_mean": float(selected["time_mean"]),
                         "loss_mean": float(selected["loss_mean"]), "pareto": bool(selected["pareto"])})
    return pd.DataFrame(rows)


def selection_frequencies(boot: pd.DataFrame, repetitions: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """统计各策略被选中的频率（基于 bootstrap 重复）：
    - 加权选择频率（每个 λ 下被选中比例）与 Pareto 频率；
    - 约束选择频率（每个退化上限下被选中比例 + NO_FEASIBLE_POLICY 占比）。"""
    # 每个策略在 bootstrap 重复中被判为 Pareto 前沿的比例
    pareto_frequency = (boot.groupby("policy", as_index=False)["pareto"].mean()
                        .rename(columns={"pareto": "pareto_frequency"}).set_index("policy"))
    # 对每个 λ 选择列，统计各策略被选中的比例（列名为 selected_lambda_*）
    for column in [name for name in boot if name.startswith("selected_lambda_")]:
        counts = boot.loc[boot[column]].groupby("policy").size() / repetitions
        pareto_frequency[column] = counts  # 写入频率列（未被选中的策略此处为缺失值）
    weighted = pareto_frequency.fillna(0.0).reset_index()  # 缺失频率补 0，恢复为规整宽表
    constrained_rows = []  # 约束选择频率的长表行
    for limit in LOSS_LIMITS:
        column = f"selected_loss_limit_{limit:.4f}"  # 对应当前约束的选中标记列名
        counts = boot.loc[boot[column]].groupby("policy").size()  # 各策略被选中次数
        selected_replicates = int(counts.sum())  # 至少有一个可行策略的重复数
        # 每个策略：选中次数 / 总重复数，即该策略在此约束下被选中的频率
        for policy in sorted(boot["policy"].unique()):
            constrained_rows.append({"loss_limit": limit,
                                     "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                                     "policy": policy,
                                     "selection_frequency": float(counts.get(policy, 0) / repetitions)})
        # 无可行策略的重复：其占比 = (总重复 - 有选中策略的重复) / 总重复
        constrained_rows.append({"loss_limit": limit,
                                 "threshold_type": "illustrative_decision_scenario_not_safety_standard",
                                 "policy": "NO_FEASIBLE_POLICY",
                                 "selection_frequency": float((repetitions - selected_replicates) / repetitions)})
    return weighted, pd.DataFrame(constrained_rows)


def fast_pair_comparison(
    summary: pd.DataFrame, boot: pd.DataFrame, uncertainty: pd.DataFrame,
    selection_frequency: pd.DataFrame,
) -> pd.DataFrame:
    """Compare the two practically fastest observed policies without forcing a winner.
    对实践中最快的两个策略（FAST_PAIR）做成对对比，但不强制选出一个胜者：
    点估计 Pareto 推荐与"近似并列不确定"敏感性分开记录。"""
    first, second = FAST_PAIR
    point = summary.set_index("policy")  # 以策略名为索引，便于取值
    # 把 bootstrap 结果透视成宽表：行=重复，列=策略，值=time/loss/pareto
    wide = boot.pivot(index="replicate", columns="policy", values=["time", "loss", "pareto"])
    # 每个重复内"策略一减策略二"的时间差（正=策略二更快）
    time_difference = wide["time"][first] - wide["time"][second]
    loss_difference = wide["loss"][first] - wide["loss"][second]  # 对应的退化差
    # 各概率估计：基于 bootstrap 重复的频数均值
    loss_probability_first_better = float((loss_difference < 0).mean())  # 策略一退化更低的概率
    time_probability_first_faster = float((time_difference < 0).mean())  # 策略一更快的概率
    time_probability_first_not_slower = float(  # 策略一不比策略二慢超过 0.01 分钟的概率
        (time_difference <= TIME_EQUIVALENCE_MINUTES).mean()
    )
    time_probability_second_not_slower = float(  # 策略二不比策略一慢超过 0.01 分钟的概率
        (-time_difference <= TIME_EQUIVALENCE_MINUTES).mean()
    )
    # 唯一胜出判定：一方需同时满足"退化更优概率≥0.95"且"不显著更慢概率≥0.95"；
    # 否则判为近似并列（unique_winner=None），避免在区间高度重叠时强行分出高下
    unique_winner = (
        first if (
            loss_probability_first_better >= SUPERIORITY_PROBABILITY
            and time_probability_first_not_slower >= SUPERIORITY_PROBABILITY
        )
        else second if (
            1.0 - loss_probability_first_better >= SUPERIORITY_PROBABILITY
            and time_probability_second_not_slower >= SUPERIORITY_PROBABILITY
        )
        else None
    )
    intervals = uncertainty.set_index("policy")  # 分位数区间表，按策略索引
    frequencies = selection_frequency.set_index("policy")  # 选择频率表，按策略索引
    rows = []
    for policy in FAST_PAIR:  # 对两个策略分别生成一行对比记录
        other = second if policy == first else first  # 对比对象为另一个策略
        point_pareto = bool(point.loc[policy, "pareto"])  # 该策略在点估计上是否 Pareto
        rows.append({
            "version": FORMAL_VERSION,
            "policy": policy,
            "comparison_policy": other,
            # 决策状态分三档：唯一胜出推荐 / 点估计 Pareto 快速推荐 / 近似并列非前沿敏感性
            "decision_status": (
                "unique_fast_tradeoff_recommendation" if policy == unique_winner
                else "point_pareto_fast_tradeoff_recommendation"
                if unique_winner is None and point_pareto
                else "uncertainty_near_tie_nonpareto_sensitivity"
                if unique_winner is None
                else "not_selected"
            ),
            "point_pareto": point_pareto,
            "time_mean": float(point.loc[policy, "time_mean"]),  # 点估计时间
            "time_p025": float(intervals.loc[policy, "time_p025"]),  # 时间 95% 区间下界
            "time_p975": float(intervals.loc[policy, "time_p975"]),  # 时间 95% 区间上界
            "loss_mean": float(point.loc[policy, "loss_mean"]),  # 点估计退化
            "loss_p025": float(intervals.loc[policy, "loss_p025"]),  # 退化 95% 区间下界
            "loss_p975": float(intervals.loc[policy, "loss_p975"]),  # 退化 95% 区间上界
            "pareto_frequency": float(frequencies.loc[policy, "pareto_frequency"]),  # Pareto 频率
            # 相对对比对象"退化更低"的概率（第二个策略取 1 - p，保持对称口径）
            "probability_lower_loss_than_pair": (
                loss_probability_first_better if policy == first else 1.0 - loss_probability_first_better
            ),
            # 相对对比对象"更快"的概率
            "probability_faster_than_pair": (
                time_probability_first_faster if policy == first else 1.0 - time_probability_first_faster
            ),
            # 相对对比对象"不慢超过 0.01 分钟"的概率
            "probability_not_slower_by_more_than_0_01_min": (
                time_probability_first_not_slower if policy == first
                else time_probability_second_not_slower
            ),
            # 时间差落在 ±0.01 分钟（近似并列窗口）内的概率
            "probability_time_difference_within_0_01_min": float(
                (time_difference.abs() <= TIME_EQUIVALENCE_MINUTES).mean()
            ),
            # 成对时间差（一减二）的分位数，用于判断区间是否跨 0
            "pair_time_difference_first_minus_second_p025": float(time_difference.quantile(0.025)),
            "pair_time_difference_first_minus_second_p50": float(time_difference.quantile(0.5)),
            "pair_time_difference_first_minus_second_p975": float(time_difference.quantile(0.975)),
            # 成对退化差（一减二）的分位数
            "pair_loss_difference_first_minus_second_p025": float(loss_difference.quantile(0.025)),
            "pair_loss_difference_first_minus_second_p50": float(loss_difference.quantile(0.5)),
            "pair_loss_difference_first_minus_second_p975": float(loss_difference.quantile(0.975)),
            "unique_recommendation_probability_threshold": SUPERIORITY_PROBABILITY,  # 胜出阈值口径
            # Q3 未被用作反事实响应面：Q3 需目标电池已有 1–150 循环轨迹，属条件预测而非策略响应面
            "q3_role": "not_used_no_early_trajectory_for_new_policy",
        })
    return pd.DataFrame(rows)


def time_model_sensitivity(summary: pd.DataFrame, battery: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """时间口径敏感性分析：
    对比 Q1/Q2 主指标（mean_chargetime）、前 200 循环均值口径与名义理论充电时间，
    检验主指标是否与问题 1、2 一致，并考察时间口径变化是否影响 Pareto 前沿与决策。"""
    # 读取 Q1 清洗后的电池汇总表（含逐电池 mean_chargetime 主指标）
    meta = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv")
    # Q1/Q2 口径：仅用训练电池（prediction_test=0），按策略平均 mean_chargetime
    official = (meta.loc[meta["prediction_test"].eq(0)]
                .groupby("policy", as_index=False)["mean_chargetime"].mean()
                .rename(columns={"mean_chargetime": "summary_time_mean"}))
    # 前 200 循环均值口径：对 battery 的逐电池 cycle_time_sensitivity 按策略平均
    cycle = (battery.groupby("policy", as_index=False)["cycle_time_sensitivity"].mean()
             .rename(columns={"cycle_time_sensitivity": "cycle_time_mean"}))
    # 合并三种时间口径：主指标、Q1 官方口径、循环口径；c1/q1/c2 用于计算名义时间
    table = summary[["policy", "c1", "q1", "c2", "time_mean", "loss_mean"]].merge(
        official, on="policy", how="left").merge(cycle, on="policy", how="left")
    table = table.rename(columns={"time_mean": "primary_time_mean"})  # 主指标列重命名，便于后续对比
    q = table["q1"] / 100.0  # 名义充电起始 SOC 比例（q1 为百分数，转为小数）
    # 名义单循环充电时间（分钟）：时间 = 60 × (充电占比/充电C率 + 剩余占比/放电C率)
    table["t0_nominal"] = 60.0 * (q / table["c1"] + (0.8 - q) / table["c2"])
    table["primary_minus_t0"] = table["primary_time_mean"] - table["t0_nominal"]  # 主指标与名义时间之差
    table["summary_minus_t0"] = table["summary_time_mean"] - table["t0_nominal"]  # Q1 口径与名义时间之差
    table["cycle_minus_summary"] = table["cycle_time_mean"] - table["summary_time_mean"]  # 两种观测口径之差
    # 主指标与 Q1 口径是否完全一致（atol=1e-12 近似精确相等）——决定主指标的可追溯性
    table["primary_equals_summary"] = np.isclose(
        table["primary_time_mean"], table["summary_time_mean"], rtol=0.0, atol=1e-12
    )
    # 三种时间口径分别配退化算 Pareto 前沿，考察前沿是否对时间口径稳定
    table["pareto_primary_time"] = pareto_mask(table["primary_time_mean"], table["loss_mean"])
    table["pareto_cycle_time"] = pareto_mask(table["cycle_time_mean"], table["loss_mean"])
    table["pareto_summary_time"] = pareto_mask(table["summary_time_mean"], table["loss_mean"])
    fastest = float(table["primary_time_mean"].min())  # 主指标下最快策略的时间
    # 是否与最快策略"近似并列"（差 ≤ 0.01 分钟）
    table["primary_time_equivalent_fastest"] = table["primary_time_mean"] <= fastest + TIME_EQUIVALENCE_MINUTES
    decisions = []
    # 对主指标与循环口径各自跑一遍加权决策：比较决策结果是否对时间口径稳健
    for metric in ("primary_time_mean", "cycle_time_mean"):
        for weight in FORMAL_LAMBDAS:
            idx = choose_scalar(table[metric].to_numpy(), table["loss_mean"].to_numpy(),
                                table["policy"].astype(str).tolist(), float(weight))
            decisions.append({"time_metric": metric, "lambda": float(weight),
                              "policy": str(table.iloc[idx]["policy"]),
                              "time_mean": float(table.iloc[idx][metric]),
                              "loss_mean": float(table.iloc[idx]["loss_mean"])})
    return table, pd.DataFrame(decisions)


def _scaled_score(time_values: np.ndarray, loss_values: np.ndarray, weight: float,
                  mode: str, front: np.ndarray) -> np.ndarray:
    """计算加权 min-max 得分 = λ·时间归一化 + (1-λ)·退化归一化。
    mode 决定归一化参考集合：all_policy_minmax（全部策略）/
    pareto_minmax（仅前沿点）/ robust_q10_q90（0.1–0.9 分位数稳健范围）。"""
    def scale(values: np.ndarray, indices: np.ndarray, robust: bool) -> np.ndarray:
        reference = values[indices]  # 归一化参考集合（据此确定 lo/hi）
        # 稳健模式取 10%/90% 分位数，否则取 min/max
        lo, hi = (np.quantile(reference, [0.1, 0.9]) if robust
                  else (float(reference.min()), float(reference.max())))
        if hi - lo < 1e-12:  # 参考范围过小（几乎恒定）时无法归一化，返回全 0
            return np.zeros_like(values)
        scaled = (values - lo) / (hi - lo)  # 线性缩放至 [0,1]
        # 稳健模式钳制到 [0,1]（分位数范围外的离群点不放大到 1 以上）
        return np.clip(scaled, 0.0, 1.0) if robust else scaled
    # 参考集合：pareto_minmax 只用前沿点，其余模式用全部点
    indices = np.flatnonzero(front) if mode == "pareto_minmax" else np.arange(len(time_values))
    robust = mode == "robust_q10_q90"  # 是否为稳健分位数口径
    return weight * scale(time_values, indices, robust) + (1.0 - weight) * scale(loss_values, indices, robust)


def scaling_sensitivity(summary: pd.DataFrame) -> pd.DataFrame:
    """归一化口径敏感性分析：在三种归一化方式下重跑加权决策，
    考察"加权打分选出的策略"是否依赖归一化口径（诊断用，非主推荐）。"""
    time_values = summary["time_mean"].to_numpy(float)  # 时间目标数组
    loss_values = summary["loss_mean"].to_numpy(float)  # 退化目标数组
    policies = summary["policy"].astype(str).tolist()  # 策略名列表（作稳定并列键）
    front = summary["pareto"].to_numpy(bool)  # Pareto 前沿掩码
    rows = []
    # 三种归一化口径逐一考察
    for mode in ("all_policy_minmax", "pareto_minmax", "robust_q10_q90"):
        # pareto_minmax 模式下只允许从前沿点里选
        eligible = np.flatnonzero(front) if mode == "pareto_minmax" else np.arange(len(summary))
        for weight in FORMAL_LAMBDAS:
            score = _scaled_score(time_values, loss_values, float(weight), mode, front)  # 加权得分
            # 得分最小的策略；并列时依次比较损失、时间、策略名，保证结果稳定
            idx = min(eligible, key=lambda i: (score[i], loss_values[i], time_values[i], policies[i]))
            rows.append({"scaling": mode, "lambda": float(weight), "policy": policies[idx],
                         "score": float(score[idx]), "time_mean": time_values[idx],
                         "loss_mean": loss_values[idx], "pareto": bool(front[idx])})
    return pd.DataFrame(rows)


def slope_and_typical_comparisons(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """晚期退化斜率敏感性 + 典型策略对比：
    1) 把退化指标换为晚期斜率重算 Pareto 前沿；
    2) 选出长寿命/快速/短寿命等典型策略，与长寿命参照策略做差，量化时间-退化权衡。"""
    sensitivity = summary[["policy", "n_battery", "time_mean", "loss_mean", "late_slope_mean"]].copy()
    # 以"全周期退化"与"晚期斜率"分别配时间算 Pareto，考察前沿是否对退化口径稳定
    sensitivity["pareto_soh200"] = pareto_mask(sensitivity["time_mean"], sensitivity["loss_mean"])
    sensitivity["pareto_late_slope"] = pareto_mask(sensitivity["time_mean"], sensitivity["late_slope_mean"])
    reference_policy = "3_6C-80PER_3_6C"  # 长寿命参照策略（典型慢充低退化）
    reference = summary.loc[summary["policy"].eq(reference_policy)].iloc[0]  # 参照策略的一行
    # 挑选典型策略：长寿命参照 + 快速对（FAST_PAIR）+ 典型短寿命策略
    selected = summary.loc[summary["policy"].isin([
        reference_policy, *FAST_PAIR,
        "3_7C_31PER_5_9C_NEWSTRUCTURE"]),
        ["policy", "n_battery", "time_mean", "loss_mean", "late_slope_mean"]].copy()
    # 为每个策略标注对比角色（供论文叙述与表格呈现使用）
    selected["comparison_role"] = selected["policy"].map({
        reference_policy: "typical_long_life_reference",
        "5_3C_54PER_4C_NEWSTRUCTURE": "point_pareto_fast_tradeoff_recommendation",
        "5C_67PER_4C_NEWSTRUCTURE": "uncertainty_near_tie_nonpareto_sensitivity",
        "3_7C_31PER_5_9C_NEWSTRUCTURE": "typical_short_life_reference",
    })
    selected["time_difference_vs_long"] = selected["time_mean"] - float(reference["time_mean"])  # 相对长寿命参照的时间差
    selected["loss_difference_vs_long"] = selected["loss_mean"] - float(reference["loss_mean"])  # 相对长寿命参照的退化差
    return sensitivity, selected


def integrity_checks(summary: pd.DataFrame, battery: pd.DataFrame, boot: pd.DataFrame,
                     loso: pd.DataFrame, recommendations: pd.DataFrame,
                     time_table: pd.DataFrame, fast_pair: pd.DataFrame,
                     before: dict[str, str], repetitions: int) -> pd.DataFrame:
    """发布前完整性校验：对主产物做一系列机器可读的断言，
    全部 passed 才允许原子发布。任何一项失败都会中止流程并列出失败项。"""
    # 读取 Q1 清洗表，获取训练电池与测试电池的 id 集合
    meta = pd.read_csv(ROOT / "data" / "processed" / "q1_cleaned" / "battery_summary_clean.csv")
    expected_ids = set(meta.loc[meta["prediction_test"].eq(0), "battery_id"].astype(int))  # 训练电池 id
    actual_ids = set(battery["battery_id"].astype(int))  # 本流程实际用到的电池 id
    lambda_columns = [name for name in boot if name.startswith("selected_lambda_")]  # λ 选择列
    constraint_columns = [name for name in boot if name.startswith("selected_loss_limit_")]  # 约束选择列
    per_rep = boot.groupby("replicate").size()  # 每个 bootstrap 重复的样本数
    lambda_sums = boot.groupby("replicate")[lambda_columns].sum()  # 每个重复中各 λ 的选中次数
    # 推荐表中的非空策略集合（排除 NO_FEASIBLE_POLICY 占位）
    recommendation_policies = set(recommendations.loc[recommendations["policy"].ne("NO_FEASIBLE_POLICY"), "policy"])
    pareto_policies = set(summary.loc[summary["pareto"], "policy"])  # 点估计 Pareto 策略集合
    # M1 留一验证中联合留出的坐标（n_test_policy=2 表示一折同时留出两个电池坐标）
    repeated_coordinate = loso.loc[loso["n_test_policy"].eq(2), "held_out_coordinate"]
    return pd.DataFrame([
        {"check": "nine_policies", "passed": len(summary) == 9, "detail": len(summary)},  # 策略数必须为 9
        {"check": "exact_complete_battery_ids", "passed": actual_ids == expected_ids and len(actual_ids) == 40, "detail": len(actual_ids)},  # 电池 id 与 Q1 训练集完全一致且共 40 块
        {"check": "test_battery_ids_excluded", "passed": actual_ids.isdisjoint(set(meta.loc[meta["prediction_test"].eq(1), "battery_id"].astype(int))), "detail": "prediction_test=1 intersection empty"},  # 不得混入测试电池
        {"check": "finite_policy_metrics", "passed": bool(summary[["time_mean", "loss_mean", "late_slope_mean"]].notna().all().all()), "detail": "finite time/loss/slope"},  # 指标须为有限值
        {"check": "bootstrap_replicates_complete", "passed": len(boot) == repetitions * 9 and per_rep.eq(9).all() and len(per_rep) == repetitions, "detail": len(boot)},  # 每个重复覆盖全部 9 策略且重复数完整
        {"check": "each_lambda_selects_one", "passed": len(lambda_columns) == 11 and lambda_sums.eq(1).all().all(), "detail": len(lambda_columns)},  # 每个 λ 恰好选中一个策略
        {"check": "constraint_rules_bootstrapped", "passed": len(constraint_columns) == len(LOSS_LIMITS), "detail": len(constraint_columns)},  # 约束规则列与场景数一致
        {"check": "late_slope_bootstrapped", "passed": bool(boot["late_slope_loss"].notna().all()), "detail": "strategy mean per replicate"},  # 晚期斜率在每个重复都有值
        {"check": "point_recommendations_pareto", "passed": recommendation_policies.issubset(pareto_policies), "detail": len(recommendation_policies)},  # 推荐策略必须是 Pareto 前沿
        {"check": "weighted_normalization_machine_readable", "passed": recommendations.loc[recommendations["rule"].eq("weighted_minmax_all_policies_diagnostic"), "normalization_scope"].eq("all_9_observed_policies_including_dominated").all(), "detail": "weighted score is diagnostic; all-policy minmax scope exposed"},  # 加权表必须显式标注诊断口径
        {"check": "m1_coordinate_folds", "passed": len(loso) == 7 and len(repeated_coordinate) == 1, "detail": "7 unique coordinates; duplicate coordinate jointly held out"},  # M1 留一折为 7 个唯一坐标，重复坐标联合留出
        {"check": "m1_failure_concentration_exposed", "passed": loso["worst_fold"].sum() == 1 and bool(loso.loc[loso["worst_fold"], "outside_train_exposure_range"].all()) and bool(loso.loc[loso["worst_fold"], "prediction_below_zero"].all()) and loso.loc[~loso["worst_fold"], "rmse"].mean() > loso.loc[~loso["worst_fold"], "constant_rmse"].mean(), "detail": f"worst-fold SSE share={loso['squared_error_share'].max():.6f}; excluding worst M1 RMSE={loso.loc[~loso['worst_fold'], 'rmse'].mean():.6f} > baseline={loso.loc[~loso['worst_fold'], 'constant_rmse'].mean():.6f}"},  # M1 失败集中于最差一折（训练 J 范围外、负退化预测），且剔除该折后 M1 仍不优于常数基线
        {"check": "fast_pair_point_pareto_roles", "passed": len(fast_pair) == 2 and fast_pair["point_pareto"].sum() == 1 and fast_pair.loc[fast_pair["point_pareto"], "decision_status"].eq("point_pareto_fast_tradeoff_recommendation").all() and fast_pair.loc[~fast_pair["point_pareto"], "decision_status"].eq("uncertainty_near_tie_nonpareto_sensitivity").all(), "detail": "point Pareto recommendation separated from non-Pareto uncertainty sensitivity"},  # 快速对中恰一者为点估计 Pareto 推荐，另一者标为非前沿近似并列
        {"check": "fast_pair_difference_intervals_cross_zero", "passed": bool((fast_pair["pair_time_difference_first_minus_second_p025"] < 0).all() and (fast_pair["pair_time_difference_first_minus_second_p975"] > 0).all() and (fast_pair["pair_loss_difference_first_minus_second_p025"] < 0).all() and (fast_pair["pair_loss_difference_first_minus_second_p975"] > 0).all()), "detail": "time and loss pairwise bootstrap intervals overlap zero"},  # 成对时间/退化差 bootstrap 区间均跨 0（近似并列成立）
        {"check": "q3_not_used_as_counterfactual", "passed": fast_pair["q3_role"].eq("not_used_no_early_trajectory_for_new_policy").all(), "detail": "Q3 is conditional prediction, not a policy response surface"},  # Q3 条件预测不作为反事实响应面
        {"check": "primary_time_matches_q1_q2", "passed": bool(time_table["primary_equals_summary"].all()), "detail": "Q4 primary equals battery_summary mean_chargetime"},  # 主时间指标与 Q1 口径一致
        {"check": "time_metric_pareto_stable", "passed": set(time_table.loc[time_table["pareto_cycle_time"], "policy"]) == set(time_table.loc[time_table["pareto_primary_time"], "policy"]), "detail": "cycle sensitivity versus primary battery_summary time"},  # 时间口径变化不改变 Pareto 前沿
        {"check": "protected_inputs_unchanged", "passed": before == protected_hashes(), "detail": "data, q4 source, smoke outputs"},  # 全程受保护文件哈希未变
    ])


def main() -> None:
    # ---------- 命令行参数解析 ----------
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=5000)  # 整块电池 bootstrap 重复次数
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "result" / "q4",  # 默认输出根目录：result/q4
        help="Directory containing the generated 02_full_validation directory.",
    )
    args = parser.parse_args()
    target = args.output_root.resolve() / "02_full_validation"  # 正式发布目录
    # 目录已存在则拒绝覆盖：保证权威结果可追溯、不被误覆盖
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    started = time.perf_counter()  # 开始计时
    before = protected_hashes()  # 记录执行前的受保护文件哈希

    # ---------- 数据整理与主分析 ----------
    observations, battery = collect_policy_observations(ROOT)  # 汇总 9 个策略的逐电池观测
    summary = observation_frame(observations)  # 整理为每策略一行的汇总表
    summary["pareto"] = pareto_mask(summary["time_mean"], summary["loss_mean"])  # 计算时间-退化 Pareto 前沿
    summary["version"] = FORMAL_VERSION  # 给汇总表打上协议版本号
    # 整块电池 bootstrap：重采样 + 每个重复内做 λ 加权选择与约束选择
    boot = bootstrap_pareto(battery, repetitions=args.bootstrap, seed=SEED,
                            lambda_grid=FORMAL_LAMBDAS, loss_limits=LOSS_LIMITS)
    boot["version"] = FORMAL_VERSION
    # M1 单 J 岭模型留一验证（oracle 坐标压力测试）：检验连续模型在观测数据下是否可用
    loso = loso_single_exposure(summary, "j", ridge_grid=RIDGE_GRID)
    loso["version"] = FORMAL_VERSION
    uncertainty = policy_uncertainty(battery, boot)  # 逐策略 bootstrap 不确定度区间
    recommendations = point_recommendations(summary)  # 点估计推荐（加权诊断 + 约束场景）
    selection_frequency, constraint_frequency = selection_frequencies(boot, args.bootstrap)  # 选择频率统计
    fast_pair = fast_pair_comparison(summary, boot, uncertainty, selection_frequency)  # 最快两策略成对对比
    time_table, time_decisions = time_model_sensitivity(summary, battery)  # 时间口径敏感性
    scale_sensitivity = scaling_sensitivity(summary)  # 归一化口径敏感性
    slope_sensitivity, typical_comparison = slope_and_typical_comparisons(summary)  # 晚期斜率/典型策略对比
    # 发布前完整性校验：任一检查项失败即中止并列出失败项
    checks = integrity_checks(summary, battery, boot, loso, recommendations, time_table, fast_pair, before, args.bootstrap)
    if not checks["passed"].all():
        raise RuntimeError(checks.loc[~checks["passed"], "check"].tolist())
    elapsed = time.perf_counter() - started  # 总耗时

    # ---------- 元数据：模型指标 / 模型登记 / 运行信息 / 运行配置 ----------
    # 四个模型的指标与状态（M0 观测 Pareto 主模型；M1 连续岭模型验证失败；B/C 为单目标基线）
    metrics = pd.DataFrame([
        {"model": "M0_discrete_pareto", "status": "pass_primary", "metric": "pareto_count", "value": float(summary["pareto"].sum()), "detail": "9 observed policies; no continuous causal extrapolation"},
        {"model": "M1_single_J_ridge", "status": "failed_validation_continuous_search_not_activated", "metric": "oracle_coordinate_pressure_rmse", "value": float(loso["rmse"].mean()), "detail": f"rejects this single-J ridge only; mean improvement={loso['improvement'].mean():.9g}; worst-fold SSE share={loso['squared_error_share'].max():.6f}"},
        {"model": "B_shortest_time", "status": "near_tie_baseline", "metric": "minimum_observed_time", "value": float(summary["time_mean"].min()), "detail": f"policies within {TIME_EQUIVALENCE_MINUTES} min treated as practical near-tie set"},
        {"model": "C_lowest_loss", "status": "baseline", "metric": "minimum_observed_loss", "value": float(summary["loss_mean"].min()), "detail": "single-objective boundary"},
    ])
    # 模型登记表：记录主模型与验证失败模型的地位说明
    registry = pd.DataFrame([
        {"version": FORMAL_VERSION, "model": "M0_discrete_pareto", "status": "primary", "detail": "observed policy Pareto, constraints and bootstrap"},
        {"version": FORMAL_VERSION, "model": "M1_single_J_ridge", "status": "failed_validation", "detail": "this single-J ridge is unusable; broader continuous model classes remain untested"},
    ])
    # 运行信息表：版本、耗时、bootstrap 次数、种子、λ 网格规模
    runtime = pd.DataFrame([{"version": FORMAL_VERSION, "stage": "full_q4_protocol",
                             "seconds": elapsed, "bootstrap_repetitions": args.bootstrap,
                             "seed": SEED, "lambda_count": len(FORMAL_LAMBDAS)}])
    # 运行配置快照：完整记录所有口径/常数，保证任何产物都可复核
    run_config = {"version": FORMAL_VERSION, "seed": SEED, "bootstrap": args.bootstrap,
                  "formal_lambda_grid": FORMAL_LAMBDAS.tolist(), "ridge_grid": list(RIDGE_GRID),
                  "loss_limits": list(LOSS_LIMITS),
                  "loss_limit_type": "illustrative_decision_scenario_not_safety_standard",
                  "primary_charge_time_metric": "battery_summary_clean.mean_chargetime",
                  "cycle_charge_time_metric_role": "sensitivity_only",
                  "time_equivalence_minutes": TIME_EQUIVALENCE_MINUTES,
                  "unique_recommendation_probability_threshold": SUPERIORITY_PROBABILITY,
                  "weighted_score_role": "diagnostic_weight_sensitivity_not_primary_recommendation",
                  "weighted_score_normalization": "minmax_all_9_observed_policies_including_dominated",
                  "q3_counterfactual_role": "not_used_no_early_trajectory_for_new_policy",
                  "continuous_model_conclusion": "single_J_ridge_failed_broader_classes_untested"}

    # ---------- 原子发布：先写临时目录，生成 manifest 后整体改名 ----------
    # 所有待发布 CSV：文件名 → DataFrame 的映射
    frames = {"policy_summary.csv": summary, "battery_observations.csv": battery,
              "bootstrap_pareto.csv": boot, "policy_uncertainty.csv": uncertainty,
              "selection_frequency.csv": selection_frequency,
              "fast_pair_comparison.csv": fast_pair,
              "constraint_selection_frequency.csv": constraint_frequency,
              "recommendations.csv": recommendations, "scaling_sensitivity.csv": scale_sensitivity,
              "time_model_sensitivity.csv": time_table,
              "time_metric_decision_sensitivity.csv": time_decisions,
              "late_slope_pareto_sensitivity.csv": slope_sensitivity,
              "typical_strategy_comparison.csv": typical_comparison,
              "m1_coordinate_loso.csv": loso, "model_metrics.csv": metrics,
              "model_registry.csv": registry, "runtime.csv": runtime,
              "integrity_checks.csv": checks}
    temp = target.with_name(target.name + ".tmp")  # 临时目录名 = 正式目录名 + ".tmp"（同目录保证改名原子性）
    temp.mkdir(parents=True)  # 创建临时目录
    for name, frame in frames.items():
        # utf-8-sig 带 BOM，便于 Excel 直接打开含中文的文件；index=False 不写行号
        frame.to_csv(temp / name, index=False, encoding="utf-8-sig")
    # 中文汇总报告：交代版本、口径、M0/M1 结论、推荐与注意事项（论文附录可直接引用）
    report = f"""# Q4 全量验证结果

版本`{FORMAL_VERSION}`，整块电池bootstrap {args.bootstrap}次，随机种子{SEED}，运行{elapsed:.3f}秒。

M0离散观测策略Pareto为主模型；M1单J岭模型的oracle坐标压力测试失败，所以本数据下不启动连续搜索。最差的3.6C留一折位于训练J范围外，产生负退化预测并贡献{loso['squared_error_share'].max():.1%}总平方误差；剔除该折后，M1平均RMSE仍为{loso.loc[~loso['worst_fold'], 'rmse'].mean():.6f}，略差于常数基线{loso.loc[~loso['worst_fold'], 'constant_rmse'].mean():.6f}。因此失败方向不依赖该折，但总体RMSE幅度明显受它驱动。该结果只否定当前单J岭代理，不证明所有连续代理或后续新增实验均无效。点估计Pareto策略为：{', '.join(summary.loc[summary['pareto'], 'policy'].astype(str))}。

充电时间主指标统一采用`battery_summary_clean.csv`中的逐电池`mean_chargetime`，与问题1、2一致。前200循环的逐循环均值仅作覆盖窗口敏感性，不能替代主指标。点估计上5.3C的时间和退化都低于5.0C，因此前者是快速区域的Pareto推荐，后者是非前沿的不确定性近似并列敏感性项。二者时间差和退化差的整块电池bootstrap区间均跨0，5.3C退化更低的概率不足0.95，因此不把5.0C排除为近似并列方案，但也不将严格被支配点标成共同主推荐。

权重结论依赖标准化集合。`recommendations.csv`中的加权结果明确标为诊断敏感性，使用全部9个观测策略（含被支配点）的min-max范围；该口径在λ=0.1时已选择5.3C，而只用Pareto点归一化要到λ=0.6才从3.6C切换到5.3C。`scaling_sensitivity.csv`保留这种差异，正式决策应报告Pareto前沿、退化约束和bootstrap稳定性，不能把任一加权表当成无条件主推荐。四个退化上限是说明规则用法的决策场景，不是工程安全标准。

`fast_pair_comparison.csv`分开记录点估计Pareto推荐与非前沿近似并列敏感性项，并给出成对区间和胜出概率。Q3模型需要目标电池已有1—150循环轨迹，未被用作新策略反事实响应面。推荐只适用于9个已有策略，不能解释为三参数因果最优。
"""
    (temp / "full_report.md").write_text(report, encoding="utf-8")  # 写中文汇总报告
    (temp / "run_config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")  # 写运行配置快照
    # 生成 manifest：目录内每个文件的文件名 + sha256 + 版本 + 种子，供事后校验目录完整性
    manifest_rows = [{"path": path.name, "sha256": _sha256(path),
                      "version": FORMAL_VERSION, "seed": SEED}
                     for path in sorted(temp.iterdir())]
    pd.DataFrame(manifest_rows).to_csv(temp / "manifest.csv", index=False, encoding="utf-8-sig")
    temp.replace(target)  # 原子发布：整个临时目录改名为正式目录（同文件系统上的原子 rename）
    print(f"Q4 full validation published: {target}", flush=True)
    print(f"Q4 full wall seconds: {elapsed:.3f}", flush=True)


if __name__ == "__main__":  # 脚本直接运行时才执行入口函数
    main()
