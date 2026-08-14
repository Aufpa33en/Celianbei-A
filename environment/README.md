# 复现环境

- 操作系统：Windows
- 数据清洗与既有原始图：MATLAB R2022b或更高
- 第一问模型比较：Python 3.11
- Python依赖：`environment/requirements-q1.txt`
- 第一问入口：`python scripts/q1/run_q1_model_comparison.py`
- 第一问正式推断：`python scripts/q1/run_q1_final_analysis.py --bootstrap 2000 --seed 20260814`
- 第一问固定随机种子：`20260814`
- 第二问smoke依赖：`environment/requirements-q2.txt`
- 第二问smoke入口：`python scripts/q2/run_q2_smoke_test.py`
- 第二问正式验证：`python scripts/q2/run_q2_formal_validation.py --bootstrap 2000 --seed 20260814 --workers 8`

建议在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r environment\requirements-q1.txt
.\.venv\Scripts\python.exe scripts\q1\run_q1_model_comparison.py
```

模型拟合只依赖NumPy与pandas；Pillow仅用于生成论文PNG图，不依赖Matplotlib、SciPy或statsmodels。第一问正式整理结果位于 `result/q1/`。
