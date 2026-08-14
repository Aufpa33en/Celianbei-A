# 2026-08-14 第二问smoke模型选择检查

## 检查范围

- `result/q2/00_design/`
- `result/q2/01_smoke_test/`
- `result/q2/02_model_selection/`
- `src/q2_models/`

## 检查依据

- 参数效应的独立单位为唯一策略坐标。
- 主模型必须优于常数基线、系数方向在删除坐标后稳定，并能回答第二问参数/SOC作用，而不只做近邻预测。
- 模型C只有在曲线外推明显改善且层次结构可稳定估计时才继续。

## 发现

1. 等`T0`事实成立，但队列名称需纠正。
   - 影响: 不能把7个非基准策略全部称为新结构。
   - 证据: `design_audit.csv`显示7个非基准标签、6个`NEWSTRUCTURE`标签；前者6个唯一坐标，后者6个唯一坐标。
   - 处理: 主模型使用6个明确新结构策略，7策略队列只作敏感性分析。
2. 理想`T0`恒定不等于实际充电时间恒定。
   - 影响: 不能宣称SOH差异只能由SOC区间造成。
   - 证据: 非基准策略`T0=9.990—10.013 min`，实际平均充电时间`10.158—13.082 min`。
   - 处理: 结论降级为排除名义恒流时间主要差异后的关联证据。
3. 最近参数坐标法预测最好，但不能解释参数效应。
   - 影响: 不能把预测基准作为第二问的论文主模型。
   - 证据: 同结构队列相对退化RMSE为0.013043。
   - 处理: 保留为预测基准，不选为解释模型。
4. `ridge_Jhigh70`是当前连续解释候选中唯一综合排序第一且双响应均优于常数的模型。
   - 影响: 正式实验优先围绕高SOC暴露开展。
   - 证据: 相对退化RMSE改善1.06%，SOH200 RMSE改善39.14%；两个响应的删除坐标系数方向均6/6稳定。
   - 处理: 采纳为smoke阶段首选解释模型。
5. `ridge_Jhigh70`证据仍弱。
   - 影响: 不能把70%解释为已验证临界SOC。
   - 证据: 相对退化改善仅1.06%，各折所选`lambda`在0.01—100间变化。
   - 处理: 后续保留50%、60%、`H`和最近坐标敏感性，不直接报告选择后显著性。
6. 完整模型C暂不值得推进。
   - 影响: 避免在6个设计点上估计过多方差参数。
   - 证据: 同结构队列`H`层次代理曲线RMSE 0.007773，无应力基线0.008019，只改善约3.1%；残差一阶相关约0.92。
   - 处理: 触发简化护栏，暂退回策略均值单应力模型。

## 已采纳

- 采纳“T0在非基准策略中无解释变异”的修正。
- 采纳模型C不稳定时退回单应力策略均值模型的护栏。
- 保持`H`为人为SOC位置矩的表述，不称为机理方程。

## 未采纳

- 未采纳“等T0后SOH差异只能来自SOC区间”的强因果表述，因为实际充电时间、结构/批次、温度和内阻没有同时固定。
- 未将最近坐标法作为论文解释主模型，因为它不能给出参数影响方向。
- 未把70%阈值写成物理临界点，因为它是候选比较后得到且相对退化改善很小。

## 验证情况

- `tests/test_q2_smoke.py`通过。
- 12项CSV均列入`result/q2/result_manifest.csv`。
- 主选择标记和最佳预测基准标记各恰好1项。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\scalar_model_comparison.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\hierarchical_model_comparison.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\coefficient_stability.csv`
- Tool: `functions.shell_command`，读取CSV、汇总系数符号与诊断，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
