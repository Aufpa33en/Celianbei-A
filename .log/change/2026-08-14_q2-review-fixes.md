# 2026-08-14 第二问审查修订

## 修改目标

- 根据完整成果审查修正第二问的响应口径说明、残差相关数字和影响程度回答，同时保持数据、程序及权威实验结果不变。

## 修改内容

1. 补充响应口径说明。
   - 区分 Q1 样条 SOH200 与 Q2 第 1—5/196—200 循环窗口均值响应。
2. 修正模型 C 残差诊断。
   - 线性版本残差一阶相关改为 0.81—0.87；补充二次项版本 0.69—0.73。
3. 补充条件性效应量。
   - 固定`Jhigh70`时，每增加 0.1 暴露单位，相对 SOH 损失约增加 0.48—1.63 个百分点，SOH200 约降低 0.45—1.91 个百分点。
   - 明确该区间未经模型选择校正、对极端策略敏感，不能作为最终独立效应。

## 涉及文件

- `result/q2/04_paper_materials/第二问完整回答.md`
- `result/q2/02_model_selection/模型选择说明.md`
- `result/q2/README.md`
- `.log/review/2026-08-14_q2-complete-review-fixes.md`

## 验证情况

- 已核对`bootstrap_summary.csv`和`hierarchical_diagnostics.csv`；
- 未修改或重跑数据与实验程序；
- `tests/test_q2_smoke.py`直接执行通过；
- `tests/test_q2_formal_validation.py`直接执行通过；
- 已复算论文中的 0.1 暴露单位效应量换算，并确认权威 Markdown 已移除错误的 0.92 残差相关表述；
- 当前环境未安装`pytest`，测试文件自带`main()`入口，故直接运行测试文件且未改变依赖。

## 未处理事项

- 未统一两套响应口径，原因是统一会改变现有参数实验输入并要求重新验证；论文中已明确二者用途和差异。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q2-complete-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\bootstrap_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\hierarchical_diagnostics.csv`
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: 工作区 Python 直接运行`tests/test_q2_smoke.py`和`tests/test_q2_formal_validation.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
