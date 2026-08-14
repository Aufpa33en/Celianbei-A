# 问题1程序

存放A题问题1的数据整理、清洗、寿命代理分布、健康状态曲线和模型比较程序。

- `run_a_data_cleaning.m`：按照冻结的清洗规则生成清洗数据、审计表和清洗前后对照图。
- `run_q1_model_comparison.py`：Python三模型比较、留一电池验证、主模型选择和论文输出。
- `run_q1_final_analysis.py`：仅使用40块完整电池完成第一问正式推断、2000次聚类自助法和CSV结果生成。
- `models/run_q1_polynomial_mixed.py`：单独运行二次多项式混合效应近似。
- `models/run_q1_spline_mixed.py`：单独运行三次样条混合效应近似。
- `models/run_q1_functional_ridge.py`：单独运行两阶段函数型岭平滑。

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

模型选择不使用80% SOH外推寿命，因为当前数据没有真实EOL标签。正式结果已按分析环节整理至 `result/q1/`；目录总说明记录了模型、输入、输出及原始CSV归档的恢复方法。
