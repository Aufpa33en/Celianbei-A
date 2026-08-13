# 2026-08-13 问题1数据清洗最终决策

## 修改目标

- 固定A题后续建模使用的数据版本和清洗规则。
- 说明第12循环异常的判断依据、修复范围及论文表述边界。
- 防止后续脚本覆盖原始数据或把异常采集记录作为寿命预测特征。

## 最终结论

1. 后续模型使用`data/processed/q1_cleaned/`中的清洗数据；`data/raw/`和A题官方附件保持不变。
2. 第12循环没有公开实验协议支持其具有特殊诊断作用。三条异常集中在同一策略`3_6C-80PER_3_6C`的三个重复样本：电池1出现单点容量突增，电池2、3出现零内阻。项目将其判定为需要修复的数据质量异常。该判断属于数据和公开协议支持下的推断，不表述为已知的出题人主观意图。
3. 清洗采用最小干预规则，只修复有物理矛盾或强局部证据的记录，不删除整块电池，不强制SOH单调，不统一缩放全部曲线。
4. 电池1第12循环容量由`1.5390544 Ah`改为第11、13循环线性插值`1.07430415 Ah`，并按初始容量重新计算SOH。
5. 电池2、3第12循环内阻`0`按物理无效值处理，分别用相邻循环插值得到`0.0168692075`和`0.0166834345`。
6. 清洗表保留`capacity_raw`、`SOH_raw`、`IR_raw`和官方平滑值，并增加清洗值、趋势值及`flag_any_repair`。原始异常用于审计、清洗前后对照和模型敏感性分析，不作为电池健康或寿命预测特征。
7. 电池41保留。其整条曲线存在初始SOH基线差异，项目同时报告绝对SOH和以首5循环容量中位数为基准的相对SOH，避免把电池级基线差异误判成单点错误。
8. 策略`80PER_3_6C`的`C1`保持缺失。后续模型可把该策略纳入策略类别比较，但不得用猜测值参与`C1`连续效应估计。
9. 官方`SOH_smooth`受容量尖峰污染，不作为建模真值。项目在修复后的SOH上重新计算7、11、15点稳健局部回归趋势，并用三个窗口检查结论敏感性。

## 论文表述

论文将该步骤写为“局部异常识别与可审计修复”，不用含义过宽的“数据正常化”。方法段需要给出局部邻域、MAD标准分数、2%相对偏差和`IR<=0`规则。结果段报告三条修复记录，并说明清洗前后敏感性分析。论文不得把第12循环解释成已确认的电化学机制。

## 权威数据与输出

- 原始数据：`data/raw/battery_summary.csv`、`data/raw/cycle_train.csv`
- 建模数据：`data/processed/q1_cleaned/battery_summary_clean.csv`、`data/processed/q1_cleaned/cycle_train_clean.csv`
- 修复审计：`outputs/summary/q1_cleaning/cleaning_actions.csv`
- 质量汇总：`outputs/summary/q1_cleaning/cleaning_quality_summary.csv`
- 对照图：`figures/cleaning/fig02_cleaning_before_after.png`

## 验证情况

- 清洗后保留49块电池和9350条循环记录。
- 清洗动作表共3条：1条容量修复和2条内阻修复。
- MATLAB测试`run('tests/test_q1_cleaning.m')`已输出`All Q1 cleaning tests passed.`。
- 全部`SOH_clean`满足容量与初始容量之比，修复后不存在非正内阻。

## 未处理事项

- 尚未比较清洗数据、原始数据和删除异常循环三种输入对模型参数及预测误差的影响。
- 尚未完成7、11、15点趋势窗口的模型级敏感性分析。
- 尚未选择问题1至问题4的正式模型；模型选择须先完成相关研究文献审阅。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-13_cycle12-purpose-and-modeling-boundary.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-13_q1-cleaning-execution.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\data_cleaning_strategy_candidates.md`
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`

