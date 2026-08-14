# 2026-08-14 第二问正式模型判定检查

## 检查范围

- `result/q2/03_formal_validation/`
- 高SOC暴露50%、60%、70%和`H`四个候选。
- 常数模型、最近坐标基准及五组敏感性队列。

## 检查依据

- 最佳单阈值需满足：bootstrap选择频率不低于50%、双响应改善比例不低于80%、预期符号比例不低于90%、选择校正精确`p<=0.05`。
- 高SOC家族关联还需在排除3.7C极端策略后继续胜出。
- 电池bootstrap只传播组内变异，策略级证据以坐标删除和精确置换为准。

## 发现

1. 没有稳定的单一SOC阈值。
   - 影响: 不能选择70%或其他阈值作为最终临界点模型。
   - 证据: 50%、60%、70%、`H`选择频率分别为37.10%、23.60%、14.35%、22.90%。
   - 处理: 不选择单阈值最终模型。
2. 方向证据一致，但选择校正显著性不足。
   - 影响: 只能写关联方向，不能写独立显著效应。
   - 证据: 四候选bootstrap方向比例均为100%；最大方向统计量精确`p=0.06528`。
   - 处理: 报告选择校正结果，不引用单阈值未校正`p`值作为主结论。
3. 结论依赖3.7C—5.9C极端策略。
   - 影响: 参数关系无法稳定推广到其余设计区域。
   - 证据: 排除该策略后常数模型胜出。
   - 处理: 将最终结论降级为描述性关联。
4. 电池41不是唯一驱动来源。
   - 影响: 清洗后的电池41不会单独决定关联方向，但会影响最优阈值和改善程度。
   - 证据: 排除电池41后选择`Jhigh60`，两个响应仍为正改善但幅度很小。
   - 处理: 保留为敏感性结果。

## 已采纳

- 采用“高SOC倍率暴露族方向一致”的描述性结果。
- 采用选择校正精确置换和极端策略删除作为策略层证据。
- 正式判定为`do_not_claim_independent_parameter_effect; descriptive_association_only`。

## 未采纳

- 不采纳smoke阶段“选择`ridge_Jhigh70`作为最终解释模型”的结论，因为其bootstrap选择频率只有14.35%。
- 不采纳单候选未校正`p<0.05`作为显著性证据，因为阈值经过比较选择。
- 不采纳继续拟合完整模型C；当前限制来自策略设计点和极端点敏感性，不是模型复杂度不足。

## 验证情况

- 2000次bootstrap和720种排列均完整输出。
- `result_manifest.csv`记录8个正式CSV及行列数。
- 正式验证测试、编译检查和空白检查通过。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\bootstrap_selection_frequency.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\permutation_test_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\sensitivity_model_comparison.csv`
- Tool: `functions.shell_command`，读取正式CSV并执行判定测试，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
