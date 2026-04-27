"""同池等权全持基准。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.dynamic_universe import DynamicLiquidUniverse
from ..data.panel_loader import PricePanels


def equal_weight_universe_weights(
    *,
    panels: PricePanels,
    universe: DynamicLiquidUniverse,
    rebalance_dates: list[pd.Timestamp],
) -> pd.DataFrame:
    target = pd.DataFrame(np.nan, index=panels.close_adj.index, columns=panels.close_adj.columns)
    for dt in rebalance_dates:
        if dt not in target.index:
            continue
        symbols = universe.universe_for_trading(dt)
        if not symbols:
            continue
        weight = 1.0 / len(symbols)
        target.loc[dt, :] = 0.0
        for s in symbols:
            if s in target.columns:
                target.loc[dt, s] = weight
    return target
