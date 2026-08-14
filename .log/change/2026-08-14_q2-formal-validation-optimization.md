# 2026-08-14 第二问正式验证与性能优化

## 修改目标

- 完成2000次整块电池bootstrap、720种策略级精确置换和预设敏感性分析。
- 将原有Pandas逐折实现优化到可在本机短时间内重复运行，同时保持数值等价。

## 修改内容

1. 新增`src/q2_models/formal_validation.py`。
   - 预先计算40块完整电池的确定性退化摘要。
   - 正式重复只重采样整块电池摘要，保持电池为bootstrap单位。
   - 使用NumPy一维岭回归、预计算策略坐标分组和100次一批的并行任务。
   - 每次bootstrap重新选择岭参数和50%、60%、70%、`H`候选。
   - 对6个主策略执行全部`6!=720`种响应排列，计算选择校正方向统计量。
2. 新增`scripts/q2/run_q2_formal_validation.py`和`tests/test_q2_formal_validation.py`。
3. 新增`result/q2/03_formal_validation/`，保存8000行bootstrap候选记录、720行置换分布、敏感性分析和最终判定。
4. 将“排除3.7C极端策略仍保留高SOC家族”纳入最终稳健性门槛。
5. 更新第二问README、环境说明和smoke阶段说明，避免继续把70%阈值当成最终模型。

## 涉及文件

- `src/q2_models/formal_validation.py`
- `scripts/q2/run_q2_formal_validation.py`
- `tests/test_q2_formal_validation.py`
- `scripts/q2/README.md`
- `environment/README.md`
- `result/q2/README.md`
- `result/q2/03_formal_validation/`

## 验证情况

- 现有Pandas标量验证内部耗时12.16 s/轮；若原样执行2720次约需9 h。
- 优化版单进程20次bootstrap耗时1.23 s；8进程100次耗时3.77 s。
- 优化版与smoke版四候选RMSE最大绝对差`1.28e-16`。
- 正式命令：`python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8`。
- 正式运行总耗时81.63 s，bootstrap阶段完成2000次，结果8000行；置换分布720行。
- `python tests/test_q2_formal_validation.py`通过，包括确定性重放、合成方向信号、常量特征不可辨识边界和文件完整性。
- `py_compile`与`git diff --check`通过。

## 未处理事项

- 未拟合完整模型C；正式验证已经触发简化与不可独立识别结论，没有继续增加复杂度的依据。
- 尚未把正式结果逐项写成第二问五个小问的最终中文回答。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\02_model_selection\scalar_model_comparison.csv`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q2\03_formal_validation\`
- Tool: `functions.shell_command`，运行基准、正式验证、测试、编译和Git检查，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`。
