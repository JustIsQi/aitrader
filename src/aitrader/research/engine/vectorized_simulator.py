"""向量化日频回测引擎。

修复旧版的所有时序与执行问题：

- T+1：target_weights.loc[t] = "t 日收盘形成的信号"，在下一交易日生效。
- 涨跌停过滤：无法买入/卖出的股票回退到原仓位。
- 空仓现金利率：未投入仓位按 cash_rate_annual 计入日收益。
- 分项交易成本：通过 CostModel.cost(buy_value, sell_value) 拿真实成本。
- 单股权重上限：max_single_weight。

target_weights 约定：
    NaN = 该日无调仓信号（保持现有仓位）；数值 = 目标权重。

execution：
    next_open  - 信号 t → 次日 t+1 开盘换仓 → 当日 close-to-close 全部归新权重；
    next_close - 信号 t → 次日 t+1 收盘换仓 → t+1 收益归旧权重，t+2 起归新权重。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd

from ..data.panel_loader import PricePanels
from ..data.tradability_mask import TradabilityMask
from .cost_model import AshareCostModel, CostModel


logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    daily_returns: pd.Series
    equity_curve: pd.Series
    holdings: pd.DataFrame
    rebalance_log: pd.DataFrame
    invested_exposure: pd.Series

    def to_dict(self) -> dict:
        return {
            "n_days": int(len(self.daily_returns)),
            "n_rebalances": int(len(self.rebalance_log)),
            "first_trade_date": (
                str(self.rebalance_log["date"].iloc[0])
                if not self.rebalance_log.empty
                else ""
            ),
        }


class VectorizedSimulator:
    def __init__(
        self,
        panels: PricePanels,
        tradability: Optional[TradabilityMask] = None,
        cost_model: Optional[CostModel] = None,
        cash_rate_annual: float = 0.02,
        execution: Literal["next_open", "next_close"] = "next_open",
        max_single_weight: float = 1.0,
    ) -> None:
        self.panels = panels
        self.tradability = tradability or TradabilityMask.from_panels(panels)
        self.cost_model = cost_model or AshareCostModel()
        self.cash_rate_annual = float(cash_rate_annual)
        self.execution = execution
        self.max_single_weight = float(max_single_weight)
        self.symbols = list(panels.close_adj.columns)
        self.dates = panels.close_adj.index
        self._returns = panels.close_adj.pct_change().fillna(0.0)

    def simulate(
        self,
        target_weights: pd.DataFrame,
        *,
        initial_capital: float = 10_000_000.0,
    ) -> SimulationResult:
        target = target_weights.reindex(index=self.dates, columns=self.symbols)
        target = target.shift(1)
        target.iloc[0] = np.nan
        if 0 < self.max_single_weight < 1.0:
            target = target.where(target.isna(), target.clip(upper=self.max_single_weight))

        returns_arr = self._returns.values
        target_arr = target.values
        can_buy = self.tradability.can_buy.reindex_like(target).fillna(False).values
        can_sell = self.tradability.can_sell.reindex_like(target).fillna(False).values
        has_data = self.tradability.can_hold.reindex_like(target).fillna(False).values

        n_days, n_symbols = target_arr.shape
        current = np.zeros(n_symbols, dtype=float)
        equity = float(initial_capital)
        holdings_history = np.zeros_like(target_arr)
        daily_returns = np.zeros(n_days, dtype=float)
        invested_exposure = np.zeros(n_days, dtype=float)
        rebalance_records: list[dict] = []
        cash_daily = (1.0 + self.cash_rate_annual) ** (1.0 / 252.0) - 1.0
        rebalance_first = self.execution == "next_open"

        for i in range(n_days):
            tgt = target_arr[i]
            cost_drag = 0.0

            if rebalance_first:
                current, cost_drag = self._rebalance(
                    i, tgt, current, can_buy, can_sell, has_data, equity, rebalance_records
                )

            row_returns = np.nan_to_num(returns_arr[i], nan=0.0)
            invested = float(current.sum())
            cash_weight = max(1.0 - invested, 0.0)
            asset_pnl = float((current * row_returns).sum())
            cash_pnl = cash_weight * cash_daily
            gross_return = asset_pnl + cash_pnl

            if not rebalance_first:
                tentative_equity = equity * (1.0 + gross_return)
                current, post_cost = self._rebalance(
                    i, tgt, current, can_buy, can_sell, has_data, tentative_equity, rebalance_records
                )
                cost_drag = post_cost

            net_return = gross_return - cost_drag
            equity *= (1.0 + net_return)
            daily_returns[i] = net_return
            holdings_history[i] = current
            invested_exposure[i] = float(current.sum())

        daily_series = pd.Series(daily_returns, index=self.dates, name="strategy")
        equity_curve = (1.0 + daily_series).cumprod() * float(initial_capital)
        holdings_df = pd.DataFrame(holdings_history, index=self.dates, columns=self.symbols)
        invested_series = pd.Series(invested_exposure, index=self.dates, name="invested")
        rebalance_df = pd.DataFrame(rebalance_records)

        return SimulationResult(
            daily_returns=daily_series,
            equity_curve=equity_curve,
            holdings=holdings_df,
            rebalance_log=rebalance_df,
            invested_exposure=invested_series,
        )

    def _rebalance(
        self,
        i: int,
        tgt: np.ndarray,
        current: np.ndarray,
        can_buy: np.ndarray,
        can_sell: np.ndarray,
        has_data: np.ndarray,
        equity_value: float,
        rebalance_records: list,
    ):
        if not bool(np.any(~np.isnan(tgt))):
            return current, 0.0
        desired = np.where(np.isnan(tgt), current, tgt)
        desired = np.clip(desired, 0.0, None)
        executable = desired.copy()
        buy_blocked = (executable > current) & (~can_buy[i])
        executable[buy_blocked] = current[buy_blocked]
        sell_blocked = (executable < current) & (~can_sell[i])
        executable[sell_blocked] = current[sell_blocked]
        executable[~has_data[i]] = current[~has_data[i]]
        executable = np.clip(executable, 0.0, None)
        delta = executable - current
        buy_value_pct = float(np.clip(delta, 0.0, None).sum())
        sell_value_pct = float(np.clip(-delta, 0.0, None).sum())
        if buy_value_pct + sell_value_pct <= 1e-12:
            return current, 0.0
        equity_value = max(equity_value, 1e-9)
        buy_value = buy_value_pct * equity_value
        sell_value = sell_value_pct * equity_value
        n_buys = int((delta > 1e-12).sum())
        n_sells = int((delta < -1e-12).sum())
        cost_value = self.cost_model.cost(
            buy_value=buy_value,
            sell_value=sell_value,
            n_buys=n_buys,
            n_sells=n_sells,
        )
        cost_drag = cost_value / equity_value if equity_value > 0 else 0.0
        new_current = executable
        rebalance_records.append(
            {
                "date": self.dates[i],
                "buy_pct": buy_value_pct,
                "sell_pct": sell_value_pct,
                "turnover_pct": (buy_value_pct + sell_value_pct) / 2.0,
                "cost_pct": cost_drag,
                "n_holdings": int((new_current > 0).sum()),
                "gross_exposure": float(new_current.sum()),
            }
        )
        return new_current, cost_drag


def simulate(
    panels: PricePanels,
    target_weights: pd.DataFrame,
    *,
    tradability: Optional[TradabilityMask] = None,
    cost_model: Optional[CostModel] = None,
    cash_rate_annual: float = 0.02,
    execution: Literal["next_open", "next_close"] = "next_open",
    max_single_weight: float = 1.0,
    initial_capital: float = 10_000_000.0,
) -> SimulationResult:
    sim = VectorizedSimulator(
        panels=panels,
        tradability=tradability,
        cost_model=cost_model,
        cash_rate_annual=cash_rate_annual,
        execution=execution,
        max_single_weight=max_single_weight,
    )
    return sim.simulate(target_weights, initial_capital=initial_capital)
