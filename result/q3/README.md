# 第三问结果目录

## 完成状态

第三问已经完成模型推导、三路代理审查、六模型smoke、40块完整电池嵌套LOBO全量验证、模型冻结、9块测试电池第151—200循环预测、保守逐循环点区间和T80情景敏感性。Q3不再停留于smoke阶段。

## 权威目录

- `01_smoke_test/`：六个候选模型的低成本可运行性和边界检查历史。
- `02_full_validation/`：40块完整电池的外层LOBO、嵌套选模、bootstrap、消融、调参与完整性审计。
- `03_final_predictions/`：冻结`C_ridge`后对9块测试电池的151—200循环预测、经验97.5%残差分位点区间和T80情景敏感性。

论文完整报告为`reports/q3_full_validation_report.md`，五项任务的最终入口为`03_final_predictions/q3_complete_answer.md`。

## 最终模型与结论边界

- 综合早期长度指标选择`C_ridge`，部署参数为`K=1, alpha=10`。
- 固定C候选在L=150的策略等权LOBO RMSE为0.000660；包含调参和模型族选择的嵌套流程RMSE为0.000709。
- 第2—4名P1、D、B处于2%并列容差内，名次不稳定；B在bootstrap下是主要替代模型。
- 预测区间以模型族已冻结为C为条件，不包含选族不确定性，也不是独立测试覆盖率。
- 49块电池均没有真实80% SOH终点；T80只作情景外推，不能报告为已验证寿命。

## 复现入口

```powershell
.venv\Scripts\python.exe scripts\q3\run_q3_full_validation.py --bootstrap 5000
.venv\Scripts\python.exe tests\test_q3_models.py
.venv\Scripts\python.exe tests\test_q3_smoke_outputs.py
.venv\Scripts\python.exe tests\test_q3_full_protocol.py
```

全量入口拒绝覆盖现有权威目录；若需要复算，应先使用新的隔离工作区或明确的新版本输出目录。
