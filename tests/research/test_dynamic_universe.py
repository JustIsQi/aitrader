"""DynamicLiquidUniverse 单元测试（用 mock 替代真实 MySQL）。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from aitrader.research.data.dynamic_universe import DynamicLiquidUniverse, UniverseSpec


def _make_provider(
    base_symbols_by_date: dict[str, list[str]],
    prices_by_window: dict[tuple[str, str], pd.DataFrame],
):
    provider = MagicMock()

    def get_all_stocks(*, as_of_date=None, **kwargs):
        return base_symbols_by_date.get(as_of_date, [])

    provider.get_all_stocks.side_effect = get_all_stocks
    provider.wind_reader = MagicMock()

    def read_prices(*, symbols=None, start_date=None, end_date=None, include_derivatives=False):
        df = prices_by_window.get((start_date, end_date), pd.DataFrame())
        if df.empty:
            return df
        return df[df["symbol"].isin(symbols)].copy()

    provider.wind_reader.read_prices.side_effect = read_prices
    return provider


def _build_price_panel(symbols: list[str], dates: list[str], amount_map: dict[str, float], close: float = 10.0) -> pd.DataFrame:
    rows = []
    for sym in symbols:
        for dt in dates:
            rows.append(
                {
                    "symbol": sym,
                    "date": pd.Timestamp(dt),
                    "real_close": close,
                    "amount": amount_map.get(sym, 1e6),
                    "volume": 1e5,
                }
            )
    return pd.DataFrame(rows)


_DATES_Q1 = [d.strftime("%Y-%m-%d") for d in pd.date_range("2019-12-01", "2020-01-01", freq="D")]
_DATES_Q2 = [d.strftime("%Y-%m-%d") for d in pd.date_range("2020-03-01", "2020-04-01", freq="D")]


def test_top_n_selection_by_liquidity() -> None:
    base = ["s1", "s2", "s3", "s4", "s5"]
    base_symbols = {"20200101": base}
    panel = _build_price_panel(
        base,
        _DATES_Q1,
        amount_map={"s1": 5e9, "s2": 4e9, "s3": 1e9, "s4": 5e8, "s5": 1e8},
    )
    prices = {("20191217", "20200101"): panel}
    provider = _make_provider(base_symbols, prices)

    spec = UniverseSpec(top_n=3, snapshot_window_days=15, min_close=1.0, min_data_days=0)
    universe = DynamicLiquidUniverse(spec, "2020-01-01", "2020-01-01", universe_provider=provider)
    picked = universe.universe_at("2020-01-01")
    assert picked == ["s1", "s2", "s3"]


def test_min_close_filter_uses_as_of_price() -> None:
    base = ["lo", "hi"]
    base_symbols = {"20200101": base}
    rows = []
    for sym, close in [("lo", 1.0), ("hi", 50.0)]:
        for dt in _DATES_Q1:
            rows.append(
                {"symbol": sym, "date": pd.Timestamp(dt), "real_close": close, "amount": 1e9, "volume": 1e5}
            )
    panel = pd.DataFrame(rows)
    prices = {("20191217", "20200101"): panel}
    provider = _make_provider(base_symbols, prices)

    spec = UniverseSpec(top_n=1, snapshot_window_days=15, min_close=3.0, min_data_days=0)
    universe = DynamicLiquidUniverse(spec, "2020-01-01", "2020-01-01", universe_provider=provider)
    picked = universe.universe_at("2020-01-01")
    assert picked == ["hi"]


def test_universe_changes_across_refresh_dates() -> None:
    """不同 as_of 应该返回不同的池子（验证滚动选池）。"""
    panel_q1 = _build_price_panel(
        ["a", "b", "c"], _DATES_Q1, amount_map={"a": 5e9, "b": 1e8, "c": 1e7}
    )
    panel_q2 = _build_price_panel(
        ["b", "c", "d"], _DATES_Q2, amount_map={"b": 5e9, "c": 1e9, "d": 1e7}
    )
    provider = _make_provider(
        base_symbols_by_date={
            "20200101": ["a", "b", "c"],
            "20200401": ["b", "c", "d"],
        },
        prices_by_window={
            ("20191217", "20200101"): panel_q1,
            ("20200317", "20200401"): panel_q2,
        },
    )
    spec = UniverseSpec(top_n=2, snapshot_window_days=15, min_close=1.0, min_data_days=0, refresh_freq="Q")
    universe = DynamicLiquidUniverse(spec, "2020-01-01", "2020-04-01", universe_provider=provider)

    pool_q1 = universe.universe_at("2020-01-01")
    pool_q2 = universe.universe_at("2020-04-01")
    assert pool_q1 == ["a", "b"]
    assert pool_q2 == ["b", "c"]
    assert pool_q1 != pool_q2


def test_union_symbols_collects_all_refresh_dates() -> None:
    panel_q1 = _build_price_panel(["a", "b"], _DATES_Q1, amount_map={"a": 5e9, "b": 4e9})
    panel_q2 = _build_price_panel(["c", "d"], _DATES_Q2, amount_map={"c": 5e9, "d": 4e9})
    provider = _make_provider(
        base_symbols_by_date={
            "20200101": ["a", "b"],
            "20200401": ["c", "d"],
        },
        prices_by_window={
            ("20191217", "20200101"): panel_q1,
            ("20200317", "20200401"): panel_q2,
        },
    )
    spec = UniverseSpec(top_n=10, snapshot_window_days=15, min_close=1.0, min_data_days=0, refresh_freq="Q")
    universe = DynamicLiquidUniverse(spec, "2020-01-01", "2020-04-01", universe_provider=provider)
    union = universe.union_symbols()
    assert set(union) == {"a", "b", "c", "d"}


def test_universe_for_trading_uses_latest_refresh() -> None:
    panel_q1 = _build_price_panel(["a", "b"], _DATES_Q1, amount_map={"a": 5e9, "b": 4e9})
    panel_q2 = _build_price_panel(["c", "d"], _DATES_Q2, amount_map={"c": 5e9, "d": 4e9})
    provider = _make_provider(
        base_symbols_by_date={
            "20200101": ["a", "b"],
            "20200401": ["c", "d"],
        },
        prices_by_window={
            ("20191217", "20200101"): panel_q1,
            ("20200317", "20200401"): panel_q2,
        },
    )
    spec = UniverseSpec(top_n=2, snapshot_window_days=15, min_close=1.0, min_data_days=0, refresh_freq="Q")
    universe = DynamicLiquidUniverse(spec, "2020-01-01", "2020-04-01", universe_provider=provider)
    # 强制让两次刷新进入缓存
    universe.universe_at("2020-01-01")
    universe.universe_at("2020-04-01")
    pool_mid_q1 = universe.universe_for_trading(pd.Timestamp("2020-02-15"))
    pool_after_q2 = universe.universe_for_trading(pd.Timestamp("2020-04-15"))
    assert pool_mid_q1 == ["a", "b"]
    assert pool_after_q2 == ["c", "d"]
