# 2026-08-14 第三问全量验证运行前硬门检查

## 检查范围

- `src/q3_models/full_validation.py`
- `src/q3_models/full_outputs.py`
- `scripts/q3/run_q3_full_validation.py`
- 第三问40块完整电池外层LOBO、模型族冻结、9块测试电池最终预测与结果发布协议

## 检查依据

- 第三问既定硬门：模型推导审查、泄漏攻击审查、运行与结果管理审查均通过后才允许全量运行。
- 选模主口径：还原后的绝对SOH、策略等权RMSE、raw预测；2%容差内按最差电池误差与模型简洁性裁决。
- 数据边界：40块完整电池用于验证和训练；9块仅有1—150循环的测试电池不得参与调参、选模或误差估计。

## 发现

1. 内层调参原先按电池普通平均RMSE，与策略等权主指标不一致。
   - 影响：不同策略电池数为2—7块，普通平均会让样本多的策略获得更高权重，可能改变B、C、D超参数和模型排名。
   - 证据：三位子代理对smoke实现和全量方案的独立只读审查。
   - 处理：采纳。B的λ、C的K/α、D的w均由内层OOF候选重新按策略等权RMSE选择。

2. 仅比较六模型LOBO后直接报告胜者误差会遗漏模型族选择偏差。
   - 影响：同一批40块电池既选模型又报告该模型误差，结果可能偏乐观。
   - 证据：泄漏攻击审查指出需单独评估“每个外折train39内部选族”的nested selector。
   - 处理：采纳。同时保存六模型固定族外层LOBO和独立的嵌套模型族选择器外层预测；部署族由固定候选的真正外层LOBO冻结。

3. 初稿部署族又用全部40块内部OOF重新选了一次，丢弃了真正外层LOBO的冻结结果。
   - 影响：模型族冻结会再次受到同批OOF调参偏差影响，并可能与正式比较胜者不一致。
   - 证据：数学与EOL审查定位到`run_full_validation`部署冻结段。
   - 处理：采纳。部署族直接读取`selection_decision.csv`的外层LOBO胜者；全部40块内部OOF只在族冻结后确定部署超参数。

4. 初稿预测区间使用嵌套选择器残差却标记为固定部署模型区间，且95%顺序统计量偏一位。
   - 影响：校准对象与最终预测器不一致；40块样本时会错误取最大残差。
   - 证据：数学与EOL审查对`_calibration_table`的复核。
   - 处理：采纳。改用冻结模型L=150的40个真正外层LOBO残差；半径取第`ceil((n+1)*0.95)`个顺序统计量，并明确为外层CV残差近似区间。

5. bootstrap胜出频率未复现冻结规则。
   - 影响：最小分数频率不能代表“2%容差—最差电池—简洁性”的实际稳定性。
   - 证据：数学与EOL审查。
   - 处理：采纳。每次策略分层整块电池重采样后同时计算加权策略等权分数和加权最差电池误差，再执行冻结规则。

6. 初稿一键入口先发布全量目录再计算最终预测，后半段失败会使重跑被拒绝；结果完整性检查也缺少组级唯一性。
   - 影响：运行不可恢复；重复循环或错分配行可能仅靠总行数检查而漏过。
   - 证据：运行与结果管理审查。
   - 处理：采纳。先在内存完成两阶段计算和完整性预检，再发布；增加`--resume-final`；对6000、450和2700行结果逐电池、模型、L检查50个唯一151—200循环和冻结ID集合；发布02后哈希复核。

7. 正式运行耗时记录不完整。
   - 影响：无法说明最耗时环节和优化效果。
   - 证据：运行与结果管理审查。
   - 处理：采纳。记录加载、外层嵌套拟合、预测、bootstrap、C特征消融、部署调参、最终拟合预测与EOL、写出和总计算时间。

## 已采纳

- 策略等权的折内调参目标。
- 六模型固定族比较与嵌套模型族选择器双重验证。
- 外层LOBO冻结部署族、冻结后再定超参数。
- 固定族外层残差区间与正确有限样本顺序统计量。
- 完整冻结规则的分层整块电池bootstrap。
- 双阶段预检、断点恢复、02目录哈希保护和组级完整性检查。
- 分阶段运行时间落盘。

## 未采纳

- 未增加RNN、LSTM、MOGP或嵌套bootstrap。现有40块完整电池不足以稳定支持更高容量模型，且这些方法不会修复当前识别出的验证边界问题。
- 未修改既有smoke程序和结果。smoke作为已冻结阶段证据保留，新协议采用新增正式模块实现。

## 验证情况

- `.venv/Scripts/python.exe -m compileall -q src/q3_models scripts/q3 tests/test_q3_full_protocol.py`：通过。
- `.venv/Scripts/python.exe tests/test_q3_models.py`：通过。
- `.venv/Scripts/python.exe tests/test_q3_smoke_outputs.py`：通过。
- `.venv/Scripts/python.exe tests/test_q3_full_protocol.py`：通过。
- `git diff --check`：通过，仅有Git对两个README行尾转换的提示。
- 三位审查代理对修订稿完成最终只读复核，数学与EOL、数据泄漏、运行与结果管理三项均为PASS。
- 权威目录`result/q3/02_full_validation`、`result/q3/03_final_predictions`及对应临时目录均不存在，允许正式运行。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Source: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/references/stage-workflow.md`
- Source: `C:/Users/Aupassen/.codex/skills/project-logbook/references/development-review-log.md`
- Tool: 三位子代理只读复核；PowerShell测试命令；`apply_patch`
