# 2026-08-14 第一问结果目录简化

## 修改目标

- 解决 `result/q1/` 下 30 个 CSV 平铺、用途不清和难以查找的问题。
- 在不遗漏、不改写结果数据的前提下减少可见文件数量，并为每个主题文件夹说明模型、输入和输出。

## 修改内容

1. 将 30 个原始 CSV 按分析环节整理为 6 个 Excel 工作簿。
   - 每个原 CSV 对应工作簿中的一个独立工作表。
   - 不合并异构表，不删除行列，不修改单元格结果值。
2. 新建 6 个主题目录：
   - `result/q1/00_overview/`
   - `result/q1/01_model_selection/`
   - `result/q1/02_main_model_results/`
   - `result/q1/03_strategy_comparison/`
   - `result/q1/04_diagnostics/`
   - `result/q1/05_integrity_audit/`
3. 每个主题目录保存一个工作簿和一个 `README.md`，README 明确记录模型、输入、输出以及原 CSV 到工作表的映射。
4. 新建根目录 `result/q1/README.md`，记录统一输入、三个模型、主模型、目录导航和结论边界。
5. 将整理前的 30 个 CSV 以原字节保存到 `result/q1/original_q1_csv_archive.zip`。
6. 在归档与工作簿校验通过后，移除根目录中已归档的 30 个散乱 CSV。该删除可通过 ZIP 完整恢复。

## 涉及文件

- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\README.md`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\original_q1_csv_archive.zip`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\00_overview\q1_overview.xlsx`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\01_model_selection\model_selection.xlsx`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\02_main_model_results\main_model_results.xlsx`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\03_strategy_comparison\strategy_comparison.xlsx`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\04_diagnostics\diagnostics_and_features.xlsx`
- `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\05_integrity_audit\integrity_audit.xlsx`

## 验证情况

- 整理前确认根目录正好包含 30 个 CSV。
- ZIP 完整性测试通过；压缩包内 30 个文件与整理前文件逐一比较 SHA-256，全部一致。
- 使用 `@oai/artifact-tool` 将每个 CSV 导入独立工作表，并重新导入生成的工作簿逐单元格核对；30 个工作表全部与源 CSV 一致。校验仅把 CSV 文件头 BOM 和空字符串/Excel 空单元格视为等价表示。
- 6 个工作簿共 30 个工作表全部完成渲染检查，未发现空白工作表、表头缺失、内容重叠或错误值。
- 每个主题文件夹均包含一个工作簿和一个 README；根目录另有总 README 和原始 CSV 归档。
- 原始实验数据、清洗数据和第一问实验程序未被本次目录整理修改。

## 未处理事项

- `scripts/q1/run_q1_final_analysis.py` 仍按原设计生成平铺 CSV。若将来重新运行正式分析，应先保留本目录或在运行后重新执行相同的整理流程，避免再次出现平铺文件。

## 依据与工具

- Skill: `C:\Users\Aupassen\.codex\plugins\cache\openai-primary-runtime\spreadsheets\26.812.11052\skills\spreadsheets\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\math-modeling-stage-workflow\SKILL.md`
- Skill: `C:\Users\Aupassen\.codex\skills\project-logbook\SKILL.md`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\result\q1\`
- Source: `C:\Users\Aupassen\Desktop\Celianbei Math Modeling\src\q1_models\core.py`
- Tool: `functions.shell_command`，CSV 盘点、ZIP 归档与 SHA-256 校验，cwd `C:\Users\Aupassen\Desktop\Celianbei Math Modeling`
- Tool: `@oai/artifact-tool`，CSV 导入、工作簿导出、重新读取和工作表渲染。
- Tool: `functions.view_image`，检查 6 组工作表渲染预览。
