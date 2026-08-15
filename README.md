# 策联杯 A 题建模项目

当前项目聚焦 A 题“锂离子电池快充策略对寿命衰减的影响建模与优化”。

## 目录结构

- `A题/`：官方题面及原始附件，保持原状。
- `configs/`：数据处理和实验配置。
- `data/raw/`：只读原始数据副本。
- `data/processed/`：清洗后的数据。
- `src/`：MATLAB数据处理函数与Q1—Q4 Python模型模块。
- `scripts/`：可直接运行的入口脚本。
  - `scripts/q1/`—`scripts/q4/`：四个问题各自的程序入口。
  - `scripts/visualization/`：原始数据诊断和论文绘图程序。
- `tests/`：数据与流程校验。
- `outputs/raw/`：逐次实验原始结果。
- `outputs/summary/`：汇总指标和审计结果。
- `figures/`：由脚本生成的 PNG 与 FIG 图。
- `reports/`：阶段报告和论文素材。
- `docs/`：项目说明和数据字典。
- `environment/`：软件环境与复现说明。
- `.log/`：变更、审查和阶段反思记录。

## 快速运行

在 MATLAB 中将当前目录切换到项目根目录，然后执行：

```matlab
run("scripts/visualization/plot_raw_figure1.m")  % 仅绘制原始数据图，不清洗
run("scripts/q1/run_a_data_cleaning.m")          % 正式清洗与审计输出
run("tests/test_q1_cleaning.m")                  % 清洗结果验证
```

流水线不会覆盖 `data/raw/` 中的文件，输出写入 `data/processed/`、`outputs/summary/` 和 `figures/`。

第一问模型比较使用Python：

```powershell
python scripts/q1/run_q1_model_comparison.py
python tests/test_q1_models.py
```

三个候选模型也可分别从 `scripts/q1/models/` 独立运行。`outputs/summary/q1_models/` 保存探索性模型比较输出；第一问正式整理结果及说明位于 `result/q1/`。

## 当前完成状态

Q1—Q4的模型、正式实验、结果审查和论文文字材料均已完成。总验收报告见`reports/A_problem_completion_report.md`。

- Q1：`result/q1/paper/`和`result/q1/raw/`。
- Q2：`result/q2/03_formal_validation/`与`result/q2/04_paper_materials/`。
- Q3：`result/q3/02_full_validation/`与`result/q3/03_final_predictions/`。
- Q4：`result/q4/02_full_validation/`与`reports/q4_full_validation_report.md`。

Python验证命令：

```powershell
.venv\Scripts\python.exe tests\test_q1_models.py
.venv\Scripts\python.exe tests\test_q2_smoke.py
.venv\Scripts\python.exe tests\test_q2_formal_validation.py
.venv\Scripts\python.exe tests\test_q2_merged_robustness.py
.venv\Scripts\python.exe tests\test_q3_models.py
.venv\Scripts\python.exe tests\test_q3_smoke_outputs.py
.venv\Scripts\python.exe tests\test_q3_full_protocol.py
.venv\Scripts\python.exe tests\test_q4_smoke.py
.venv\Scripts\python.exe tests\test_q4_full_validation.py
```

MATLAB清洗验证：

```powershell
matlab -batch "run('tests/test_q1_cleaning.m')"
```
