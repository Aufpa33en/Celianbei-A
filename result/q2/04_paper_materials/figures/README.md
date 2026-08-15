# 第二问论文图

本目录是第二问当前论文图的权威位置。图件仅重排既有正式验证结果，不重新拟合模型，也不改变显著性判断。

- `fig_q2_strategy_late_rate.png`：九种策略第151–200循环平均退化速率；误差线是策略内电池标准差，不是置信区间。数据来自`../../05_merged_robustness/paper/strategy_late_rate.csv`。
- `fig_q2_model_stability.png`：左图为2000次整块电池bootstrap的模型选择频率；右图为明确新结构队列中各低维暴露模型相对常数模型的留一坐标RMSE改善。数据来自`../../03_formal_validation/`。

两图共同支持“高SOC倍率暴露方向一致，但阈值选择和参数效应不稳定”的结论；不能据图宣称`C1、Q1、C2`存在独立因果效应。

复现命令：

```powershell
python scripts/visualization/generate_q2_q3_paper_figures.py
```
