"""同池 N 日动量 Top-K 基准。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.dynamic_universe import DynamicLiquidUniverse
from ..data.panel_loader import PricePanels


def momentum_topk_weights(
    *,
    panels: PricePanels,
    universe: DynamicLiquidUniverse,
    rebalance_dates: list[pd.Timestamp],
    lookback_days: int = 60,
    top_k: int = 15,
) -> pd.DataFrame:
    target = pd.DataFrame(np.nan, index=panels.close_adj.index, columns=panels.close_adj.columns)
    momentum = panels.close_adj.pct_change(lookback_days)
    for dt in rebalance_dates:
        if dt not in target.index:
            continue
        # 用 dt 前一日（避免未来信息）
        prior_idx = target.index.get_indexer([dt])[0]
        if prior_idx <= 0:
            continue
        prior = target.index[prior_idx - 1]
        symbols = universe.universe_for_trading(dt)
        if not symbols:
            continue
        scores = momentum.loc[prior].reindex(symbols).dropna()
        if scores.empty:
            continue
        selected = scores.sort_values(ascending=False).head(top_k).index.tolist()
        if not selected:
            continue
        weight = 1.0 / len(selected)
        target.loc[dt, :] = 0.0
        for s in selected:
            if s in target.columns:
                target.loc[dt, s] = weight
    return target
