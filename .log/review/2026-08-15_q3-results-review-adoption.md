# 2026-08-15 第三问全量结果复核意见采纳

## 检查范围

- `.log/review/2026-08-14_q3-full-validation-results-review.md`、Q3权威结果、正式报告和最终回答。

## 检查依据

- 已冻结的Q3嵌套LOBO协议、权威CSV、论文口径一致性和“不修改既有实验结果”的约束。

## 发现

1. “近似95%区间”与实际经验97.5%残差分位不一致。
   - 影响: 低估区间保守性，并忽略固定模型族条件。
   - 处理: 采纳；正式报告和最终回答统一写成经验97.5%残差分位的保守逐循环点区间，并说明不含选族不确定性。
2. 第2—4名的点排序不稳定。
   - 影响: 表格可能被误读为P1稳定第二。
   - 处理: 采纳；说明三者处于2%并列容差内，并报告B、D、P1的bootstrap胜出频率。
3. 策略特征作用表述偏宽。
   - 影响: L=150动态特征0.000645优于完整模型0.000660，不能概括为稳定补充。
   - 处理: 采纳；明确该窗口连续策略特征没有提高预测精度。
4. Q3结果README仍停留在全量运行前。
   - 影响: 与已存在的全量结果和最终预测矛盾。
   - 处理: 更新为完成状态和正式复现入口。
5. `_bootstrap_selection`模块常量、部署冻结冗余字段等代码整洁建议。
   - 影响: 当前配置下不改变任何数值。
   - 处理: 不采纳代码改动；Q3结果已冻结，修改程序会触发受保护文件哈希变化，收益不足。冗余字段和最差指标语义改在报告中解释。

## 已采纳

- 区间口径、排名稳定性、消融解释、指标语义和结果目录状态等论文/说明修正。

## 未采纳

- 未修改冻结后的Q3数值程序，也未重做split conformal、EOL新模型或额外实验；这些属于后续方法提升，不是当前结果正确性的阻断项。

## 验证情况

- Q3三个测试脚本全部通过。
- 修改`q3_complete_answer.md`后同步更新`03_final_predictions/manifest.csv`中的行数、大小和SHA256。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q3-full-validation-results-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\q3_full_validation_report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\03_final_predictions\`
- Tool: `functions.exec`与`apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
