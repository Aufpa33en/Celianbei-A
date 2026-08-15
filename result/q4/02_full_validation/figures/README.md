# Q4论文图

本目录只读取`q4_full_v4`权威CSV，不重新拟合、bootstrap或选择策略。

- `fig_q4_pareto_uncertainty.png`：9个观测策略的时间—退化点、整块电池bootstrap区间、5.3C点Pareto推荐和5.0C非前沿近似并列敏感性项。
- `fig_q4_fast_pair_comparison.png`：5.3C减5.0C的时间差和退化差成对bootstrap区间，说明5.0C为何保留为敏感性项而不是共同主推荐。
- `fig_q4_m1_validation.png`：单J岭与常数基线的7个留一坐标RMSE，限定“当前代理失败”的证据范围。
- `figure_manifest.csv`：每张图、其冻结源CSV和生成脚本的SHA-256绑定。
