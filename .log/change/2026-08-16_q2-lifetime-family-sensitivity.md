# Q2寿命模型族点敏感性

## 范围

- 保持现有2000次全流程bootstrap算法和数值不变。
- 读取Q1权威三族逐电池T80，对Q2六个新结构策略重新执行相同LOCO暴露模型选择。
- 将三族策略汇总、LOCO预测、模型比较和选择摘要写入正式目录，并复制论文用表。
- 未修改`paper/main.tex`。

## 方法边界

- 模型族：局部线性、幂律、加速指数，均使用Q1冻结候选。
- 每个族独立聚合策略内`mean(log(T80))`，再比较常数模型与J、H、J_high_50/60/70五个单暴露模型。
- 不做跨族bootstrap，不输出跨族置信区间。
- 正式2000次全流程bootstrap仍条件于Q1已选局部线性族。

## 结果

| T80族 | 点选模型 | J相对常数改善 | J斜率 |
|---|---|---:|---:|
| linear | linear_J | 20.29% | -10.0032 |
| power | linear_J | 31.54% | -9.0231 |
| exponential | linear_J | 22.93% | -5.8980 |

三族下J点方向一致，但正式线性族bootstrap改善区间仍为`[-10.29%,47.86%]`并跨0，删除极端策略后仍只剩常数模型。因此结论维持探索性关联，不升级为显著或因果效应。

## 验证

```text
python -X utf8 scripts/q2/run_q2_lifetime_validation.py --bootstrap 2000 --seed 20260816
python -X utf8 tests/test_q2_lifetime_family_sensitivity.py
python -X utf8 tests/test_q2_lifetime_validation.py
python -X utf8 tests/test_q2_full_pipeline_bootstrap.py
python -X utf8 tests/test_q2_formal_validation.py
python -X utf8 tests/test_q2_merged_robustness.py
python -X utf8 tests/test_q2_q3_paper_figures.py
```
