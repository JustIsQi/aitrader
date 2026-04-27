"""超参 grid ablation：在 train 上跑全部组合，holdout 上验证 Top-1。"""
from __future__ import annotations

import itertools
import logging
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd

from ..engine.cost_model import CostModel
from ..engine.vectorized_simulator import VectorizedSimulator
from ..metrics.performance import compute_performance, PerformanceReport


logger = logging.getLogger(__name__)


def _expand_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not grid:
        return [{}]
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    out = []
    for combo in itertools.product(*values):
        out.append(dict(zip(keys, combo)))
    return out


def run_grid_ablation(
    *,
    base_params: dict,
    grid: dict[str, list[Any]],
    select_fn: Callable,
    context,
    simulator: VectorizedSimulator,
    train_window: tuple[str, str],
    holdout_window: tuple[str, str],
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_annual: float = 0.02,
    score_fn: Callable[[PerformanceReport], float] = lambda r: (r.sharpe if r.sharpe == r.sharpe else -1e9),
    grid_filter: Optional[Callable[[dict], bool]] = None,
    top_k: int = 5,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """跑 grid。

    Returns:
        ablation_train_df: 每个组合在 train 上的表现 + 排序。
        best_params: train 上最佳组合的参数。
        ablation_holdout_df: train Top-K 在 holdout 上的表现。
    """
    combos = _expand_grid(grid)
    if grid_filter is not None:
        combos = [c for c in combos if grid_filter(c)]
    logger.info("Grid ablation: %d 组合", len(combos))

    train_records: list[dict] = []
    cache: dict[tuple, "SelectionResult"] = {}

    train_start, train_end = train_window
    holdout_start, holdout_end = holdout_window

    def _key(params: dict) -> tuple:
        return tuple(sorted(params.items()))

    for combo in combos:
        params = {**base_params, **combo}
        try:
            sel = select_fn(context, params)
        except Exception as exc:  # noqa: BLE001
            logger.warning("select_fn 失败 params=%s: %s", combo, exc)
            continue
        cache[_key(combo)] = sel

        result = simulator.simulate(sel.target_weights)
        rets = result.daily_returns
        train_rets = rets.loc[(rets.index >= pd.Timestamp(train_start)) & (rets.index <= pd.Timestamp(train_end))]
        if train_rets.empty:
            continue
        bench_train = None
        if benchmark_returns is not None:
            bench_train = benchmark_returns.loc[
                (benchmark_returns.index >= pd.Timestamp(train_start))
                & (benchmark_returns.index <= pd.Timestamp(train_end))
            ]
        report_train = compute_performance(
            train_rets,
            benchmark_returns=bench_train,
            risk_free_annual=risk_free_annual,
            holdings=result.holdings.loc[train_rets.index],
            rebalance_log=result.rebalance_log[
                (result.rebalance_log["date"] >= pd.Timestamp(train_start))
                & (result.rebalance_log["date"] <= pd.Timestamp(train_end))
            ] if not result.rebalance_log.empty else result.rebalance_log,
        )
        score = score_fn(report_train)

        record = {
            "score": score,
            "train_total_return": report_train.total_return,
            "train_cagr": report_train.cagr,
            "train_sharpe": report_train.sharpe,
            "train_max_drawdown": report_train.max_drawdown,
            "train_calmar": report_train.calmar,
            **combo,
        }
        train_records.append(record)

    if not train_records:
        return pd.DataFrame(), {}, pd.DataFrame()

    train_df = pd.DataFrame(train_records).sort_values("score", ascending=False).reset_index(drop=True)
    best_combo = {k: train_df.iloc[0][k] for k in grid.keys() if k in train_df.columns}

    # Holdout: 跑 train Top-K
    top_records: list[dict] = []
    for _, row in train_df.head(top_k).iterrows():
        combo = {k: row[k] for k in grid.keys() if k in row.index}
        params = {**base_params, **combo}
        try:
            sel = select_fn(context, params)
        except Exception as exc:  # noqa: BLE001
            logger.warning("holdout select_fn 失败 params=%s: %s", combo, exc)
            continue
        result = simulator.simulate(sel.target_weights)
        rets = result.daily_returns
        holdout_rets = rets.loc[
            (rets.index >= pd.Timestamp(holdout_start)) & (rets.index <= pd.Timestamp(holdout_end))
        ]
        if holdout_rets.empty:
            continue
        bench_holdout = None
        if benchmark_returns is not None:
            bench_holdout = benchmark_returns.loc[
                (benchmark_returns.index >= pd.Timestamp(holdout_start))
                & (benchmark_returns.index <= pd.Timestamp(holdout_end))
            ]
        report_holdout = compute_performance(
            holdout_rets,
            benchmark_returns=bench_holdout,
            risk_free_annual=risk_free_annual,
            holdings=result.holdings.loc[holdout_rets.index],
            rebalance_log=result.rebalance_log[
                (result.rebalance_log["date"] >= pd.Timestamp(holdout_start))
                & (result.rebalance_log["date"] <= pd.Timestamp(holdout_end))
            ] if not result.rebalance_log.empty else result.rebalance_log,
        )
        top_records.append(
            {
                "train_score": row["score"],
                "holdout_total_return": report_holdout.total_return,
                "holdout_cagr": report_holdout.cagr,
                "holdout_sharpe": report_holdout.sharpe,
                "holdout_max_drawdown": report_holdout.max_drawdown,
                "holdout_calmar": report_holdout.calmar,
                **combo,
            }
        )

    holdout_df = pd.DataFrame(top_records)
    return train_df, best_combo, holdout_df
