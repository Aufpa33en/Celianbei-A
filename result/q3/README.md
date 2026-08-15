# 第三问结果目录

## 当前阶段

第三问已完成40块完整电池嵌套LOBO全量验证、最终模型冻结、9块测试电池151—200循环预测、逐循环近似区间、T80情景敏感性和论文图。当前权威结果为`02_full_validation/`与`03_final_predictions/`。

## 目录

- `01_smoke_test/`：冻结的工程排错与估时证据，不作为最终选模结果。
- `02_full_validation/`：40块完整电池的六模型外层LOBO、嵌套模型族选择、消融和稳定性分析；正式模型比较入口。
- `03_final_predictions/`：模型冻结后对9块真实测试电池的151—200预测、近似区间、T80情景敏感性和论文图；最终论文入口。

## 关键入口

- 数学与验证协议：`docs/q3_literature_and_model_derivation.md`
- 正式程序：`scripts/q3/run_q3_full_validation.py`
- 最终报告：`reports/q3_full_validation_report.md`
- 论文图程序：`scripts/visualization/generate_q2_q3_paper_figures.py`

## 当前结论

- 最终冻结模型为`C_ridge`，固定模型L=150策略等权RMSE为0.000660；
- 包含调参与模型族选择的嵌套流程L=150策略等权RMSE为0.000709；
- 9块测试电池已生成151—200循环预测和逐循环近似区间；
- 情景T80对模型、拟合起点和预测口径敏感，不能作为已验证寿命。
