# 2026-08-15 A题项目关闭反思

## 背景

- Q1—Q4依次完成后，最新review触发整题一致性和入口状态复核。
- 关闭条件是四问权威结果齐全、论文表述与CSV一致、全测试通过并推送远程。

## 事实记录

- 四问模型与正式计算均已完成；Q1—Q4共10项MATLAB/Python测试全部通过。
- 最新Q4 review发现一处文字把末段衰减反转写反，数值CSV本身正确。
- Q3 README仍保留全量运行前状态，且最终回答把经验97.5%残差分位写成近似95%。
- 上述入口和论文口径已经修正，不改变冻结数值结果。

## 原因分析

- 各问题按阶段关闭后，历史README和自动生成报告没有统一的项目级状态源，导致权威结果已经生成但入口文字仍停留在旧阶段。
- “累计退化”和“末段斜率”是不同响应，若只读主Pareto表而未逐项对照敏感性CSV，容易把方向一致误写成没有反转。

## 经典坑或可复用经验

- 阶段关闭必须同时更新代码、结果、manifest、结果README和项目总入口。
- 同一结论使用多个响应变量时，应明确写出每个对象是否进入各自前沿，不能用概括性语言替代布尔结果表。
- 经验覆盖分位、名义覆盖率和联合覆盖率必须分开命名。

## 流程调整

- 后续论文阶段以`reports/A_problem_completion_report.md`为四问入口，不再从历史smoke README推断完成状态。
- 每次修改权威目录中的说明文件都同步更新manifest并复算SHA256。
- 最终论文引用数值前，按“正文数值—CSV字段—样本量—不确定性口径”四项对账。

## 不纳入本次调整

- 不重跑Q3长耗时全量验证；review已确认计算正确，当前修改只涉及解释层。
- 不扩展Q4连续参数搜索；数据可识别性不足，M1已按证据淘汰。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\A_problem_completion_report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-15_q4-full-validation-results-review.md`
- Tool: `functions.exec`、MATLAB和Python测试，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
