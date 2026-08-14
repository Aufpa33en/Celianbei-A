# 2026-08-14 第三问阶段关闭

## 背景

- 阶段范围：第三问第151—200循环SOH轨迹预测、模型比较、测试电池预测与80%终点情景外推。
- 关闭条件：模型推导和文献依据齐全；三路运行前审查通过；40块完整电池全量验证完成；9块测试电池预测完成；运行后审计、结果完整性和论文材料全部通过。

## 事实记录

- 当前权威结果为`result/q3/02_full_validation`与`result/q3/03_final_predictions`。
- 六个预先定义模型完成40块电池、三个早期长度的外层LOBO；冻结模型为`C_ridge`。
- L=150部署参数为(K=1, alpha=10)；完整嵌套选模流程L=150策略等权RMSE为0.000709。
- 9块测试电池均已生成151—200循环预测、逐循环近似区间及EOL敏感性结果。
- 02目录15/15项、03目录9/9项完整性检查通过；68个受保护文件哈希不变。
- `tests/test_q3_models.py`、`tests/test_q3_smoke_outputs.py`、`tests/test_q3_full_protocol.py`均通过。
- 论文材料位于`reports/q3_full_validation_report.md`；详细变更记录位于`.log/change/2026-08-14_q3-full-validation-and-final-prediction.md`。

## 原因分析

- `C_ridge`胜出来自预先规定的L=50/100/150综合目标；单独L=150时`P1_linear`略优。因此模型选择结论依赖明确的任务权重，不应脱离综合指标表述。
- C特征消融耗时583.91秒，是922秒总墙钟中的主要瓶颈。原因是三个特征模式均执行严格的外层验证，而不是最终9块电池预测本身耗时。
- EOL范围对拟合窗口和幂指数明显敏感，因为全部电池均未观测到80% SOH，远期交点缺少真实标签约束。

## 经典坑或可复用经验

- 模型超参数调优指标必须与最终策略等权评价一致，否则每策略2—7块电池的不平衡会改变模型排序。
- smoke只负责排错和估时；正式选模必须让所有数值可运行候选进入相同外层验证。
- 固定候选的LOBO误差与包含模型族选择的嵌套流程误差必须分开报告。
- 测试电池必须在模型、超参数和区间校准全部冻结后才读取，且最终结果不能包含不存在的未来真值或测试RMSE。
- 无真实阈值标签的T80只能作为敏感性情景，不能参与选模或称为已验证寿命。

## 流程调整

- 后续问题继续保留“推导—多代理攻击—smoke—阶段报告—用户放行—全量—运行后审计”的硬门。
- 正式运行前冻结主指标、并列规则、模型族和消融是否参与选模，避免看到结果后改变口径。
- 对高成本消融优先实现折级缓存或并行；优化不得改变外层隔离与策略等权评价。
- 结果目录继续采用版本化、拒绝覆盖、临时目录校验后原子发布和manifest哈希。

## 不纳入本次调整

- 未因L=150下P1略优而事后改选模型；这会违反预先冻结的多长度综合指标并产生结果后选模偏差。
- 未把动态特征消融变体追加为第七候选；该结果只作机制分析，若未来要参与选模，必须在新版本中预先登记并重跑完整嵌套验证。
- 未对T80给出预测准确率或置信区间，因为没有真实80%终点标签。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/reports/q3_full_validation_report.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/.log/change/2026-08-14_q3-full-validation-and-final-prediction.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/result/q3/02_full_validation`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/result/q3/03_final_predictions`
- Tool: PowerShell，命令`git status --short`、三个Q3测试脚本、完整性CSV检查与`git push origin main`，cwd `C:/Users/Aupassen/Desktop/Celianbei Math Modeling`
