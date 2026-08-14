# 00 结论与数据范围

## 使用的模型

本文件夹不重新拟合模型，而是汇总三模型比较后选出的主模型 `functional_ridge` 及第一问的统一分析设置。

## 输入

- 清洗后的循环数据与电池摘要。
- 49 块电池的完整样本标记，其中 40 块进入周期 200 推断，9 块留给第三问。
- 三模型验证和主模型正式推断产生的结论表。

## 输出

工作簿 `q1_overview.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `Conclusions` | `q1_conclusions.csv` | 可直接用于论文的结论与限制 |
| `Settings` | `analysis_settings.csv` | 随机种子、自助次数、主模型和样本口径 |
| `Cohort` | `analysis_cohort.csv` | 每块电池是否进入第一问正式推断 |
| `Coverage` | `data_coverage.csv` | 每种策略的电池数、完整/截断样本数和 SOH 范围 |
| `OldManifest` | `result_manifest.csv` | 整理前 29 个非清单 CSV 的行列数和字节数 |

建议先阅读 `Conclusions`，再用 `Settings`、`Cohort` 和 `Coverage` 核对结论边界。

`Q1四小问文字回答.md` 将上述结果整理为对应原题四项任务的中文回答，可作为论文第一问结果分析部分的初稿。
