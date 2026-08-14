# 第二问正式验证结果

## 输入与范围

主队列为6个明确标注`NEWSTRUCTURE`的完整策略，策略内共有34块完整电池。参数设计单位为6个唯一坐标，bootstrap单位为整块电池。

## 文件说明

- `bootstrap_replicates.csv`：2000次重复×4个SOC暴露候选的逐次指标、系数、惩罚参数和选择标记。
- `bootstrap_summary.csv`：改善率和系数的均值、中位数、95%分位区间与符号比例。
- `bootstrap_selection_frequency.csv`：50%、60%、70%、`H`和常数模型的选择次数。
- `permutation_distribution.csv`：6个策略响应的720种完整排列及最大方向统计量。
- `permutation_test_summary.csv`：单候选未校正和四候选选择校正后的精确`p`值。
- `sensitivity_model_comparison.csv`：全部策略、等`T0`策略、同结构策略、排除3.7C极端策略和排除电池41的结果。
- `formal_model_decision.csv`：预设门槛及最终判定。
- `runtime_checkpoints.csv`：每100次bootstrap的运行检查点和总耗时。
- `result_manifest.csv`：正式结果文件完整性清单。

## 复现命令

```powershell
python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8
python tests/test_q2_formal_validation.py
```

固定种子为`20260814`。本机16核32线程、约16 GB内存，8进程正式运行总耗时81.63秒。
