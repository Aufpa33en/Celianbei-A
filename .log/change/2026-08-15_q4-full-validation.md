# 2026-08-15 第四问全量验证

## 修改目标

- 在不修改原始数据、Q1—Q3程序和Q4 smoke结果的前提下，完成第四问正式全量计算、结果审查和论文材料整理。

## 修改内容

1. 新增`scripts/q4/run_q4_full_validation.py`，实现5000次策略内整块电池bootstrap、11点权重扫描、四个退化约束场景、M1坐标oracle压力测试和原子发布。
2. 扩展`src/q4_models/core.py`，使bootstrap同时保存策略均值时间、退化、末段斜率、权重选择和约束选择。
3. 增加双时间口径和`T0`审计、三种标准化敏感性、SOH200/末段斜率Pareto对照及典型长短寿命策略比较。
4. 新增全量协议测试并为Q4 smoke/full测试增加独立命令行入口。
5. 首次全量结果保留为`result/q4/02_full_validation_v1/`审查快照；修正版`result/q4/02_full_validation/`为唯一权威目录。

## 涉及文件

- `src/q4_models/core.py`
- `scripts/q4/run_q4_full_validation.py`
- `tests/test_q4_full_validation.py`
- `tests/test_q4_smoke.py`
- `result/q4/02_full_validation/`
- `reports/q4_full_validation_report.md`

## 验证情况

- `.venv\Scripts\python.exe scripts\q4\run_q4_full_validation.py --bootstrap 5000`：通过，版本`q4_full_v2`，随机种子`20260815`，耗时7.705秒，生成45,000行bootstrap记录。
- `.venv\Scripts\python.exe tests\test_q4_full_validation.py`：通过。
- `.venv\Scripts\python.exe tests\test_q4_smoke.py`：通过。
- Q3模型边界、smoke输出和全量协议测试：通过。
- 12项Q4全量完整性检查全部通过；结果清单SHA256逐文件复算通过。

## 未处理事项

- 未把M1用于连续参数推荐，因为7折中6折不优于常数基线，且其误差是使用留出真值调参的oracle压力测试。
- 未把80% EOL作为优化目标，因为200循环数据没有真实EOL标签。
- 未生成Q4图片；本阶段已形成论文所需数值表、文字结论和可复现长表，图片可在论文排版阶段从权威CSV生成。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\plugins\cache\openai-primary-runtime\pdf\26.813.12317\skills\pdf\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\A题\2026年度“策联杯”数学建模精英联赛-A题.pdf`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-15_q4-smoke-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q4_literature_and_model_derivation.md`
- Tool: `functions.exec`，PowerShell与`.venv\Scripts\python.exe`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
