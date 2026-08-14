# 2026-08-14 第三问模型实现与smoke test

## 修改目标

- 在不运行全量测试和真实测试电池最终预测的前提下，实现第三问候选模型，完成smoke排错、计时、工程可行性检查和全量测试前阶段报告。

## 修改内容

1. 新增第三问模型包。
   - P0末值保持、P1线性趋势、A约束幂律、B同策略迁移、C降维多输出岭、D凸组合；
   - 冻结随机种子、超参数、验证折、raw/projected口径和EOL边界。
2. 新增统一smoke入口和原子输出。
   - 结果只写入`result/q3/01_smoke_test/`；
   - 固定7个权威文件，不建立按模型重复的CSV目录。
3. 新增边界、泄漏和输出完整性测试。
4. 新增全量测试前阶段报告与Q3目录README。

## 涉及文件

- `docs/q3_literature_and_model_derivation.md`
- `src/q3_models/`
- `scripts/q3/run_q3_smoke.py`
- `scripts/q3/README.md`
- `tests/test_q3_models.py`
- `tests/test_q3_smoke_outputs.py`
- `result/q3/01_smoke_test/`
- `result/q3/README.md`
- `reports/q3_pre_full_validation_report.md`
- `environment/requirements-q3.txt`

## Smoke设置

- 随机种子：20260814；
- 伪测试电池：1、35、8、17、29、48、21、15、6；
- 训练电池：其余31块完整电池；
- 早期长度：50、100、150；
- 目标：统一预测151—200；
- 主口径：raw策略等权RMSE；
- 运行时硬门：单模型三个L累计不超过120秒。

## 运行结果

| 暂定排名 | 模型 | 综合分数 | 加权最差电池RMSE | 三个L时间/s | 工程通过 |
|---:|---|---:|---:|---:|---|
| 1 | D组合 | 0.001189 | 0.003870 | 0.043 | 是 |
| 2 | B同策略迁移 | 0.001187 | 0.004784 | 0.189 | 是 |
| 3 | C多输出岭 | 0.001346 | 0.004125 | 5.605 | 是 |
| 4 | P1线性趋势 | 0.001644 | 0.004977 | 0.037 | 是 |
| 5 | A约束幂律 | 0.002329 | 0.005030 | 0.048 | 是 |
| 6 | P0末值保持 | 0.003893 | 0.012240 | 0.024 | 是 |

D与B综合分数相差小于2%，按冻结规则比较最差电池误差后D暂列第一。该结果不是最终选模证据，六个模型均须进入全量嵌套LOBO。

L=150时，B策略等权RMSE最低，为0.000660；P1为0.000693，D为0.000748。P1的池化RMSE和最差电池RMSE略低于B，说明不同聚合口径尚未给出唯一胜者。

## 运行时间与优化

- smoke总墙钟时间约8秒；
- 最耗时部分为C模型的内层PCA与多输出岭；
- 已缓存前缀特征、每折只做一次SVD、复用矩阵和B/C OOF预测；
- 预计全量40电池、全部六模型嵌套LOBO约2—5分钟。

## EOL结果边界

- 仅L=150生成情景`T80`；
- 不同模型有限结果约466—2327循环；
- EOL没有真实标签且对外推形式高度敏感，不参与模型排序，也不报告验证精度。

## 验证情况

- `.venv\Scripts\python.exe -m compileall -q src\q3_models scripts\q3 tests\test_q3_models.py`：通过；
- `.venv\Scripts\python.exe tests\test_q3_models.py`：通过；
- `.venv\Scripts\python.exe scripts\q3\run_q3_smoke.py`：通过；
- `.venv\Scripts\python.exe tests\test_q3_smoke_outputs.py`：通过；
- 结果文件数量、字段、9块电池、6模型、3个L和每轨迹50个未来循环均通过完整性检查。

## 未处理事项

- 未运行40块电池全量嵌套LOBO；
- 未确定最终模型；
- 未生成9块真实测试电池的151—200预测；
- 未生成正式预测区间；
- 上述内容必须等待用户确认后执行。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\docs\q3_literature_and_model_derivation.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\.log\review\2026-08-14_q3-model-hard-gate-review.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q3\01_smoke_test\`
- Tool: `apply_patch`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `.venv\Scripts\python.exe scripts\q3\run_q3_smoke.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `.venv\Scripts\python.exe tests\test_q3_models.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `.venv\Scripts\python.exe tests\test_q3_smoke_outputs.py`，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
