"""网络中心性 / 主因子 / 复杂度缺口测试。"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aitrader.research.signals.network import (
    complexity_gap,
    eigenvector_centrality,
    pca_leading_factor,
)


def test_perron_centrality_star_graph() -> None:
    """星形图：中心节点的中心性应该最高。"""
    nodes = ["hub", "a", "b", "c", "d"]
    arr = np.zeros((5, 5))
    for i in range(1, 5):
        arr[0, i] = 1.0
        arr[i, 0] = 1.0
    adj = pd.DataFrame(arr, index=nodes, columns=nodes)
    cent = eigenvector_centrality(adj, mode="perron")
    assert cent.index[0] == "hub"
    leaf_values = cent.loc[["a", "b", "c", "d"]].values
    assert np.allclose(leaf_values, leaf_values[0], atol=1e-6)
    assert cent["hub"] > cent["a"]


def test_perron_centrality_non_negative() -> None:
    """Perron 模式应该始终输出非负向量。"""
    rng = np.random.default_rng(0)
    n = 8
    base = rng.uniform(0.1, 0.9, (n, n))
    arr = (base + base.T) / 2
    np.fill_diagonal(arr, 0.0)
    adj = pd.DataFrame(arr, index=[f"s{i}" for i in range(n)], columns=[f"s{i}" for i in range(n)])
    cent = eigenvector_centrality(adj, mode="perron")
    assert (cent.values >= 0).all()
    assert cent.sum() == pytest.approx(1.0, abs=1e-6)


def test_perron_centrality_negative_edges_clipped() -> None:
    """Perron 模式遇到负边应该 clip 到 0，不应崩溃。"""
    nodes = ["a", "b", "c"]
    arr = np.array(
        [
            [0.0, 1.0, -0.5],
            [1.0, 0.0, 0.8],
            [-0.5, 0.8, 0.0],
        ]
    )
    adj = pd.DataFrame(arr, index=nodes, columns=nodes)
    cent = eigenvector_centrality(adj, mode="perron")
    assert (cent.values >= 0).all()


def test_pca_leading_factor_sign_aligned() -> None:
    """PCA 主因子方向应该统一为正向（多数载荷为正）。"""
    rng = np.random.default_rng(1)
    n = 50
    common = rng.normal(0, 1, n)
    data = pd.DataFrame(
        {
            "a": common + rng.normal(0, 0.1, n),
            "b": common + rng.normal(0, 0.1, n),
            "c": common + rng.normal(0, 0.1, n),
        }
    )
    corr = data.corr()
    factor = pca_leading_factor(corr)
    assert (factor > 0).sum() >= 2
    assert factor.sum() > 0


def test_complexity_gap_positive_when_correlated() -> None:
    """高度相关的资产 → complexity_gap 接近 0；几乎独立 → gap 为正。"""
    rng = np.random.default_rng(2)
    n_obs = 252
    common = rng.normal(0, 1, n_obs)
    correlated = pd.DataFrame(
        {f"s{i}": common + rng.normal(0, 0.1, n_obs) for i in range(5)}
    )
    independent = pd.DataFrame(
        {f"s{i}": rng.normal(0, 1, n_obs) for i in range(5)}
    )
    gap_corr = complexity_gap(correlated)
    gap_indep = complexity_gap(independent)
    assert np.isfinite(gap_corr)
    assert np.isfinite(gap_indep)
    assert gap_indep > gap_corr


def test_eigenvector_centrality_empty() -> None:
    cent = eigenvector_centrality(pd.DataFrame())
    assert cent.empty


def test_pca_leading_factor_empty() -> None:
    f = pca_leading_factor(pd.DataFrame())
    assert f.empty


def test_complexity_gap_single_asset_returns_nan() -> None:
    df = pd.DataFrame({"a": np.random.randn(100)})
    assert np.isnan(complexity_gap(df))
