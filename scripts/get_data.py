#!/usr/bin/env python3
"""
通过 Wind 数据源同步 A 股历史行情到本地数据库。
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from loguru import logger

from aitrader.infrastructure.market_data.downloaders.stock_downloader import StockDownloader


def main():
    parser = argparse.ArgumentParser(description="同步 Wind A股行情到本地数据库")
    parser.add_argument("--symbol", type=str, help="单只股票代码，如 000001.SZ")
    parser.add_argument("--qfq", action="store_true", help="同步前复权数据（stock_history_qfq）")
    args = parser.parse_args()

    downloader = StockDownloader()

    if args.symbol:
        if args.qfq:
            ok = downloader.update_stock_data_qfq(args.symbol)
        else:
            ok = downloader.update_stock_data(args.symbol)
        logger.info(f"单票同步结果 {args.symbol}: {'成功' if ok else '失败'}")
        return 0 if ok else 1

    stats = downloader.update_all_stock_data()
    logger.info(stats)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
