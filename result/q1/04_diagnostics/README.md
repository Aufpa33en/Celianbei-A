# 04 残差诊断与机制线索

## 使用的模型

残差来自主模型 `functional_ridge` 对完整样本的拟合。特征分析不是新的预测模型，而是把 SOH、内阻、温度和充电时间在早期与末期窗口内进行汇总，并计算策略级描述性相关。

## 输入

- 主模型逐电池拟合值与 `SOH_clean` 的残差。
- 每块完整电池的 `SOH`、内阻、温度、充电时间序列。
- 9 种策略的特征均值和标准差。

## 得到的结果

- 整体、策略级和电池级残差 RMSE、MAE、偏差、最大误差、Lag-1 相关和 Durbin–Watson 统计量。
- 每块电池早期20循环、末期20循环及二者差值的健康/机理特征。
- 策略级特征摘要及其与 SOH200 的 Pearson、Spearman 相关。

工作簿 `diagnostics_and_features.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `ResidualOverall` | `residual_diagnostics_overall.csv` | 全部观测的残差汇总 |
| `ResidualByPolicy` | `residual_diagnostics_by_policy.csv` | 按充电策略汇总残差 |
| `ResidualByBattery` | `residual_diagnostics_by_battery.csv` | 逐电池残差诊断 |
| `BatteryFeatures` | `battery_feature_metrics.csv` | 逐电池早期/末期特征 |
| `StrategyFeatures` | `strategy_feature_summary.csv` | 策略级特征均值和标准差 |
| `Associations` | `strategy_association_summary.csv` | 特征与 SOH200 的描述性相关 |

相关分析只有 9 个策略级样本，不能解释为因果关系。
