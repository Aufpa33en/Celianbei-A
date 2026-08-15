# 02 主模型策略结果

## 使用的模型

主模型内部标识为 `functional_ridge`：用标准化循环位置构造带三个节点的三次样条基，逐电池拟合 SOH 曲线，再在同一充电策略内对电池系数等权平均。扩展网格后验证选中 `lambda_curve=0`，所以当前主模型应称为两阶段函数型曲线，不是正惩罚的岭解。该处理避免循环记录较多或波动较小的单块电池获得过大权重。

本工作簿同时保留另外两个候选模型的策略曲线和汇总，便于复核主结论是否依赖单一模型。

## 输入

- 40 块完整电池的 `cycle`、`policy`、`battery_id`、`SOH_clean`。
- 主模型曲线惩罚 `lambda_curve=0`（扩展网格的自然端点）。
- 2000 次策略内电池聚类自助样本。

## 得到的结果

- 9 种策略在第 1—200 循环的 SOH 估计曲线。
- 周期 200 SOH、累计损失、区间平均 SOH、末段斜率、局部线性 L80 代理和平均充电时间。
- 点置信区间、策略排名及进入 Top/Bottom 组的概率。

工作簿 `main_model_results.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `AllModelCurves` | `all_model_strategy_curves.csv` | 三模型的策略级周期曲线 |
| `AllModelSummary` | `all_model_strategy_summary.csv` | 三模型策略级标量摘要 |
| `CurveConfidenceBand` | `strategy_curve_confidence_band.csv` | 主模型逐周期点置信区间 |
| `ScalarEstimates` | `strategy_scalar_estimates.csv` | 主模型标量估计、标准误和区间 |
| `RankStability` | `strategy_rank_stability.csv` | 点排名与自助排名稳定性 |
