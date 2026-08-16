# 第一问权威结果

`result/q1/` 是第一问当前唯一权威结果目录。

- `paper/`：论文入口；保存报告、核心汇总表和300 dpi图片。
- `raw/`：审计入口；保存完整推断表、逐电池/逐循环结果、参数、运行环境和清单。
- `00_overview/`—`05_integrity_audit/`：上一轮Excel查看包，仅作辅助浏览；若与 `paper/` 或 `raw/` 冲突，以后两者为准。
- `original_q1_csv_archive.zip`：上一轮CSV归档，仅用于历史审计。

## 输入、模型与结论边界

- 输入：`data/processed/q1_cleaned/cycle_train_clean.csv`和`battery_summary_clean.csv`；响应变量为`SOH_clean`。
- 队列：49块电池统一使用前150循环估计T80；其中40块完整电池的151—200循环只用于选择末段窗口和验证近端预测。
- 寿命主模型：40循环局部线性趋势与SOH=0.8的交点；SOH曲线模型和SOH150/200为辅助分析。
- 不确定性：2000次策略内整块电池bootstrap用于局部线性族条件下的策略T80中位数区间和排名稳定性；三种单调外推族的点包络单列模型形式敏感性，不称置信区间；双侧精确置换按36组策略对作Holm校正。

正式运行：`python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`；也可用当前系统虚拟环境中的Python替换`python`。
当前附件没有观测到80% SOH终点，所有T80均为早期SOH趋势外推；151—200回测只验证近端趋势预测，不能替代真实寿命终点验证。
