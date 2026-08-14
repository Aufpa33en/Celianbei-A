# 第一问权威结果

`result/q1/` 是第一问当前唯一权威结果目录。

- `paper/`：可直接用于论文的报告、汇总表和300 dpi图片。
- `raw/`：完整推断表、逐电池/逐循环结果、参数、运行环境和完整性审计。
- `00_overview/`—`05_integrity_audit/`：上一轮Excel查看包，仅作辅助浏览；若与 `paper/` 或 `raw/` 冲突，以后两者为准。
- `original_q1_csv_archive.zip`：上一轮CSV归档，仅用于历史审计。

## 数据保护与统一输入

- 原始归档已经逐文件进行SHA-256比对，可解压到空目录恢复旧结构。
- 循环数据：`data/processed/q1_cleaned/cycle_train_clean.csv`。
- 电池摘要：`data/processed/q1_cleaned/battery_summary_clean.csv`。
- 响应变量：`SOH_clean`。
- 正式推断使用40块完整观测至第200循环的电池；9块`prediction_test=1`电池留给第三问验证。

## 模型与旧查看包

比较模型包括二次多项式混合曲线、惩罚样条混合曲线和两阶段函数型岭平滑。函数型岭平滑是第一问主模型；正式不确定性分析采用2000次策略内整块电池bootstrap，随机种子为`20260814`。

旧Excel查看包按以下顺序浏览：`00_overview/`、`01_model_selection/`、`02_main_model_results/`、`03_strategy_comparison/`、`04_diagnostics/`、`05_integrity_audit/`。

## 复现与结论边界

正式运行：`.venv/bin/python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`。

当前附件没有观测到80% SOH终点，所有L80均为未验证外推代理；可靠结论限定于1—200循环内的健康状态差异。
