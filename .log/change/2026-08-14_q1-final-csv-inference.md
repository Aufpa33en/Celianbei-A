# 第一问正式计算与 CSV 结果归档

## 1. 变更目标

在不修改原始数据、既有清洗数据和已有第一问实验程序的前提下，完成第一问的正式计算、模型选择、策略比较、不确定性分析与结果归档。正式结果仅输出 CSV，不生成新图片，并统一存入 `result/q1/`。

## 2. 变更内容

- 新增 `src/q1_models/inference.py`，在已有三模型实验代码之上实现正式统计推断。
- 新增 `scripts/q1/run_q1_final_analysis.py`，作为第一问正式分析入口。
- 第一问周期 200 的比较仅使用 40 块具有完整 1—200 循环记录的电池；9 块 `prediction_test=1`、仅观测至第 150 循环的电池留给第三问预测检验，不用于第一问的周期 200 排序。
- 对二次多项式混合效应近似、三次样条混合效应近似、两阶段函数岭回归进行统一的分层调参与留一电池验证。
- 以留一电池 RMSE 最低的 `functional_ridge` 为主模型；对 9 种充电策略计算周期 1—200 的估计曲线、周期 200 SOH、累计损失、平均 SOH、末段斜率、平均充电时间等指标。
- 使用 2000 次“策略内整块电池”聚类自助法估计点置信区间、同时置信带、两两差异、Holm 多重比较校正和排名稳定性。
- 补充残差诊断、模型一致性、基线口径敏感性、数据覆盖度和描述性机制关联。
- 生成 30 个 CSV 文件至 `result/q1/`；该目录没有图片或其他格式文件。

## 3. 数据与程序保护

- 正式运行前后分别计算 `A题/`、`data/raw/`、`data/processed/q1_cleaned/` 中相关文件的 SHA-256 和字节数。
- 9 个受保护数据文件运行前后全部一致，证据见 `result/q1/data_integrity_check.csv`。
- 对已有第一问 Python 程序及本次正式入口计算运行前后哈希；10 个程序文件在运行过程中全部一致，证据见 `result/q1/program_integrity_check.csv`。
- 本次没有覆盖或删除既有的模型比较程序及其历史输出。

## 4. 正式结果摘要

- 三模型留一电池平均 RMSE：`functional_ridge=0.004338`、`spline_mixed=0.004342`、`polynomial_mixed=0.004394`；主模型选择为 `functional_ridge`。
- 三种模型对 9 种策略的周期 200 SOH 排名完全一致。
- 周期 200 SOH 点估计前三名为 `3_6C-80PER_3_6C`、`5C_67PER_4C_NEWSTRUCTURE`、`5_3C_54PER_4C_NEWSTRUCTURE`。
- 点估计后三名为 `4_8C_80PER_4_8C`、`80PER_3_6C`、`3_7C_31PER_5_9C_NEWSTRUCTURE`。
- 周期 200 SOH 的 36 组两两比较中，16 组经 Holm 校正后显著。
- 当前 49 块电池均未观测到 SOH=80% 的真实寿命终点，因此局部线性 L80 只能作为未验证的外推代理，不作为第一问主结论。

## 5. 验证命令

```powershell
C:\Users\Aupassen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests\test_q1_models.py
C:\Users\Aupassen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\q1\run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
```

验证结果：模型测试通过；正式分析成功生成 30 个 CSV；数据完整性检查和程序运行期完整性检查均通过。

## 6. 使用的工作流与资料

- 技能：`C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- 阶段流程：`C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\references\stage-workflow.md`
- 收尾模板：`C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\references\stage-closeout-template.md`
- 日志技能：`C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- 变更日志规范：`C:\Users\Aupassen\.codex\skills\project-logbook\references\development-change-log.md`
- 运行工具：PowerShell、项目固定 Python 运行时、pandas、NumPy、SciPy、scikit-learn、pytest。

## 7. 复现入口

正式入口为 `scripts/q1/run_q1_final_analysis.py`。权威结果目录为 `result/q1/`，文件索引为 `result/q1/result_manifest.csv`，正式参数为 `result/q1/analysis_settings.csv`。
