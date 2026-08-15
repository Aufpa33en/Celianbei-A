# 2026-08-14 第三问全量验证与最终预测结果审查

## 检查范围

- `src/q3_models/full_validation.py`、`src/q3_models/full_outputs.py`、`src/q3_models/features.py`、`src/q3_models/config.py`
- `scripts/q3/run_q3_full_validation.py`、`tests/test_q3_full_protocol.py`
- `result/q3/02_full_validation/` 权威结果（`selection_decision.csv`、`selection_bootstrap.csv`、`pairwise_selection.csv`、`deployment_freeze.csv`、`deployment_tuning.csv`、`nested_selector_summary.csv`、`c_ablation_summary.csv`）
- `result/q3/03_final_predictions/` 权威结果（`prediction_interval_calibration.csv`、`q3_complete_answer.md`）
- `reports/q3_full_validation_report.md`

## 检查依据

- 外层 40 折留一电池；折内调参（B 的 λ、C 的 K/α、D 的 w）与模型族选择必须嵌套，且只在内层训练折（剔除目标电池）上进行；9 块测试电池不得参与任何拟合、标准化、PCA、调参或区间校准。
- 误差均在还原后的绝对 SOH 上计算，raw 为唯一选模口径；策略等权 RMSE 为主指标（综合权重 0.15/0.25/0.60）。
- 部署族必须来自真正外层 LOBO 的冻结结果；族冻结后才允许用全部 40 块重选超参。
- bootstrap 必须按整块电池分层（策略内）重采样，配对分数差与完整冻结规则胜率是两个不同统计量。
- EOL 只作为「真实 1—150 ＋ 预测 151—200」拼接后的情景外推，不与真实 80% 寿命混为一谈。

## 发现

1. 报告正文「近似95%区间」与数据口径 `quantile_level=0.975` 不一致（轻微，表述层）。
   - 影响: 区间实际覆盖 97.5% 分位，比「95%」更保守（更宽），不构成错误，但「95% vs 97.5%」并非「近似」二字所能概括，读者可能低估其保守性。
   - 证据: `full_validation.py:685` 的 `order = ceil((n+1)*0.95)`，n=40 时 `order=39`、`level=39/40=0.975`；`prediction_interval_calibration.csv` 每行 `quantile_level` 均为 0.975，而 `q3_complete_answer.md` 与 `reports/q3_full_validation_report.md` 均写「近似95%区间」。
   - 处理: 该 `ceil((n+1)*0.95)` 公式是硬门审查第 4 条的既定决定（为避免 40 样本取到最大残差），应保留；建议仅把正文措辞改为「≈97.5% 分位（保守）」或在脚注说明该顺序统计量约定。

2. 第 2—4 名名次由 2% 并列容差 + 最差电池 tie-break 决定，不具备统计稳定性（表述层，易误导）。
   - 影响: 点排序表单独呈现会让人误以为 P1 稳居第二、B 稳居第四；实际三者综合分差 <0.5%，且 bootstrap 胜率与点排序方向相反。
   - 证据: P1(0.001529)/D(0.001525)/B(0.001536) 两两差异均落在 2% 容差内，`_select_from_summary` 的最终名次由 `worst[m]` 裁决；但 `selection_bootstrap.csv` 给出 B 胜率 0.231、P1 仅 0.0002、D 0.0136——B 才是重采样下 C 的真实潜在对手。
   - 处理: 建议在报告选模结论处加一句「第 2—4 名分数差在并列容差内，名次由最差电池 tie-break 决定且不稳定；bootstrap 显示策略迁移模型 B 在重采样下竞争力强于 P1/D」。

3. 预测区间是「模型选择后的固定族外层 CV 残差」区间，不是完整流程的预测区间（已披露，但性质需认清）。
   - 影响: 区间以「族已冻结为 C_ridge」为前提，不含（a）从 6 族选 C 的选择不确定性，也不含（b）全 40 块重选 (K,α) 与折内调参的差异，会系统性低估真实部署流程的不确定性。
   - 证据: `_calibration_table` 只取 `model == selected_model & L == 150` 的 `predictions_long.csv` 外层残差；报告已诚实标注「不是独立测试覆盖率」，但未点明「即使作为 CV 区间也以族已知为前提」。
   - 处理: 已披露、可接受；若论文引用该区间，建议明确其为「固定族 C_ridge 的点区间」，并把 0.000709 的嵌套选择器口径并列表述。

4. `_bootstrap_selection` 使用模块级 `CONFIG` 而非函数参数 `config`（极轻微，代码整洁）。
   - 影响: 无——`_full_config` 只改 version，`tie_relative_tolerance` 值一致；纯属不一致笔误。
   - 证据: `full_validation.py:356` 用 `CONFIG.tie_relative_tolerance`，同函数其余处用 `SCORE_WEIGHTS`、`FULL_VERSION` 等模块常量，但外层已传入 `config`。
   - 处理: 建议统一改为传参 `config`。

5. `deployment_freeze.csv` 记录了冻结模型 C_ridge 并不使用的超参（极轻微，簿记）。
   - 影响: 读者可能疑惑「C 的部署为何带 `lambda_gamma=10`、`w_strategy=0.2`」（分别是 B、D 的超参）。
   - 证据: `deployment_freeze.csv` 含 `lambda_gamma_L150=10.0`、`w_strategy_L150=0.2`，而 C 只用 `K=1`、`alpha=10`；该行是为 `deployment_hyperparameters_frozen` 交叉核对而做的全超参快照。
   - 处理: 报告正文已只引 (K=1, α=10)，正确；建议在 CSV 旁注或报告中点明这两个字段仅供审计。

