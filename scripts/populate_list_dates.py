#!/usr/bin/env python3
"""
填充股票上市日期（Wind/本地行情路径）

通过 `stock_history` 的最早交易日推断 `stock_metadata.list_date`。
"""

import sys
from pathlib import Path

from sqlalchemy import func

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from loguru import logger

from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.db.models import StockMetadata, StockHistory


def populate_list_dates():
    db = get_db()
    logger.info("开始通过 stock_history 回填上市日期...")
    updated = 0

    with db.get_session() as session:
        rows = session.query(
            StockHistory.symbol,
            func.min(StockHistory.date).label("first_trade_date"),
        ).group_by(StockHistory.symbol).all()

        for symbol, first_trade_date in rows:
            if not first_trade_date:
                continue
            stock = session.query(StockMetadata).filter(StockMetadata.symbol == symbol).first()
            if stock is None:
                continue
            if stock.list_date is None or stock.list_date > first_trade_date:
                stock.list_date = first_trade_date
                updated += 1
        session.commit()

    logger.info(f"上市日期回填完成，更新 {updated} 条记录")


def verify_list_dates():
    db = get_db()
    with db.get_session() as session:
        total = session.query(StockMetadata).count()
        with_date = session.query(StockMetadata).filter(StockMetadata.list_date.isnot(None)).count()
    pct = (with_date / total * 100) if total else 0.0
    logger.info(f"总股票数: {total}, 有上市日期: {with_date} ({pct:.1f}%)")


if __name__ == "__main__":
    populate_list_dates()
    verify_list_dates()
