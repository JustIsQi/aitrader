"""
Wind A股行情读取工具。

历史价格镜像表已退役，调用方应直接读取 Wind MySQL。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd

from aitrader.infrastructure.config.logging import logger
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


class StockDownloader:
    """A 股历史行情直读工具（Wind only）。"""

    def __init__(self, reader: Optional[MySQLAshareReader] = None):
        self.reader = reader or MySQLAshareReader()

    def _normalize_symbol(self, symbol: str) -> str:
        symbol = str(symbol).strip().upper()
        if "." in symbol:
            return symbol
        code = symbol.zfill(6)
        if code.startswith("6"):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        if code.startswith(("4", "8")):
            return f"{code}.BJ"
        return code

    def _to_price_df(self, wind_df: pd.DataFrame) -> pd.DataFrame:
        if wind_df.empty:
            return pd.DataFrame()

        df = wind_df.copy()

        out = pd.DataFrame({
            "date": pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce"),
            "open": pd.to_numeric(df.get("open"), errors="coerce"),
            "high": pd.to_numeric(df.get("high"), errors="coerce"),
            "low": pd.to_numeric(df.get("low"), errors="coerce"),
            "close": pd.to_numeric(df.get("close"), errors="coerce"),
            "volume": pd.to_numeric(df.get("volume"), errors="coerce"),
            "amount": pd.to_numeric(df.get("amount"), errors="coerce"),
            "amplitude": pd.NA,
            "change_pct": pd.to_numeric(df.get("change_pct"), errors="coerce"),
            "change_amount": pd.NA,
            "turnover_rate": pd.NA,
        })
        out = out.dropna(subset=["date", "open", "high", "low", "close"])
        return out

    def fetch_stock_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq",
    ) -> Optional[pd.DataFrame]:
        normalized = self._normalize_symbol(symbol)
        start = (start_date or "20200101").replace("-", "")
        end = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
        try:
            adjust_type = (adjust or "qfq").lower()
            if adjust_type != "qfq":
                raise ValueError("当前仅支持直接读取 Wind 前复权行情（qfq）")

            query = """
                SELECT
                    TRADE_DT AS date,
                    S_INFO_WINDCODE AS symbol,
                    S_DQ_ADJOPEN AS open,
                    S_DQ_ADJHIGH AS high,
                    S_DQ_ADJLOW AS low,
                    S_DQ_ADJCLOSE AS close,
                    S_DQ_VOLUME AS volume,
                    S_DQ_AMOUNT AS amount,
                    S_DQ_PCTCHANGE AS change_pct
                FROM ASHAREEODPRICES
                WHERE S_INFO_WINDCODE = %s
                  AND TRADE_DT >= %s
                  AND TRADE_DT <= %s
                ORDER BY TRADE_DT ASC
            """
            wind_df = self.reader.read_query(query, [normalized, start, end])
            df = self._to_price_df(wind_df)
            return df
        except Exception as e:
            logger.error(f"读取 Wind 行情失败 {normalized}: {e}")
            return None

    def update_stock_data(self, symbol: str) -> bool:
        raise RuntimeError("本地行情镜像已移除，请直接通过 Wind MySQL 读取价格数据。")

    def update_stock_data_qfq(self, symbol: str) -> bool:
        raise RuntimeError("本地前复权镜像已移除，请直接通过 Wind MySQL 读取 qfq 价格数据。")

    def update_all_stock_data(self) -> dict:
        raise RuntimeError("本地行情批量镜像已移除，请直接通过 Wind MySQL 批量读取价格数据。")

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """
        直接从 Wind 读取 A 股代码列表。
        """
        try:
            query = """
                SELECT DISTINCT S_INFO_WINDCODE AS symbol
                FROM ASHAREEODPRICES
                WHERE S_INFO_WINDCODE IS NOT NULL
                ORDER BY S_INFO_WINDCODE
            """
            wind_df = self.reader.read_query(query, [])
            if wind_df is not None and not wind_df.empty:
                wind_df["symbol"] = wind_df["symbol"].astype(str).str.upper()
                return wind_df[["symbol"]]
        except Exception as e:
            logger.error(f"Wind 股票列表读取失败: {e}")
        return pd.DataFrame(columns=["symbol"])
