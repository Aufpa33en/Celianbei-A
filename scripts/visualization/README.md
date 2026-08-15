# 绘图程序

这里存放跨问题使用的论文绘图和原始数据诊断程序。

- `plot_raw_figure1.m`：直接读取官方原始CSV，生成异常诊断图和按策略分面的正常SOH曲线图；不执行数据清洗。
- `generate_q2_q3_paper_figures.py`：只读取Q2/Q3冻结结果CSV和第一问清洗数据，生成5张论文图；不重新拟合、调参或选模。
- `generate_q4_paper_figures.py`：只读取Q4冻结结果CSV，生成Pareto不确定性、快速候选成对比较和M1验证三张论文图。

Windows复现命令：

```powershell
.\.venv\Scripts\python.exe scripts\visualization\generate_q2_q3_paper_figures.py
.\.venv\Scripts\python.exe tests\test_q2_q3_paper_figures.py
.\.venv\Scripts\python.exe scripts\visualization\generate_q4_paper_figures.py
.\.venv\Scripts\python.exe tests\test_q4_paper_figures.py
```

