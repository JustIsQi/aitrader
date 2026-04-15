"""
Wind A股行情同步器

从 Wind MySQL 读取 A 股历史数据并写入本地数据库。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy import text

from aitrader.infrastructure.config.logging import logger
from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


class StockDownloader:
    """A 股历史行情同步器（Wind -> 本地 DB）。"""

    def __init__(self, reader: Optional[MySQLAshareReader] = None):
        self.db = get_db()
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

    def _to_db_history_df(self, wind_df: pd.DataFrame, use_qfq: bool) -> pd.DataFrame:
        if wind_df.empty:
            return pd.DataFrame()

        df = wind_df.copy()
        open_col = "open" if use_qfq else "real_open"
        close_col = "close" if use_qfq else "real_close"
        high_col = "high" if use_qfq else "high"
        low_col = "low" if use_qfq else "real_low"

        out = pd.DataFrame({
            "date": pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce"),
            "open": pd.to_numeric(df.get(open_col), errors="coerce"),
            "high": pd.to_numeric(df.get(high_col), errors="coerce"),
            "low": pd.to_numeric(df.get(low_col), errors="coerce"),
            "close": pd.to_numeric(df.get(close_col), errors="coerce"),
            "volume": pd.to_numeric(df.get("volume"), errors="coerce"),
            "amount": pd.to_numeric(df.get("amount"), errors="coerce"),
            "amplitude": pd.NA,
            "change_pct": pd.to_numeric(df.get("change_pct"), errors="coerce"),
            "change_amount": pd.NA,
            "turnover_rate": pd.to_numeric(df.get("turnover_rate"), errors="coerce"),
        })
        out = out.dropna(subset=["date", "open", "high", "low", "close"])
        return out

    def fetch_stock_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "hfq",
    ) -> Optional[pd.DataFrame]:
        normalized = self._normalize_symbol(symbol)
        start = (start_date or "20200101").replace("-", "")
        end = (end_date or datetime.now().strftime("%Y%m%d")).replace("-", "")
        try:
            wind_df = self.reader.read_prices([normalized], start, end)
            use_qfq = (adjust or "").lower() == "qfq"
            df = self._to_db_history_df(wind_df, use_qfq=use_qfq)
            return df
        except Exception as e:
            logger.error(f"读取 Wind 行情失败 {normalized}: {e}")
            return None

    def update_stock_data(self, symbol: str) -> bool:
        """增量更新非复权（real_*）行情到 stock_history。"""
        try:
            normalized = self._normalize_symbol(symbol)
            latest_date = self.db.get_stock_latest_date(normalized)
            end_date = datetime.now().strftime("%Y%m%d")
            if latest_date:
                start_date = (latest_date + timedelta(days=1)).strftime("%Y%m%d")
                if start_date > end_date:
                    logger.info(f"{normalized} 数据已是最新")
                    return True
            else:
                start_date = "20200101"

            df = self.fetch_stock_history(normalized, start_date, end_date, adjust="hfq")
            if df is None or df.empty:
                logger.info(f"{normalized} 无新增数据")
                return True
            return self.db.append_stock_history(df, normalized)
        except Exception as e:
            logger.error(f"更新股票数据失败 {symbol}: {e}")
            return False

    def update_stock_data_qfq(self, symbol: str) -> bool:
        """增量更新前复权行情到 stock_history_qfq。"""
        try:
            normalized = self._normalize_symbol(symbol)
            latest_date = self.db.get_stock_qfq_latest_date(normalized)
            end_date = datetime.now().strftime("%Y%m%d")
            if latest_date:
                start_date = (latest_date + timedelta(days=1)).strftime("%Y%m%d")
                if start_date > end_date:
                    logger.info(f"{normalized} 前复权数据已是最新")
                    return True
            else:
                start_date = "20200101"

            df = self.fetch_stock_history(normalized, start_date, end_date, adjust="qfq")
            if df is None or df.empty:
                logger.info(f"{normalized} 无新增前复权数据")
                return True
            return self.db.append_stock_history_qfq(df, normalized)
        except Exception as e:
            logger.error(f"更新前复权数据失败 {symbol}: {e}")
            return False

    def update_all_stock_data(self) -> dict:
        symbols = self.db.get_stock_codes()
        stats = {"total": len(symbols), "success": 0, "failed": 0}
        logger.info(f"开始同步 {len(symbols)} 只股票（Wind）")
        for idx, symbol in enumerate(symbols, 1):
            if idx % 100 == 0:
                logger.info(f"进度: {idx}/{len(symbols)}")
            if self.update_stock_data(symbol):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        logger.info(f"同步完成: 成功 {stats['success']}, 失败 {stats['failed']}")
        return stats

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """
        读取 A 股代码列表（优先 Wind，兜底本地 stock_metadata）。
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
            logger.warning(f"Wind 股票列表读取失败，尝试本地表兜底: {e}")

        with self.db.get_session() as session:
            rows = session.execute(text("SELECT symbol FROM stock_metadata ORDER BY symbol")).fetchall()
        if not rows:
            return pd.DataFrame(columns=["symbol"])
        return pd.DataFrame({"symbol": [r[0] for r in rows]})

