# Q2权威说明同步

## 修正内容

- `result/q2/README.md`的正式全流程bootstrap区间由旧固定T80口径`[-10.96%,48.28%]`更新为`[-10.29%,47.86%]`。
- Q2正式入口和默认配置随机种子统一为`20260816`。
- README增加三种冻结T80模型族敏感性表的取数入口，并明确没有跨族联合置信区间。
- 历史变更日志保留当时数值，不回写历史记录。
- 未修改`paper/main.tex`。

## 验证

```text
python -X utf8 tests/test_q2_lifetime_family_sensitivity.py
python -X utf8 tests/test_q2_lifetime_validation.py
python -X utf8 tests/test_q2_full_pipeline_bootstrap.py
python -X utf8 tests/test_q2_formal_validation.py
```
