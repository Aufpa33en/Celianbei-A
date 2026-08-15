# 2026-08-15 第四问范围与Review意见采纳审查

## 检查范围

- 第四问原题PDF与数据字典。
- 第二问正式验证结论、第三问阶段关闭记录和第三问结果审查意见。
- 新增`docs/q4_model_direction_and_boundary.md`中的模型边界、候选模型和停止规则。

## 检查依据

- 第四问题目要求：兼顾两阶段充电时间和SOH衰减，优先比较已有策略，连续优化须限制在实验合理邻域。
- 第二问硬边界：约7个独立完整参数坐标，`C1/Q1/C2`独立因果效应不可稳定辨识，`J/H/Jhigh`仅作描述性关联。
- 第三问硬边界：`C_ridge`是已观测策略条件下的早期轨迹预测器，T80没有真实标签，只能作情景外推。

## 发现

1. 第四问适用既定“推导—文献—代理审查—smoke—全量”的流程，但属于在第二问基础上的策略优化扩展，不是完全沿用第三问。
   - 处理：采纳，主模型从策略级离散比较开始。

2. 直接用Q3 `C_ridge`优化连续`C1/Q1/C2`会把条件预测器误当反事实模型。
   - 影响：新策略没有真实早期SOH轨迹，无法合法构造Q3动态输入。
   - 处理：不采纳，Q3仅作已有策略轨迹和不确定性辅助。

3. 理论恒流时间`T0`在7个非基准新结构策略中约为10分钟，主要时间差来自实际结构/批次/温度/内阻和恒压尾段。
   - 影响：`T0`没有足够变异估计时间效应，不能代替实测充电时间。
   - 处理：采纳，M0使用实测策略时间，`T0`仅作解释敏感性。

4. 自由三参数响应面和联合层次时间—退化模型受到坐标少、结构混杂、`J/H`共线和`C1`缺失的共同限制。
   - 处理：不作为主模型；只允许低维、凸包内、留一策略验证的探索性M1。

5. 目标函数存在分钟与SOH损失量纲不同的问题。
   - 处理：采纳Pareto和约束选择；权重扫描前分别min-max标准化，并明确权重是决策偏好。

## 已采纳

- 9个已有策略离散Pareto主线。
- 策略内整块bootstrap不确定性。
- 受限单应力响应面敏感性。
- 观测域/凸包约束、LOSO策略验证和连续优化停止规则。
- 预计运行时间1—15分钟分层说明。

## 未采纳

- Q3 `C_ridge`连续反事实优化。
- 自由三参数、二次交互和联合层次主模型。
- 使用未观测80% EOL作为优化目标。

## 验证情况

- 已阅读题目原文、Q2正式结果、Q3关闭记录及最新Q3结果审查意见。
- Q3既有权威结果未修改；当前仅新增Q4边界文档和本审查记录。
- Q4正式代码、smoke和全量计算尚未开始。
- 两名子代理已完成文档级复核并要求修正：训练折内标准化、经验时间模型口径、Pareto平局与空约束处理、唯一坐标LOSO/凸包外推标记和可计算停止阈值。上述修正已写入两份Q4设计文档。
- 修正后代理结论：M0离散Pareto PASS；M1仅条件PASS且只能作敏感性；自由连续三参数优化 FAIL。Q4 smoke尚未开始。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/docs/q2_literature_screening_and_model_derivation.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/docs/q3_literature_and_model_derivation.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/result/q2/03_formal_validation/正式验证结论.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/.log/review/2026-08-14_q3-full-validation-results-review.md`
- Tool: `functions.exec`，PowerShell文件读取和`pdftotext`，cwd `C:/Users/Aupassen/Desktop/Celianbei Math Modeling`
