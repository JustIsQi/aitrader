"""
A-share code table initialization.

This script keeps the stock-code workflow for callers that still depend on the
existing code table while Database persistence is being retired.
"""
import argparse
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from database.db_manager import get_db
from datafeed.downloaders.stock_downloader import StockDownloader


class CodeInitializer:
    """A-share code initializer."""

    def __init__(self):
        self.db = get_db()
        self.stock_downloader = StockDownloader()

    def fetch_stock_list_from_akshare(self):
        logger.info("正在从 AkShare 获取 A股列表...")
        df = self.stock_downloader.fetch_stock_list()
        if df is None or df.empty:
            logger.error("获取 A股列表失败")
            return df

        logger.info(f"成功获取 {len(df)} 只 A股(已过滤)")
        return df[["symbol"]]

    def init_stock_codes(self, force: bool = False) -> int:
        logger.info("=" * 60)
        logger.info("开始初始化A股代码表")
        logger.info("=" * 60)

        existing_count = self.db.get_code_count("stock").get("stock", 0)
        if existing_count > 0 and not force:
            logger.info(f"A股代码表已有 {existing_count} 条记录,跳过初始化")
            return existing_count

        if force and existing_count > 0:
            logger.info(f"强制模式:清空现有的 {existing_count} 条记录")
            self.db.clear_stock_codes()

        df = self.fetch_stock_list_from_akshare()
        if df is None or df.empty:
            return 0

        inserted = self.db.batch_add_stock_codes(df["symbol"].tolist())
        logger.info(f"✓ A股代码表初始化完成: {inserted} 条记录")
        return inserted

    def init_all_codes(self, force: bool = False) -> dict:
        return {"stock": self.init_stock_codes(force=force)}


def main():
    parser = argparse.ArgumentParser(description="初始化A股代码表")
    parser.add_argument("--stock", action="store_true", help="初始化A股代码表")
    parser.add_argument("--all", action="store_true", help="初始化所有保留的代码表")
    parser.add_argument("--force", action="store_true", help="强制重新初始化")
    args = parser.parse_args()

    initializer = CodeInitializer()
    initializer.init_stock_codes(force=args.force)


if __name__ == "__main__":
    main()
