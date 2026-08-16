# 第二问论文材料

本目录以预测T80为循环寿命主响应；SOH200、相对损失和末段衰减率材料保留为辅助稳健性证据。

- `第二问完整回答.md`：按题目五个小问组织的正式回答。
- `figures/fig_q2_t80_parameter_evidence.png`：J与T80点关系、候选模型LOCO改善及2000次全流水线bootstrap区间。
- `tables/lifetime_family_selection_summary.csv`：三种冻结T80模型族下的参数模型点选择、J改善率和斜率；不含跨族置信区间。
- `tables/lifetime_family_policy_t80_summary.csv`、`lifetime_family_strategy_design.csv`和`lifetime_family_model_comparison.csv`：三族策略T80及完整LOCO审计表。
- 数值依据：`../03_formal_validation/lifetime_*.csv`。
- Q1电池级寿命依据：`../../q1/paper/battery_lifetime_estimates.csv`。

确认性边界：正式bootstrap区间条件于已选局部线性T80族；跨族结果只是三组冻结点敏感性，不是联合置信区间。策略非随机、样本异方差且只有6个明确新结构参数点；排列尾部比例不是确认性p值，删除3.7C–5.9C策略后常数模型胜出。
