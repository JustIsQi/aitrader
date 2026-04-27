"""基准策略的统一规格与构造入口。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from ..data.dynamic_universe import DynamicLiquidUniverse
from ..data.panel_loader import PricePanels


@dataclass
class BaselineSpec:
    """基准策略声明。

    - ``name``: 显示名（出现在报告里）
    - ``builder``: 调用 ``builder(panels, universe, rebalance_dates)`` 返回 ``target_weights``
    - ``rebalance_freq``: ``W`` / ``M``，仅供 buy_and_hold 等策略内部使用
    """

    name: str
    builder: Callable[..., pd.DataFrame]
    kwargs: dict = field(default_factory=dict)


def build_baseline_targets(
    spec: BaselineSpec,
    *,
    panels: PricePanels,
    universe: DynamicLiquidUniverse,
    rebalance_dates: list[pd.Timestamp],
) -> pd.DataFrame:
    return spec.builder(
        panels=panels,
        universe=universe,
        rebalance_dates=rebalance_dates,
        **spec.kwargs,
    )
