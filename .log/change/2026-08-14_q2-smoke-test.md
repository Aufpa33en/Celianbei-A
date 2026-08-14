# 2026-08-14 第二问模型smoke test

## 修改目标

- 复算等`T0`设计并比较第二问的简化参数模型与模型C层次代理。
- 保存全部候选程序、逐折预测、诊断和模型选择依据。

## 修改内容

1. 新增`src/q2_models/`，按`core.py`、`experiments.py`、`outputs.py`拆分数值逻辑、实验和输出。
2. 新增入口`scripts/q2/run_q2_smoke_test.py`和轻量完整性测试`tests/test_q2_smoke.py`。
3. 建立10个策略级候选：常数、最近坐标、原始三参数、阶段暴露、`J`、`H`、`J+H`和三个高SOC阈值暴露。
4. 建立无应力层次基线及4个模型C线性化代理；保留策略、电池、循环层次，但不冒充正式指数链接+AR(1)似然。
5. 设置三种队列：全部8策略、7个非基准等`T0`策略、6个明确`NEWSTRUCTURE`策略。参数外推均按唯一坐标成组留出。
6. 输出12个CSV及`result_manifest.csv`，并为三个结果子目录编写README。
7. 更新第二问理论文档：`corr(T0,J)`由单个3.6C基准点撑起，主队列排除`T0`是因为无可用变异，而非机制共线。

## 涉及文件

- `src/q2_models/__init__.py`
- `src/q2_models/core.py`
- `src/q2_models/experiments.py`
- `src/q2_models/outputs.py`
- `scripts/q2/run_q2_smoke_test.py`
- `tests/test_q2_smoke.py`
- `environment/requirements-q2.txt`
- `result/q2/`
- `docs/q2_literature_screening_and_model_derivation.md`

## 验证情况

- 运行命令：`python scripts/q2/run_q2_smoke_test.py`，固定种子常量`20260814`，最终完整运行约146.9 s。
- 运行命令：`python tests/test_q2_smoke.py`，输出`Q2 smoke tests passed`。
- 运行`py_compile`检查5个Python文件，通过。
- 运行`git diff --check`，无空白错误。
- 输入仍为40块、每块200循环的第一问完整电池队列；Git状态未显示`data/processed/q1_cleaned/`发生修改。

## 未处理事项

- 未运行完整指数链接、策略层积分和AR(1)模型C；smoke代理残差一阶相关约0.92，正式实现成本高且当前改进有限。
- 未进行正式参数自助显著性检验。阈值70%是比较多个候选后选出，后续检验必须处理选择后偏差。
- 未完成第二问五个小问的最终文字答案。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q2_literature_screening_and_model_derivation.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\processed\q1_cleaned\cycle_train_clean.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\processed\q1_cleaned\battery_summary_clean.csv`
- Tool: `functions.shell_command`，运行Python入口、测试、编译和Git检查，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
