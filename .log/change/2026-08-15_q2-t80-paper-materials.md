# 2026-08-15 Q2 T80论文材料

## 范围

将问题2正式结论、五个小问回答、README和论文图统一切换为T80主响应；原SOH200、相对损失和末段速率结论明确降级为辅助稳健性证据。

## 图形

新增`fig_q2_t80_parameter_evidence.png`：

- 左图展示6个新结构策略的总倍率应力J与预测T80，纵轴为真实对数坐标，点位编号映射放在数据稀疏区。
- 右图展示五个单暴露量模型相对常数基线的LOCO RMSE改善及2000次整块电池bootstrap 95%区间。
- 图中没有图例或文字遮挡数据，输出300 dpi并完成目视检查。

## 论文结论

点估计支持J增加与T80缩短的探索性关联，但bootstrap改善区间跨0，删除3.7C–5.9C策略后常数模型胜出。论文不报告确认性参数p值，不把单一SOC阈值或C1、Q1、C2写成独立因果效应。

## 复现

```text
python -X utf8 scripts/q2/run_q2_lifetime_validation.py --bootstrap 2000 --seed 20260815
python -X utf8 tests/test_q2_lifetime_validation.py
```
