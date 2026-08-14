# Smoke test逐项结果

- `battery_degradation_summary.csv`：40块完整电池的SOH200、相对退化、二次曲线摘要和策略参数。
- `strategy_degradation_summary.csv`：先在策略内对电池等权平均后的8个参数完整策略摘要。
- `scalar_fold_predictions.csv`：10种策略级候选在三种队列、两种响应上的全部留一坐标预测。
- `hierarchical_fold_predictions.csv`：无应力基线及4种模型C线性化代理在8个循环检查点上的留一坐标预测。

层次代理采用

`SOH = 固定循环项 + 应力×循环 + 电池随机截距/斜率 + 策略随机斜率`

的惩罚最小二乘近似，抽取第1循环和每5个循环拟合。它只用于判断完整模型C是否值得继续，不替代正式指数链接、策略层积分和AR(1)似然。
