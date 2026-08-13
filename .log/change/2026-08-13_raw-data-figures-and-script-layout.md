# 2026-08-13 原始数据论文图与程序目录重构

## 修改目标

- 将原始SOH总览图改为可用于论文和数据清洗论证的清晰图件。
- 定位0—20循环区间的尖峰来源，并在不清洗原数据的前提下单独诊断。
- 按A题四问及绘图用途整理程序目录。

## 修改内容

1. 将原绘图入口迁移至`scripts/visualization/plot_raw_figure1.m`。
2. 建立`scripts/q1/`、`scripts/q2/`、`scripts/q3/`、`scripts/q4/`和`scripts/visualization/`。
3. 将问题1预备流水线迁移至`scripts/q1/run_a_data_pipeline.m`，修正项目根目录解析。
4. 生成原始异常诊断图：单独展示电池1第12循环，并联动容量、SOH、SOH_smooth、内阻、平均温度和充电时间。
5. 生成正常尺度SOH图：仅为展示分离电池1，其余48块电池按9种充电策略分面，每条曲线带电池编号，问题3测试电池使用虚线。
6. 新增`docs/raw_data_observation.md`，说明原始变量关系、异常证据和后续待审核事项。
7. 移除旧的低辨识度`fig01_raw_soh_curves.png/.fig`，避免论文误用。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\visualization\plot_raw_figure1.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q1\run_a_data_pipeline.m`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q1\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q2\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q3\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\q4\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\scripts\visualization\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01a_battery1_cycle12_anomaly.png`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01a_battery1_cycle12_anomaly.fig`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01b_normal_soh_by_policy.png`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\figures\raw_data\fig01b_normal_soh_by_policy.fig`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\raw_data_observation.md`

## 验证情况

- MATLAB读取`battery_summary.csv`的49行与`cycle_train.csv`的9350行，未进行删除、替换、插值、截断或二次平滑。
- 最大SOH定位为电池1第12循环，`SOH=1.4374427`、`capacity=1.5390544 Ah`；容量相对邻近四点中位数高43.2%。
- 同循环`IR=0.018950272`为全表最大值，`Tavg=30.282579`同步下降，`chargetime=13.341273`未同量级跳变。
- 两张300 dpi PNG均完成原始分辨率视觉检查，无标题、图例、坐标或曲线裁切问题。
- MATLAB矢量PDF导出对9面板高密度曲线耗时过长，最终正式输出采用300 dpi PNG和可编辑FIG；旧PDF移至本地`figures/archive/`且不纳入版本控制。

## 未处理事项

- 尚未执行正式数据清洗。电池1第12循环仅列为异常候选，不代表已经决定删除。
- 电池41整体低SOH基线、两条`IR=0`记录以及策略`80PER_3_6C`缺失`C1`仍需在清洗规则设计阶段处理。
- 本次修改尚未提交或推送，等待后续确认。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\plugins\cache\openai-primary-runtime\pdf\26.812.11052\skills\pdf\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\battery_summary.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\raw\cycle_train.csv`
- Tool: `functions.exec`调用`shell_command`，运行Python原始数据审计和MATLAB批处理，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `view_image`，检查两张300 dpi PNG及PDF渲染中间图。

