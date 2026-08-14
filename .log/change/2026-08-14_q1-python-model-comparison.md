# 2026-08-14 第一问Python多模型比较

## 修改目标

- 用多个可比较模型完成A题第一问的SOH策略曲线分析。
- 统一使用电池级验证选择主模型，避免用训练集拟合优度或无真实标签的80% SOH外推寿命选模型。
- 输出策略排序、长短寿命分组、充电时间关系、模型一致性和电池41敏感性材料。

## 修改内容

1. 建立三个Python候选模型。
   - `polynomial_mixed`：策略二次曲线，加电池随机截距/斜率的岭收缩近似。
   - `spline_mixed`：策略三次截断幂样条，加曲线平滑和电池随机效应收缩。
   - `functional_ridge`：逐电池岭平滑后，在策略内按电池等权汇总。
2. 为三个模型建立共同协议。
   - 固定随机种子：`20260814`。
   - 三折策略分层调参；每策略至少保留两块训练电池。
   - 选定超参数后执行49次留一电池验证。
   - 指标：电池级RMSE、MAE、偏差、最大误差、最差策略RMSE和非单调增量比例。
3. 完成模型一致性与差异检验。
   - 三模型SOH200策略排序完全一致，任意两模型Spearman系数均为1.000。
   - 模型策略曲线RMSE为0.000139—0.000323。
   - 配对电池bootstrap共5000次；样条与函数型岭的RMSE差区间跨0。
4. 选定主模型。
   - `functional_ridge`留一电池RMSE最低，为0.003549；`spline_mixed`为0.003562，二者统计上近似并列。
   - 数值选择采用`functional_ridge`；论文同时保留样条混合模型作为稳健性对照。
5. 完成第一问策略材料。
   - 基于SOH200给出策略平均曲线、排序和充电时间—SOH图。
   - 三种SOH口径下，`5C_67PER_4C_NEWSTRUCTURE`、`5_3C_54PER_4C_NEWSTRUCTURE`、`3_6C-80PER_3_6C`始终处于前四，作为稳健长寿命组；`80PER_3_6C`、`4_8C_80PER_4_8C`、`3_7C_31PER_5_9C_NEWSTRUCTURE`始终处于后三，作为稳健短寿命组。
   - 电池41会改变`4_8C_80PER_4_8C_NEWSTRUCTURE`的精确排名，因此不把组内细微名次写成稳健结论。
6. 明确寿命边界。
   - 49块电池真实达到80% SOH的数量为0。
   - 局部线性L80及策略分布只作为外推代理，不参与模型选择，不称为验证寿命。

## 涉及文件

- `src/q1_models/core.py`
- `src/q1_models/experiments.py`
- `src/q1_models/outputs.py`
- `scripts/q1/run_q1_model_comparison.py`
- `scripts/q1/models/*.py`
- `tests/test_q1_models.py`
- `environment/requirements-q1.txt`
- `outputs/raw/q1_models/`
- `outputs/summary/q1_models/`（第一问权威数值目录）
- `figures/q1_models/`
- `reports/q1_model_comparison.md`

## 验证情况

- 语法检查：Python `compileall`通过。
- 合成数据测试：三个模型均恢复预设的长—中—短策略顺序。
- 真实数据检查：9350行、49块电池、9种策略断言通过。
- 三个候选模型的独立入口均成功运行。
- 主入口成功运行并重复得到相同超参数、误差、排序和图表。
- 图像已人工检查；策略曲线图、模型误差图和充电时间—SOH图可读。
- `git diff --check`通过，仅有Windows换行提示。

## 未处理事项

- 未把80% SOH外推作为真实寿命结论，原因是没有EOL标签。
- 未进行连续策略参数效应和新策略优化；这些属于问题2和问题4。
- `.venv`依赖下载曾因网络读取超时失败；本轮使用Codex工作区已安装的Python 3.11、NumPy、pandas和Pillow完成验证。仓库已提供依赖清单，普通环境可重新安装。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill reference: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/references/stage-workflow.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Skill reference: `C:/Users/Aupassen/.codex/skills/project-logbook/references/development-change-log.md`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/data/processed/q1_cleaned/cycle_train_clean.csv`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/data/processed/q1_cleaned/battery_summary_clean.csv`
- Source: `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/docs/mathematical_models_from_literature_A.md`
- Tool: `functions.shell_command`，command `python -m compileall ...; python tests/test_q1_models.py`，cwd `C:/Users/Aupassen/Desktop/Celianbei Math Modeling`
- Tool: `functions.shell_command`，command `python scripts/q1/run_q1_model_comparison.py`，cwd `C:/Users/Aupassen/Desktop/Celianbei Math Modeling`
- Tool: `functions.view_image`，检查 `C:/Users/Aupassen/Desktop/Celianbei Math Modeling/figures/q1_models/*.png`
