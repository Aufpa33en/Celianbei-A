# 2026-08-15 第四问全量结果复核

## 检查范围

- Q4 全量权威结果 `result/q4/02_full_validation/`（`q4_full_v2`），对照正式报告、变更日志、修正日志、协议测试与上一轮 smoke 审查。

## 检查依据

- 原题第四问五项任务、Q4 推导文档、smoke 审查边界、`review-fixes`/`change` 日志，以及对各 CSV 的逐项复算。

## 验证情况

- 版本/种子/耗时/规模一致：`q4_full_v2`、seed `20260815`、5000 次 bootstrap、7.705 秒、45,000 行、12/12 完整性检查通过。
- M1 七折 RMSE 手算均值 0.015826，与 `model_metrics.csv` 的 0.015827 一致；7 折中 6 折改善为负，与报告一致。
- 上一轮 smoke 的 7 项发现（λ 网格 11 点、末段斜率统一为策略均值 bootstrap、双时间口径、0.01min 近似并列、三种缩放敏感性、非安全阈值、测试独立入口）在 `review-fixes`/`change` 日志中逐条落实；`_v1` 快照原样保留，权威目录为修正版。

## 发现

1. 报告第 3 节"没有反转"与自身数据相反。
   - 影响: `late_slope_pareto_sensitivity.csv` 中 3_6C 掉出前沿（`pareto_late_slope=False`），只剩 {4_8C_new, 5_3C}；3_6C 累计退化最低（0.000428）但末段衰减率最高（5.00e-5/循环），高于 4_8C_new（2.77e-5）与 5_3C（3.15e-5），在末段口径下被 4_8C_new 严格支配。这正是报告声称"没有出现"的"累计退化较低但末段衰减恶化"反转。
   - 处理: 建议必改。文字反过来写才成立：3.6C 的"最低累计退化"一部分来自 n=2 抽样噪声（loss_sd 0.00275 远大于 loss_mean 0.0004），其末段衰减率反而最高；推荐 5.3C 与 4.8C 新结构在 SOH200 与末段斜率两个口径的前沿上同时成立，不存在快充导致的末段加速恶化。此为论文亮点而非缺陷。

2. 退化代理 D 可为负。
   - 影响: 3_6C 的 `loss_p025=-0.0015`，即 bootstrap 下部分电池 SOH200 高于前 5 循环基线，退化跌破 0。报告未点明该口径，低退化策略的 D≈0.0004 已贴近测量噪声地板。
   - 处理: 建议在论文退化定义处加脚注，避免对 3.6C"最低退化"作过强断言。

3. "7个参数完整的新结构策略"表述不精确。
   - 影响: 报告第 2 节称"7个参数完整的新结构策略的`T0`约为9.99—10.02分钟"，但 7 个完整坐标的非基准策略含旧结构 `4_8C_80PER_4_8C`，不全为"新结构"。
   - 处理: 应改为"7 个参数完整的非基准策略"。

4. 主 Pareto 表只列 3 点，未提示前沿成员不稳定。
   - 影响: 点估计前沿 {3_6C, 4_8C_new, 5_3C} 复算正确，但 `selection_frequency.csv` 显示 5C_67PER(0.414)、5_6C_36PER(0.312)、5_6C_19PER(0.173) 也频繁进入前沿，9 个策略中 6 个在 ≥17% 的重复里进过前沿。主表仅呈现 3 点，读者可能误以为这是稳定划分。
   - 处理: 建议补一句"3 点仅为点估计，前沿成员不稳定"。

## 已核验通过

- M1 淘汰证据充分：`(3.6,80,3.6)` 折 RMSE 0.053 约为其余折（0.004—0.007）的 10 倍，线性 J 模型外推到低 J 基线彻底失效；6/7 折劣于常数基线；已正确标注为 oracle-only 压力测试而非优化器。
- 约束频率每阈值合计恰为 1（40 行）；`D_max=0.0017` 时 5.3C 频率 0.5174、无可行 0.0166，与报告一致。
- 双时间口径 Pareto 一致（cycle 与 summary 均 {3_6C, 4_8C_new, 5_3C}），`time_metric_pareto_stable` 通过。
- 推荐 5_3C 稳健性四证据成立：点估计前沿、Pareto 频率最高 0.892、n=7 最大、最快四策略（近似并列）中退化最低（0.001615）。
- 协议测试覆盖充分（9 策略、3 Pareto、45,000 行、11 权重列恰选 1、约束频率合计 1、双口径前沿一致）。

## 建议

1. 修正发现 1 的措辞，把"没有反转"改为"3.6C 末段衰减率反而最高，推荐策略无末段加速"，并升级为论文亮点。
2. 退化定义处补 D 可负的脚注。
3. 主表补前沿成员不稳定说明；"新结构"改"非基准"。

## 依据与工具

- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q4\02_full_validation\`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\q4_full_validation_report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-15_q4-full-validation-review-fixes.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-15_q4-full-validation.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\tests\test_q4_full_validation.py`
