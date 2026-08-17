"""Complete Question 1 and write CSV-only authoritative results to result/q1."""
# 中文注释说明（仅注释，不改动任何可执行代码）：
# 本脚本是 Q1 的权威实验入口。它在运行完整推断前、后分别对"实验数据文件"与"实验程序文件"
# 计算 SHA256 哈希并比对，确保实验期间数据与代码均未被改动（数据完整性审计，保证结果可复现）；
# 随后把推断结果以 CSV 形式写到 result/q1/ 下。

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


# 定位项目根目录：本文件位于 scripts/q1/，向上两级即项目根；把 src 加入导入路径以便直接 import 项目模块。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 导入 Q1 推断与输出模块（noqa: E402 说明在修改 sys.path 后导入是故意的，忽略 flake8 的顺序告警）。
from q1_models.inference import InferenceSettings, file_hashes, run_final_inference  # noqa: E402
from q1_models.outputs import write_authoritative_outputs  # noqa: E402


def parse_args() -> argparse.Namespace:
    # 解析命令行参数：bootstrap 重抽样次数与随机种子（均提供默认值，保证结果可复现）。
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", type=int, default=2000)   # Bootstrap 重抽样次数
    parser.add_argument("--seed", type=int, default=20260814)    # 固定随机种子，保证可复现
    return parser.parse_args()


def main() -> None:
    args = parse_args()   # 读取命令行参数
    result_dir = PROJECT_ROOT / "result" / "q1"   # 权威结果的输出目录

    # —— 汇总所有"实验数据文件"路径 ——
    # 依次扫描 A题/、data/raw/、data/processed/q1_cleaned/ 三个数据来源，
    # 仅收集文件（跳过目录），并按路径排序保证哈希顺序稳定。
    data_paths = sorted(path for path in (PROJECT_ROOT / "A题").rglob("*") if path.is_file())
    data_paths += sorted(path for path in (PROJECT_ROOT / "data" / "raw").rglob("*") if path.is_file())
    data_paths += sorted(
        path for path in (PROJECT_ROOT / "data" / "processed" / "q1_cleaned").rglob("*") if path.is_file()
    )
    # 不同来源可能覆盖同一文件，用 dict.fromkeys 按顺序去重（保持首次出现的路径）。
    data_paths = list(dict.fromkeys(data_paths))

    # —— 汇总"实验程序文件"路径：scripts/q1 下所有 py 与 src/q1_models 下所有 py ——
    program_paths = sorted((PROJECT_ROOT / "scripts" / "q1").rglob("*.py")) + sorted(
        (PROJECT_ROOT / "src" / "q1_models").glob("*.py")
    )

    # —— 运行前快照：对数据文件与程序文件分别计算哈希，列名加 Before 后缀便于之后合并比对 ——
    data_before = file_hashes(data_paths).rename(columns={"SHA256": "SHA256Before", "SizeBytes": "SizeBytesBefore"})
    programs_before = file_hashes(program_paths).rename(columns={"SHA256": "SHA256Before", "SizeBytes": "SizeBytesBefore"})

    # —— 组装推断设置并执行完整推断（计时以写入最终报告）——
    settings = InferenceSettings(seed=args.seed, bootstrap_repetitions=args.bootstrap)
    inference_started = time.perf_counter()     # 记录开始时刻（高性能计时器）
    tables = run_final_inference(PROJECT_ROOT, settings)   # 返回各结果表组成的字典
    inference_seconds = time.perf_counter() - inference_started   # 推断耗时（秒）

    # —— 运行后快照：重新计算哈希，与运行前比对以检测数据/程序是否被改动 ——
    data_after = file_hashes(data_paths).rename(columns={"SHA256": "SHA256After", "SizeBytes": "SizeBytesAfter"})
    programs_after = file_hashes(program_paths).rename(columns={"SHA256": "SHA256After", "SizeBytes": "SizeBytesAfter"})
    # 按文件路径合并前后哈希；Unchanged 为 True 当且仅当 SHA256 与字节数均一致。
    data_check = data_before.merge(data_after, on="Path")
    data_check["Unchanged"] = (
        (data_check["SHA256Before"] == data_check["SHA256After"])
        & (data_check["SizeBytesBefore"] == data_check["SizeBytesAfter"])
    )
    program_check = programs_before.merge(programs_after, on="Path")
    program_check["UnchangedDuringRun"] = (
        (program_check["SHA256Before"] == program_check["SHA256After"])
        & (program_check["SizeBytesBefore"] == program_check["SizeBytesAfter"])
    )
    # 任一实验数据文件在运行期间被改动即抛错终止，防止在已污染数据上输出"权威"结果。
    if not data_check["Unchanged"].all():
        raise RuntimeError("experimental data changed during Q1 final analysis")
    # 任一已有实验程序在运行期间被改动同样报错（防止代码被意外覆盖导致结果不可复现）。
    if not program_check["UnchangedDuringRun"].all():
        raise RuntimeError("an existing experiment program changed during Q1 final analysis")

    # 把两份完整性比对表一并放入结果表字典，随最终输出一起落盘，让审计信息随结果存档。
    tables["data_integrity_check"] = data_check
    tables["program_integrity_check"] = program_check

    # 记录复现本次运行的完整命令行（含参数），随结果输出以便他人按同样命令重跑。
    command = (
        f"{Path(sys.executable).resolve()} scripts/q1/run_q1_final_analysis.py "
        f"--bootstrap {args.bootstrap} --seed {args.seed}"
    )

    # —— 写权威输出：所有结果表导出为 CSV 到 result/q1/，并附运行信息（命令、耗时）——
    write_authoritative_outputs(PROJECT_ROOT, tables, command, inference_seconds)
    # 终端回显结果摘要，方便人工核对。
    print(f"Q1 final analysis complete: {result_dir}")
    print(f"Inference tables: {len(tables)}")
    print("Experimental data unchanged: true")
    print("Existing experiment programs unchanged during run: true")


if __name__ == "__main__":
    main()   # 仅当作为脚本直接运行时才执行，避免被 import 时产生副作用
