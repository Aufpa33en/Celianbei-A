# 2026-08-14 Q1/Q2分支比较审查

## 检查范围

- 远程分支`origin/compare/remote-q1-q2-20260814`的3个提交及独立工作树`分支/`。
- 第一问模型、推断程序、权威结果、论文图和文字结论。
- 第二问正式验证、合并稳健性程序、结果与五个小问回答。
- 当前主线第三问smoke阶段对Q1/Q2结论和结果路径的依赖。

## 检查依据

- 原始数据与清洗数据不得被修改；统计单位必须是整块电池。
- bootstrap用于区间和排名稳定性，显著性检验必须有明确零假设和多重比较校正。
- 参数效应必须按唯一参数坐标验证，并区分描述关联、全局差异和独立因果效应。
- smoke、正式验证和论文权威材料必须分层保存。

## 发现

1. 分支修正了第一问显著性口径。
   - 影响: 原主线把bootstrap差值同号比例近似当作检验量，得到“16/36组显著”；分支改用电池级双侧精确置换和Holm校正，结果为0/36。
   - 证据: `src/q1_models/inference.py`、`result/q1/raw/pairwise_strategy_scalar_comparison.csv`。
   - 处理: 采纳。0/36表示小样本两两检验功效有限，不表示九策略等效。
2. 分支对第二问增加了独立的末段退化率审计。
   - 影响: 九策略全局置换给出Monte Carlo `p=0.000050`，说明至少一个策略的末段退化分布不同；该结论不能定位具体策略对，也不能替代SOH200两两检验。
   - 证据: `result/q2/05_merged_robustness/paper/global_strategy_permutation.csv`。
   - 处理: 采纳为补充证据，不替代`03_formal_validation/`。
3. `J+H`候选只在混合队列上表现较好，在6个明确新结构策略上失效。
   - 影响: 全队列坐标留出对数RMSE为0.390，对明确新结构队列为4.901，差于常数模型0.733；37.4%换向点没有稳健依据。
   - 证据: `result/q2/05_merged_robustness/paper/jh_coordinate_sensitivity.csv`。
   - 处理: 采纳分支的否决结论；保留高SOC暴露为描述框架。
4. 同一4.8C参数坐标的新旧组存在78.1%末段速率差，精确置换`p=0.0476`。
   - 影响: 旧组只有2块、新组5块，且结构与数据集批次完全混杂；该p值是当前样本划分下的边界性结果。
   - 证据: `result/q2/05_merged_robustness/paper/matched_4p8_comparison.csv`。
   - 处理: 仅写“结构/批次联合差异”，不归因于结构改进。
5. 分支的结果层级比原主线清楚，但文件总数没有真正减少。
   - 影响: `paper/`与`raw/`明确了论文入口和审计入口；旧Excel查看包仍保留，因此是“降低查找成本”而非“物理删除旧文件”。
   - 证据: `result/q1/README.md`、`result/q1/paper/`、`result/q1/raw/`。
   - 处理: 采纳分层，不删除历史结果；后续论文只引用`paper/`，审计才进入`raw/`。
6. 三张Q1图中，原分支模型比较图难以表达微小差异，权衡图的S1—S9缺少图内映射。
   - 影响: 图可以生成，但直接入论文时读者需要往返查表。
   - 证据: `result/q1/paper/fig_q1_model_comparison.png`、`fig_q1_strategy_tradeoff.png`。
   - 处理: 采纳数据与图形框架，修改标签和比较方式后重新生成。
7. Q3计算程序不依赖“16/36组显著”结论，也不读取Q1新建的`paper/raw`路径。
   - 影响: Q3不需要重做smoke；只需在后续论文叙述中继承修正后的证据边界。
   - 证据: `docs/q3_literature_and_model_derivation.md`、`src/q3_models/`。
   - 处理: 保留现有Q3阶段成果，在全量测试前先修复已记录的Q3实现审查项。

## 已采纳

- Q1精确置换检验与0/36显著结论。
- Q1 `paper/`与`raw/`权威分层。
- Q2末段退化率全局置换、4.8C匹配诊断及`J+H`失败证据。
- Q2继续以选择校正`p=0.06528`作为参数效应主结论。

## 未采纳

- 不恢复“16/36组显著”的旧结论，因为检验量不成立。
- 不把`J+H`或37.4% SOC换向点作为第二问主模型，因为同结构队列验证失败。
- 不把4.8C匹配差异归因于新结构，因为结构与批次不可分离。
- 不删除旧结果包；保留其审计价值，但降级为历史入口。

## 验证情况

- 独立分支工作树中Q1、Q2 smoke、Q2 formal、Q2 merged四套测试通过。
- 合并后上述四套测试与Q3边界/泄漏、Q3输出完整性测试均通过。
- Q1正式推断在Windows/Python 3.11重新运行；数据和已有实验程序的运行前后哈希均未改变。
- Windows与分支Linux结果的关键数值最大绝对差：模型比较`4.31e-14`、两两比较`3.01e-13`、策略标量`2.63e-08`；非数值字段一致，不改变任何结论。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\分支\result\q1\paper\report.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\分支\result\q2\04_paper_materials\第二问完整回答.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\分支\result\q2\05_merged_robustness\`
- Tool: `shell_command`，commands `git diff ...`、Q1/Q2/Q3 tests及Q1正式推断，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `view_image`，检查3张Q1论文图。
