# 2026-08-15 第四问阶段关闭

## 背景

- 第四问目标是兼顾充电时间和寿命衰减，在已有实验策略范围内给出可审计推荐。
- 关闭条件为全量计算完成、论文五小问数据齐全、独立审查问题修复且回归测试通过。

## 事实记录

- M0离散Pareto通过，M1连续优化器被淘汰。
- 权威目录为`result/q4/02_full_validation/`；5000次bootstrap、11点权重、四个约束场景、双时间口径、末段衰减和典型策略对比均已保存。
- 点估计Pareto为3.6C基准、4.8C新结构和5.3C新结构；5.3C在近似并列最快组中退化最低。
- 12项完整性检查与Q3回归测试通过。

## 原因分析

- 第一次全量结果计算正确但输出契约不足，原因是只把smoke协议放大到5000次，没有逐条对照题目五项任务和审查文档中的所有承诺。
- 严格浮点排序和全体min-max会给出形式上唯一、实际不稳健的权重推荐；bootstrap和缩放敏感性揭示了这一点。

## 经典坑或可复用经验

- 全量验证不仅是增加重复次数，还必须兑现smoke阶段登记的每一种不确定性、敏感性和论文输出。
- 多目标权重的结论必须审计缩放集合；有极端点时，权重切换不能当作稳定机理证据。
- 数值上最小不等于工程上可区分，必须同时报告实际容差和bootstrap选择频率。
- 直接运行测试脚本前，应确认其具有独立执行入口或使用可用的测试运行器。

## 流程调整

- 后续问题关闭前逐条建立“题目小问—结果文件—正文结论”映射。
- 将约束选择频率、无可行频率、标准化敏感性和数据口径敏感性列为多目标优化的固定验收项。

## 不纳入本次调整

- 不扩展到未观测连续协议，因为当前7个完整独立坐标不足以支持三参数因果优化。
- 不估计真实T80，因为没有寿命终点标签。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-15_q4-full-validation-review-fixes.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\q4_full_validation_report.md`
- Tool: `functions.exec`与Q4代理审查，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
