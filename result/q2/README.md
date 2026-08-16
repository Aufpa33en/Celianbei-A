# 第二问权威结果

## 当前主口径

循环寿命以每块电池前150循环预测的SOH=80%交点T80定义。问题2参数主分析使用`03_formal_validation/lifetime_*.csv`；早期SOH200、相对损失和末段衰减率分析保留为辅助稳健性证据，不再替代循环寿命。

## 主要结论

- 九种策略的T80中位数约1000.8—8537.6循环；36组寿命两两精确置换经Holm校正后为0组显著，不能解释为寿命等价。
- 参数效应限定在6个明确新结构策略，响应为策略内电池`log(T80)`均值。
- `linear_J`点估计LOCO RMSE较常数模型改善20.29%，全流程bootstrap入选频率77.55%。
- 条件于已选局部线性T80族，其RMSE改善bootstrap 95%区间为[-10.29%, 47.86%]，跨0；删除3.7C–5.9C极端策略后常数模型胜出。
- 幂律、加速指数冻结T80的点敏感性也选择`linear_J`且斜率为负，但三族比较没有联合置信区间。
- 最大方向统计量排列尾部比例0.1556仅为非交换性诊断，不是确认性p值。
- 因此只能报告“总倍率应力增加与预测T80缩短存在探索性关联”，不能确认C1、Q1、C2或某个SOC阈值的独立显著因果效应。

## 结果结构

- `00_design/`：原参数坐标、名义时间和暴露量设计审计。
- `01_smoke_test/`、`02_model_selection/`：原SOH200/相对损失辅助模型。
- `03_formal_validation/lifetime_*.csv`：T80主响应的留一策略验证、bootstrap、删除诊断与排列诊断。
- `03_formal_validation/正式验证结论.md`：T80主分析正式判定。
- `03_formal_validation/lifetime_family_*.csv`：三种冻结T80模型族的点敏感性，不解释为跨族置信区间。
- `04_paper_materials/第二问完整回答.md`：按五个小问组织的论文文本。
- `04_paper_materials/tables/lifetime_family_*.csv`：可直接用于论文的三族汇总表。
- `04_paper_materials/figures/fig_q2_t80_parameter_evidence.png`：T80参数效应论文图。
- `05_merged_robustness/`：末段退化率、4.8C匹配诊断及J+H失败证据，仅作辅助。

## 复现命令

```text
python -X utf8 scripts/q2/run_q2_lifetime_validation.py --bootstrap 2000 --seed 20260816
python -X utf8 tests/test_q2_lifetime_validation.py
python -X utf8 tests/test_q2_lifetime_family_sensitivity.py
```
