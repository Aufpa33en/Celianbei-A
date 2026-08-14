# 2026-08-14 第三问模型完整正确性审查

## 检查范围

- `docs/q3_literature_and_model_derivation.md`
- `src/q3_models/`（`config.py`、`core.py`、`features.py`、`experiments.py`、`outputs.py` 与 `models/` 全部）
- `scripts/q3/run_q3_smoke.py`、`scripts/q3/README.md`
- `result/q3/01_smoke_test/` 全部 7 个权威文件
- `.log/review/2026-08-14_q3-model-hard-gate-review.md`、`.log/change/2026-08-14_q3-smoke-test.md`

## 检查依据

- 按整块电池划分训练/验证；所有内层调参、预处理、PCA 和超参数选择必须嵌套，且只在内层训练折（剔除目标电池）上进行。
- 所有动态特征只能使用 `cycle<=L` 前缀；未来目标以 `relative_at(L)` 为锚，不得读取被遮蔽的 151—200 答案。
- 相对 SOH 必须换算绝对 80% 阈值（`h_i=0.8/b_i`）。
- 模型 B 的 γ 估计必须无量纲；模型 C 的中心化岭回归必须无截距且折内标准化。
- 综合分数权重 0.15/0.25/0.60、2% 并列规则、raw/projected 口径、EOL 边界与冻结随机种子必须与推导文档一致。

## 发现

1. 模型 D 的并列权重 tie-break 与推导 §11 相悖，方向写反。
   - 影响: 冻结协议内部矛盾。若触发会选出与文档相反的结果。
   - 证据: 推导 §11（第 266 行）冻结「模型 D 取更靠近 0 或 1 的权重，等距时取 w=1 以偏向更简单的模型 B」；而 `experiments.py:73` 的 `tied.sort(key=lambda w: (-abs(w - 0.5), -w))` 实际偏好最接近 0.5 的均衡权重，与文档完全相反。正确写法应为 `key=lambda w: (min(w, 1-w), -w)`。
   - 处理: 不改动本次 smoke 结论（`atol=1e-12` 下浮点几乎不可能触发）；建议修正排序键使其与冻结协议一致。

2. 模型 B 的末端窗口 `min(20, L)` 是硬编码魔数，未冻结也未在文档说明。
   - 影响: 该窗口直接参与 γ 估计，是实际调参旋钮，却既不在 `config.py` 也不在推导冻结清单里。
   - 证据: `models/strategy_transfer.py:56` 写死 `window = min(20, L)`；推导 §7 只说「末端窗口」，§11 未冻结该值；且与 P1 的 `min(50, L)`（`models/baselines.py:20`）口径不一致。
   - 处理: 建议将该 20 并入冻结配置并说明取值理由，或在推导文档补一句窗口冻结说明。

3. P1 的「线性 EOL」从未被真正计算，实际给的是「幂律套在延长线上」的 T80。
   - 影响: 结果名不副实；文档 §5 与代码语义不一致。
   - 证据: 推导 §5 说 P1「远期线性 EOL 只作附加敏感性结果」；但 `experiments.py:89-93` 里 P1 的 `direct_fit=None`，走「真实 1—150 ＋ P1 线性 151—200 拼接后再拟合约束幂律」路径，而非线性外推 T80。
   - 处理: EOL 不参与排序、无实质影响；建议在报告中注明该口径，或补一个真正线性外推的 P1 EOL 作敏感性。

4. 模型 A 的 raw 与 projected EOL 使用了不同的估计量。
   - 影响: 两套 T80 出自不同数据，口径不统一。
   - 证据: A 的 raw EOL 用自身幂律（1—150 拟合，`direct_fits["A_power"]`）；projected EOL 却显式传 `None` 走拼接重拟路径（`experiments.py:234-237`）。
   - 处理: 仅情景性、不影响排序；建议在报告里注明，或让 projected 也复用 A 的 native 幂律。

5. smoke 排名里 D 的优势脆弱且高度依赖 L=50，L=150 主口径下 B 全面占优。
   - 影响: 综合冠军掩盖了「分窗口赢家」差异；D 的胜出靠 2% 并列 + 最差电池分，不靠 L=150 主口径。
   - 证据: L=150 下 B 的 `strategy_equal_rmse=0.000660` 同时优于 D(0.000748)、C(0.000803)、P1(0.000693)；且 L=150 时 `w_strategy=0.2`（几乎全 C），OOF 选出的权重在 9 块留出电池上未泛化出「比纯 B 更好」。
   - 处理: 全量 LOBO 应按 L 分窗口报告赢家，而非只给一个综合冠军；B 很可能在 L=150 就是最终主模型。

