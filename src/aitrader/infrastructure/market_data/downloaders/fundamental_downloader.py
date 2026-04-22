"""
Wind A股衍生指标读取工具。

本地基本面快照镜像已退役，调用方应直接从 Wind MySQL 读取。
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from aitrader.infrastructure.config.logging import logger

from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


class FundamentalDownloader:
    """Direct Wind derivative-indicator reader kept for compatibility."""

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
        raise RuntimeError("本地基本面镜像已移除，请直接从 Wind MySQL 读取衍生指标。")

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
    raise SystemExit(
        "本地基本面镜像入口已移除，请直接通过 Wind MySQL 读取衍生指标。"
    )
