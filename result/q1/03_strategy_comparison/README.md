# 03 策略差异与稳健性

## 使用的模型

策略差异以主模型 `functional_ridge` 的策略级曲线为基础。推断单位是整块电池，而不是单个循环点；使用 2000 次策略内电池聚类自助法。

## 输入

- 主模型的 9 条策略曲线和每次自助重抽样曲线。
- 周期 200 SOH、累计损失、平均 SOH、平均充电时间等标量。
- 三种基线口径：主清洗 SOH、相对 SOH、排除电池 41。

## 得到的结果

- 36 组策略对的逐循环差值、点置信区间和同时置信带。
- 36 组策略对的曲线差异摘要。
- 多个标量指标的两两比较、符号自助检验和 Holm 多重比较校正。
- 策略排名对 SOH 基线口径及异常电池处理的敏感性。

工作簿 `strategy_comparison.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `PairwiseCurveByCycle` | `pairwise_strategy_curve_by_cycle.csv` | 每一策略对在每个循环的差异与区间 |
| `PairwiseCurveSummary` | `pairwise_strategy_curve_summary.csv` | 曲线 RMSE、积分差和显著循环比例 |
| `PairwiseScalar` | `pairwise_strategy_scalar_comparison.csv` | 标量差异、置信区间、P 值和 Holm 结果 |
| `BaselineSensitivity` | `baseline_sensitivity_strategy_rank.csv` | 三种数据口径下的 SOH200 排名 |