## 已核实通过项

- 嵌套留一调参正确：`select_strategy_lambda`、`select_trajectory_hyperparameters`、`_choose_ensemble_weight` 均只在内层训练折（剔除目标电池）上选超参，D 仅复用 B/C 的 OOF 预测，无验证折信息泄漏。
- 无未来泄漏：所有动态特征先过滤 `cycle<=L`；模型 C 的未来目标矩阵以 `relative_at(L)` 为锚；模型 B 的 `_curve_for_target` 只用训练电池完整曲线且剔除目标电池本身。
- EOL 阈值正确：`h_i = 0.8/baseline` 把绝对 80% 阈值正确换算到相对 SOH 尺度（对应硬门审查第 1 条）。
- 模型 B 的 γ 公式与量纲正确：`(s_i·s_g + λ·σ²)/(s_g² + λ·σ²)`，σ 用 `1.4826·MAD` 稳健尺度，γ∈[0,3] 裁剪冻结。
- 模型 C 中心化正确：目标 Y 减 `y_mean` 后再 SVD，X 经折内标准化为零均值，无截距岭回归成立；`max_rank` 防御秩不足内层折。
- 单调投影正确：`project_absolute_prediction` 以 `y(L)` 为锚做 `cummin`，保证首个未来预测不高于末观测值；幂律 `a≥0` 裁剪保证非增。
- 排名数值全部对账无误：综合分数权重 0.15/0.25/0.60、2% 并列规则、B=0.0011875 / D=0.0011885、最差电池加权分（D 0.003870 < B 0.004784）与 `experiments.py:276-299` 一致。
- 冻结 smoke 抽样经种子校验覆盖 9 种策略；原子 CSV 写入（temp + `os.replace` + 回读校验）正确。

## 后续提升建议

1. 补预测区间：用整块电池 bootstrap（与 Q1/Q2 口径一致）对 151—200 轨迹与 T80 生成区间，或用 LOBO 残差做 split conformal 得到分布自由覆盖。
2. 补模型间误差差异显著性：用电池级配对 bootstrap 估计 RMSE(B)−RMSE(D) 的分布，把「D 比 B 好 0.02%」诚实写为「B 与 D 统计不可区分」。
3. 执行特征消融并联动 Q2：把「仅早期动态 → ＋策略参数 → ＋独热编码」的消融跑完，并把增益归因到 Q2 的应力特征（T0、J、H、J_high）。
4. 补学习曲线 RMSE(L)，量化「达到 X% 精度所需的最少早期循环数」，直接命中题目意图。
5. 把 EOL 的高度不确定当结论而非隐藏：466—2327 的 5 倍跨度本身就是「150 循环不足以可靠外推 EOL」的发现，可加多阈值（80%/85%）＋多外推形式的敏感性图。
6. 补一个轻量非参数基线（kNN 或简单 GP）以强化模型优势证据；MOGP/RNN/P2D 仍不采纳（无电压曲线、样本小）。
7. 收尾闭环：给出一块新电池「前 150 循环预测 T80」的落地结论，并指出策略参数本身是二阶效应、电池个体差异才是主导，呼应 Q2「仅描述性关联」与题目「优化」诉求。

## 验证情况

- 本次为只读审查：仅读取程序、推导文档、审查日志与 smoke 结果 CSV，未修改任何文件、未改动数据、未运行程序。
- smoke 的 `model_summary.csv`、`selection_decision.csv`、`manifest.csv` 数值均与 `experiments.py`/`outputs.py` 复算一致；`runtime.csv` 与 `selection_decision.csv` 的 `total_wall_seconds=5.968` 对账一致。

## 依据与工具

- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q3_literature_and_model_derivation.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\experiments.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\models\strategy_transfer.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\models\baselines.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q3_models\outputs.py`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\01_smoke_test\model_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\01_smoke_test\selection_decision.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\01_smoke_test\manifest.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q3-model-hard-gate-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-14_q3-smoke-test.md`
- Tool: 只读读取文件与 CSV 并逐项复算，未修改数据或运行程序，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
