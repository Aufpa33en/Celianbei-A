# 2026-08-15 Q1 T80权威结果接入

## 范围

将电池级T80协议接入问题1正式流水线，生成可供问题1、问题2和论文引用的权威CSV。本次不替换原SOH200文字结论，避免计算与叙述在同一提交中混改。

## 新增结果

- `battery_lifetime_estimates.csv`：49块电池统一由前150循环估计的T80。
- `lifetime_window_validation_*.csv`：40块完整电池的151至200循环截断回测。
- `lifetime_window_sensitivity.csv`：30、40、50、60、80循环窗口敏感性。
- `strategy_lifetime_summary.csv`：按策略汇总的电池T80中位数、四分位数和2000次bootstrap区间。
- `strategy_lifetime_rank_stability.csv`：按策略T80中位数得到的排名概率。
- `pairwise_strategy_lifetime_comparison.csv`：电池级T80精确置换检验及36组Holm校正。

## 主要结果

- 40循环窗口被截断回测选中。
- 策略T80中位数前三位为3.6C基准、4.8C新结构、5C-67%-4C新结构；后三位为80%-3.6C、旧结构4.8C、3.7C-31%-5.9C新结构。
- 36组寿命两两检验经Holm校正后仍为0组显著；该结论说明样本分辨率有限，不表示策略寿命等价。

## 验证

```text
python -X utf8 scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
python -X utf8 tests/test_q1_models.py
```

正式运行确认实验数据和运行中的既有程序均未改变。
