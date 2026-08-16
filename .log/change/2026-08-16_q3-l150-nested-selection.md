# Q3 L=150专用嵌套选模验证

## 范围

- 不更换六个预注册候选，不修改冻结`P1_linear`的预测公式和最终9电池预测。
- 在既有40折外层LOBO中，新增与最终信息集一致的L=150专用选族规则。
- 新增5000次策略内整块电池配对bootstrap，区分固定候选误差与完整选模流程误差。
- 未修改`paper/main.tex`。

## 折结构与选择规则

- 每折留出1块完整电池，只在其余39块电池内部调B/C/D并比较六个模型。
- 选择指标为L=150、151—200循环raw绝对SOH的策略等权RMSE。
- 2%并列范围内按最差电池RMSE、再按冻结模型顺序破并列。
- 留出电池只评价本折已选模型，不参与调参、选族或标准化。
- bootstrap在9个策略内有放回抽取整块电池，同一次抽样对所有方法共用。

## 结果

- L=150专用嵌套选模流程策略等权RMSE：`0.000704490`。
- 固定P1候选外层LOBO策略等权RMSE：`0.000616521`。
- 40折选择次数：P1=`25`、D=`14`、C=`1`。
- 嵌套流程减固定P1的配对bootstrap RMSE差95%区间：`[0.000016682, 0.000246429]`。
- 固定候选P1在5000次重采样中的赢家频率：`81.04%`。
- 原、新六模型外层预测最大绝对差：`3.7e-14`；冻结P1最终9电池预测最大绝对差：`0`。

## 判定

- 保留`P1_linear`冻结决定；它是当前六个预注册固定候选中L=150点误差最小且重采样领先最稳定的模型。
- `0.000617`只称固定P1候选的外层LOBO误差。
- `0.000704`用于描述“先在训练集选族、再部署”的完整L=150选模流程泛化误差。
- 该验证消除了本轮最直接的赢家误差口径混淆，但不是外部独立数据验证。

## 正式运行

```text
python -X utf8 scripts/q3/run_q3_full_validation.py --bootstrap 5000 --output-root <isolated-temp-root>
python -X utf8 tests/test_q3_full_protocol.py
python -X utf8 tests/test_q3_models.py
python -X utf8 tests/test_q3_smoke_outputs.py
python -X utf8 tests/test_q2_q3_paper_figures.py
```

- 随机种子：`20260814`
- 正式墙钟时间：`825.266 s`
- 完整性检查：`20/20`通过

## 权威产物

- `result/q3/02_full_validation/l150_nested_selector_folds.csv`
- `result/q3/02_full_validation/l150_nested_selector_predictions.csv`
- `result/q3/02_full_validation/l150_nested_selector_summary.csv`
- `result/q3/02_full_validation/l150_paired_bootstrap_summary.csv`
- `result/q3/02_full_validation/l150_candidate_bootstrap_summary.csv`
