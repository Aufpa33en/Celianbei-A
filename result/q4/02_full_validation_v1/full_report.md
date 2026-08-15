# Q4 全量验证报告

- 版本：`q4_full_v1`
- 策略内整块bootstrap：5000次
- 正式lambda网格：11点 `0.0,0.1,...,1.0`
- 完整电池：40块；测试电池未参与聚合
- 运行时间：6.771秒

## 主结论

M0离散观测策略Pareto模型通过全量完整性检查，作为Q4主模型。M1单J岭模型仅保留为坐标LOSO外推压力测试，不能生成连续三参数推荐。

点估计Pareto策略：3_6C-80PER_3_6C, 4_8C_80PER_4_8C_NEWSTRUCTURE, 5_3C_54PER_4C_NEWSTRUCTURE。结果必须结合`n_battery`、Pareto频率和时间/退化百分位区间解释；n=2策略的bootstrap频率仅作粗粒度稳定性证据。

## 输出

`policy_uncertainty.csv`包含time/loss/late_slope_loss的2.5%、50%和97.5%分位数；`selection_frequency.csv`包含Pareto及11个lambda权重的策略频率；`recommendations.csv`包含权重扫描和预设退化约束下的观测域推荐。

## 限制

推荐仅适用于9个已有实验策略。旧/新同坐标差异的结构/批次混杂不能归因于参数因果效应；T0仅作解释；80% EOL无真实标签，不作为优化目标。
