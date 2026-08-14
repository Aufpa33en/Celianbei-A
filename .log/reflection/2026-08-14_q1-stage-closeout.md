# 第一问阶段收尾记录

## 阶段目标

以清洗后的电池循环数据完成不同充电策略在 1—200 循环内的健康状态比较，选择可复现的主模型，并给出具有不确定性说明的典型长寿命与短寿命策略结论。

## 已完成内容

- 保留并复用三套独立 Python 实验程序，统一执行调参和留一电池验证。
- 将仅有前 150 循环的 9 块预测测试电池从第一问周期 200 推断中剔除，避免用模型补值反过来参与模型结论；它们继续作为第三问的外部验证数据。
- 建立主模型选择、策略曲线与标量估计、聚类自助法、两两比较、Holm 校正、排名稳定性、敏感性和残差诊断的完整计算链。
- 将第一问的权威结果固定为 `result/q1/` 下 30 个 CSV 文件，不在本阶段生成图片。
- 通过运行前后哈希证明受保护数据和已有实验程序未被正式分析过程修改。

## 核心结论

1. `functional_ridge` 的留一电池平均 RMSE 最低，为 0.004338；它与 `spline_mixed` 的差距仅约 0.000004，因而应表述为“按预先规定的 RMSE 规则胜出”，而不是声称具有实质性绝对优势。
2. 三种模型的周期 200 策略排序一致，说明主排序不是单一模型形式偶然造成的。
3. 周期 200 SOH 点估计的前三名为 `3_6C-80PER_3_6C`、`5C_67PER_4C_NEWSTRUCTURE`、`5_3C_54PER_4C_NEWSTRUCTURE`；后三名为 `4_8C_80PER_4_8C`、`80PER_3_6C`、`3_7C_31PER_5_9C_NEWSTRUCTURE`。
4. 排名不确定性不能忽略：前三名进入 Top 3 的自助概率分别为 0.9140、0.8575、0.7720；其中第三名未达到 80% 稳定阈值。后三名中 `80PER_3_6C` 和 `3_7C_31PER_5_9C_NEWSTRUCTURE` 的 Bottom 3 概率超过 80%，`4_8C_80PER_4_8C` 为 0.7100。
5. 当前没有任何电池达到 80% SOH，因此第一问只能严谨回答 0—200 循环内的相对健康表现，不能把局部线性 L80 当成已经验证的真实寿命。

## 验证与证据

- 主模型比较：`result/q1/model_comparison.csv`
- 模型一致性：`result/q1/model_agreement.csv`
- 策略估计与置信区间：`result/q1/strategy_scalar_estimates.csv`
- 排名稳定性：`result/q1/strategy_rank_stability.csv`
- 两两比较：`result/q1/pairwise_strategy_scalar_comparison.csv`
- 基线敏感性：`result/q1/baseline_sensitivity_strategy_rank.csv`
- 残差诊断：`result/q1/residual_diagnostics_overall.csv`
- 数据保护证据：`result/q1/data_integrity_check.csv`
- 程序保护证据：`result/q1/program_integrity_check.csv`
- 完整结果索引：`result/q1/result_manifest.csv`

正式运行命令：

```powershell
C:\Users\Aupassen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\q1\run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
```

## 局限与后续承接

- 每种策略只有 2—7 块完整电池，策略间差异的置信区间仍受小样本影响。
- 整体训练残差存在明显序列相关，平均一阶相关系数为 0.710；正式推断已以整块电池为自助单位，但训练残差不能替代跨电池验证误差。
- 基线口径敏感性显示第 2—4 名会交换，`3_6C-80PER_3_6C` 的第一名和后三名整体位置更稳健。
- 机制变量关联仅有 9 个策略级样本，只能作为描述性线索，不能作因果解释。
- 下一阶段进入第二问时，应直接引用本目录的权威 CSV，不重新运行或覆盖第一问结果；第三问再使用预留的 9 块 150 循环电池检验预测能力。

## 使用的技能与经验来源

- `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\references\stage-closeout-template.md`
- `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- `C:\Users\Aupassen\.codex\skills\project-logbook\references\project-reflection-log.md`

这些工作流促使本阶段把“模型代码、正式结果、验证证据、论文可用结论和下一问接口”分别固化，避免把探索性输出误当成最终证据。
