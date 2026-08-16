# 2026-08-16 论文审查问题修正

## 修改目标

- 修正 Claude 论文审查发现的 Q1、Q3、Q4 科学口径和旧版数值问题。
- 保留 T80 为早期 SOH 趋势外推情景、Q2 非因果、Q4 离散策略边界等限制。

## 修改内容

1. Q1 将电池级 T80 设为寿命主口径，补充按 T80 排序的策略表及 bootstrap 区间，并把 SOH200/前 200 循环损失降为辅助指标。
2. Q1 更新残差一阶相关为 0.645，统一长短寿命策略与权威 T80 结果。
3. Q3 补全 9 块测试电池表，补入电池 5、10、11、14、24、16、25 的情景 T80；区分 L=150 排名和多长度综合排名。
4. Q4 将 4.8C 新结构行更新为 v4 权威值 11.160 min、0.001622，并修正最快策略并列组的时间描述。
5. 建议项中“0.015827”“约 2% 并列”等旧数值/表述已同步修正；仅未改动与当前论文边界一致的可选文风项。

## 涉及文件

- `E:/AIworkspace/math_models/Celianbei-A-main/paper/main.tex`
- `E:/AIworkspace/math_models/Celianbei-A-main/.log/change/2026-08-16_paper-audit-fixes.md`

## 验证情况

- `git diff --check`：通过。
- 已核对 `paper/main.tex` 不再出现 Q4 旧值 11.039、0.001436、Q4 旧并列描述；Q3 表已列 9 条电池数据。
- LaTeX 完整编译：未运行，本次只完成论文正文与数据口径修正，待提交前单独编译检查。

## 未处理事项

- T80 仍是基于早期 SOH 趋势的外推情景，不是实际观测寿命；该边界保留。
- Claude 的宽范围写入任务和随后仅写日志的收尾任务因证据读取不收敛被取消；已保留其已完成的论文修改，本日志由主代理补写。
- 未执行 git commit/push；提交前仍需人工或自动 LaTeX 编译确认表格排版。

## 依据与工具

- Skill: `C:/Users/Firefly/.claude/skills/humanizer/SKILL.md`
- Skill: `C:/Users/Firefly/.claude/skills/claude-dispatch/SKILL.md`
- Source: `E:/AIworkspace/math_models/Celianbei-A-main/result/q1/00_overview/Q1四小问文字回答.md`
- Source: `E:/AIworkspace/math_models/Celianbei-A-main/result/q1/paper/report.md`
- Source: `E:/AIworkspace/math_models/Celianbei-A-main/result/q4/02_full_validation/policy_summary.csv`
- Tool: `claude_worker`，工作目录 `E:/AIworkspace/math_models/Celianbei-A-main`
- Tool: `functions.exec_command`，command `git diff --check`，cwd `E:/AIworkspace/math_models/Celianbei-A-main`
