# 2026-08-14 第二问论文筛选与模型推导

## 修改目标

- 按“先检查数据可识别性，再筛论文、建模型、独立核查”的顺序完成第二问建模准备。

## 修改内容

1. 新增`docs/q2_literature_screening_and_model_derivation.md`。
2. 筛选混合效应、层次贝叶斯、充电协议、SOC依赖和快充优化文献，区分可借鉴结构与不可迁移结论。
3. 建立三类模型：离散策略函数模型、策略级参数岭基线、三层约束退化混合效应模型。
4. 推导理想充电时间、阶段暴露、欧姆热代理、SOC位置矩和固定高SOC阈值暴露。
5. 建立7折留一唯一坐标与8折留一策略标签两套验证，规定嵌套调参与停止规则。
6. 根据三路子agent核查修正策略伪重复、随机效应积分、相对SOH约束、验证泄漏和效应量解释。
7. 更新`result/q2/README.md`，记录当前阶段和权威模型入口。

## 验证情况

- 方程编号1—22连续且无重复。
- 设计边界明确为8个完整策略标签、7个唯一参数坐标。
- 已逐条核对三路审查意见并记录接受/限条件接受结论。
- 当前只完成理论建模与审查，未运行第二问正式实验，也未生成数值结论。

## 未处理事项

- 编写并运行第二问Python程序。
- 输出模型比较、坐标分组验证、参数稳定性和辅助响应CSV。
- 根据停止规则选择正式主模型并完成第二问文字答案。

## 依据与工具

- Skill: `math-modeling-stage-workflow`
- Skill: `project-logbook`
- Source: A题PDF、第一问清洗数据与正式结果。
- Sources: Saxena et al. (2019), Jiang et al. (2021), Keil and Jossen (2016), Zhang et al. (2006), Anseán et al. (2016), Attia et al. (2020), Severson et al. (2019).
- Tool: Web检索核对原始论文页面。
- Agents: `check_mixed_stress`, `check_optimization`, `check_prediction`。
