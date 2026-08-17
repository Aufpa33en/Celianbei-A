"""Run complete Q3 nested validation, freeze a model, then predict test cells.
Q3 全量验证入口：先运行嵌套留一验证（六模型）→ 冻结最终选定模型 → 对测试电池做最终预测。
所有产物在完整性校验全部通过后才原子发布，保证论文所用结果的权威性、可复现性。"""

from __future__ import annotations  # 使用延迟求值的类型注解（兼容旧版 Python），本文件大量依赖类型注解

import argparse  # 命令行参数解析（--bootstrap / --resume-final / --output-root）
import sys  # 修改 sys.path，使项目 src 下的包可被直接导入
import time  # 统计整个验证流程的运行时长（秒）
from pathlib import Path  # 跨平台路径处理

import pandas as pd  # 表格数据处理（读取/筛选 CSV 结果）


# 项目根目录：本文件位于 scripts/q3/run_q3_full_validation.py，向上上溯两级即仓库根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# 把 src 目录加入模块搜索路径，使下文能直接 import q3_models.* 包
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from q3_models.config import CONFIG  # noqa: E402  # 全局配置（含随机种子 seed，保证结果可复现）
from q3_models.full_outputs import (  # noqa: E402  # 权威产物目录的写入与完整性校验
    directory_hashes,          # 统计目录内所有文件的哈希，用于校验发布前后目录未被改动
    final_integrity_checks,    # 最终预测产物（03）的发布前完整性校验
    full_integrity_checks,     # 全量验证产物（02）的发布前完整性校验
    write_final_outputs,       # 原子发布 03_final_predictions 目录（先写临时目录再整体改名）
    write_full_outputs,        # 原子发布 02_full_validation 目录
)
from q3_models.full_validation import (  # noqa: E402  # Q3 核心验证与预测流程
    compare_protected_hashes,  # 对比前后两次受保护文件哈希，检测验证期间文件是否被意外改动
    protected_file_hashes,     # 计算受保护文件（数据/程序/smoke 输出）的哈希快照
    run_final_prediction,      # 冻结最终选定模型后，对测试电池做最终预测
    run_full_validation,       # 运行全量嵌套留一验证：六个候选模型逐一验证，内部用 bootstrap 评估超参稳定性
)


