# 第一问权威结果

`result/q1/` 是第一问当前唯一权威结果目录。

- `paper/`：论文入口；保存报告、核心汇总表和300 dpi图片。
- `raw/`：审计入口；保存完整推断表、逐电池/逐循环结果、参数、运行环境和清单。
- `00_overview/`—`05_integrity_audit/`：上一轮Excel查看包，仅作辅助浏览；若与 `paper/` 或 `raw/` 冲突，以后两者为准。
- `original_q1_csv_archive.zip`：上一轮CSV归档，仅用于历史审计。

## 输入、模型与结论边界

- 输入：`data/processed/q1_cleaned/cycle_train_clean.csv`和`battery_summary_clean.csv`；响应变量为`SOH_clean`。
- 队列：40块完整电池用于正式推断；9块`prediction_test=1`电池留给第三问。
- 主模型：两阶段函数型岭平滑；2000次策略内整块电池bootstrap用于区间和排名稳定性。
- 显著性：以整块电池为单位执行双侧精确置换，并按指标作Holm校正。

正式运行：`python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`；也可用当前系统虚拟环境中的Python替换`python`。
当前附件没有观测到80% SOH终点，所有L80均为未验证外推代理；可靠结论限定于1—200循环内的健康状态差异。
