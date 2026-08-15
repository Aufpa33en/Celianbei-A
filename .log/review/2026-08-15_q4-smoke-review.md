# 2026-08-15 第四问 Smoke 阶段审查

## 检查范围

- `docs/q4_literature_and_model_derivation.md`、`docs/q4_model_direction_and_boundary.md`
- `src/q4_models/core.py`、`scripts/q4/run_q4_smoke.py`、`tests/test_q4_smoke.py`
- `result/q4/01_smoke_test_v2/` 权威结果（`policy_summary.csv`、`m1_coordinate_loso.csv`、`selection_decision.csv`、`model_metrics.csv`、`integrity_checks.csv`、`bootstrap_pareto.csv`、`smoke_report.md`）
- `reports/q4_pre_full_validation_report.md`
- `.log/review/2026-08-15_q4-scope-and-review-adoption.md`、`.log/change/2026-08-15_q4-smoke-test.md`

## 检查依据

- 第四问：基于前两问设计兼顾充电时间与寿命衰减的两阶段快充策略优化，策略由 `C1/Q1/C2` 描述，优先在已有实验策略范围内比较。
- 数据边界：40 块 `prediction_test=0` 完整电池用于聚合与 bootstrap；9 块仅有 1—150 循环的测试电池不得参与。
- 退化代理 `D_i=1-SOH_{i,200}/b_i`，`b_i` 为前 5 循环 `SOH_clean` 均值，全策略同一清洗口径；80% EOL 无真实标签，不作优化目标。
- M1 的训练折标准化、岭参数与拟合只来自训练坐标；相同 `(4.8,80,4.8)` 坐标共同留出；缺失 `C1` 策略不进入 M1；凸包外为外推压力测试。
- 停止规则：M1 若在至少 4/7 个留一坐标折中未优于常数基线，则停止连续优化，正式答案退回 M0。

## 发现

1. λ 网格文档与代码不一致（轻微，需放行前统一）。
   - 影响: 直接改变「每个策略在多少个 λ 下被选中」的分母与膝点分辨率；全量阶段若沿用 5 点网格会与推导 §4 的 11 点口径不符。
   - 证据: `docs/q4_literature_and_model_derivation.md` §4 写 `λ∈{0,0.1,…,1}`（11 点），而 `src/q4_models/core.py:16` 的 `LAMBDA_GRID=[0.0,0.25,0.5,0.75,1.0]`（5 点）。
   - 处理: 全量阶段改用 11 点网格，或在文档注明 smoke 使用粗网格仅为排错。

2. M1 的 λ 用留出折 oracle 选择，存在轻微选择偏差（方法学说明，非缺陷）。
   - 影响: 报告的「best RMSE」是跨 λ 取最小，偏乐观；但方向保守——「给 M1 最好机会仍输给常数」反而强化负结果。
   - 证据: `src/q4_models/core.py:152-160` 对每个 λ 直接算 test RMSE 取最小，未做折内嵌套选择。
   - 处理: 结论不变；全量阶段若把 M1 误差写进论文，标注「oracle 调参上界」。

3. n=2 策略的整块 bootstrap 极度粗糙（数据口径注意）。
   - 影响: `3_6C`/`3_7C`/`4_8C-old`/`80PER_3_6C` 均 n=2，有放回重采样只有 4 种不同组合，分布退化为「两点及其均值」；前沿上 `3_6C`(n=2，进入频率 0.739) 与 `5_3C`(n=7，频率 0.883) 的稳定性不可直接比较。
   - 证据: `policy_summary.csv` 的 `n_battery` 列；`bootstrap_pareto` 对每策略 `rng.integers(0, len(data), size=len(data))` 重采样。
   - 处理: 论文报告推荐频率时显式标注每策略样本量；n=7 的 `5_3C_54PER_4C_NEWSTRUCTURE` 才是可辩护的最稳推荐。

4. `late_slope_mean` 已计算但 smoke 无模型使用；`time_sd`/`loss_sd` 未进入推荐区间（待接续，非 bug）。
   - 影响: 推导 §3 声明的「末段退化率敏感性」与 §4 的「T/D 百分位区间」在 smoke 尚未兑现。
   - 证据: `collect_policy_observations` 计算并落盘 `late_slope_mean`、`time_sd`、`loss_sd`，但 `pareto_mask`/`choose_scalar`/`bootstrap_pareto` 只使用 `loss_mean`、`time_mean`。
   - 处理: 全量阶段接上末段退化率敏感性与时间/退化百分位区间。

