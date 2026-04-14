"""
A-share derivative-indicator updater.

PE/PB/PS and market-cap fields come from Wind MySQL table
ASHAREEODDERIVATIVEINDICATOR. This module keeps the historical
FundamentalDownloader entry point used by scripts/unified_update.py, but no
longer fetches valuation data from AkShare.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from datafeed.mysql_ashare_reader import MySQLAshareReader
from database.db_manager import get_db


class FundamentalDownloader:
    """Update local fundamental snapshots from Wind derivative indicators."""

    REQUIRED_COLUMNS = [
        "pe_ratio",
        "pb_ratio",
        "ps_ratio",
        "roe",
        "roa",
        "profit_margin",
        "operating_margin",
        "debt_ratio",
        "current_ratio",
        "total_mv",
        "circ_mv",
    ]

    def __init__(self, reader: Optional[MySQLAshareReader] = None):
        self.db = get_db()
        self.reader = reader or MySQLAshareReader()
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
        }

    def get_all_a_stocks_with_fundamentals(self) -> pd.DataFrame:
        """
        Return the latest derivative-indicator row for each symbol.

        Kept for compatibility with older callers that expected this method to
        return a market-wide DataFrame.
        """
        return self.reader.read_latest_derivative_indicators()

    def fetch_stock_fundamental(self, symbol: str, code: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch the latest PE/PB/PS and market-cap snapshot for one symbol.

        Args:
            symbol: Wind code such as 000001.SZ. If a raw six-digit code is
                supplied, code is used to infer the Wind suffix.
            code: optional raw six-digit code kept for older callers.
        """
        wind_code = symbol if "." in str(symbol) else self._format_symbol(code or symbol)
        df = self.reader.read_latest_derivative_indicators(symbols=[wind_code])
        if df.empty:
            return None
        return self._to_fundamental_records(df).iloc[0].to_dict()

    def update_fundamental_data(
        self,
        symbols: Optional[List[str]] = None,
        batch_size: int = 100,
        **_ignored,
    ) -> dict:
        """
        Update local fundamental snapshots from ASHAREEODDERIVATIVEINDICATOR.

        Args:
            symbols: Wind codes to update. None updates the latest row for all
                symbols available in the derivative-indicator table.
            batch_size: retained for compatibility; rows are still written in
                chunks to keep memory and transaction size bounded.

        Returns:
            dict: update statistics.
        """
        self.stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0,
        }
        try:
            logger.info("从 Wind MySQL ASHAREEODDERIVATIVEINDICATOR 读取基本面快照...")
            indicators = self.reader.read_latest_derivative_indicators(symbols=symbols)
            if indicators.empty:
                logger.error("未读取到任何基本面衍生指标")
                return self.stats

            fundamentals = self._to_fundamental_records(indicators)
            self.stats["total"] = len(fundamentals)
            logger.info(f"开始更新 {len(fundamentals)} 条基本面快照...")

            for start in range(0, len(fundamentals), batch_size):
                batch = fundamentals.iloc[start:start + batch_size]
                self.db.batch_upsert_fundamental(batch.copy())
                self.stats["success"] += len(batch)

            logger.info("基本面数据更新完成:")
            logger.info(f"  总计: {self.stats['total']}")
            logger.info(f"  成功: {self.stats['success']}")
            logger.info(f"  失败: {self.stats['failed']}")
            return self.stats

        except Exception as exc:
            logger.error(f"更新基本面数据失败: {exc}")
            self.stats["failed"] = self.stats.get("total", 0)
            return self.stats

    def _to_fundamental_records(self, df: pd.DataFrame) -> pd.DataFrame:
        records = df.copy()
        keep_columns = ["date", "symbol", *self.REQUIRED_COLUMNS]
        for column in self.REQUIRED_COLUMNS:
            if column not in records.columns:
                records[column] = None

        # Fields unavailable in ASHAREEODDERIVATIVEINDICATOR stay empty in the
        # local snapshot table until a dedicated financial-statement source is added.
        unavailable_columns = [
            "roe",
            "roa",
            "profit_margin",
            "operating_margin",
            "debt_ratio",
            "current_ratio",
        ]
        for column in unavailable_columns:
            records[column] = None

        for column in self.REQUIRED_COLUMNS:
            records[column] = pd.to_numeric(records[column], errors="coerce")

        return records[keep_columns]

    def _format_symbol(self, code: str) -> str:
        code = str(code).zfill(6)
        if code.startswith("6"):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        if code.startswith(("8", "4")):
            return f"{code}.BJ"
        return code


if __name__ == "__main__":
    downloader = FundamentalDownloader()
    stats = downloader.update_fundamental_data()
    print(stats)
