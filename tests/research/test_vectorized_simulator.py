"""向量化 simulator 单元测试。

覆盖：
- T+1 时序（next_open / next_close）
- 涨跌停回退
- 空仓现金利率
- 分项交易成本
- 单股权重上限
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aitrader.research.data.panel_loader import PricePanels
from aitrader.research.data.tradability_mask import TradabilityMask
from aitrader.research.engine import (
    AshareCostModel,
    ZeroCostModel,
    VectorizedSimulator,
    simulate,
)


def _build_synthetic_panels(close_df: pd.DataFrame, status: pd.DataFrame | None = None) -> PricePanels:
    if status is None:
        status = pd.DataFrame(0.0, index=close_df.index, columns=close_df.columns)
    return PricePanels(
        close_adj=close_df,
        open_adj=close_df,
        high_adj=close_df,
        low_adj=close_df,
        close_unadj=close_df,
        open_unadj=close_df,
        volume=pd.DataFrame(1e7, index=close_df.index, columns=close_df.columns),
        amount=pd.DataFrame(1e9, index=close_df.index, columns=close_df.columns),
        up_down_limit_status=status,
    )


@pytest.fixture
def simple_panels() -> PricePanels:
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    close = pd.DataFrame(
        {
            "A": [100 * 1.01**i for i in range(10)],
            "B": [100.0] * 10,
        },
        index=dates,
    )
    return _build_synthetic_panels(close)


def test_t1_timing_next_open(simple_panels: PricePanels) -> None:
    target = pd.DataFrame(np.nan, index=simple_panels.close_adj.index, columns=simple_panels.close_adj.columns)
    target.iloc[1] = [1.0, 0.0]
    r = simulate(
        simple_panels,
        target,
        cost_model=ZeroCostModel(),
        cash_rate_annual=0.0,
        execution="next_open",
    )
    # next_open: 信号在 day 1 收盘 → day 2 起持仓 A → day 2 收益 = +1%
    assert r.daily_returns.iloc[0] == pytest.approx(0.0)
    assert r.daily_returns.iloc[1] == pytest.approx(0.0)
    assert r.daily_returns.iloc[2] == pytest.approx(0.01, abs=1e-9)
    assert r.daily_returns.iloc[5] == pytest.approx(0.01, abs=1e-9)
    assert len(r.rebalance_log) == 1


def test_t1_timing_next_close(simple_panels: PricePanels) -> None:
    target = pd.DataFrame(np.nan, index=simple_panels.close_adj.index, columns=simple_panels.close_adj.columns)
    target.iloc[1] = [1.0, 0.0]
    r = simulate(
        simple_panels,
        target,
        cost_model=ZeroCostModel(),
        cash_rate_annual=0.0,
        execution="next_close",
    )
    # next_close: 信号在 day 1 收盘 → day 2 收盘换仓 → day 3 起得 +1%
    assert r.daily_returns.iloc[2] == pytest.approx(0.0)
    assert r.daily_returns.iloc[3] == pytest.approx(0.01, abs=1e-9)


def test_limit_up_blocks_buy() -> None:
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    close = pd.DataFrame({"A": [100.0] * 10, "B": [100.0] * 10}, index=dates)
    status = pd.DataFrame(0.0, index=dates, columns=["A", "B"])
    status.iloc[2, 0] = 1.0  # A 涨停
    panels = _build_synthetic_panels(close, status)
    target = pd.DataFrame(np.nan, index=dates, columns=["A", "B"])
    target.iloc[1] = [1.0, 0.0]
    r = simulate(panels, target, cost_model=ZeroCostModel(), cash_rate_annual=0.0, execution="next_open")
    assert r.holdings.iloc[2, 0] == pytest.approx(0.0)


def test_limit_down_blocks_sell() -> None:
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    close = pd.DataFrame({"A": [100.0] * 10, "B": [100.0] * 10}, index=dates)
    status = pd.DataFrame(0.0, index=dates, columns=["A", "B"])
    panels = _build_synthetic_panels(close, status)
    # day 1 信号：满仓 A → day 2 起 100% A
    # day 4 信号：清仓 A → day 5 跌停，不能卖
    target = pd.DataFrame(np.nan, index=dates, columns=["A", "B"])
    target.iloc[1] = [1.0, 0.0]
    target.iloc[4] = [0.0, 0.0]
    status.iloc[5, 0] = -1.0  # day 5 跌停
    r = simulate(panels, target, cost_model=ZeroCostModel(), cash_rate_annual=0.0, execution="next_open")
    # day 5 想清仓但跌停 → 维持原仓 A=1.0
    assert r.holdings.iloc[5, 0] == pytest.approx(1.0)


def test_cash_rate_when_empty() -> None:
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    close = pd.DataFrame({"A": [100.0] * 10}, index=dates)
    panels = _build_synthetic_panels(close)
    target = pd.DataFrame(np.nan, index=dates, columns=["A"])
    r = simulate(panels, target, cost_model=ZeroCostModel(), cash_rate_annual=0.0252)
    expected = (1.0252) ** (1 / 252) - 1
    assert r.daily_returns.iloc[5] == pytest.approx(expected, abs=1e-12)


def test_cost_model_breakdown() -> None:
    dates = pd.date_range("2020-01-01", periods=10, freq="B")
    close = pd.DataFrame({"A": [100.0] * 10}, index=dates)
    panels = _build_synthetic_panels(close)
    target = pd.DataFrame(np.nan, index=dates, columns=["A"])
    target.iloc[1] = [1.0]
    target.iloc[5] = [0.0]
    cost = AshareCostModel(min_commission=0.0, slippage_bps=0.0)
    r = simulate(panels, target, cost_model=cost, cash_rate_annual=0.0, execution="next_open", initial_capital=10_000_000.0)
    # 第一次买入：cost = 1 × (0.0002 + 0.00001) = 0.00021
    # 第二次卖出：cost = 1 × (0.0002 + 0.0005 + 0.00001) = 0.00071
    assert r.rebalance_log["cost_pct"].iloc[0] == pytest.approx(0.00021, abs=1e-9)
    assert r.rebalance_log["cost_pct"].iloc[1] == pytest.approx(0.00071, abs=1e-9)


def test_max_single_weight_clip() -> None:
    dates = pd.date_range("2020-01-01", periods=5, freq="B")
    close = pd.DataFrame({"A": [100.0] * 5, "B": [100.0] * 5}, index=dates)
    panels = _build_synthetic_panels(close)
    target = pd.DataFrame(np.nan, index=dates, columns=["A", "B"])
    target.iloc[1] = [0.9, 0.1]  # A 想要 90%，但 cap 0.3
    sim = VectorizedSimulator(
        panels,
        cost_model=ZeroCostModel(),
        cash_rate_annual=0.0,
        execution="next_open",
        max_single_weight=0.3,
    )
    r = sim.simulate(target)
    assert r.holdings.iloc[2, 0] == pytest.approx(0.3, abs=1e-9)
    assert r.holdings.iloc[2, 1] == pytest.approx(0.1, abs=1e-9)