def main() -> None:
    # ---------- 命令行参数解析 ----------
    parser = argparse.ArgumentParser()
    # bootstrap 重复次数：嵌套留一验证内部用它估计超参选择的稳定性
    parser.add_argument("--bootstrap", type=int, default=5000)
    # 断点续跑模式：仅当 02_full_validation 已存在、03_final_predictions 不存在时使用，
    # 只执行"冻结模型→最终预测→发布 03"这一后半段流程，避免重跑昂贵的全量验证
    parser.add_argument("--resume-final", action="store_true")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "result" / "q3",  # 默认输出根目录：result/q3
        help="Directory containing 02_full_validation and 03_final_predictions.",
    )
    args = parser.parse_args()
    output_root = args.output_root.resolve()  # 归一化为绝对路径，消除相对路径歧义
    full_dir = output_root / "02_full_validation"  # 全量验证产物目录
    final_dir = output_root / "03_final_predictions"  # 最终预测产物目录

    # ---------- 分支一：续跑最终预测（仅发布 03，跳过全量验证） ----------
    if args.resume_final:
        # 前提约束：02 必须已存在、03 必须不存在，否则拒绝执行，保证产物状态机一致
        if not full_dir.exists() or final_dir.exists():
            raise FileExistsError("--resume-final requires existing 02 and absent 03")
        # 读取 02 目录下全部 CSV 作为既有验证结果；
        # manifest / integrity_checks 等元数据文件不属于结果本体，故排除
        full = {
            path.name: pd.read_csv(path)
            for path in full_dir.glob("*.csv")
            if path.name not in {"manifest.csv", "integrity_checks.csv", "protected_files_integrity.csv"}
        }
        full_hashes = directory_hashes(full_dir)  # 记录发布 03 前 02 目录的哈希，稍后复核其未变
        before = protected_file_hashes(PROJECT_ROOT)  # 记录执行前的受保护文件哈希
        final = run_final_prediction(PROJECT_ROOT, full)  # 基于已冻结的超参，对测试电池做最终预测
        # 校验最终预测执行期间受保护文件未被改动
        protected_final = compare_protected_hashes(before, protected_file_hashes(PROJECT_ROOT))
        settings = final["final_hyperparameters.csv"]  # 最终超参数表（含被选中的模型名）
        # 从超参数表中取出"selected_model"行的 value，即全量验证最终选定的模型名
        selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
        # 从最终预测表中筛出所选模型的预测行，供发布前校验
        selected = final["final_predictions.csv"].loc[
            final["final_predictions.csv"]["model"].eq(selected_model)
        ]
        # 对最终预测产物做发布前完整性校验（覆盖所选模型预测、全表、超参数、受保护文件）
        checks = final_integrity_checks(selected, final["final_predictions.csv"], settings, protected_final)
        if not checks["passed"].all():  # 任一校验项不通过即中止，防止发布残缺/不一致的结果
            raise RuntimeError("Final pre-publication integrity checks failed")
        # 原子发布 03_final_predictions（先写临时目录再整体改名，发布过程不产生半成品）
        published_final = write_final_outputs(
            PROJECT_ROOT, final, protected_final, CONFIG.seed, output_root=output_root
        )
        # 发布完成后复核 02 目录哈希：若发布 03 的过程污染了 02，则拒绝通过
        if directory_hashes(full_dir) != full_hashes:
            raise RuntimeError("Published 02_full_validation changed during resumed final prediction")
        print(f"Q3 final predictions published: {published_final}", flush=True)
        return  # 续跑模式到此结束

    # ---------- 分支二：全新全量验证（02 与 03 都从零生成） ----------
    # 权威目录已存在则拒绝覆盖：保证论文所用的 02/03 结果可追溯、不会被误覆盖
    if full_dir.exists() or final_dir.exists():
        raise FileExistsError("Q3 authoritative full/final directory already exists; refusing overwrite")

    started = time.perf_counter()  # 开始计时
    before = protected_file_hashes(PROJECT_ROOT)  # 记录执行前的受保护文件哈希（数据/程序/smoke 输出）
    # 核心步骤：运行全量嵌套留一验证——对六个候选模型逐一做留一电池组验证，
    # 内部用 bootstrap 评估超参选择的稳定性，返回各模型验证结果与最终选定模型
    full = run_full_validation(PROJECT_ROOT, bootstrap_repetitions=args.bootstrap)
    after_full = protected_file_hashes(PROJECT_ROOT)  # 全量验证完成后再次计算受保护文件哈希
    protected_full = compare_protected_hashes(before, after_full)  # 检查验证期间文件是否被改动
    if not protected_full["unchanged"].all():  # 任一受保护文件变动即视为流程被污染
        raise RuntimeError("Protected data, programs, or smoke outputs changed during full validation")
    final = run_final_prediction(PROJECT_ROOT, full)  # 冻结选定模型，对测试电池做最终预测
    after_final = protected_file_hashes(PROJECT_ROOT)
    protected_final = compare_protected_hashes(before, after_final)  # 最终预测期间受保护文件同样须未变
    if not protected_final["unchanged"].all():
        raise RuntimeError("Protected data, programs, or smoke outputs changed during final prediction")
    # Validate both products before publishing either authoritative directory.
    # 关键设计：在发布任一权威目录之前，先把 02 与 03 两份产物都校验通过，再统一发布
    if not full_integrity_checks(full, protected_full)["passed"].all():
        raise RuntimeError("Full pre-publication integrity checks failed")
    settings = final["final_hyperparameters.csv"]  # 最终超参数表
    # 取最终选定模型名（与续跑分支逻辑一致，见上）
    selected_model = str(settings.loc[settings["parameter"].eq("selected_model"), "value"].iloc[0])
    # 筛出所选模型的预测行
    selected = final["final_predictions.csv"].loc[
        final["final_predictions.csv"]["model"].eq(selected_model)
    ]
    # 最终预测产物发布前校验
    if not final_integrity_checks(selected, final["final_predictions.csv"], settings, protected_final)["passed"].all():
        raise RuntimeError("Final pre-publication integrity checks failed")
    # 两份产物均校验通过后，先原子发布 02_full_validation
    published_full = write_full_outputs(
        PROJECT_ROOT, full, protected_full, CONFIG.seed, output_root=output_root
    )
    print(f"Q3 full validation published: {published_full}", flush=True)
    full_hashes = directory_hashes(published_full)  # 记录已发布 02 目录的哈希
    # 再原子发布 03_final_predictions
    published_final = write_final_outputs(
        PROJECT_ROOT, final, protected_final, CONFIG.seed, output_root=output_root
    )
    # 发布 03 之后再复核 02 目录哈希：确保整个发布过程不污染已发布的 02
    if directory_hashes(published_full) != full_hashes:
        raise RuntimeError("Published 02_full_validation changed during final publication")
    print(f"Q3 final predictions published: {published_final}", flush=True)
    # 输出总耗时（秒），便于记录完整验证流程的运行成本
    print(f"Q3 complete wall seconds: {time.perf_counter() - started:.3f}", flush=True)


if __name__ == "__main__":  # 脚本直接运行时才执行入口函数
    main()
