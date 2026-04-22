"""
A-share direct-Wind maintenance script.

本地价格/基本面镜像已退役，脚本仅保留代码表检查与初始化。
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
for path in (project_root, src_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.config.logging import logger


class UnifiedUpdater:
    """A-share direct-Wind maintenance helper."""

    def __init__(self):
        self.db = get_db()
        self.stats = {
            "start_time": datetime.now(),
            "stages": {},
        }

    def check_and_init_codes(self) -> bool:
        logger.info("[阶段0] 检查A股代码表状态...")
        stock_count = self.db.get_code_count("stock").get("stock", 0)
        logger.info(f"  stock_codes: {stock_count} 条")

        if stock_count == 0:
            logger.warning("A股代码表为空,开始自动初始化...")
            from scripts.init_codes import CodeInitializer

            CodeInitializer().init_stock_codes(force=False)
            return True

        logger.info("✓ A股代码表状态正常")
        return False

    def unified_data_update(
        self,
        stages: Optional[List[str]] = None,
        skip_code_check: bool = False,
    ) -> dict:
        start_time = datetime.now()
        logger.info(f"统一A股数据更新启动 - {start_time:%Y-%m-%d %H:%M:%S}")

        if not skip_code_check:
            self.check_and_init_codes()

        stages = stages or []
        if stages:
            logger.warning(f"已忽略镜像更新阶段 {stages}；当前模式统一直读 Wind，不再落本地镜像。")

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"统一A股数据更新完成, 总耗时 {total_duration:.2f} 秒")
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="A股直读 Wind 维护流程")
    parser.add_argument(
        "--stage",
        action="append",
        help="镜像更新阶段已移除，保留参数仅为兼容旧调用。",
    )
    parser.add_argument("--skip-code-check", action="store_true")
    args = parser.parse_args()

    UnifiedUpdater().unified_data_update(
        stages=args.stage,
        skip_code_check=args.skip_code_check,
    )


if __name__ == "__main__":
    main()
