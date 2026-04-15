from datetime import datetime
from typing import Optional

import pandas as pd
from aitrader.infrastructure.config.logging import logger

from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


class DbDataLoader:
    """A-share batch data loader backed by Wind MySQL prices and indicators."""

    SUPPORTED_ADJUST_TYPES = {"qfq"}

    def __init__(self, auto_download=False, adjust_type="qfq", reader: Optional[MySQLAshareReader] = None):
        """
        Args:
            auto_download: Kept for backward compatibility. Missing MySQL data is
                never downloaded or written back.
            adjust_type: supported value is 'qfq', mapped to Wind adjusted columns.
            reader: optional reader injection for tests.
        """
        self.auto_download = auto_download
        self.adjust_type = adjust_type
        self.reader = reader or MySQLAshareReader()
        logger.info(f"DbDataLoader: 使用 MySQL/Wind A股行情和衍生指标作为数据源, 复权类型={adjust_type}")

    def read_dfs(
        self,
        symbols: list[str],
        start_date="20100101",
        end_date=datetime.now().strftime("%Y%m%d"),
    ):
        """Read multiple A-share symbols as {symbol: DataFrame}."""
        if not symbols:
            raise ValueError("没有提供任何标的代码。请确保策略生成了有效的A股股票列表。")

        if self.adjust_type not in self.SUPPORTED_ADJUST_TYPES:
            raise ValueError(
                f"不支持的复权类型: {self.adjust_type}. MySQL/Wind 读取当前仅支持 qfq。"
            )

        unique_symbols = sorted({symbol for symbol in symbols if symbol})
        start_date_fmt = self._format_log_date(start_date)
        end_date_fmt = self._format_log_date(end_date)
        logger.info(
            f"DbDataLoader: 开始加载 {len(unique_symbols)} 个A股标的数据 "
            f"({start_date_fmt} ~ {end_date_fmt})"
        )

        df_all = self.reader.read_prices(unique_symbols, start_date, end_date)
        if df_all.empty:
            raise ValueError(
                f"没有可用的MySQL/Wind A股行情数据。缺失标的: {unique_symbols}"
            )

        dfs = {}
        for symbol, group in df_all.groupby("symbol", sort=True):
            group = group.copy()
            group["date"] = pd.to_datetime(group["date"]).dt.strftime("%Y%m%d")
            group.sort_values("date", inplace=True)
            group.dropna(subset=["date", "open", "high", "low", "close"], inplace=True)
            if not group.empty:
                dfs[symbol] = group

        missing_symbols = [symbol for symbol in unique_symbols if symbol not in dfs]
        if not dfs:
            raise ValueError(
                f"没有可用的MySQL/Wind A股行情数据。缺失标的: {missing_symbols}"
            )
        if missing_symbols:
            logger.warning(f"MySQL/Wind A股行情缺失部分标的: {missing_symbols}")

        logger.success(f"✓ MySQL/Wind A股行情加载完成: {len(dfs)} 个标的")
        return dfs

    def _format_log_date(self, value: str) -> str:
        value = str(value).replace("-", "")
        if len(value) == 8:
            return f"{value[:4]}-{value[4:6]}-{value[6:]}"
        return value


# Backward-compatible alias used by older docs/callers.
CsvDataLoader = DbDataLoader


if __name__ == "__main__":
    dfs = DbDataLoader().read_dfs(symbols=["000001.SZ"])
    print(dfs)
