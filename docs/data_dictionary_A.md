# A题数据字典

## battery_summary.csv

| 变量 | 含义 |
|---|---|
| `battery_id` | 本题使用的电池编号 |
| `global_id` | 原始公开数据集中的全局编号 |
| `dataset_id` | 原始数据批次编号 |
| `local_id` | 批次内局部编号 |
| `policy` | 两阶段快充策略名称 |
| `C1` | 第一阶段充电倍率 |
| `Q1` | 第一阶段结束、切换至第二阶段时的 SOC 百分比 |
| `C2` | 第二阶段充电倍率 |
| `initial_capacity` | 初始可用容量，单位 Ah |
| `mean_chargetime` | 已观测循环的平均充电时间 |
| `mean_IR` | 已观测循环的平均内阻 |
| `mean_Tavg` | 已观测循环的平均温度 |
| `prediction_test` | 问题3测试电池标记，1为测试、0为训练 |

## cycle_train.csv

| 变量 | 含义 |
|---|---|
| `battery_id` | 电池编号，与摘要表关联 |
| `cycle` | 循环次数 |
| `capacity` | 当前循环可用容量，单位 Ah |
| `SOH` | 原始健康状态，约等于 capacity / initial_capacity |
| `SOH_smooth` | 平滑后的 SOH，用于观察总体退化趋势 |
| `chargetime` | 当前循环充电时间 |
| `IR` | 当前循环内阻 |
| `Tavg` | 当前循环平均温度 |
| `policy` | 当前电池采用的充电策略 |

## 清洗后新增变量

`cycle_train_clean.csv` 增加 `prediction_test`、`C1`、`Q1`、`C2`、`initial_capacity`、
`SOH_recomputed`、`SOH_residual`、`flag_nonpositive_measurement` 和
`flag_soh_outside_expected`。这些字段用于数据关联和质量审计，不覆盖原始测量值。

