# 2026-08-13 Git初始化、目录建立与原始曲线图1

## 修改目标

- 初始化A题建模项目的Git仓库并关联指定远程。
- 参考Paper2实验设计文档建立可复现项目目录。
- 在不清洗数据的前提下，直接绘制49块电池的原始SOH循环曲线图1。

## 修改内容

1. 在项目根目录初始化`main`分支，并设置`origin`为`git@github.com:Aufpa33en/Celianbei-A.git`。
2. 建立`configs/`、`data/raw/`、`data/processed/`、`src/`、`tests/`、`scripts/`、`outputs/raw/`、`outputs/summary/`、`figures/`、`environment/`、`docs/`、`reports/`和`.log/`目录。
3. 将A题两份官方CSV复制到`data/raw/`，未覆盖或移动`A题/`中的原文件。
4. 新增`scripts/plot_raw_figure1.m`，直接绘制`cycle_train.csv`中的`SOH`字段；未执行去重、插值、截断、异常修正或二次平滑。
5. 生成`figures/fig01_raw_soh_curves.png`和`figures/fig01_raw_soh_curves.fig`。
6. 曾启动清洗流水线，但在用户要求暂停后立即终止；检查确认未生成清洗CSV或清洗汇总结果。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\plot_raw_figure1.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\fig01_raw_soh_curves.png`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\fig01_raw_soh_curves.fig`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\battery_summary.csv`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\cycle_train.csv`

## 验证情况

- MATLAB命令`run('scripts/plot_raw_figure1.m')`执行成功，读取摘要表49行、循环表9350行。
- PNG已按原始分辨率进行视觉检查；曲线、坐标、标题、图例和150循环分界可读。
- 原始SOH中存在早期尖峰和少数偏低轨迹，图中按原值保留。
- 未运行清洗测试，原因是用户要求先观察原始数据。
- 首次内容提交`48bfb5e`已成功推送至`origin/main`。

## 未处理事项

- 数据清洗、变量质量审计、其余探索性图表和建模暂不执行，等待用户确认图1后继续。
- 暂未执行数据清洗流水线，现有清洗代码仅为后续准备，尚未验证或生成清洗结果。

## 后续修订（论文级原始数据图）

- 根据用户反馈将原单坐标系叠加图替换为两张分工明确的论文图。
- `fig01a_battery1_cycle12_anomaly`单独诊断电池1第12循环，联动容量、SOH、SOH_smooth、内阻、温度和充电时间。
- `fig01b_normal_soh_by_policy`将其余48块电池按9种策略分面展示，每条曲线标明电池编号，测试电池使用虚线。
- 两图均直接读取原始CSV；电池1只从正常尺度图中分离，并未从原始数据删除。
- 建立`scripts/q1/`至`scripts/q4/`及`scripts/visualization/`，分别存放四问入口和跨问题绘图程序。
- 新增`docs/raw_data_observation.md`，记录原始变量关系和异常候选证据。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\plugins\cache\openai-primary-runtime\documents\26.812.11052\skills\documents\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Paper2\VALID_实验设计与实施方案.docx`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\A题\2026年度“策联杯”数学建模精英联赛-A题-附件\2026年度“策联杯”数学建模精英联赛-A题-附件\battery_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\A题\2026年度“策联杯”数学建模精英联赛-A题-附件\2026年度“策联杯”数学建模精英联赛-A题-附件\cycle_train.csv`
- Tool: `functions.exec`调用`shell_command`，命令`git init -b main`、`git remote add origin ...`和MATLAB批处理，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `view_image`，检查`C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\fig01_raw_soh_curves.png`
