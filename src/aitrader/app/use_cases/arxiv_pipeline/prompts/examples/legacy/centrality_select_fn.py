"""网络中心性选股策略的 select_fn。

修复点：
- 用 ``eigenvector_centrality(adj, mode='perron')`` 求 Perron 特征向量，
  对非负邻接矩阵语义正确（修复"特征向量物理含义混淆"）。
- ``centrality`` 与 ``momentum`` 拆成两个独立信号；权重 ``alpha`` 进 grid（修复"硬编码 0.7/0.3"）。
- 可选行业中性化（``industry_neutralize=True``）：组合分数在行业内 z-score 后再排序。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from aitrader.research.runner.specs import SelectFnContext, SelectionResult
from aitrader.research.signals.network import eigenvector_centrality
from aitrader.research.signals.industry import industry_neutralize_scores


logger = logging.getLogger(__name__)


def _previous_idx(index: pd.DatetimeIndex, dt: pd.Timestamp):
    pos = index.get_indexer([dt])[0]
    if pos <= 0:
        return None
    return index[pos - 1]


def select_centrality(context: SelectFnContext, params: dict) -> SelectionResult:
    panels = context.panels
    universe = context.universe
    rebalance_dates = context.rebalance_dates

    corr_window = int(params.get("corr_window", 60))
    centrality_weight = float(params.get("centrality_weight", 0.5))  # alpha
    edge_quantile = float(params.get("edge_quantile", 0.60))
    momentum_lookback = int(params.get("momentum_lookback", 20))
    top_k = int(params.get("top_k", 12))
    industry_neutralize = bool(params.get("industry_neutralize", False))
    min_network_size = int(params.get("min_network_size", 12))

    industry_metadata = params.get("industry_metadata")  # 可选 DataFrame

    close = panels.close_adj
    returns = close.pct_change()
    momentum = close.pct_change(momentum_lookback)

    target = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    signal_rows: list[dict] = []

    for dt in rebalance_dates:
        prior = _previous_idx(close.index, dt)
        if prior is None:
            continue
        symbols = universe.universe_for_trading(dt)
        if not symbols:
            continue

        window = returns.loc[:prior].tail(corr_window)
        window = window.reindex(columns=[s for s in symbols if s in window.columns])
        valid = window.dropna(axis=1, thresh=int(corr_window * 0.7))
        if valid.shape[1] < min_network_size:
            continue

        corr = valid.corr().clip(lower=-1.0, upper=1.0).fillna(0.0)
        np.fill_diagonal(corr.values, 0.0)

        # 阈值化：仅保留正相关 top quantile，作为非负邻接矩阵
        positive = corr.where(corr > 0).stack()
        threshold = float(positive.quantile(edge_quantile)) if not positive.empty else 0.0
        non_neg = corr.clip(lower=0.0)
        adjacency = non_neg.where(non_neg >= threshold, 0.0)
        scores = eigenvector_centrality(adjacency, mode="perron")
        if scores.empty:
            continue

        momentum_scores = momentum.loc[prior].reindex(scores.index).fillna(0.0)

        cent_rank = scores.rank(pct=True)
        mom_rank = momentum_scores.rank(pct=True)
        composite = centrality_weight * cent_rank + (1.0 - centrality_weight) * mom_rank
        composite = composite.dropna()

        if industry_neutralize and industry_metadata is not None:
            composite = industry_neutralize_scores(composite, metadata=industry_metadata)

        if composite.empty:
            continue
        selected = composite.sort_values(ascending=False).head(top_k).index.tolist()
        if not selected:
            continue

        target.loc[dt, :] = 0.0
        weight = 1.0 / len(selected)
        for s in selected:
            if s in target.columns:
                target.loc[dt, s] = weight

        signal_rows.append(
            {
                "rebalance_date": dt.strftime("%Y-%m-%d"),
                "signal_date": prior.strftime("%Y-%m-%d"),
                "network_size": int(valid.shape[1]),
                "edge_threshold": threshold,
                "top_symbol": selected[0],
                "top_score": float(composite.loc[selected[0]]),
                "centrality_weight": centrality_weight,
            }
        )

    return SelectionResult(target_weights=target, signal_df=pd.DataFrame(signal_rows))
