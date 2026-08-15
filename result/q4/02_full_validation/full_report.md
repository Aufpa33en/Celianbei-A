# Q4 全量验证结果

版本`q4_full_v3`，整块电池bootstrap 5000次，随机种子20260815，运行7.343秒。

M0离散观测策略Pareto为主模型；M1单J模型的oracle坐标压力测试失败，正式淘汰为优化器。点估计Pareto策略为：3_6C-80PER_3_6C, 4_8C_80PER_4_8C_NEWSTRUCTURE, 5_3C_54PER_4C_NEWSTRUCTURE。

充电时间主指标统一采用`battery_summary_clean.csv`中的逐电池`mean_chargetime`，与问题1、2一致。前200循环的逐循环均值仅作覆盖窗口敏感性，不能替代主指标。按主指标和0.01分钟容差，只有5.3C-54%-4C与5C-67%-4C属于最快近似并列组。

权重结论依赖标准化集合，`scaling_sensitivity.csv`只作敏感性；正式决策应报告Pareto前沿、退化约束和bootstrap稳定性。四个退化上限是说明规则用法的决策场景，不是工程安全标准。

`time_model_sensitivity.csv`同时保存主指标、逐循环敏感性均值和T0；`typical_strategy_comparison.csv`对比推荐策略与典型长/短寿命策略。推荐只适用于9个已有策略，不能解释为三参数因果最优。
