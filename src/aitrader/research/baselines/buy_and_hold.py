"""始终持有股票池中前 N 只的基准。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.dynamic_universe import DynamicLiquidUniverse
from ..data.panel_loader import PricePanels


def buy_and_hold_weights(
    *,
    panels: PricePanels,
    universe: DynamicLiquidUniverse,
    rebalance_dates: list[pd.Timestamp],
    top_n: int = 30,
) -> pd.DataFrame:
    """每个 refresh 点重新等权持有当时池子的前 N 只股票。"""
    target = pd.DataFrame(np.nan, index=panels.close_adj.index, columns=panels.close_adj.columns)
    if not rebalance_dates:
        return target
    for dt in rebalance_dates:
        symbols = universe.universe_for_trading(dt)[:top_n]
        if not symbols:
            continue
        weight = 1.0 / len(symbols)
        if dt in target.index:
            target.loc[dt, :] = 0.0
            for s in symbols:
                if s in target.columns:
                    target.loc[dt, s] = weight
    return target
