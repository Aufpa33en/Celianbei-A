# 2026-08-14 第三问模型硬门审查

## 检查范围

- `docs/q3_literature_and_model_derivation.md`
- 模型A—D、基线P0/P1、无泄漏验证、EOL外推和smoke工程方案

## 检查依据

- 按整块电池划分训练/验证；
- 所有动态特征只能使用`cycle<=L`前缀；
- 相对SOH必须换算绝对80%阈值；
- 所有预处理、PCA和超参数选择必须嵌套；
- smoke不能按9块伪测试电池误差淘汰模型；
- 结果目录、运行时间和选择口径必须冻结。

## 发现

1. 初稿把相对SOH的EOL阈值写成0.8。
   - 影响：当电池基线SOH不等于1时，`T80`数学定义错误。
   - 处理：采纳；改为`h_i=0.8/b_i`，输出乘`b_i`还原绝对SOH。
2. 初稿没有关闭L=50/100的EOL拼接数据来源。
   - 影响：若使用真实L+1—150会泄漏被遮蔽未来。
   - 处理：采纳；EOL主报告仅限L=150，L=50/100不拼接真实空档。
3. 动态均值和平滑趋势存在读取完整序列的风险。
   - 影响：伪盲测预测会使用151—200答案。
   - 处理：采纳；所有动态特征先过滤`cycle<=L`，并增加前缀不变性测试。
4. 模型B惩罚量纲不一致且零斜率尺度可能除零。
   - 影响：普通lambda会把gamma错误锁定在1或造成数值失败。
   - 处理：采纳；使用`1.4826*MAD`尺度，MAD过小时回退标准差与`1e-8`下限。
5. 模型C/D的嵌套过程和组合权重选择不完整。
   - 影响：PCA或权重可能读取验证折信息。
   - 处理：采纳；每个内层折重做填补、编码、标准化、PCA和岭回归，D仅用B/C OOF预测选权重。
6. 原smoke流程允许按9块电池误差形成短名单。
   - 影响：后续在同一40块电池做LOBO会产生选择偏差。
   - 处理：采纳；smoke只按代码、泄漏、数值和120秒门槛判断工程可行性，所有可运行模型进入全量LOBO。
7. raw/projected误差口径未冻结。
   - 影响：物理投影可能改变模型排序。
   - 处理：采纳；raw用于调参与排序，projected仅作敏感性，两个版本显式分行保存。
8. 工程审查要求固定目录、字段、计时和边界测试。
   - 影响：否则结果可能散乱或无法复现。
   - 处理：采纳；冻结7个权威输出、7个计时阶段、抽样ID和最小测试集。

## 已采纳

- 三位子agent提出的全部硬阻断项均已修订；
- 修订后，`q3_math_eol_review`、`q3_leakage_attack`和`q3_runtime_review`均明确给出PASS；
- 模型A—D总体框架保留，无需加入MOGP、RNN、LSTM或P2D高成本模型。

## 未采纳

- 未采纳“smoke中三个L均不优于基线即可按误差淘汰”的工程建议。原因是这仍会利用9块伪测试电池答案筛模型，破坏后续全量LOBO的无偏性；仅保留代码、泄漏、数值和运行时间淘汰条件。

## 验证情况

- 三路子agent复查：全部PASS；
- `tests/test_q3_models.py`：通过；
- 覆盖已知幂律、常数斜率、缺失C1、无同策略、秩不足、单调锚点和前缀不变性。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\plugins\cache\openai-primary-runtime\pdf\26.812.11052\skills\pdf\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\A题\2026年度“策联杯”数学建模精英联赛-A题.pdf`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q3_literature_and_model_derivation.md`
- Source: <https://www.nature.com/articles/s41560-019-0356-8>
- Source: <https://doi.org/10.1016/j.etran.2023.100243>
- Source: <https://doi.org/10.1016/j.energy.2023.127633>
- Source: <https://doi.org/10.3390/batteries8100134>
- Source: <https://doi.org/10.1016/j.jpowsour.2010.11.134>
- Agents: `q3_leakage_attack`、`q3_math_eol_review`、`q3_runtime_review`
- Tool: `web.run`，检索和打开原始论文页面
- Tool: `view_image`，核对赛题PDF第4页
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `.venv\Scripts\python.exe tests\test_q3_models.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
