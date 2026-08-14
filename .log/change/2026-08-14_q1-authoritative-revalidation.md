# 2026-08-14 第一问权威结果复算与统计修正

## 修改目标

- 在Linux环境复现第一问完整流程，并让模型、统计检验、论文表述和结果目录使用同一口径。
- 修正普通bootstrap符号概率被当作正式p值的问题。

## 修改内容

1. 建立仓库内`.venv`并安装第一问依赖；项目依赖增加Matplotlib，用于生成300 dpi论文图。
2. 保留`functional_ridge`主模型和两个比较基线，使用40块完整电池重新执行分层调参、留一电池验证和2000次策略内电池bootstrap。
3. 将策略标量两两检验改为整块电池双侧精确置换检验，随后按指标分别进行Holm校正；bootstrap只用于置信区间。
4. 建立`result/q1/paper/`和`result/q1/raw/`：前者保存论文报告、汇总表和图片，后者保存29张推断/审计表、运行环境与结果清单。
5. 更新环境说明、入口说明和旧报告状态，明确旧49电池探索结果不再是正式结论。
6. 在用户级模型经验库登记函数型岭模型的适用条件、验证结果和限制。

## 涉及文件

- `src/q1_models/inference.py`
- `src/q1_models/outputs.py`
- `scripts/q1/run_q1_final_analysis.py`
- `tests/test_q1_models.py`
- `environment/requirements-q1.txt`
- `environment/README.md`
- `scripts/q1/README.md`
- `reports/q1_model_comparison.md`
- `result/q1/`
- `/home/firefly/.codex/model_registry/model_cards/functional_ridge_battery_soh_curves.md`
- `/home/firefly/.codex/model_registry/test_rounds/2026-08-14_celianbei_q1_functional_ridge.md`

## 验证情况

- `.venv/bin/python tests/test_q1_models.py`：通过；覆盖三种模型合成数据排序、真实数据规模和精确置换检验边界。
- `.venv/bin/python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`：通过；数据和程序运行前后哈希未改变。
- 复算主模型留一电池RMSE为`0.004337846`，样条基线为`0.004341906`，差值约`0.000004060`。
- 精确置换检验加Holm校正后，SOH200、1—200损失和平均SOH均为0组显著；平均充电时间为11组显著。
- `check_result_tree.py result/q1`：通过，`paper/`共9个文件，`raw/`共31个文件。
- 结果清单逐文件大小复核通过；三张论文PNG已打开检查，无图例裁剪或坐标标签缺失。

## 已采纳与未采纳

- 已采纳：电池作为独立推断单位、精确置换检验、论文/原始结果分离、旧结果降级为历史对照。
- 未采纳：第一问升级为完整GAMM或AR(1)混合效应模型。原因是当前目标为已观测策略的前200循环描述，每策略仅2—7块完整电池；现模型与样条基线已实际近似并列。残差序列相关作为限制保留。
- 未采纳：下载公开全寿命原始数据并混入附件主分析。原因是这会改变竞赛附件口径；当前附件没有80% SOH观测，真实EOL保持为不可直接验证边界。

## 未处理事项

- 真实80% SOH寿命没有附件标签，不能在第一问验证。第三问只能进行明确标注的外推与敏感性分析。
- 每策略样本量小导致置换检验功效有限；“0组显著”不能解释为策略完全等效。
- 主模型残差平均一阶相关约`0.710`，若后续需要正式纵向参数推断，应比较显式AR(1)或似然型混合效应模型。

## 依据与工具

- Skill: `/home/firefly/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `/home/firefly/.codex/skills/model-experience-registry/SKILL.md`
- Skill: `/home/firefly/.codex/skills/paper-output-optimizer/SKILL.md`
- Skill: `/home/firefly/.codex/skills/figure-output-polish/SKILL.md`
- Skill: `/home/firefly/.codex/skills/project-logbook/SKILL.md`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/A题/2026年度“策联杯”数学建模精英联赛-A题.pdf`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/result/q1/paper/report.md`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/result/q1/raw/model_comparison.csv`
- Source: `/home/firefly/AIworkspace/math_models/Celianbei-A/.log/reflection/2026-08-14_q1-stage-closeout.md`
- Tool: `functions.exec_command`，command `.venv/bin/python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`，cwd `/home/firefly/AIworkspace/math_models/Celianbei-A`
- Tool: `functions.view_image`，检查`result/q1/paper/`三张PNG。
- Tool: `web.run`，阅读Severson、Jiang、Geslin与函数型退化分析论文的作者/机构公开全文。
