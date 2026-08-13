# 2026-08-13 A题相关文献初筛

## 修改目标

- 在正式提出候选模型前，查阅与A题数据、退化建模、早期预测和快充优化相关的研究论文。
- 建立可用于论文引用的文献表，记录各方法与A题数据条件的适配边界。

## 修改内容

1. 新增`docs/literature_review_A.md`，整理9篇原始研究论文。
2. 按A题四个问题记录文献方法、可借鉴内容和数据限制。
3. 新增`reports/references/A_literature.bib`，保存论文写作可调用的BibTeX条目。
4. 暂不确定主模型。文献初筛保留早期特征回归、混合效应、层次贝叶斯、高斯过程和代理模型优化等方向。

## 关键发现

- A题数据与Severson等人的快充寿命数据体系直接相关，该论文及Attia、Jiang后续研究应作为数据背景和方法来源的核心参考。
- 原论文效果较好的早期寿命特征依赖完整放电电压—容量曲线；A题CSV只有循环级容量、SOH、内阻、温度和充电时间，因此不能声称复现原论文模型。
- A题每种策略只有3—8块电池。混合效应和层次贝叶斯研究为处理策略内电池差异提供直接依据。
- 高斯过程论文支持第151—200循环的概率预测，但不能解决A题缺少80% SOH终点数据的问题。
- 快充优化文献支持使用寿命代理模型和贝叶斯优化；A题策略数量少，后续搜索必须限制在已观测策略范围或其邻域。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\literature_review_A.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\reports\references\A_literature.bib`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\change\2026-08-13_A-literature-initial-screening.md`

## 验证情况

- 已通过出版社页面、作者机构页面、DOI页面或作者公开全文核对论文题名、年份、期刊和主要方法。
- BibTeX共包含9条文献记录。
- 本轮未复现论文实验，也未完成补充材料的逐项核对；方法性能数字只用于理解原研究，不作为A题模型性能预期。

## 未处理事项

- 尚未进行题目数据的参数覆盖、共线性和可辨识性检查。
- 尚未建立统一的候选模型评价指标表。
- 尚未决定问题1至问题4的正式主模型。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\stop-slop\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\A题\2026年度“策联杯”数学建模精英联赛-A题.pdf`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\model_validation_plan.md`
- Source: <https://doi.org/10.1038/s41560-019-0356-8>
- Source: <https://doi.org/10.1038/s41586-020-1994-5>
- Source: <https://doi.org/10.1016/j.joule.2021.10.010>
- Source: <https://doi.org/10.1016/j.est.2016.02.005>
- Source: <https://doi.org/10.1016/j.est.2015.05.003>
- Source: <https://doi.org/10.1016/j.ijepes.2018.12.016>
- Source: <https://doi.org/10.1016/j.jpowsour.2017.05.004>
- Source: <https://doi.org/10.1109/TTE.2019.2944802>
- Source: <https://doi.org/10.1016/j.ifacol.2023.10.708>
- Tool: `web.run`，检索并打开出版社与作者机构页面。
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`

