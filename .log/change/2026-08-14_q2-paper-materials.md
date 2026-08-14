# 第二问论文材料整理

- 日期：2026-08-14
- 类型：结果文档与目录说明变更
- 范围：第二问阶段完善

## 变更目的

把已完成的第一问策略比较、第二问 smoke test 和正式验证结果整理为可直接用于论文的第二问完整回答，同时保持数据、实验程序和原始 CSV 不变，避免继续增加零散结果文件。

## 新增与修改

### 新增

- `result/q2/04_paper_materials/README.md`
  - 说明本目录只存论文文字；
  - 列出输入、模型、结论层级和权威证据位置。
- `result/q2/04_paper_materials/第二问完整回答.md`
  - 按题目五个小问给出完整回答；
  - 补充函数型岭回归、分段倍率函数、`T0`、`J`、`H`和`Jhigh`的数学定义；
  - 区分策略差异显著性与参数独立效应显著性；
  - 写入 bootstrap、精确置换、删除敏感性和局限性；
  - 加入既有文献入口。

### 修改

- `result/q2/README.md`
  - 增加`04_paper_materials/`目录说明和完整回答入口。

## 未修改内容

- 未修改`data/`下任何原始或清洗数据；
- 未修改`scripts/q2/`、`src/q2_models/`和`tests/`下任何程序；
- 未重跑实验，未覆盖`00_design/`至`03_formal_validation/`内任何 CSV；
- 未删除或重命名既有文件。

## 关键模型决策

1. 第一问函数型岭回归继续用于回答不同策略的曲线和 SOH200 差异。
2. 第二问参数层不强行选择`Jhigh70`或其他单一阈值模型。
3. 原因是四候选选择校正后的精确置换检验为`p=0.06528`，未达到 0.05；删除 3.7C–5.9C 极端策略后常数模型胜出。
4. 最终保留“高 SOC 倍率暴露方向一致但阈值和独立效应不可稳定识别”的描述性结论。

## 依据与工具

- 工作流：`math-modeling-stage-workflow`，用于按阶段收口和建立证据链；
- 写作：`math-modeling-paper-writer`，用于区分模型、实验结果、机制解释和适用边界；
- 日志：`project-logbook`，用于记录事实变更、核查与阶段复盘；
- 编辑工具：`apply_patch`；
- 只读核查：PowerShell `Import-Csv`、`Get-Content`、`Test-Path`和`git status --short`；
- 数值来源：
  - `result/q1/00_overview/Q1四小问文字回答.md`；
  - `result/q2/03_formal_validation/bootstrap_selection_frequency.csv`；
  - `result/q2/03_formal_validation/permutation_test_summary.csv`；
  - `result/q2/03_formal_validation/sensitivity_model_comparison.csv`；
  - `result/q2/03_formal_validation/formal_model_decision.csv`；
  - `docs/q2_literature_screening_and_model_derivation.md`。
