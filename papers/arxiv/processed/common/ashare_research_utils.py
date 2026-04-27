"""向后兼容薄层 - 转发到 ``aitrader.research``。

旧脚本（早期 ``papers/arxiv/processed/<paper>/03_strategy_code.py``）依赖了一组
重复的辅助函数（流动性选股、价格快照、调仓日生成、特征向量、复杂度缺口、写
markdown 报告等）。现在统一沉到 ``src/aitrader/research/``，本文件只保留兼容入口
以避免历史脚本立刻失效。

新代码请直接使用：

- 数据：``aitrader.research.data.{DynamicLiquidUniverse, PanelLoader, TradabilityMask}``
- 引擎：``aitrader.research.engine.{simulate, AshareCostModel, position_policies}``
- 信号：``aitrader.research.signals.{rebalance, network, industry}``
- 指标：``aitrader.research.metrics.{compute_performance, rolling_*}``
- 输出：``aitrader.research.io.{csv_writer, report_writer, chart_writer}``
- Runner：``aitrader.research.runner.run_research``

后续会删除本文件，请尽快迁移。
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from aitrader.domain.market.stock_universe import StockUniverse
from aitrader.research.data.dynamic_universe import DynamicLiquidUniverse, UniverseSpec
from aitrader.research.data.panel_loader import PanelLoader
from aitrader.research.signals.network import complexity_gap, eigenvector_centrality
from aitrader.research.signals.rebalance import (
    monthly_rebalance_dates,
    weekly_rebalance_dates,
)


__all__ = [
    "DEFAULT_START_DATE",
    "DEFAULT_END_DATE",
    "ResearchBacktestResult",
    "build_mainboard_universe",
    "pick_liquid_symbols",
    "weekly_rebalance_dates",
    "monthly_rebalance_dates",
    "leading_eigenvector_scores",
    "complexity_gap",
    "format_pct",
    "format_num",
]


DEFAULT_START_DATE = "20190101"
DEFAULT_END_DATE = "20241231"


def _deprecated(name: str, replacement: str) -> None:
    warnings.warn(
        f"{name} 已迁移到 {replacement}，本兼容入口将在未来版本删除。",
        DeprecationWarning,
        stacklevel=3,
    )


@dataclass
class ResearchBacktestResult:
    """旧版回测结果占位（建议改用 ``compute_performance`` + ``SimulationResult``）。"""

    strategy: str = ""
    total_return: float = float("nan")
    cagr: float = float("nan")
    sharpe: float = float("nan")
    max_drawdown: float = float("nan")
    volatility: float = float("nan")
    trade_count: int = 0
    first_trade_date: str = ""
    invested_days_pct: float = float("nan")
    avg_holdings: float = float("nan")
    equity_curve: pd.Series = None
    daily_returns: pd.Series = None

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "total_return": self.total_return,
            "cagr": self.cagr,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
            "trade_count": self.trade_count,
            "first_trade_date": self.first_trade_date,
            "invested_days_pct": self.invested_days_pct,
            "avg_holdings": self.avg_holdings,
        }


def build_mainboard_universe(
    end_date: str = DEFAULT_END_DATE,
    min_data_days: int = 750,
) -> list[str]:
    """旧入口：取 end_date 截面的全市场可交易股票。

    新代码请直接使用 ``StockUniverse.get_all_stocks(as_of_date=...)``。
    """
    _deprecated("build_mainboard_universe", "StockUniverse.get_all_stocks(as_of_date=...)")
    universe = StockUniverse()
    return universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=365,
        min_data_days=min_data_days,
        exclude_restricted_stocks=True,
        as_of_date=end_date,
    )


def pick_liquid_symbols(
    end_date: str = DEFAULT_END_DATE,
    top_n: int = 30,
    snapshot_window_days: int = 45,
    min_close: float = 3.0,
) -> list[str]:
    """旧入口：单 as_of 流动性 Top-N。

    会强烈劝退使用 - 本接口在整段回测中只用 end_date 选一次池子，必然引入
    look-ahead 与幸存者偏差。新代码请用 ``DynamicLiquidUniverse``。
    """
    _deprecated("pick_liquid_symbols", "aitrader.research.data.DynamicLiquidUniverse")
    spec = UniverseSpec(
        top_n=top_n,
        snapshot_window_days=snapshot_window_days,
        min_close=min_close,
    )
    universe = DynamicLiquidUniverse(spec, end_date, end_date)
    return universe.universe_at(end_date)


def leading_eigenvector_scores(matrix: pd.DataFrame) -> pd.Series:
    """旧入口：相关/邻接矩阵的最大特征向量绝对值。

    语义已被拆开：
    - 网络中心性 → ``eigenvector_centrality(adj, mode='perron')``
    - PCA 主因子 → ``pca_leading_factor(corr)``
    """
    _deprecated(
        "leading_eigenvector_scores",
        "aitrader.research.signals.network.eigenvector_centrality(mode='perron')",
    )
    return eigenvector_centrality(matrix, mode="perron")


def format_pct(value: float, digits: int = 2) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    return f"{value * 100:+.{digits}f}%"


def format_num(value: float, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"
