# 2026-08-13 A题文献方法适用性评审

## 检查范围

- 初筛的9篇电池退化、寿命预测和快充优化论文。
- 补充的Geslin等人2023年特征选择与泄漏分析论文。
- A题现有循环级变量、策略重复数、训练测试截断和寿命观测边界。

## 检查依据

- 方法所需输入是否存在于A题CSV。
- 论文目标变量是否能由A题数据直接验证。
- 方法是否处理电池内重复测量与策略内个体差异。
- 模型复杂度是否与49块电池、9种策略的样本规模匹配。

## 发现

1. 原始数据论文与A题同源，但其关键特征不能复现。
   - 影响：不能把原论文9.1%寿命预测误差或电压曲线特征移植到本题。
   - 证据：Severson论文使用循环10与100的放电电压—容量差分曲线；A题CSV没有电压曲线。
   - 处理：采纳早期特征和Elastic Net思想，重新基于SOH、内阻、温度及充电时间构造特征。
2. 混合效应与层次贝叶斯结构适配A题层次。
   - 影响：模型可以区分策略总体效应、电池个体差异和循环噪声。
   - 证据：A题每种策略3至8块电池，每块电池150或200次重复测量；Saxena、Jiang和Zhou分别使用混合效应或层次贝叶斯处理同类差异。
   - 处理：纳入首轮方法比较，不提前决定频率学或贝叶斯版本。
3. 高斯过程适合问题3的短区间概率预测。
   - 影响：可预测151至200循环并评价区间覆盖率。
   - 证据：Richardson比较复合核、退化均值函数和多输出高斯过程；Liu将工况协变量写入核函数。
   - 处理：纳入首轮比较，限制多输出共享范围，并禁止把短区间覆盖率解释成80%寿命验证。
4. 快充闭环优化无法原样实施。
   - 影响：A题不能通过新实验更新代理模型。
   - 证据：Attia方法需要分轮测试算法选出的新协议；A题只有固定的9种策略。
   - 处理：保留概率代理和不确定性思想，暂不采用闭环采样流程。
5. 特征泄漏需要单独设计验证。
   - 影响：随机混合不同策略可能夸大模型对单块电池的预测能力。
   - 证据：Geslin等人表明，编码充电条件的特征可能主要学习协议差异，无法代表同协议电池差异预测能力。
   - 处理：后续至少报告同策略留一电池和留一策略两类测试。

## 已采纳

- 将混合效应/层次贝叶斯、高斯过程和Elastic Net列为首轮方法来源。
- 将Keil和Schuster论文用于交互项、非线性与外推风险的理论说明。
- 增补Geslin等人的论文，并把特征泄漏检查写入后续验证要求。
- 在`docs/literature_detailed_assessment_A.md`中形成逐篇梗概和适用性分级。

## 未采纳

- 未采纳基于完整电压—容量曲线的原始特征，原因是题目没有相应输入。
- 未采纳完整寿命监督模型，原因是没有80% SOH标签。
- 未采纳闭环贝叶斯优化，原因是无法追加实验。
- 未采纳Arrhenius×DOD组合核，原因是A题没有DOD变量，`Q1`也不等同于DOD。
- 未采纳自由拐点模型作为当前主模型，原因是数据只覆盖早期约0.95以上SOH。

## 验证情况

- 已核对10篇文献的题名、DOI、数据类型、主要方法和验证目标。
- 对Severson、Jiang、Richardson和Geslin读取了作者公开全文；其余论文依据出版社全文页面、摘要和方法摘录完成本轮适用性判断。
- 本轮没有实现或运行模型，因此没有产生模型精度结果。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\literature_review_A.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\model_validation_plan.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\data\processed\q1_cleaned\cycle_train_clean.csv`
- Source: <https://doi.org/10.1038/s41560-019-0356-8>
- Source: <https://doi.org/10.1038/s41586-020-1994-5>
- Source: <https://doi.org/10.1016/j.joule.2021.10.010>
- Source: <https://doi.org/10.1016/j.est.2016.02.005>
- Source: <https://doi.org/10.1016/j.est.2015.05.003>
- Source: <https://doi.org/10.1016/j.ijepes.2018.12.016>
- Source: <https://doi.org/10.1016/j.jpowsour.2017.05.004>
- Source: <https://doi.org/10.1109/TTE.2019.2944802>
- Source: <https://doi.org/10.1016/j.ifacol.2023.10.708>
- Source: <https://doi.org/10.1016/j.joule.2023.07.021>
- Tool: `web.run`，检索、打开和定位论文方法及结论。
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`

