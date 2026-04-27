"""偏度分散度择时策略的 select_fn。

修复点：
- 信号池（用整个动态池子）与持仓池（用前 N 只）解耦，缓解 30 只小池子的统计噪声。
- 信号输出连续 ``risk_exposure ∈ [0, 1]``，由 runner 端的 tiered_weight 政策映射成多档仓位。
- 阈值改为参数，可在 grid ablation 中扫描。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aitrader.research.runner.specs import SelectFnContext, SelectionResult


def _previous_idx(index: pd.DatetimeIndex, dt: pd.Timestamp):
    pos = index.get_indexer([dt])[0]
    if pos <= 0:
        return None
    return index[pos - 1]


def select_skew_dispersion(context: SelectFnContext, params: dict) -> SelectionResult:
    panels = context.panels
    universe = context.universe
    rebalance_dates = context.rebalance_dates

    skew_window = int(params.get("skew_window", 20))
    smooth_window = int(params.get("smooth_window", 5))
    risk_on_q = float(params.get("risk_on_q", 0.45))
    risk_off_q = float(params.get("risk_off_q", 0.70))
    history_window = int(params.get("history_window", 252))
    min_history = int(params.get("min_history", 126))
    holding_top_n = int(params.get("holding_top_n", 30))
    on_weight = float(params.get("on_weight", 1.0))
    half_weight = float(params.get("half_weight", 0.5))

    close = panels.close_adj
    returns = close.pct_change()
    realized_skew = returns.rolling(skew_window, min_periods=max(int(skew_window * 0.75), 5)).skew()
    skew_dispersion = realized_skew.std(axis=1, ddof=1).rolling(
        smooth_window, min_periods=max(smooth_window // 2, 1)
    ).mean()

    target = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    invested = 0.0
    signal_rows: list[dict] = []

    for dt in rebalance_dates:
        prior = _previous_idx(close.index, dt)
        if prior is None:
            continue
        history = skew_dispersion.loc[:prior].dropna().tail(history_window)
        if len(history) < min_history:
            continue
        current_value = float(skew_dispersion.loc[prior]) if pd.notna(skew_dispersion.loc[prior]) else float("nan")
        if not np.isfinite(current_value):
            continue

        risk_on_threshold = float(history.quantile(risk_on_q))
        risk_off_threshold = float(history.quantile(risk_off_q))

        # 多档仓位：低于 risk_on → 满仓 on_weight；介于 → 半仓 half_weight；高于 risk_off → 空仓
        if current_value <= risk_on_threshold:
            invested = on_weight
        elif current_value >= risk_off_threshold:
            invested = 0.0
        else:
            invested = half_weight

        # 持仓池：当时动态池的前 N 只
        symbols = universe.universe_for_trading(dt)[:holding_top_n]
        if not symbols or invested <= 0:
            target.loc[dt, :] = 0.0
        else:
            valid = [s for s in symbols if s in target.columns]
            target.loc[dt, :] = 0.0
            if valid:
                w = invested / len(valid)
                for s in valid:
                    target.loc[dt, s] = w

        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "skew_dispersion": current_value,
                "risk_on_threshold": risk_on_threshold,
                "risk_off_threshold": risk_off_threshold,
                "exposure": invested,
                "n_holdings_target": len(symbols) if invested > 0 else 0,
            }
        )

    return SelectionResult(target_weights=target, signal_df=pd.DataFrame(signal_rows))
