#!/usr/bin/env python3
"""Run the merged Q2 robustness analysis."""
# 中文注释说明（仅注释，不改动任何可执行代码）：
# 本脚本是 Q2"合并稳健性分析"的权威实验入口：
# 1) 用置换检验（permutation test）评估结果的统计显著性（默认 20000 次置换）；
# 2) 固定随机种子保证结果可复现；
# 3) 执行合并稳健性分析，并把结果以 CSV 形式写出。

from __future__ import annotations

import argparse
from pathlib import Path
import sys


# 定位项目根目录：本文件位于 scripts/q2/，向上两级即项目根；把 src 加入导入路径以便直接 import 项目模块。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 导入 Q2 合并稳健性分析主函数与结果写出函数（noqa: E402 说明在修改 sys.path 后导入是故意的）。
from q2_models.merged_robustness import run_merged_robustness, write_merged_robustness  # noqa: E402


def main() -> None:
    # 解析命令行参数：permutations 为置换检验次数，seed 为随机种子，均提供默认值保证可复现。
    parser = argparse.ArgumentParser()
    parser.add_argument("--permutations", type=int, default=20000)   # 置换检验重排次数
    parser.add_argument("--seed", type=int, default=20260814)        # 固定随机种子
    args = parser.parse_args()
    # 执行合并稳健性分析：传入项目根目录与参数，返回结果表（字典结构）供写出。
    outputs = run_merged_robustness(PROJECT_ROOT, args.permutations, args.seed)
    # 将结果表以 CSV 形式写到结果目录，形成权威存档。
    write_merged_robustness(PROJECT_ROOT, outputs)
    # 终端回显完成信息，便于人工核对。
    print("Merged Q2 robustness analysis complete")


if __name__ == "__main__":
    main()   # 仅当作为脚本直接运行时才执行，避免被 import 时产生副作用