6. 「加权最差电池 RMSE」是不同电池跨 L 的加权平均，不对应任何单一电池（极轻微，度量语义）。
   - 影响: 三个 L 的最差电池可能是不同电池，故该量不是某块电池的真实最差表现；仅作为冻结 tie-break 度量可接受。
   - 证据: `_choose_family:230-232` 的 `worst = Σ SCORE_WEIGHTS[L]·worst_by_l[L][model]`，而 `worst_by_l` 各 L 独立取 `max(battery_rmse)`。
   - 处理: 若论文把它当作「最差电池 RMSE」引用，需加脚注说明其为逐 L 最差的加权平均。

## 已核实通过项

- 三处 smoke 审查发现已修复：① D 的 tie-break 改为 `min(w,1-w)`（`full_validation.py:156-158`），且 `test_q3_full_protocol.py:35-37` 用「相同预测 → weight=1.0」直接断言；③ P1 新增 `_linear_eol`（`full_validation.py:694`）得到原生线性 EOL；④ A 的 EOL 拆为「拼接幂律 18 设置 + 原生幂律」口径统一。
- 嵌套选模无泄漏：外层 40 折 → 折内 `_inner_family_oof` 在 39 块上内部 OOF 选超参与模型族 → 预测被留出电池；目标电池数据不参与任何选择。
- 部署冻结协议正确：`deployment_freeze.csv` 的 `freeze_source=outer_LOBO_selection_decision`，族冻结后才用全 40 块 OOF 定 (K=1, α=10)，最后全 40 块重拟合预测 9 块测试电池；测试电池从未进入 `complete`。
- bootstrap 分层与配对正确：策略内整块电池有放回重采样（`rng.choice(ids, size=len(ids), replace=True)`），`difference = score[C]−score[P1]` 用同一重采样配对；`probability_a_lower=0.9994` 与 `frozen_rule_winner_frequency=0.7552` 被正确区分为两个统计量。
- C 特征消融列切分正确：`prefix_numeric_features` 返回 `sampled(20)+斜率统计(5)+dynamic(9)+策略[c1,q1,c2,c1_missing,J,H,high×3](9)`，末尾恰 9 列为策略参数，`raw[:, :-9]` 精确剥离「仅动态特征」。
- D 凸组合恒等式被机器验证：`ensemble_identity` 逐电池逐循环断言 `D = w·B+(1−w)·C` 误差 <1e-12。
- 数据完整性硬约束：`validate_record_shapes` 强制 40 块 1—200 + 9 块 1—150、循环号连续唯一。
- 受保护文件哈希与完整性门：68 个数据/程序/测试/smoke 文件哈希前后不变；全量 15/15、最终 9/9 通过才发布。
- 数字交叉核对一致：C 综合分 0.001283 = 0.15·0.003324+0.25·0.001555+0.60·0.000660；C−P1 点差 −0.000245；16.0% = (0.001529−0.001283)/0.001529；冻结行与 L=150 调参行逐字段相等；嵌套选择器 L=150 raw=0.000709 与固定 C 的 0.000660 的差异被正确解释为「含选模环节的预期误差」。

## 后续提升建议

1. 预测区间换成真正校准口径：用 split conformal / 分位回归，或至少并列报告嵌套选择器残差区间（对应 0.000709），而不是只报固定 C 的点区间。
2. 把 B 的 23.1% bootstrap 胜率写成正面稳健性结论：策略迁移是参数最少、可解释性最强的替代模型，其重采样竞争力本身就是论文亮点，不必只在 bootstrap 表里罗列。
3. 消融结论再锋利一档：L=150 上 `dynamic_only(0.000645) < full(0.000660) < dynamic_plus_strategy(0.000670)`，说明连续策略特征在该窗口反而轻微有害、独热编码才拉回一点，比「策略信息提供有限补充」更有信息量。
4. EOL 表已做 18 情景 + 原生外推，可再补一行「原生幂律/线性」T80 与拼接法的偏差方向，直接回应「哪种外推更可信」。
5. 收尾闭环呼应题目优化诉求：给出新电池「前 150 循环预测 T80」的落地口径，并指出策略参数是二阶效应、电池个体差异为主导（呼应 Q2 的「仅描述性关联」结论）。

## 验证情况

- 本次为只读审查：仅读取程序、审查日志与权威结果 CSV，未修改任何文件、未改动数据、未运行程序。
- `selection_decision.csv`、`selection_bootstrap.csv`、`pairwise_selection.csv`、`deployment_freeze.csv`、`deployment_tuning.csv`、`nested_selector_summary.csv`、`c_ablation_summary.csv`、`prediction_interval_calibration.csv` 的关键数值均与 `full_validation.py`/`full_outputs.py` 逐项复算一致。
- 复核 `.log/review/2026-08-14_q3-full-validation-hard-gate.md` 第 4 条，确认 `ceil((n+1)*0.95)` 顺序统计量为既定决定，非新引入缺陷（仅正文「95%」措辞待统一）。

## 依据与工具

- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\full_validation.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\full_outputs.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\features.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\config.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q3\run_q3_full_validation.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\tests\test_q3_full_protocol.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\02_full_validation\`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\03_final_predictions\`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\q3_full_validation_report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q3-full-validation-hard-gate.md`
- Tool: 只读读取文件与 CSV 并逐项复算，未修改数据或运行程序，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
