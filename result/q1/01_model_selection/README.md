# 01 模型选择与验证

## 使用的模型

- `polynomial_mixed`：二次多项式策略曲线 + 电池随机截距/斜率。
- `spline_mixed`：截断三次样条策略曲线 + 电池随机截距/斜率。
- `functional_ridge`：逐电池三次样条岭平滑 + 策略内电池等权平均。

## 输入

- 40 块完整观测电池的 `cycle`、`policy`、`battery_id`、`SOH_clean`。
- 候选惩罚系数网格。
- 分层三折调参和留一电池验证划分。

## 得到的结果

按留一电池平均 RMSE 选择 `functional_ridge`，其 RMSE 为 `0.004338`；`spline_mixed` 为 `0.004342`，二者非常接近。三种模型的周期 200 策略排序一致。

工作簿 `model_selection.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `Tuning` | `all_model_tuning.csv` | 全部候选超参数及三折验证误差 |
| `AllModelLOBO` | `all_model_lobo_by_battery.csv` | 三模型逐电池留一验证结果 |
| `MainModelLOBO` | `main_model_lobo_by_battery.csv` | 主模型逐电池留一验证结果 |
| `CVByPolicy` | `authoritative_model_cv_by_policy.csv` | 主模型按策略汇总的验证误差 |
| `ModelComparison` | `model_comparison.csv` | 三模型总体验证指标与选择标记 |
| `PairwiseCVDiff` | `model_pairwise_cv_difference.csv` | 模型间电池级 RMSE 差值区间 |
| `ModelAgreement` | `model_agreement.csv` | 模型曲线差异与排名相关性 |
| `RankByModel` | `strategy_rank_by_model.csv` | 每种模型给出的策略排名 |
