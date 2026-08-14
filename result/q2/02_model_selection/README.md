# 模型选择结果

- `scalar_model_comparison.csv`：策略等权的RMSE、MAE及相对常数模型改善率。
- `coefficient_stability.csv`：每次删除一个唯一坐标后的岭系数和训练折内所选惩罚参数。
- `hierarchical_model_comparison.csv`：模型C线性化代理的曲线RMSE和MAE。
- `hierarchical_diagnostics.csv`：各折训练误差、残差一阶相关和惩罚参数。
- `smoke_model_selection.csv`：主队列的双响应排序和选择标记。
- `selected_model_fit.csv`：当前选中解释模型在6个新结构策略上的完整拟合参数。
- `selected_model_predictions.csv`：选中模型对每个策略的拟合值和残差。

纯预测与解释模型分开选择：最近坐标法是预测基准，但不能回答参数如何影响退化；`ridge_Jhigh70`是当前解释候选。
