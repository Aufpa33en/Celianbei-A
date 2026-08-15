# 问题4程序

存放A题问题4关于充电时间—寿命衰减多目标优化和推荐策略比较的程序。

- `run_q4_smoke.py`：2000次bootstrap与5点权重粗网格的模型排错入口。
- `run_q4_full_validation.py`：5000次策略内整块bootstrap、11点正式权重扫描、M1坐标LOSO压力测试和不确定性汇总的全量入口。

从项目根目录运行：

```powershell
.venv\Scripts\python.exe scripts\q4\run_q4_full_validation.py --bootstrap 5000
```
