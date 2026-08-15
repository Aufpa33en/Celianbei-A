# 问题1程序

存放A题问题1的数据整理、清洗、寿命代理分布、健康状态曲线和模型比较程序。

- `run_a_data_cleaning.m`：按照冻结的清洗规则生成清洗数据、审计表和清洗前后对照图。
- `run_q1_model_comparison.py`：Python三模型比较、留一电池验证、主模型选择和论文输出。
- `run_q1_final_analysis.py`：仅使用40块完整电池完成正式推断、2000次电池级聚类自助法、精确置换检验和论文图表生成。
- `models/run_q1_polynomial_mixed.py`：单独运行二次多项式混合效应近似。
- `models/run_q1_spline_mixed.py`：单独运行三次样条混合效应近似。
- `models/run_q1_functional_ridge.py`：单独运行两阶段函数型曲线候选（文件名保留历史内部标识，惩罚可由验证选为0）。

运行：

```matlab
run("scripts/q1/run_a_data_cleaning.m")
run("tests/test_q1_cleaning.m")
```

```powershell
python scripts/q1/run_q1_model_comparison.py
python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
python tests/test_q1_models.py
```

模型选择不使用80% SOH外推寿命，因为当前数据没有真实EOL标签。当前权威结果位于`result/q1/paper/`与`result/q1/raw/`；不要再引用旧的`outputs/summary/q1_models/`作为最终数值。
