# 2026-08-13 第12循环异常用途与建模边界复核

## 复核问题

- 第12循环是否可能是实验中有特殊作用的诊断循环。
- 对该循环直接进行局部修复是否会删除有意义的物理信息。
- 异常记录在后续数学模型中应当如何使用。

## 数据证据

1. 电池1第12循环容量为`1.5390544 Ah`，相对第11、13循环均值`1.07430415 Ah`高`43.2606%`。
2. 电池2、3第12循环容量相对相邻均值仅高`0.3174%`和`0.2921%`，但内阻均精确等于`0`；相邻循环内阻均值分别为`0.0168692075`和`0.0166834345`。
3. 三条异常均位于`dataset_id=1`、策略`3_6C-80PER_3_6C`的三个重复样本，并集中在同一个第12循环，但异常字段不同。
4. 其余电池第12循环未出现同类型的容量突增或零内阻。除电池1外，第12循环容量相对相邻均值的最大偏差仅为`0.3174%`。

## 外部协议证据

- 原始研究说明循环级数据包含放电容量、充电容量、内阻、温度和充电时间，内阻由循环中的脉冲测试获得；论文和作者公开代码没有把第12循环定义为一个独立的诊断或校准阶段。
- 作者公开代码读取经过`errorcorrect`处理的数据文件，并对采集问题和高测量噪声样本进行排除，说明原始实验数据确实存在需要质量控制的测量异常。
- 原研究存在暂停、恢复实验后容量变化等真实实验事件，但当前三个异常同时集中在第12循环，且分别表现为单点容量极端值和零内阻，更符合数据污染或题目设置的数据清洗考点，而不是统一的电化学过程。

## 判断

没有证据支持“第12循环是有特殊物理作用的循环”。从跨电池一致性和字段表现看，三条记录更可能是出题人有意保留或注入的数据质量异常。该结论属于基于数据结构和公开协议的推断，不能表述为已知的出题人主观意图。

局部修复是合理的，但不应称为一般性的“正常化”。本项目采用可审计的最小修复：电池1容量用第11、13循环线性插值，随后重算SOH；电池2、3的零内阻按物理无效值处理并用相邻循环插值。其他第12循环记录不修改。

## 异常记录的可用方式

- 作为数据质量控制案例，说明异常识别规则具有针对性。
- 作为模型鲁棒性与敏感性试验：比较原始数据、清洗数据以及删除异常循环三种输入下的结论。
- 作为观测可靠性标记，用于残差诊断或样本权重分析。
- 不作为电池健康或寿命的预测特征，防止模型学习采集故障和人为污染模式。

## 后续模型边界

- 描述退化规律和预测SOH时使用`capacity_clean`、`SOH_clean`及重新生成的稳健趋势。
- 原始字段和`flag_any_repair`只用于审计、画清洗对照图和敏感性分析。
- 交叉验证必须按电池划分；不得把同一电池的不同循环随机分到训练集和测试集。
- 第151—200循环可由40块完整电池做截断回测；80% SOH寿命只能作为带不确定性的外推结果。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `data/raw/cycle_train.csv`
- Source: `data/raw/battery_summary.csv`
- Source: `data/processed/q1_cleaned/cycle_train_clean.csv`
- Source: <https://doi.org/10.1038/s41560-019-0356-8>
- Source: <https://github.com/rdbraatz/data-driven-prediction-of-battery-cycle-life-before-capacity-degradation>
- Source: <https://github.com/rdbraatz/data-driven-prediction-of-battery-cycle-life-before-capacity-degradation/blob/master/LoadData.m>
- Tool: PowerShell按电池比较第12循环与第11、13循环的容量和内阻。

