# 处理后数据

运行 `scripts/q1/run_a_data_cleaning.m` 后，正式清洗结果写入`q1_cleaned/`：

- `q1_cleaned/battery_summary_clean.csv`：保留摘要字段，并增加C1缺失、前5循环基线和基线异常标记。
- `q1_cleaned/cycle_train_clean.csv`：原始字段统一使用`_raw`后缀，清洗字段使用`_clean`或`_trend`后缀。

清洗动作和质量统计位于`outputs/summary/q1_cleaning/`。官方原始CSV仍保存在`data/raw/`，清洗程序不会覆盖它们。

