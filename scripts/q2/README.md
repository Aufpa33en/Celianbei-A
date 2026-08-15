# 问题2程序

## Smoke test入口

```powershell
python scripts/q2/run_q2_smoke_test.py
```

程序只读取第一问清洗结果，不修改原始数据或清洗数据。数值核心位于`src/q2_models/`，输出写入`result/q2/00_design/`、`01_smoke_test/`和`02_model_selection/`。

候选包含策略均值常数、最近参数坐标、原始三参数岭回归、阶段暴露、`J`、`H`、固定高SOC阈值暴露，以及模型C的线性化层次代理。模型C代理只用于判断复杂层次是否值得继续拟合，不冒充正式指数链接+AR(1)边际似然。

## 正式验证入口

```powershell
python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8
```

正式验证按策略内整块电池重采样，执行2000次bootstrap。另保留6个策略均值的720种标签排列，仅用于展示“若策略均值可交换”时统计量的位置；由于策略样本量、方差不同且策略并非随机分配，该尾部比例不是确认性`p`值。每次bootstrap都重新选择岭参数和SOC暴露候选，输出写入`result/q2/03_formal_validation/`。

## 合并稳健性入口

```powershell
python scripts/q2/run_q2_merged_robustness.py --permutations 20000 --seed 20260814
```

该入口提取第151—200循环末段退化率，执行九策略全局置换、4.8C匹配诊断和`J+H`模型的唯一坐标留出敏感性分析，输出写入`result/q2/05_merged_robustness/`。它补充而不替代正式高SOC暴露验证。
