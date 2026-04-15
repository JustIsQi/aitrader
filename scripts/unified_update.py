"""
A-share data update script.

Historical price updates are no longer downloaded into Database. Daily
prices are read directly from Wind MySQL by datafeed.db_dataloader.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
for path in (project_root, src_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from loguru import logger

from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.market_data.downloaders.fundamental_downloader import FundamentalDownloader


class UnifiedUpdater:
    """A-share-only updater for retained non-price datasets."""

    def __init__(self):
        self.db = get_db()
        self.fundamental_downloader = FundamentalDownloader()
        self.stats = {
            "start_time": datetime.now(),
            "stages": {
                "fundamental": {"success": 0, "failed": 0, "skipped": 0, "duration": 0},
            },
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

    def update_fundamental_stage(self) -> dict:
        logger.info("=" * 60)
        logger.info("[阶段1] 更新A股基本面数据")
        logger.info("=" * 60)

        start = time.time()
        symbols = self.db.get_stock_codes()
        if not symbols:
            logger.warning("没有找到A股代码,跳过基本面更新")
            return {"success": 0, "failed": 0, "skipped": 0, "duration": 0}

        stats = self.fundamental_downloader.update_fundamental_data(symbols=symbols)
        stats["duration"] = time.time() - start
        logger.info(f"✓ 基本面更新完成: 成功 {stats['success']}, 失败 {stats['failed']}")
        return stats

    def unified_data_update(
        self,
        stages: Optional[List[str]] = None,
        skip_code_check: bool = False,
    ) -> dict:
        start_time = datetime.now()
        logger.info(f"统一A股数据更新启动 - {start_time:%Y-%m-%d %H:%M:%S}")

        if not skip_code_check:
            self.check_and_init_codes()

        stages = stages or ["fundamental"]
        if "fundamental" in stages:
            self.stats["stages"]["fundamental"] = self.update_fundamental_stage()

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"统一A股数据更新完成, 总耗时 {total_duration:.2f} 秒")
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="A股数据更新流程")
    parser.add_argument(
        "--stage",
        action="append",
        choices=["fundamental"],
        help="要执行的阶段。历史行情从MySQL读取，不再本地下载。",
    )
    parser.add_argument("--skip-code-check", action="store_true")
    args = parser.parse_args()

    UnifiedUpdater().unified_data_update(
        stages=args.stage,
        skip_code_check=args.skip_code_check,
    )


if __name__ == "__main__":
    main()
