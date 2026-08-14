# 2026-08-14 Q1/Q2分支合并与权威结果校正

## 修改目标

- 保留当前Q3 smoke阶段成果的可恢复状态，合并Q1/Q2比较分支，并让前两问的程序、结果和论文文字使用同一统计口径。

## 修改内容

1. 在提交Q3 smoke阶段快照后，将`origin/compare/remote-q1-q2-20260814`合并到`main`。
2. 第一问采用整块电池双侧精确置换与Holm校正，替换旧bootstrap同号显著性口径。
3. 第二问加入`05_merged_robustness/`，保留全局策略差异和候选失败证据，但不替代正式参数验证。
4. 重新生成Q1权威结果与3张论文图。
   - 策略图使用可读倍率/SOC标签；
   - 模型图同时呈现绝对RMSE重叠和配对RMSE差；
   - 权衡图在图内列出R1—R9与策略的对应关系。
5. 统一Windows/Linux复现说明，并明确`paper/`为论文入口、`raw/`为审计入口。
6. 收紧第二问文字：SOH200的3.09个百分点极差是描述性跨度，不能单独替代总体或两两显著性检验。

## 涉及文件

- `src/q1_models/inference.py`
- `src/q1_models/outputs.py`
- `scripts/q1/run_q1_final_analysis.py`
- `src/q2_models/merged_robustness.py`
- `scripts/q2/run_q2_merged_robustness.py`
- `result/q1/paper/`
- `result/q1/raw/`
- `result/q2/04_paper_materials/`
- `result/q2/05_merged_robustness/`
- `environment/README.md`

## 验证情况

- `tests/test_q1_models.py`：通过。
- `tests/test_q2_smoke.py`：通过。
- `tests/test_q2_formal_validation.py`：通过。
- `tests/test_q2_merged_robustness.py`：通过。
- `tests/test_q3_models.py`与`tests/test_q3_smoke_outputs.py`：通过。
- `scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`：通过；数据与已有实验程序哈希未改变。
- 三张Q1 PNG已逐张打开检查，无中文缺字、标签截断或编号缺失。

## 未处理事项

- 未执行Q3全量LOBO，也未预测9块真实测试电池。
- Q3完整审查记录中的组合权重tie-break、模型B末端窗口和EOL口径问题尚未修正；全量测试前必须处理。
- 旧Q1 Excel查看包和归档仍保留，只降级为历史/辅助入口。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q1-q2-branch-comparison.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\paper\report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\04_paper_materials\第二问完整回答.md`
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `shell_command`，commands `git merge ...`、测试及正式推断，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `view_image`，检查Q1论文图。
