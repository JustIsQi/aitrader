from __future__ import annotations

from typing import Protocol
import pandas as pd


class MarketDataReader(Protocol):
    def read_dfs(self, symbols: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
        ...
