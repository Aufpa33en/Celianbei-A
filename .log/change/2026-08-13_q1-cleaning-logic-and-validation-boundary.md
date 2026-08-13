# 2026-08-13 问题1清洗逻辑与模型验证边界

## 修改目标

- 在运行清洗程序前冻结清洗规则、阈值、处理动作和理由。
- 记录问题3可验证与不可直接验证的目标，防止后续论文夸大验证范围。
- 将清洗结果与官方原始数据分目录、分字段保存。

## 修改内容

1. 冻结容量单点异常规则：同一电池当前循环相对于前后各2个循环的局部中位数，局部MAD标准分数大于8且相对偏差超过2%时标记。
   - 理由：MAD不受单个极端值主导；附加2%偏差门槛可避免局部波动很小时标准分数虚高。该规则在当前容量数据中仅识别电池1第12循环。
2. 冻结容量修复规则：孤立异常点使用前后相邻有效循环线性插值，并按摘要表初始容量重新计算SOH。
   - 理由：电池1异常前后容量连续，单点线性插值不改变长期趋势；SOH与容量存在精确公式关系，必须同步重算。
3. 冻结零内阻规则：`IR<=0`视为无效测量，转为缺失后使用相邻有效循环线性插值。
   - 理由：电池内阻应为正值；当前仅电池2、3第12循环为0，且两侧记录有效。
4. 冻结趋势重建规则：保留附件`SOH_smooth`原值供审计，模型趋势使用清洗后SOH的11点`rlowess`重新计算，并用7点和15点窗口做敏感性检验。
   - 理由：附件平滑列受到电池1尖峰污染；稳健局部回归降低孤立噪声影响且允许非线性退化。早期容量激活存在，故不强制单调。
5. 冻结电池41处理：保留电池及其绝对SOH，不修改初始容量；增加相对前5循环容量中位数的`SOH_relative_clean`。
   - 理由：电池41属于整条曲线基线偏低，不符合单点异常修复条件。双轨指标可区分初始状态和后续退化速度。
6. 冻结`C1`缺失处理：不猜补`80PER_3_6C`的三条`C1`。
   - 理由：当前附件不能证明该字段代表“不适用”还是遗漏。问题1可按策略类别保留，问题2估计`C1`连续效应时应排除未知值。
7. 冻结输出边界：`data/raw/`只读；清洗表写入`data/processed/q1_cleaned/`；审计表写入`outputs/summary/q1_cleaning/`；清洗图写入`figures/cleaning/`。
8. 记录模型验证边界：40块完整电池可用于第151—200循环截断回测；9块正式测试电池的未来真值不可见；当前数据没有80% SOH终止寿命真值。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\data_cleaning_strategy_candidates.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\model_validation_plan.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\battery_summary.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\cycle_train.csv`

## 验证情况

- 规则冻结前已核对：SOH公式最大残差`5.55e-16`；容量联合判据只标记电池1第12循环；零内阻共2条；`C1`缺失共3条；电池41初始基线稳健标准分数为-48.39。
- 本日志创建时尚未运行正式清洗程序。清洗运行结果、输出行数和测试结论将在同日执行日志中单独记录。

## 未处理事项

- 尚未确定问题3主预测模型。
- 80% SOH寿命缺少直接真值，只能做外推与不确定性分析。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\data_cleaning_strategy_candidates.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01a_battery1_cycle12_anomaly.png`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01b_normal_soh_by_policy.png`
- Tool: `functions.exec`调用`shell_command`，运行Python/Pandas审计，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`

