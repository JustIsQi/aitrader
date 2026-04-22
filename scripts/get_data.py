#!/usr/bin/env python3
"""
直接从 Wind 读取 A 股历史行情并打印预览。
"""

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aitrader.infrastructure.config.logging import logger
from aitrader.infrastructure.market_data.downloaders.stock_downloader import StockDownloader


def main():
    parser = argparse.ArgumentParser(description="直接读取 Wind A股行情预览")
    parser.add_argument("--symbol", type=str, help="单只股票代码，如 000001.SZ")
    parser.add_argument("--start", type=str, default="20240101", help="开始日期 YYYYMMDD")
    parser.add_argument("--end", type=str, help="结束日期 YYYYMMDD，默认今天")
    args = parser.parse_args()

    downloader = StockDownloader()

    if not args.symbol:
        logger.error("请通过 --symbol 指定要读取的股票代码")
        return 1

    df = downloader.fetch_stock_history(args.symbol, start_date=args.start, end_date=args.end, adjust="qfq")
    if df is None or df.empty:
        logger.error(f"{args.symbol} 未读取到任何 Wind 行情")
        return 1

    logger.info(f"{args.symbol} 读取成功: {len(df)} 条")
    logger.info(f"日期范围: {df['date'].min()} ~ {df['date'].max()}")
    print(df.tail(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
