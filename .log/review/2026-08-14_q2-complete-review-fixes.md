# 2026-08-14 第二问完整成果审查意见处理

## 检查范围

- 审查意见：`.log/review/2026-08-14_q2-complete-review.md`
- 论文材料：`result/q2/04_paper_materials/第二问完整回答.md`
- 模型说明：`result/q2/02_model_selection/模型选择说明.md`
- 总目录说明：`result/q2/README.md`

## 检查依据

- Q1 样条策略结果与 Q2 原始窗口参数响应属于不同操作口径，必须显式区分；
- 残差相关数字必须与`hierarchical_diagnostics.csv`一致；
- “影响程度”可以报告条件性效应量，但必须同时说明阈值选择未校正、设计点稀少和极端策略敏感性；
- 不修改数据、程序或权威实验 CSV。

## 发现

1. 审查指出 Q1 样条估计与 Q2 窗口均值响应没有口径说明。
   - 影响：读者可能把两套数值不一致误认为计算错误。
   - 证据：3.6C 基准在 Q1 表中的 SOH200 为 99.679%，Q2 参数响应使用第 196—200 循环均值，数值为 99.583%。
   - 处理：采纳；增加两套口径的构造、用途和不可直接换算说明，不覆盖任何结果。

2. 审查指出文档中的残差一阶相关“约 0.92”与正式诊断 CSV 不一致。
   - 影响：模型 C 的残差诊断数字失真。
   - 证据：线性版本实测约 0.81—0.87，二次项版本约 0.69—0.73。
   - 处理：采纳；修改总 README 和模型选择说明。历史日志保留原样，作为当时 smoke 阶段记录，不回写旧日志。

3. 审查建议为小问 3 补充带警示的效应量区间。
   - 影响：原文字只说明方向和不显著性，未正面量化“可能的影响程度”。
   - 证据：`bootstrap_summary.csv`中`Jhigh70`原尺度相对损失系数 95% bootstrap 区间为[0.048252, 0.162620]，SOH200 系数区间为[-0.191170, -0.044719]。
   - 处理：采纳；换算为每增加 0.1 暴露单位，相对损失约增加 0.48—1.63 个百分点、SOH200 约降低 0.45—1.91 个百分点，并在同段注明它未经四候选选择校正、对 3.7C–5.9C 极端策略敏感，不是最终独立效应。

## 已采纳

- 增加 Q1 样条口径与 Q2 窗口均值口径的显式说明；
- 把残差相关从“约 0.92”改为正式 CSV 支持的区间；
- 增加`Jhigh70`条件性效应量区间及限制说明；
- 更新五问简答中的小问 3 表述。

## 未采纳

- 未采用“统一改成 Q1 样条响应”的备选建议。原因是这会改变已完成的 Q2 参数实验输入并需要整套重跑；当前只需把两套口径说明清楚即可消除歧义。
- 未修改旧 smoke 日志中的“约 0.92”。日志记录的是历史阶段状态，回写旧日志会破坏审计时间线；正确数字已在当前审查处理日志和权威结果说明中记录。

## 验证情况

- 已重新读取`bootstrap_summary.csv`和`hierarchical_diagnostics.csv`核对原始数值；
- 已按 0.1 暴露单位复算效应量区间，结果为 0.48—1.63 和 0.45—1.91 个百分点；
- 直接运行`tests/test_q2_smoke.py`，输出`Q2 smoke tests passed`；
- 直接运行`tests/test_q2_formal_validation.py`，输出`Q2 formal validation tests passed`；
- 已检查权威 Q2 Markdown，不再存在“残差一阶相关约 0.92”的旧表述；
- 系统 Python 和工作区 Python 均未安装`pytest`，因此按测试文件自带的`main()`入口直接执行，未安装依赖、未修改测试程序。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q2-complete-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\bootstrap_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\hierarchical_diagnostics.csv`
- Tool: `functions.exec`调用 PowerShell `Import-Csv`、`Select-String`和`Get-Content`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `apply_patch`，修改上述 Markdown 文档，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `C:\Users\Aupassen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests\test_q2_smoke.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `C:\Users\Aupassen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests\test_q2_formal_validation.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
