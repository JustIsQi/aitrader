#!/usr/bin/env python3
"""
检查 Wind 行情与 Wind 元数据的上市日期一致性。

原先基于本地 `stock_history` / `stock_metadata` 的回填逻辑已移除。
"""

import sys
from pathlib import Path

import pandas as pd

project_root = Path(__file__).resolve().parents[1]
src_dir = project_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from aitrader.infrastructure.config.logging import logger
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


def verify_list_dates(limit: int = 50):
    reader = MySQLAshareReader()
    metadata = reader.read_stock_metadata()

    if metadata.empty:
        logger.warning("Wind 元数据为空，无法校验上市日期")
        return

    symbols = metadata["symbol"].dropna().astype(str).tolist()[:limit]
    placeholders = ", ".join(["%s"] * len(symbols))
    first_trade = reader.read_query(
        f"""
        SELECT
            S_INFO_WINDCODE AS symbol,
            MIN(TRADE_DT) AS first_trade_date
        FROM ASHAREEODPRICES
        WHERE S_INFO_WINDCODE IN ({placeholders})
        GROUP BY S_INFO_WINDCODE
        ORDER BY S_INFO_WINDCODE
        """,
        symbols,
    )

    merged = metadata[metadata["symbol"].isin(symbols)][["symbol", "name", "list_date"]].merge(
        first_trade,
        on="symbol",
        how="left",
    )
    merged["first_trade_date"] = pd.to_datetime(
        merged["first_trade_date"],
        format="%Y%m%d",
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    logger.info(f"抽样校验 {len(merged)} 只股票的上市日期/首个交易日")
    mismatch = merged[
        merged["list_date"].notna()
        & merged["first_trade_date"].notna()
        & (merged["list_date"] != merged["first_trade_date"])
    ]
    logger.info(f"存在差异的样本数: {len(mismatch)}")

    preview = merged.head(20)
    for _, row in preview.iterrows():
        logger.info(
            f"  {row['symbol']} | {row['name']} | list_date={row['list_date']} | "
            f"first_trade={row['first_trade_date']}"
        )


if __name__ == "__main__":
    verify_list_dates()
