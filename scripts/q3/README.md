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
