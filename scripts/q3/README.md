# 问题3程序

存放A题问题3关于第151—200循环SOH预测、寿命外推和预测验证的程序。

## 当前阶段：smoke test

```powershell
python scripts/q3/run_q3_smoke.py
```

该入口只运行9块分层伪测试电池的工程验证，结果写入`result/q3/01_smoke_test/`。它不会运行40块电池全量LOBO，也不会生成9块真实测试电池的最终预测。

模型数值实现位于`src/q3_models/models/`：

- `baselines.py`：末值保持和最近50循环线性趋势；
- `power_law.py`：个体约束幂律；
- `strategy_transfer.py`：同策略曲线迁移；
- `trajectory_ridge.py`：PCA未来轨迹基与多输出岭回归；
- 凸组合模型在`experiments.py`中复用B/C的交叉拟合预测，不重复训练基础模型。

冻结配置见`src/q3_models/config.py`，数学推导与无泄漏验证协议见`docs/q3_literature_and_model_derivation.md`。

## 正式全量入口

`run_q3_full_validation.py`是新增入口，不覆盖现有smoke程序或结果。它依次执行40块完整电池外层LOBO、39块训练集内部模型族选择、策略分层bootstrap、C模型特征消融、部署模型冻结，以及9块真实测试电池预测。

```powershell
python scripts/q3/run_q3_full_validation.py --bootstrap 5000
```

结果分别写入`result/q3/02_full_validation/`和`result/q3/03_final_predictions/`；若权威目录已经存在，程序拒绝覆盖。

复算时必须写入隔离目录，不能删除或覆盖权威结果：

```powershell
python scripts/q3/run_q3_full_validation.py --bootstrap 5000 --output-root <隔离目录>
```
