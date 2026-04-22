#!/usr/bin/env python3
"""
检查 Wind 元数据中的上市日期覆盖情况。

本地 `stock_metadata` / `stock_history` 镜像链路已移除，
当前脚本只做 Wind 直读检查，不再写入任何镜像表。
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aitrader.infrastructure.config.logging import logger
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


def inspect_wind_list_dates(sample_size: int = 20):
    reader = MySQLAshareReader()
    metadata = reader.read_stock_metadata()

    if metadata.empty:
        logger.warning("Wind 元数据为空，无法检查上市日期覆盖情况")
        return

    total = len(metadata)
    with_list_date = int(metadata["list_date"].notna().sum())
    pct = with_list_date / total * 100 if total else 0.0

    logger.info(f"Wind 元数据股票数: {total}")
    logger.info(f"有上市日期: {with_list_date} ({pct:.1f}%)")

    preview = metadata[["symbol", "name", "list_date", "list_board_name", "sector"]].head(sample_size)
    logger.info("样例预览:")
    for _, row in preview.iterrows():
        logger.info(
            f"  {row['symbol']} | {row['name']} | {row['list_date']} | "
            f"{row['list_board_name']} | {row['sector']}"
        )


if __name__ == '__main__':
    logger.info('=' * 60)
    logger.info('检查 Wind 股票上市日期覆盖情况')
    logger.info('=' * 60)
    inspect_wind_list_dates()
    logger.info('=' * 60)
