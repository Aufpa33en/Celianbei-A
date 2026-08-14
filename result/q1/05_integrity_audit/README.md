# 05 完整性审计

## 使用的模型

本文件夹不使用统计模型，记录第一问正式分析运行前后的文件完整性检查。

## 输入

- `A题/`、`data/raw/`、`data/processed/q1_cleaned/` 中的受保护数据文件。
- 第一问已有 Python 实验程序和正式推断入口。
- 每个文件运行前的 SHA-256 与字节数。

## 得到的结果

正式计算结束后重新计算 SHA-256 与字节数，并与运行前比较。受保护数据和程序在正式分析运行期间全部保持一致。

工作簿 `integrity_audit.xlsx`：

| 工作表 | 原 CSV | 内容 |
|---|---|---|
| `DataIntegrity` | `data_integrity_check.csv` | 9 个数据/题目文件的运行前后哈希和大小 |
| `ProgramIntegrity` | `program_integrity_check.csv` | 10 个第一问程序文件的运行前后哈希和大小 |

这里证明的是“正式分析运行期间未修改”。整理结果目录本身不会改动上述输入数据与程序。
