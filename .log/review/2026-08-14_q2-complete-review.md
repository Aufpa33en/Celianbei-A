# 2026-08-14 第二问完整成果审查

## 检查范围

- `result/q2/00_design/`
- `result/q2/01_smoke_test/`
- `result/q2/02_model_selection/`
- `result/q2/03_formal_validation/`
- `result/q2/04_paper_materials/第二问完整回答.md`
- `src/q2_models/` 与 `scripts/q2/`

## 检查依据

- 参数效应的独立单位为唯一策略坐标；共享 `(4.8,0.8,4.8)` 坐标的旧/新结构标签必须同时留出。
- bootstrap 以整块电池为抽样单位，只传播策略内电池差异，不增加设计坐标。
- 四候选高 SOC 暴露与 `H` 高度相关，显著性必须采用最大方向统计量的选择校正精确置换。
- 最终结论必须区分“策略差异显著”与“参数独立效应不显著”，且不报告选择后未校正的单阈值 `p` 值。

## 发现

1. SOH200 与 SOH 损失存在两套操作口径，且文档未作标注。
   - 影响: 同一策略在“小问 1 表格”与“小问 2—5 参数回归”中对应不同的响应值，读者对照会看到数字对不上。
   - 证据: 小问 1 表格中 3.6C 基准 SOH200=99.679%、损失=0.137%（来自 Q1 样条值 `strategy_scalar_estimates.csv` 的 0.996788/0.001370）；而 Q2 参数回归用的 `battery_degradation_summary.csv` 中同一策略 `soh200=0.995834`（99.583%）、`relative_loss200=0.001537`（0.154%），是第 1—5 循环均值做基线、第 196—200 循环均值做终点的原始均值。两套排序一致，但数值不一致。
   - 处理: 不修改结论；在文档中加一句口径说明，或统一采用 Q1 样条值作为 Q2 响应。

2. “残差一阶相关约 0.92”与正式 CSV 不符。
   - 影响: 文档数字与证据文件不一致，削弱“需处理 AR(1)”论点的精确性。
   - 证据: `hierarchical_diagnostics.csv` 中各线性模型 `lag1_residual_correlation` 实测在 0.81—0.87，二次项版降到 0.69—0.73；`模型选择说明.md` 与 `result/q2/README.md` 均写“约 0.92”。
   - 处理: 将文档中的“约 0.92”改为实测区间 0.81—0.87，或直接引用 CSV 数值。结论“仍需处理 AR(1)”不受影响。

3. 小问 3 的“影响程度”被完全回避，有条件补一个带警示的效应量区间。
   - 影响: 小问 3 明确要求“分析各因素可能的影响程度”，当前只报方向、不报任何效应量，评委可能认为该部分被回避。
   - 证据: `bootstrap_summary.csv` 已算出系数的 bootstrap 分布，且方向完全单侧——例如 Jhigh70 的 SOH200 原尺度系数中位数 -0.146，95% 区间 [-0.191, -0.045]，2000 次全为负；相对退化原尺度系数 95% 区间 [0.048, 0.163] 全为正。
   - 处理: 补充一句“条件性、未经选择校正”的效应量区间以正面回答“影响程度”，同时保留“不作为最终显著效应量”的声明。

## 已核实通过项

- 8 个参数完整策略标签对应 7 个唯一坐标；6 个 NEWSTRUCTURE 主队列 T0 范围 9.99—10.013 min。
- 2000 次 bootstrap 选择频率 37.10%/23.60%/22.90%/14.35%/2.05% 与 CSV 完全一致（742/472/458/287/41）。
- 四候选最大方向统计量选择校正精确置换 `p=0.06528`（47/720，720=6!）与 CSV 一致。
- 排除 3.7C—5.9C 极端策略后常数模型胜出；排除电池 41 后选 Jhigh60、改善约 1.54%/1.20%；均与 CSV 一致。
- `ridge_Jhigh70` 删除任一坐标后相对退化系数 6/6 为正、SOH200 系数 6/6 为负，与 `coefficient_stability.csv` 一致。
- 六条判定 criterion 的 passed/False 与 `formal_model_decision.csv` 逐行一致。
- 核心结论“do_not_claim_independent_parameter_effect; descriptive_association_only”是当前 7 个设计坐标下的正确且诚实的答案。

## 验证情况

- 本次为只读审查：仅读取程序、结论与结果 CSV，未修改任何文件、未改动数据、未运行程序。
- 所有结果 CSV 的路径、行列数在 `result/q2/03_formal_validation/result_manifest.csv` 中可对账。

## 依据与工具

- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\04_paper_materials\第二问完整回答.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\bootstrap_selection_frequency.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\permutation_test_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\sensitivity_model_comparison.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\bootstrap_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\01_smoke_test\strategy_degradation_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\coefficient_stability.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\hierarchical_diagnostics.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\00_overview\` 权威样条值（用于对照口径）
- Tool: 只读读取文件与 CSV 并逐项复算，未修改数据或运行程序，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
