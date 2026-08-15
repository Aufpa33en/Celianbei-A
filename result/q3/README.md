# 第三问结果目录

## 完成状态

第三问已经完成模型推导、三路代理审查、六模型smoke、40块完整电池嵌套LOBO全量验证、模型冻结、9块测试电池第151—200循环预测、保守逐循环点区间、T80情景敏感性和论文图。Q3不再停留于smoke阶段。

## 权威目录

- `01_smoke_test/`：六个候选模型的工程排错与估时历史，不作为最终选模结果。
- `02_full_validation/`：40块完整电池的外层LOBO、嵌套选模、bootstrap、消融、调参与完整性审计。
- `03_final_predictions/`：冻结`P1_linear`后对9块测试电池的151—200循环预测、经验97.5%残差分位点区间、T80情景敏感性和论文图。

论文完整报告为`reports/q3_full_validation_report.md`，五项任务的最终入口为`03_final_predictions/q3_complete_answer.md`。

## 关键入口

- 数学与验证协议：`docs/q3_literature_and_model_derivation.md`
- 正式程序：`scripts/q3/run_q3_full_validation.py`
- 最终报告：`reports/q3_full_validation_report.md`
- 论文图程序：`scripts/visualization/generate_q2_q3_paper_figures.py`

## 最终模型与结论边界

- 最终任务拥有150个观测循环，因此按L=150外层LOBO冻结`P1_linear`；其策略等权RMSE为0.000617，优于C的0.000669，差异超过2%并列容差。
- 50/100/150综合指标仍由`C_ridge`领先，但只作多长度鲁棒性敏感性；嵌套选族流程L=150 RMSE为0.000701，评估的是另一条动态选族流程。
- C消融显示策略特征并非稳定增益；事后消融变体不追加进本轮六个预注册候选。
- 预测区间以模型族已冻结为P1为条件，不包含选族不确定性，也不是独立测试覆盖率。
- 49块电池均没有真实80% SOH终点；T80只作情景外推，不能报告为已验证寿命。

## 复现入口

```powershell
.venv\Scripts\python.exe scripts\q3\run_q3_full_validation.py --bootstrap 5000
.venv\Scripts\python.exe tests\test_q3_models.py
.venv\Scripts\python.exe tests\test_q3_smoke_outputs.py
.venv\Scripts\python.exe tests\test_q3_full_protocol.py
.venv\Scripts\python.exe tests\test_q2_q3_paper_figures.py
```

全量入口拒绝覆盖现有权威目录；若需要复算，应先使用新的隔离工作区或明确的新版本输出目录。
