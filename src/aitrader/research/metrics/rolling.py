"""滚动指标。"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


def rolling_sharpe(
    daily_returns: pd.Series,
    window: int = TRADING_DAYS_PER_YEAR,
    risk_free_annual: float = 0.02,
) -> pd.Series:
    rf = (1.0 + risk_free_annual) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    excess = daily_returns - rf
    mean = excess.rolling(window, min_periods=window // 2).mean()
    std = excess.rolling(window, min_periods=window // 2).std(ddof=1)
    sharpe = mean / std * np.sqrt(TRADING_DAYS_PER_YEAR)
    return sharpe


def rolling_alpha(
    daily_returns: pd.Series,
    benchmark_returns: pd.Series,
    window: int = TRADING_DAYS_PER_YEAR,
    risk_free_annual: float = 0.02,
) -> pd.Series:
    rf = (1.0 + risk_free_annual) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    aligned = pd.concat([daily_returns, benchmark_returns], axis=1, join="inner").dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    aligned.columns = ["s", "b"]
    excess_s = aligned["s"] - rf
    excess_b = aligned["b"] - rf

    def _alpha(window_df: pd.DataFrame) -> float:
        if len(window_df) < window // 2:
            return float("nan")
        cov = float(np.cov(window_df["s"].values, window_df["b"].values, ddof=1)[0, 1])
        var_b = float(np.var(window_df["b"].values, ddof=1))
        if var_b <= 0:
            return float("nan")
        beta = cov / var_b
        a_daily = float(window_df["s"].mean()) - beta * float(window_df["b"].mean())
        return a_daily * TRADING_DAYS_PER_YEAR

    pair = pd.concat([excess_s.rename("s"), excess_b.rename("b")], axis=1)
    out = []
    idx = []
    for end in range(window, len(pair) + 1):
        sub = pair.iloc[end - window: end]
        out.append(_alpha(sub))
        idx.append(pair.index[end - 1])
    return pd.Series(out, index=idx, name="rolling_alpha")
