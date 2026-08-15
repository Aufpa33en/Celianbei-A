# A题第一问旧版模型比较报告

本文件记录早期49电池探索性比较，数值不再作为正式结论。第一问当前权威报告为
`result/q1/paper/report.md`，权威表格和完整审计数据分别位于`result/q1/paper/`与
`result/q1/raw/`。正式分析只使用40块完整观测至第200循环的电池，当前嵌套选择
流水线的外层留一电池RMSE为`0.004325`。

以下内容仅保留为历史对照。

## 三模型比较

| 模型 | RMSE | RMSE标准误 | MAE | 最差策略RMSE | 20循环后明显回升比例 |
|---|---:|---:|---:|---:|---:|
| polynomial_mixed | 0.003620 | 0.000997 | 0.003360 | 0.015274 | 0.0000 |
| spline_mixed | 0.003562 | 0.001001 | 0.003316 | 0.015265 | 0.0000 |
| functional_ridge | 0.003549 | 0.001000 | 0.003309 | 0.015271 | 0.0000 |

## 模型一致性

- `polynomial_mixed` 与 `spline_mixed`：策略曲线RMSE 0.000305，SOH200排序Spearman系数 1.000。
- `functional_ridge` 与 `polynomial_mixed`：策略曲线RMSE 0.000323，SOH200排序Spearman系数 1.000。
- `functional_ridge` 与 `spline_mixed`：策略曲线RMSE 0.000139，SOH200排序Spearman系数 1.000。

配对电池bootstrap的模型RMSE差异：

- `polynomial_mixed - spline_mixed`：均值 0.000058，95%区间 [0.000040, 0.000076]。
- `polynomial_mixed - functional_ridge`：均值 0.000071，95%区间 [0.000048, 0.000095]。
- `spline_mixed - functional_ridge`：均值 0.000013，95%区间 [-0.000010, 0.000040]。

## 主模型策略结果

| 策略 | SOH200 | 排名 | 分组 | 1—200损失 | 平均充电时间 | 局部线性L80外推 |
|---|---:|---:|---|---:|---:|---:|
| 5C_67PER_4C_NEWSTRUCTURE | 0.995336 | 1 | typical_long | 0.002618 | 10.158 | 5228.6 |
| 5_3C_54PER_4C_NEWSTRUCTURE | 0.995205 | 2 | typical_long | 0.002619 | 10.156 | 5504.9 |
| 3_6C-80PER_3_6C | 0.995070 | 3 | typical_long | 0.001665 | 13.382 | 3455.5 |
| 5_6C_36PER_4_3C_NEWSTRUCTURE | 0.994734 | 4 | middle | 0.003363 | 10.219 | 4851.3 |
| 5_6C_19PER_4_6C_NEWSTRUCTURE | 0.994118 | 5 | middle | 0.004152 | 10.248 | 4498.2 |
| 4_8C_80PER_4_8C_NEWSTRUCTURE | 0.988422 | 6 | middle | 0.002104 | 11.157 | 5589.0 |
| 80PER_3_6C | 0.983802 | 7 | typical_short | 0.014034 | 14.080 | 1696.5 |
| 4_8C_80PER_4_8C | 0.983566 | 8 | typical_short | 0.013023 | 13.103 | 1405.9 |
| 3_7C_31PER_5_9C_NEWSTRUCTURE | 0.963581 | 9 | typical_short | 0.036777 | 10.847 | 992.4 |

## 寿命分布口径

49块电池中真实达到80% SOH的数量为 0。
因此 `ProjectedL80LocalLinear` 及策略分布均只是第151循环以后局部斜率外推，不能写成观测寿命或验证寿命。

## 电池41基准敏感性

主模型分别使用原SOH、相对SOH以及剔除电池41重新拟合。完整排名见 `outputs/summary/q1_models/baseline_sensitivity_strategy_rank.csv`。
- `primary_soh_clean`：前三名为 5C_67PER_4C_NEWSTRUCTURE、5_3C_54PER_4C_NEWSTRUCTURE、3_6C-80PER_3_6C；后三名为 80PER_3_6C、4_8C_80PER_4_8C、3_7C_31PER_5_9C_NEWSTRUCTURE。
- `relative_soh`：前三名为 3_6C-80PER_3_6C、4_8C_80PER_4_8C_NEWSTRUCTURE、5_3C_54PER_4C_NEWSTRUCTURE；后三名为 4_8C_80PER_4_8C、80PER_3_6C、3_7C_31PER_5_9C_NEWSTRUCTURE。
- `exclude_battery_41`：前三名为 4_8C_80PER_4_8C_NEWSTRUCTURE、5C_67PER_4C_NEWSTRUCTURE、5_3C_54PER_4C_NEWSTRUCTURE；后三名为 80PER_3_6C、4_8C_80PER_4_8C、3_7C_31PER_5_9C_NEWSTRUCTURE。

主模型最难泛化的策略是 `4_8C_80PER_4_8C_NEWSTRUCTURE`，策略平均RMSE为 0.015271；该策略包含基准异常的电池41，因此不能把这一误差完全解释为曲线模型不足。
三种口径下，5C_67PER_4C_NEWSTRUCTURE、5_3C_54PER_4C_NEWSTRUCTURE、3_6C-80PER_3_6C始终位于前四；80PER_3_6C、4_8C_80PER_4_8C、3_7C_31PER_5_9C_NEWSTRUCTURE始终位于后三，可作为较稳健的长寿命组和短寿命组。组内精确名次不作稳健结论。

## 如何解释模型不一致

不同模型只要回答相同的策略平均轨迹问题，主要趋势和明显优劣策略通常应一致。数值不完全相同并不意味着推导错误；样条平滑、随机效应收缩和电池等权汇总会产生正常差异。若出现大范围排序反转，同时伴随较差的留一电池误差、明显非单调振荡或对单块电池高度敏感，才应优先检查模型设定和程序实现。
