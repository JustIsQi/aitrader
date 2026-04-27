"""复杂度缺口风控策略的 select_fn。

修复点：
- 复杂度缺口仅在 ``rebalance_dates`` 上计算，避免逐日 O(T²) 重算。
- 风控开关 (`risk_position`) 与持仓篮子 (`top_k_momentum`) 显式分离：
  风控 → exposure ∈ {0, half, full}；持仓篮子 → 60 日动量 Top-K。
- 阈值进入 grid。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aitrader.research.runner.specs import SelectFnContext, SelectionResult
from aitrader.research.signals.network import complexity_gap


logger = logging.getLogger(__name__)


def _previous_idx(index: pd.DatetimeIndex, dt: pd.Timestamp):
    pos = index.get_indexer([dt])[0]
    if pos <= 0:
        return None
    return index[pos - 1]


def select_complexity_gap(context: SelectFnContext, params: dict) -> SelectionResult:
    panels = context.panels
    universe = context.universe
    rebalance_dates = context.rebalance_dates

    gap_window = int(params.get("gap_window", 60))
    momentum_lookback = int(params.get("momentum_lookback", 60))
    risk_off_q = float(params.get("risk_off_q", 0.35))
    risk_on_q = float(params.get("risk_on_q", 0.55))
    history_window = int(params.get("history_window", 126))
    min_history = int(params.get("min_history", 52))
    top_k = int(params.get("top_k", 15))
    full_weight = float(params.get("full_weight", 1.0))
    half_weight = float(params.get("half_weight", 0.5))

    close = panels.close_adj
    returns = close.pct_change()
    momentum = close.pct_change(momentum_lookback)

    target = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    signal_rows: list[dict] = []

    # 仅在 rebalance_dates 的"prior"日上算 gap，O(T)
    gap_lookup: dict[pd.Timestamp, float] = {}
    prior_dates: list[pd.Timestamp] = []
    for dt in rebalance_dates:
        prior = _previous_idx(close.index, dt)
        if prior is not None:
            prior_dates.append(prior)
    for prior in prior_dates:
        window = returns.loc[:prior].tail(gap_window)
        symbols = universe.universe_for_trading(prior)
        if symbols:
            window = window.reindex(columns=[s for s in symbols if s in window.columns])
        valid = window.dropna(axis=1, thresh=int(gap_window * 0.7))
        if valid.shape[1] < 12:
            continue
        gap_lookup[prior] = complexity_gap(valid)
    gap_series = pd.Series(gap_lookup).sort_index()

    invested = 0.0
    for dt in rebalance_dates:
        prior = _previous_idx(close.index, dt)
        if prior is None or prior not in gap_series.index:
            continue
        history = gap_series.loc[:prior].dropna().tail(history_window)
        if len(history) < min_history:
            continue
        current_gap = float(gap_series.loc[prior])
        if not np.isfinite(current_gap):
            continue
        risk_off_threshold = float(history.quantile(risk_off_q))
        risk_on_threshold = float(history.quantile(risk_on_q))
        recent_mean = float(history.tail(4).mean())

        if current_gap <= risk_off_threshold:
            invested = 0.0
        elif current_gap >= risk_on_threshold and current_gap >= recent_mean:
            invested = full_weight
        else:
            invested = half_weight

        if invested <= 0:
            target.loc[dt, :] = 0.0
            signal_rows.append(
                {
                    "rebalance_date": dt.strftime("%Y-%m-%d"),
                    "signal_date": prior.strftime("%Y-%m-%d"),
                    "complexity_gap": current_gap,
                    "risk_off_threshold": risk_off_threshold,
                    "risk_on_threshold": risk_on_threshold,
                    "exposure": 0.0,
                    "n_holdings_target": 0,
                }
            )
            continue

        # 持仓篮子：60 日动量 Top-K
        symbols = universe.universe_for_trading(dt)
        mom_scores = momentum.loc[prior].reindex(symbols).dropna()
        selected = mom_scores.sort_values(ascending=False).head(top_k).index.tolist()
        if not selected:
            target.loc[dt, :] = 0.0
            continue

        weight = invested / len(selected)
        target.loc[dt, :] = 0.0
        for s in selected:
            if s in target.columns:
                target.loc[dt, s] = weight

        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "complexity_gap": current_gap,
                "risk_off_threshold": risk_off_threshold,
                "risk_on_threshold": risk_on_threshold,
                "exposure": invested,
                "n_holdings_target": len(selected),
            }
        )

    return SelectionResult(target_weights=target, signal_df=pd.DataFrame(signal_rows))
