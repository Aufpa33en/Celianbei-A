# 第二问正式验证结果

## 输入与范围

主队列为6个明确标注`NEWSTRUCTURE`的完整策略，策略内共有34块完整电池。参数设计单位为6个唯一坐标，bootstrap单位为整块电池。

T80主分析另运行2000次全流水线bootstrap：每次在全部9种策略内重采样49块电池，重新选择Q1寿命尾窗、重算T80，再对6个新结构策略重新执行参数模型选择。它替代固定T80 bootstrap作为论文主区间；旧结果保留为对照。

## 文件说明

- `bootstrap_replicates.csv`：2000次重复×4个SOC暴露候选的逐次指标、系数、惩罚参数和选择标记。
- `bootstrap_summary.csv`：改善率和系数的均值、中位数、95%分位区间与符号比例。
- `bootstrap_selection_frequency.csv`：50%、60%、70%、`H`和常数模型的选择次数。
- `permutation_distribution.csv`：6个策略均值的720种完整标签排列及最大方向统计量，仅作交换性敏感性。
- `permutation_test_summary.csv`：历史文件名保留兼容；其中只报告假设策略均值可交换时的尾部比例，并明确`confirmatory_p_value_available=false`，不是精确检验或确认性`p`值。
- `sensitivity_model_comparison.csv`：全部策略、等`T0`策略、同结构策略、排除3.7C极端策略和排除电池41的结果。
- `formal_model_decision.csv`：预设门槛及最终判定。
- `runtime_checkpoints.csv`：每100次bootstrap的运行检查点和总耗时。
- `result_manifest.csv`：正式结果文件完整性清单。
- `lifetime_bootstrap_replicates.csv`：2000次全流水线重复中六个参数候选的逐次选择、改善率、斜率和寿命窗口。
- `lifetime_bootstrap_selection.csv`：全流水线bootstrap主汇总。
- `lifetime_fixed_t80_bootstrap_selection.csv`：不重选窗口、不重算T80的旧bootstrap对照。
- `lifetime_bootstrap_window_frequency.csv`：30—80循环寿命尾窗的重选频率。
- `lifetime_full_pipeline_runtime.csv`：缓存等价实现的运行时间、种子与样本行数。
- `lifetime_family_policy_t80_summary.csv`、`lifetime_family_strategy_design.csv`、`lifetime_family_model_comparison.csv`、`lifetime_family_selection_summary.csv`：局部线性、幂律和加速指数三种冻结T80族的点敏感性；没有跨族联合置信区间。

## 复现命令

```powershell
python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8
python scripts/q2/run_q2_lifetime_validation.py --bootstrap 2000 --seed 20260816
python tests/test_q2_formal_validation.py
python tests/test_q2_full_pipeline_bootstrap.py
```

固定种子为`20260814`。本机16核32线程、约16 GB内存，8进程正式运行总耗时81.63秒。
