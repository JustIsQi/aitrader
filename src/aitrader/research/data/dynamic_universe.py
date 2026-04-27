"""动态流动性股票池。

每个调仓日从 ``StockUniverse`` 重新选 Top-N，彻底消除 look-ahead bias。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from aitrader.domain.market.stock_universe import StockUniverse


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UniverseSpec:
    """动态股票池配置。"""

    top_n: int = 120
    min_data_days: int = 750
    min_close: float = 3.0
    snapshot_window_days: int = 45
    refresh_freq: str = "Q"  # 每季度重选；'M' / 'Q' / 'Y'
    exclude_st: bool = True
    exclude_new_ipo_days: int = 365


@dataclass
class _UniverseCacheEntry:
    symbols: list[str]
    snapshot: pd.DataFrame


class DynamicLiquidUniverse:
    """按 as_of 日动态重选流动性股票池。

    与旧版 ``pick_liquid_symbols`` 的区别：
    1. 不再用回测末日的快照作为整段回测的池子，避免幸存者偏差。
    2. ``min_close`` 阈值用 as_of 当时的价格判断，而不是 end_date 的价格。
    3. 提供 ``universe_at(date)`` 给回测引擎按需读取。
    4. ``union_symbols()`` 返回回测期间出现过的所有股票，供 ``PanelLoader``
       一次性加载，避免逐日查 MySQL。
    """

    def __init__(
        self,
        spec: UniverseSpec,
        start_date: pd.Timestamp | str,
        end_date: pd.Timestamp | str,
        universe_provider: StockUniverse | None = None,
    ) -> None:
        self.spec = spec
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        self._provider = universe_provider or StockUniverse()
        self._cache: dict[pd.Timestamp, _UniverseCacheEntry] = {}
        self._refresh_dates: list[pd.Timestamp] | None = None

    def refresh_dates(self) -> list[pd.Timestamp]:
        """返回池子刷新点（含 ``start_date``）。"""
        if self._refresh_dates is not None:
            return list(self._refresh_dates)

        freq = self.spec.refresh_freq.upper()
        if freq not in {"M", "Q", "Y"}:
            raise ValueError(f"refresh_freq 必须为 'M' / 'Q' / 'Y'，实际={freq}")

        offset_alias = {"M": "MS", "Q": "QS", "Y": "AS"}[freq]
        rng = pd.date_range(self.start_date, self.end_date, freq=offset_alias)
        if rng.empty or rng[0] > self.start_date:
            rng = rng.insert(0, self.start_date)
        self._refresh_dates = [pd.Timestamp(dt.normalize()) for dt in rng]
        return list(self._refresh_dates)

    def universe_at(self, as_of: pd.Timestamp | str) -> list[str]:
        """返回 as_of 当天可用的股票池（按流动性 Top-N）。"""
        as_of_ts = pd.Timestamp(as_of).normalize()
        cached = self._cache.get(as_of_ts)
        if cached is not None:
            return list(cached.symbols)

        # 用最近 ``snapshot_window_days`` 估算流动性
        snapshot_end = as_of_ts.strftime("%Y%m%d")
        snapshot_start = (as_of_ts - timedelta(days=self.spec.snapshot_window_days)).strftime("%Y%m%d")

        base_symbols = self._provider.get_all_stocks(
            exclude_st=self.spec.exclude_st,
            exclude_suspend=False,
            exclude_new_ipo_days=self.spec.exclude_new_ipo_days,
            min_data_days=self.spec.min_data_days,
            exclude_restricted_stocks=True,
            as_of_date=snapshot_end,
        )
        if not base_symbols:
            logger.warning("as_of=%s 基础股票池为空", as_of_ts.date())
            self._cache[as_of_ts] = _UniverseCacheEntry([], pd.DataFrame())
            return []

        prices = self._provider.wind_reader.read_prices(
            symbols=base_symbols,
            start_date=snapshot_start,
            end_date=snapshot_end,
            include_derivatives=False,
        )
        if prices.empty:
            logger.warning("as_of=%s 价格快照为空", as_of_ts.date())
            self._cache[as_of_ts] = _UniverseCacheEntry([], pd.DataFrame())
            return []

        prices = prices.copy()
        prices["amount"] = pd.to_numeric(prices["amount"], errors="coerce")
        prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")
        prices["real_close"] = pd.to_numeric(prices["real_close"], errors="coerce")
        prices = prices.dropna(subset=["real_close"])

        per_symbol = prices.sort_values(["symbol", "date"]).groupby("symbol")
        rows = []
        for symbol, df in per_symbol:
            recent = df.tail(20)
            if len(recent) < 10:
                continue
            last = recent.iloc[-1]
            rows.append(
                {
                    "symbol": symbol,
                    "real_close": float(last.get("real_close", np.nan)),
                    "avg_amount": float(recent["amount"].mean()),
                    "median_amount": float(recent["amount"].median()),
                    "avg_volume": float(recent["volume"].mean()),
                }
            )

        snapshot = pd.DataFrame(rows)
        if snapshot.empty:
            logger.warning("as_of=%s 流动性快照统计为空", as_of_ts.date())
            self._cache[as_of_ts] = _UniverseCacheEntry([], snapshot)
            return []

        filtered = snapshot[
            snapshot["real_close"].gt(self.spec.min_close)
            & snapshot["avg_amount"].gt(0)
            & snapshot["avg_volume"].gt(0)
        ].copy()
        if len(filtered) < self.spec.top_n:
            filtered = snapshot[snapshot["avg_amount"].gt(0)].copy()

        filtered = filtered.sort_values(
            ["avg_amount", "median_amount", "avg_volume", "real_close"],
            ascending=[False, False, False, False],
        )
        symbols = filtered["symbol"].head(self.spec.top_n).tolist()
        self._cache[as_of_ts] = _UniverseCacheEntry(symbols, snapshot)
        logger.info(
            "DynamicLiquidUniverse refreshed at %s: %d symbols (target=%d)",
            as_of_ts.date(),
            len(symbols),
            self.spec.top_n,
        )
        return list(symbols)

    def universe_by_date(self) -> dict[pd.Timestamp, list[str]]:
        """返回所有刷新点对应的股票池。"""
        return {dt: self.universe_at(dt) for dt in self.refresh_dates()}

    def union_symbols(self) -> list[str]:
        """所有刷新点出现过的股票并集，用于一次性预加载价格面板。"""
        union: set[str] = set()
        for symbols in self.universe_by_date().values():
            union.update(symbols)
        return sorted(union)

    def universe_for_trading(self, dt: pd.Timestamp) -> list[str]:
        """给定回测交易日 dt，返回最近一次刷新时的股票池。"""
        dt = pd.Timestamp(dt).normalize()
        active_refresh = self.start_date
        for refresh_dt in self.refresh_dates():
            if refresh_dt <= dt:
                active_refresh = refresh_dt
            else:
                break
        return self.universe_at(active_refresh)
