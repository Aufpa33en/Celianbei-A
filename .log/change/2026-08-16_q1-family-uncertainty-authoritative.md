# Q1寿命模型族不确定性接入权威流水线

## 范围

- 在Q1正式运行上下文中比较局部线性、幂律、加速指数三种单调T80外推族。
- 将模型族验证、逐电池/逐策略T80、包络表和论文图接入`result/q1/paper`与`result/q1/raw`。
- 保留原支持性生成目录，但不再作为论文取数入口。
- 未修改`paper/main.tex`。

## 选择规则与一致性门

- 信息长度：前150循环。
- 目标：预测40块完整电池的151—200循环SOH。
- 外层：留一电池；内层只用其余电池冻结候选参数。
- 指标：策略等权RMSE，兼看最差电池RMSE。
- 唯一选中族必须为`linear`，冻结候选必须为`linear_w40_s1`。
- 线性族49块逐电池T80必须与原主流水线逐值一致，绝对容差`1e-10`。

## 结果

- 局部线性策略等权RMSE：`0.000706218`。
- 幂律策略等权RMSE：`0.000831090`。
- 加速指数策略等权RMSE：`0.000848668`。
- 电池级三族T80跨度比：中位数`2.76`，最大`4.34`。
- 策略级三族中位T80跨度比：`1.31—3.59`。
- 局部线性族继续作为主模型；没有因模型更复杂而替换验证胜者。

## 结论边界

- 2000次策略内整块电池bootstrap区间条件于已选局部线性族。
- 三族最大/最小包络表达模型形式敏感性，不是置信区间。
- 151—200回测不能验证远期SOH=80%终点，T80仍是情景外推。

## 验证

```text
python -X utf8 scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
python -X utf8 tests/test_q1_authoritative_lifetime_family.py
python -X utf8 tests/test_q1_lifetime_model_comparison.py
python -X utf8 tests/test_q1_models.py
```

上述测试均通过，权威图已完成视觉检查。
