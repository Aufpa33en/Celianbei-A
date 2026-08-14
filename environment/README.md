# 复现环境

- 操作系统：Windows
- 数据清洗与既有原始图：MATLAB R2022b或更高
- 第一问模型比较：Python 3.11或更高（本轮在Python 3.12复现）
- Python依赖：`environment/requirements-q1.txt`
- 第一问入口：`python scripts/q1/run_q1_model_comparison.py`
- 第一问正式推断：`python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`
- 第一问固定随机种子：`20260814`
- 第二问smoke依赖：`environment/requirements-q2.txt`
- 第二问smoke入口：`python scripts/q2/run_q2_smoke_test.py`
- 第二问正式验证：`python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8`
- 第二问合并稳健性：`python scripts/q2/run_q2_merged_robustness.py --permutations 20000 --seed 20260814`
- 第三问smoke依赖：`environment/requirements-q3.txt`
- 第三问smoke入口：`python scripts/q3/run_q3_smoke.py`

Linux/WSL建议在项目根目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r environment/requirements-q1.txt
.venv/bin/python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
```

Windows PowerShell可执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r environment\requirements-q1.txt
.\.venv\Scripts\python.exe scripts\q1\run_q1_final_analysis.py --bootstrap 2000 --seed 20260814
```

模型拟合依赖NumPy与pandas；Matplotlib用于生成300 dpi论文图，Pillow保留给旧版轻量绘图入口。第一问正式结果位于 `result/q1/`，其中`paper/`保存论文材料，`raw/`保存完整审计数据。
