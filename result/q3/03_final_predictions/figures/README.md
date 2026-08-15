# 第三问论文图

本目录是第三问最终预测阶段的论文图权威位置。图件读取冻结的`q3_full_v1`结果和第一问清洗数据，不重新调参或选模。

- `fig_q3_early_length_rmse.png`：六个候选模型在L=50、100、150时的外层LOBO策略等权RMSE；突出最终冻结的`C_ridge`。
- `fig_q3_test_predictions.png`：九块测试电池前150循环清洗SOH、151–200循环raw/单调投影预测及逐循环近似区间。
- `fig_q3_t80_sensitivity.png`：冻结`C_ridge`在不同拟合起点和预测口径下的有限T80情景范围与默认情景。

预测区间是固定模型外层CV残差校准得到的逐循环近似区间，不是整条轨迹的联合95%区间；T80没有真实阈值标签，只能解释为敏感性情景。

复现命令：

```powershell
python scripts/visualization/generate_q2_q3_paper_figures.py
```