5. 「n_p=3 不用正态近似」规则在现数据下空转（文档冗余）。
   - 影响: 无任何策略恰有 3 块电池（实际 n∈{2,5,6,7}），该规则永不触发。
   - 证据: `policy_summary.csv` 的 `n_battery` 取值。
   - 处理: 可删除或改述为「n≤3 不使用正态近似」。

## 已核实通过项

- Pareto 支配关系正确：9 个策略点逐对复算，前沿恰为 `3_6C-80PER_3_6C`、`4_8C_80PER_4_8C_NEWSTRUCTURE`、`5_3C_54PER_4C_NEWSTRUCTURE` 三个；`pareto_mask` 的 `1e-12` 容差无假并列。
- 退化代理口径正确：`loss=1−relative_at(200)`，`baseline` 为前 5 循环 `SOH_clean` 均值（继承 Q3 且一致），故 `loss=1−SOH200/b_i` 与推导 §3 一致，全 40 块同一 `SOH_clean` 口径。
- M1 折内标准化无泄漏：`fit_single_exposure` 的 mean/scale 只来自 train，预测用同一 train 参数标准化 test。
- 缺失 `C1` 的 `80PER_3_6C` 正确被排除出 M1；两个相同 `(4.8,80,4.8)` 坐标正确共同留出（该折 `n_test_policy=2`）；共 7 折 = 7 个唯一完整坐标。
- 停止规则正确触发：7 折中 6 折 `improvement<0`，满足「至少 4/7 未优于常数基线」→ M1 停止、M0 为最终答案，与代码/报告/`selection_decision.csv` 一致。
- 数字对账一致：M1 平均 RMSE 0.015827、相对常数改善 −0.006806、Pareto 数 3、bootstrap 18000 行、最短时间 10.042734、最低退化 0.000428，逐项复算无误。
- 数据隔离正确：`complete_batteries_only=40`，9 块测试电池未进入聚合。

## 论文亮点建议

1. 「快充几乎免费」的量化主结论：前沿上 13.4→10.0 分钟（−25% 充电时间）只换 0.04%→0.16%（+0.12% 的 200 循环退化），推荐最快且仍在前沿的 `5_3C_54PER_4C_NEWSTRUCTURE`。
2. 时间维度降维为「伪优化」：理论恒流时间 `T0=60(q/C1+(0.8−q)/C2)` 已几乎精确复现实测时间（13.33 vs 13.38；10 vs 10.04），所有 NEWSTRUCTURE 策略钉死在 ~10 分钟，真正杠杆是退化。
3. 把 M1 失败写成正面负结果：`J` 在 7 个完整坐标内近乎常数（3.84–4.04，约 5% 波动），单 `J` 响应面不可识别；`3.6C` 是唯一 `J` 离群点（2.88），LOSO 外推到它 RMSE 从常数基线 0.0075 爆炸到 0.053，直接呼应 Q2「J/H 仅描述性」。
4. 同坐标结构混杂铁证：`4_8C_80PER_4_8C`（旧）与 `4_8C_80PER_4_8C_NEWSTRUCTURE`（新）的 `(C1,Q1,C2)` 完全相同，退化却 0.0104 vs 0.00144（7 倍），证明退化不由三参数唯一决定、结构/批次主导。
5. 决策表替代单一最优：给定退化容忍度 `D_max` 的最短时间（≤0.05%→3.6C；≤0.15%→4.8C-new；≤0.17%→5.3C-new），并用 bootstrap 进入频率当「推荐稳定性」替代 p 值。

## 验证情况

- 本次为只读审查：仅读取程序、推导文档、审查日志与 smoke 结果 CSV，未修改任何文件、未改动数据、未运行程序。
- `policy_summary.csv`、`m1_coordinate_loso.csv`、`selection_decision.csv`、`model_metrics.csv`、`integrity_checks.csv` 的关键数值均与 `core.py`/`run_q4_smoke.py` 逐项复算一致；Pareto 支配关系手算与代码输出一致。
- 原题 PDF 中文字体无法干净抽取（CID 字体缺 Unicode 映射），第四问子问题原文未能逐字核验；范围审查日志已记录子代理读取原题并完成对齐，本审查以两份 Q4 设计文档的一致表述为题目依据。

## 依据与工具

- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q4_literature_and_model_derivation.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q4_model_direction_and_boundary.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q4_models\core.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\core.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q4\run_q4_smoke.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\tests\test_q4_smoke.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q4\01_smoke_test_v2\`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\q4_pre_full_validation_report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-15_q4-scope-and-review-adoption.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-15_q4-smoke-test.md`
- Tool: 只读读取文件与 CSV 并逐项复算，未修改数据或运行程序，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
