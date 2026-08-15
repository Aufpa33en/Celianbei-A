# 2026-08-15 第四问Smoke Test

## 修改目标

- 在不改动Q1—Q3数据、程序和权威结果的前提下，验证第四问候选优化模型是否可运行、可识别并满足外推边界。

## 修改内容

1. 新增`src/q4_models/core.py`：策略时间/退化聚合、离散Pareto、策略内整块bootstrap和单`J`岭响应面坐标留出压力测试。
2. 新增`scripts/q4/run_q4_smoke.py`：运行M0、M1、单目标基线，写入临时目录后原子发布。
3. 新增`tests/test_q4_smoke.py`和`result/q4/README.md`。
4. 输出当前权威smoke目录`result/q4/01_smoke_test_v2/`；旧`01_smoke_test/`保留为首次字段契约排错快照，不作为当前结果。

## 关键结果

- M0离散Pareto点估计保留3个策略，主模型通过。
- M1单J岭坐标LOSO压力测试RMSE=0.015827，平均比常数基线差0.006806，按停止规则不作为连续优化模型。
- 2000次策略内整块bootstrap完成；Pareto进入频率最高为`5_3C_54PER_4C_NEWSTRUCTURE` 0.883和`3_6C-80PER_3_6C` 0.739。
- 最短时间边界10.042734分钟；最低退化边界0.000428。
- smoke耗时2.263秒。

## 验证情况

- `.venv/Scripts/python.exe -m compileall -q src/q4_models scripts/q4 tests/test_q4_smoke.py`：通过。
- `.venv/Scripts/python.exe scripts/q4/run_q4_smoke.py`：通过。
- `.venv/Scripts/python.exe tests/test_q4_smoke.py`：通过。
- smoke完整性检查6/6通过；使用40块完整电池，9块测试电池未进入聚合。
- 运行中发现并修正`chargetime_raw`字段契约；修正后重新运行通过。

## 未处理事项

- 未运行Q4全量bootstrap、完整M1敏感性网格和最终策略推荐，原因是阶段硬门要求先停止并等待用户放行。
- 未把Q3 `C_ridge`用于新策略反事实优化，原因是缺少新策略早期轨迹且Q2不支持独立参数因果效应。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/docs/q4_literature_and_model_derivation.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/docs/q4_model_direction_and_boundary.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/reports/q4_pre_full_validation_report.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/result/q4/01_smoke_test_v2/`
- Tool: `functions.exec`，命令`python scripts/q4/run_q4_smoke.py`、`python tests/test_q4_smoke.py`、`python -m compileall`，cwd `C:/Users/Aupassen/Desktop/Celianbei Math Modeling`
