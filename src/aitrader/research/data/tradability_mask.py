"""可交易性掩码。

判定每只股票每天是否可买、可卖、可持，用于回测引擎在调仓日做过滤。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .panel_loader import PricePanels


@dataclass
class TradabilityMask:
    """逐日可交易性面板（True 表示可执行）。

    - ``can_buy``: 当日不涨停 + 有成交量
    - ``can_sell``: 当日不跌停 + 有成交量
    - ``can_hold``: 仅要求有数据
    """

    can_buy: pd.DataFrame
    can_sell: pd.DataFrame
    can_hold: pd.DataFrame

    @classmethod
    def from_panels(cls, panels: PricePanels) -> "TradabilityMask":
        # 涨跌停标志：1=涨停, -1=跌停, 0=普通；NaN 视作未知
        status = panels.up_down_limit_status
        if status is None or status.empty:
            status = pd.DataFrame(0.0, index=panels.close_adj.index, columns=panels.close_adj.columns)
        else:
            status = status.reindex(index=panels.close_adj.index, columns=panels.close_adj.columns)

        volume = panels.volume.reindex_like(panels.close_adj).fillna(0.0)
        has_data = panels.close_unadj.reindex_like(panels.close_adj).notna()
        traded = volume.gt(0)

        is_limit_up = status.eq(1)
        is_limit_down = status.eq(-1)

        can_buy = traded & (~is_limit_up) & has_data
        can_sell = traded & (~is_limit_down) & has_data
        can_hold = has_data

        return cls(
            can_buy=can_buy.astype(bool),
            can_sell=can_sell.astype(bool),
            can_hold=can_hold.astype(bool),
        )
