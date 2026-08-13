# 2026-08-13 问题1数据清洗执行

## 修改目标

- 执行已冻结的数据清洗逻辑。
- 输出与原始数据显式分离的清洗数据、动作审计表、质量汇总和对照图。
- 用MATLAB专项测试核对清洗范围和数据完整性。

## 修改内容

1. 新增`src/clean_a_battery_data.m`，执行主键检查、公式检查、局部容量异常识别、容量与内阻插值、SOH重算、稳健趋势生成和初始基线标记。
2. 新增`scripts/q1/run_a_data_cleaning.m`作为正式清洗入口。
3. 新增`src/plot_a_cleaning_comparison.m`，生成清洗前后对照图。
4. 新增`tests/test_q1_cleaning.m`，检查行数、原始列保留、修复数量、插值结果、SOH公式、正内阻、C1缺失、电池41保留和趋势完整性。
5. 删除早期未验证的`a_data_pipeline_config.m`、`clean_battery_data.m`、`generate_exploratory_figures.m`和`test_a_data_pipeline.m`，防止与正式清洗流程混用。

## 清洗结果

- 保留49块电池和9350条循环记录，没有删除电池或循环。
- 电池1第12循环容量由`1.5390544`修复为`1.07430415 Ah`，使用第11、13循环线性插值。
- 电池2第12循环内阻由`0`修复为`0.0168692075`。
- 电池3第12循环内阻由`0`修复为`0.0166834345`。
- 修复后内阻非正记录为0。
- 电池41保留，摘要表将其标记为唯一初始SOH基线异常电池；循环表增加`SOH_relative_clean`。
- `C1`缺失仍为3块电池，没有填补。
- 清洗表保留`capacity_raw`、`SOH_raw`、`SOH_smooth_official_raw`、`IR_raw`等原始字段；派生结果使用`capacity_clean`、`SOH_clean`、`IR_clean`、`SOH_trend_rlowess_7/11/15`和`SOH_relative_clean`。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\processed\q1_cleaned\battery_summary_clean.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\processed\q1_cleaned\cycle_train_clean.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\outputs\summary\q1_cleaning\cleaning_actions.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\outputs\summary\q1_cleaning\cleaning_quality_summary.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\cleaning\fig02_cleaning_before_after.png`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\cleaning\fig02_cleaning_before_after.fig`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\clean_a_battery_data.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\plot_a_cleaning_comparison.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q1\run_a_data_cleaning.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\tests\test_q1_cleaning.m`

## 验证情况

- MATLAB命令`run('tests/test_q1_cleaning.m')`最终输出`All Q1 cleaning tests passed.`。
- 原始容量和内阻在清洗CSV中逐值一致；原始SOH经CSV序列化后最大末位差异为`5.11e-15`，测试容差设为`1e-14`。
- 全部清洗SOH满足`SOH_clean=capacity_clean/initial_capacity`，误差阈值为`1e-12`。
- 清洗动作表恰有3行：1个容量值、2个内阻值。
- 300 dpi清洗前后对照图完成原始分辨率视觉检查，标题、图例、坐标和曲线可读。
- 首次执行因质量汇总表的变量名类型不兼容失败；将变量名改为字符向量元胞数组后解决。
- 第二次执行因柱状图类别重复失败；聚合为`capacity=1`、`IR=2`后解决。

## 未处理事项

- 尚未运行7、11、15点趋势对问题1统计结论的敏感性分析。
- 尚未建立问题3预测模型和第151—200循环分组回测。
- 80% SOH寿命仍无直接观测真值。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-13_q1-cleaning-logic-and-validation-boundary.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\battery_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\cycle_train.csv`
- Tool: `functions.exec`调用`shell_command`，运行MATLAB清洗入口与测试，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `view_image`，检查`C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\cleaning\fig02_cleaning_before_after.png`

