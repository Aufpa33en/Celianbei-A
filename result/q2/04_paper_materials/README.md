# 第二问论文材料说明

本目录只存放由既有实验结果整理出的论文文字，不存放新的数据副本或程序副本。数值结果仍以`../03_formal_validation/`和第一问结果目录为准。

## 文件

- `第二问完整回答.md`：按照题目五个小问组织的论文级回答，包含模型、统计证据、结论边界和局限性。

## 输入与模型

- 策略寿命差异：沿用第一问函数型岭回归；bootstrap用于区间和排名，SOH200两两显著性采用整块电池精确置换与Holm校正。
- 参数与 SOC 区间分析：使用分段倍率函数、名义恒流时间`T0`、总倍率暴露`J`、SOC 加权描述量`H`和高 SOC 暴露`Jhigh50/Jhigh60/Jhigh70`。
- 参数模型验证：以唯一参数坐标为分组单位留出；使用 2000 次整块电池 bootstrap、720 种精确置换和删除敏感性分析。

## 结论层级

1. **可以确认**：九种策略的末段退化率存在全局差异（20000次Monte Carlo置换，`p=0.000050`）；但SOH200的36组两两精确检验经Holm校正后为0组显著，具体策略对只能作描述性排序。
2. **可以描述**：高 SOC 倍率暴露增加时，相对退化增大、SOH200 降低的方向一致。
3. **不能确认**：选择校正后的精确置换检验为`p=0.06528`，且删除 3.7C–5.9C 极端策略后常数模型胜出，故不能声称某个 SOC 阈值或`C1、Q1、C2`的独立因果效应已经显著。
4. **不能确认**：`J+H`对数速率模型不能通过明确新结构队列验证，其37.4% SOC换向点不进入最终结论。

## 权威证据位置

- 第一问策略结果：`../../q1/paper/report.md`
- 参数设计审计：`../00_design/design_audit.csv`
- 正式验证结论：`../03_formal_validation/正式验证结论.md`
- bootstrap 选择频率：`../03_formal_validation/bootstrap_selection_frequency.csv`
- 精确置换检验：`../03_formal_validation/permutation_test_summary.csv`
- 敏感性分析：`../03_formal_validation/sensitivity_model_comparison.csv`
- 最终模型判定：`../03_formal_validation/formal_model_decision.csv`
- 合并稳健性结果：`../05_merged_robustness/`
