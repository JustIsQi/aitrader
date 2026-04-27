"""runner 入口的数据规格。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pandas as pd

from ..data.dynamic_universe import DynamicLiquidUniverse, UniverseSpec
from ..data.panel_loader import PricePanels


@dataclass
class RebalanceSpec:
    """调仓 + 仓位政策规格。"""

    freq: str = "W"
    warmup_days: int = 60
    max_single_weight: float = 0.5


@dataclass
class TrainHoldoutWindow:
    train_start: str = "2019-01-01"
    train_end: str = "2021-12-31"
    holdout_start: str = "2022-01-01"
    holdout_end: str = "2024-12-31"


@dataclass
class SelectFnContext:
    panels: PricePanels
    universe: DynamicLiquidUniverse
    rebalance_dates: list[pd.Timestamp]


@dataclass
class SelectionResult:
    target_weights: pd.DataFrame
    signal_df: Optional[pd.DataFrame] = None
    extras: dict = field(default_factory=dict)


@dataclass
class StrategySpec:
    paper_id: str
    paper_title: str
    strategy_name: str
    methodology: str
    universe_spec: UniverseSpec
    rebalance: RebalanceSpec
    select_fn: Callable[[SelectFnContext, dict], SelectionResult]
    select_params: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    param_grid: Optional[dict[str, list[Any]]] = None
    param_grid_filter: Optional[Callable[[dict], bool]] = None
    train_holdout: TrainHoldoutWindow = field(default_factory=TrainHoldoutWindow)
