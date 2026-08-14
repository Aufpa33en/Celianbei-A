# 2026-08-14 Q1/Q2远程合并与结论校正

## 修改目标

- 合并远程第二问正式验证与本地第一问校正、第二问末段退化率分析，形成单一权威论文口径并保留可复现证据。

## 修改内容

1. 校正第一问显著性文字。
   - bootstrap继续用于置信区间与排名稳定性。
   - SOH200两两显著性以整块电池双侧精确置换和Holm校正为准，36组中0组显著。
2. 保留远程第二问正式参数主线。
   - 主队列为6个明确新结构策略，按唯一参数坐标留出。
   - 高SOC暴露四候选的选择校正精确置换`p=0.06528`，不声明独立显著参数效应。
3. 新增`05_merged_robustness/`。
   - 九策略末段对数退化率全局置换`p=0.000050`。
   - 同一4.8C坐标中新结构组末段速率低78.1%，精确置换`p=0.0476`，但结构与批次完全混杂。
   - `J+H`模型在全部坐标上有改善，但在6个明确新结构策略中对数RMSE为4.901，差于常数模型0.733，因此否决其主模型地位和37.4% SOC换向阈值。
4. 更新Q2权威说明、复现命令、综合manifest和回归测试。

## 涉及文件

- `result/q1/00_overview/Q1四小问文字回答.md`
- `result/q2/04_paper_materials/第二问完整回答.md`
- `result/q2/05_merged_robustness/`
- `src/q2_models/merged_robustness.py`
- `scripts/q2/run_q2_merged_robustness.py`
- `tests/test_q2_merged_robustness.py`
- `tests/test_q2_smoke.py`

## 验证情况

- `.venv/bin/python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8`：复现选择频率、`p=0.06528`和描述性关联决策；Linux末位浮点差异未纳入提交。
- `.venv/bin/python scripts/q2/run_q2_merged_robustness.py --permutations 20000 --seed 20260814`：通过。
- Q1、Q2 smoke、Q2 formal、Q2 merged四套测试：通过。
- Python `py_compile`、`git diff --check`：通过。
- `check_result_tree.py result/q2/05_merged_robustness`：通过。

## 取舍记录

- 采纳：远程唯一坐标留出、阈值族选择校正、极端策略/电池41敏感性。
- 采纳：本地末段退化率全局检验和4.8C匹配诊断。
- 拒绝：远程“16组SOH200两两显著”旧结论，因为其把bootstrap同号比例当作检验量。
- 拒绝：本地`J+H`作为主模型及37.4%阈值，因为同结构队列验证失败。

## 未处理事项

- 没有恢复或删除`stash@{0}`；其中保存合并前的本地Q2完整快照，待推送确认后再决定是否清理。
- 没有声称真实80% SOH寿命、结构因果效应或独立`C1/Q1/C2`效应。

## 依据与工具

- Skill: `/home/firefly/.codex/plugins/cache/openai-curated-remote/github/0.1.8-2841cf9749ae/skills/yeet/SKILL.md`
- Skill: `/home/firefly/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `/home/firefly/.codex/skills/model-experience-registry/SKILL.md`
- Skill: `/home/firefly/.codex/skills/paper-output-optimizer/SKILL.md`
- Skill: `/home/firefly/.codex/skills/project-logbook/SKILL.md`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/result/q1/paper/report.md`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/result/q2/03_formal_validation/`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/result/q2/05_merged_robustness/`
- Source: `/home/firefly/.codex/model_registry/model_cards/positive_log_jh_battery_degradation.md`
- Tool: `functions.exec_command`，command `git pull --rebase origin main`，cwd `/home/firefly/AIworkspace/math_models/Celianbei-A`
- Tool: `functions.exec_command`，command `.venv/bin/python scripts/q2/run_q2_merged_robustness.py --permutations 20000 --seed 20260814`，cwd `/home/firefly/AIworkspace/math_models/Celianbei-A`
