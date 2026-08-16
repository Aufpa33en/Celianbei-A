# Q4 充电时间—预测 T80 Pareto 支持性敏感性

## 变更范围

- 未修改 `paper/main.tex`，未替换 Q4 既有 SOH200/末段斜率主结果。
- 将 Q1 的三种单调寿命模型 T80 与 Q4 的 40 块完整电池充电时间按电池联合。
- 对局部线性主模型执行 5000 次策略内整块电池联合 bootstrap，重新计算时间—T80 Pareto 前沿。
- 比较局部线性、幂律、加速指数三种模型族下的点 Pareto 成员稳定性。
- 生成论文可用图、表、策略编号映射和短报告，原始结果与论文材料分目录保存。

## 验证设置

- 随机种子：`20260816`
- bootstrap 重复数：`5000`
- 重采样单位：同一策略内的整块电池；时间与预测 T80 保持联合重采样
- T80 终止阈值：`SOH = 80%`
- 图中纵轴为真实对数轴；误差线为联合重采样的 2.5%—97.5% 分位区间；点大小编码 Pareto 频率。

## 主要结果

- 局部线性 T80 点前沿包含 4 个策略：3.6C、new 4.8C、5C-67%-4C、5.3C-54%-4C。
- 与早期 SOH200 损失点前沿的逐策略成员一致率为 8/9；唯一差异是 5C-67%-4C 在 T80 前沿上、但不在早期损失点前沿上。
- 三种 T80 模型族下始终位于点前沿的策略为 new 4.8C、5C-67%-4C、5.3C-54%-4C。
- 3.6C 只在局部线性模型下位于点前沿，因此不能表述为模型族稳定的前沿成员。
- 该结果仅支持“用预测寿命替代早期代理后，结论大体一致但存在一项前沿成员变化”；不把外推 T80 当作真实寿命标签，也不替代正式 Q4 结论。

## 验证命令

```text
python -X utf8 scripts/q4/run_q4_t80_sensitivity.py --bootstrap 5000 --seed 20260816
python -X utf8 tests/test_q4_t80_sensitivity.py
python -X utf8 tests/test_q4_full_validation.py
python -X utf8 tests/test_q4_paper_figures.py
python -X utf8 tests/test_q4_smoke.py
```

## 产物

- `result/q4/03_t80_pareto_sensitivity/paper/`
- `result/q4/03_t80_pareto_sensitivity/raw/`
- `result/q4/03_t80_pareto_sensitivity/manifest.csv`
