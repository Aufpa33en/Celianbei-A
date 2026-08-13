# 2026-08-13 原始曲线差异复核与清洗方案评审

## 检查范围

- A题49块电池的摘要表和9350条循环记录。
- 原始异常诊断图与按9种充电策略分面的SOH曲线图。
- 同策略电池间的初始SOH、第150循环SOH、末循环SOH和下降量。
- 数据清洗候选策略及其对后续统计和预测的影响。

## 检查依据

- 题目给出的SOH定义与训练/测试截断规则。
- 原始CSV中的容量、SOH、SOH_smooth、内阻、温度和充电时间。
- 局部中位数、MAD、相对偏差和电池级初始基线诊断。
- 小样本条件：49块电池，每种策略3—8块。

## 发现

1. 九个面板分别对应九种`policy`。
   - 影响：同一面板内的曲线属于相同策略的不同电池，曲线差异同时包含个体差异、批次差异和数据质量问题。
   - 证据：`battery_summary.csv`按`policy`分组后共有9组，每组3—8块电池。
   - 处理：论文图以策略参数作为面板标题，并给每条曲线标注电池编号。
2. 多数策略的内部差异较小。
   - 影响：图中统一窄纵轴会放大千分位SOH差异，不能仅凭视觉距离判断异常。
   - 证据：5.0C/67%/4.0C策略第150循环SOH极差约0.00183；5.6C/19%/4.6C策略约0.00194。
   - 处理：保留统一纵轴以便策略间比较，同时在文字中报告数值极差。
3. `80PER_3_6C`内部差异主要来自电池4。
   - 影响：第150循环SOH极差约0.01892，远高于多数策略。
   - 证据：电池4第150循环SOH约0.97737，电池5、6约0.996。
   - 处理：暂不删除；清洗阶段检查其容量、内阻、温度和批次特征，模型中保留电池级随机效应。
4. `4_8C_80PER_4_8C_NEWSTRUCTURE`内部差异主要来自电池41。
   - 影响：电池41整条SOH曲线约比同策略其他电池低0.045，绝对SOH比较会受初始基线支配。
   - 证据：电池41首5循环SOH中位数0.95284，全体电池中位数0.99760，稳健标准分数-48.39。
   - 处理：不采用孤立点插值，也不直接删除整块电池；使用绝对SOH与基线校正退化指标双轨分析。
5. 电池1第12循环是原始数据单点异常。
   - 影响：压缩总图尺度，并污染附件`SOH_smooth`的循环10—14。
   - 证据：容量较局部中位数高43.2%，局部稳健标准分数超过1200；SOH、内阻和温度同步异常。
   - 处理：推荐在建模副本中用相邻有效循环插值容量并重新计算SOH；原始数据和原始诊断图保留该点。
6. 两条零内阻与三条`C1`缺失需要分类处理。
   - 影响：零内阻会破坏内阻趋势特征；猜补`C1`会扭曲问题2参数效应。
   - 证据：电池2、3第12循环`IR=0`；`80PER_3_6C`的三块电池`C1`均为空。
   - 处理：零内阻按缺失值局部插值；`C1`保持缺失并在连续参数模型中排除，仅保留策略类别分析。

## 已采纳

- 形成四套候选清洗策略：最小干预、稳健趋势重建、基线校正双轨分析和整电池剔除对照。
- 推荐采用最小干预、稳健趋势重建和基线校正辅助分析的组合方案。
- 明确保留原始数据、审计标记和建模清洗数据三层产物。
- 将可直接进入论文的方法段写入`docs/data_cleaning_strategy_candidates.md`，但标注需在实际清洗验证后定稿。

## 未采纳

- 暂不整块删除电池1、4或41。当前样本量小，整块删除会损失大量正常循环并削弱策略重复数。
- 暂不把电池41强行缩放到SOH=1作为唯一主数据。该操作会改变题目定义的绝对SOH，只能作为辅助敏感性分析。
- 暂不对所有SOH施加强制单调约束。早期容量激活和测量波动可能具有实验含义。
- 暂不猜测`80PER_3_6C`的`C1`。需要公开数据集策略说明或其他可靠依据。

## 验证情况

- SOH公式一致性最大残差为`5.55e-16`。
- “局部MAD标准分数>8且相对偏差>2%”在容量列仅标记电池1第12循环。
- `IR<=0`共2条，均出现在电池2、3第12循环。
- 本轮未修改任何原始或清洗数据，未运行正式清洗流水线。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\battery_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\cycle_train.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01a_battery1_cycle12_anomaly.png`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01b_normal_soh_by_policy.png`
- Tool: `functions.exec`调用`shell_command`，运行Python/Pandas诊断脚本，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`

