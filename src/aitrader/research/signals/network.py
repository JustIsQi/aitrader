"""网络中心性 / 主因子 / 复杂度缺口工具集。

明确语义区分：

- ``eigenvector_centrality(adj, mode='perron')``: 邻接矩阵的 Perron 特征向量，
  适用于"网络中心性"语义（无负边，结果非负）。
- ``pca_leading_factor(corr)``: 相关矩阵的最大特征向量，符号不丢失，
  适用于"主因子载荷"语义。
- ``complexity_gap(window_returns)``: RMT 复杂度缺口（最大特征值占比 - 平均相关）。
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


def eigenvector_centrality(
    adjacency: pd.DataFrame,
    *,
    mode: Literal["perron", "abs"] = "perron",
    max_iter: int = 200,
    tol: float = 1e-10,
) -> pd.Series:
    """非负邻接矩阵的特征向量中心性。

    - ``mode='perron'``: 幂迭代求 Perron-Frobenius 特征向量（保证非负、唯一）。
    - ``mode='abs'``: 兼容老版本，eigh 取最大特征值对应的 |vec|。
    """
    if adjacency.empty:
        return pd.Series(dtype=float)
    arr = adjacency.fillna(0.0).to_numpy(dtype=float, copy=True)
    if not np.isfinite(arr).all():
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(arr, 0.0)

    n = arr.shape[0]
    if n == 0:
        return pd.Series(dtype=float)

    if mode == "perron":
        non_neg = np.where(arr < 0, 0.0, arr)
        if non_neg.sum() <= 0:
            return pd.Series(np.full(n, 1.0 / n), index=adjacency.index)
        # Shifted power iteration: 加单位阵避免二部图特征值正负对称导致幂迭代振荡。
        shifted = non_neg + np.eye(n)
        vec = np.full(n, 1.0 / np.sqrt(n))
        for _ in range(max_iter):
            new_vec = shifted @ vec
            norm = np.linalg.norm(new_vec)
            if norm <= 0:
                break
            new_vec /= norm
            if np.allclose(new_vec, vec, atol=tol):
                vec = new_vec
                break
            vec = new_vec
        vec = np.abs(vec)
    else:
        try:
            vals, vecs = np.linalg.eigh(arr)
            vec = np.abs(vecs[:, -1])
        except np.linalg.LinAlgError:
            vec = np.abs(arr).sum(axis=1)

    series = pd.Series(vec, index=adjacency.index, dtype=float)
    if series.sum() > 0:
        series /= series.sum()
    return series.sort_values(ascending=False)


def pca_leading_factor(corr: pd.DataFrame) -> pd.Series:
    """相关矩阵的主因子载荷（保留符号方向）。"""
    if corr.empty:
        return pd.Series(dtype=float)
    arr = corr.fillna(0.0).to_numpy(dtype=float)
    if not np.isfinite(arr).all():
        arr = np.nan_to_num(arr, nan=0.0)
    try:
        vals, vecs = np.linalg.eigh(arr)
    except np.linalg.LinAlgError:
        return pd.Series(np.zeros(arr.shape[0]), index=corr.index)
    leading = vecs[:, -1]
    # 统一方向：使大多数载荷为正
    if float(leading.sum()) < 0:
        leading = -leading
    return pd.Series(leading, index=corr.index, dtype=float)


def complexity_gap(window_returns: pd.DataFrame) -> float:
    """RMT 复杂度缺口（最大特征值/n - 平均相关）。"""
    if window_returns is None or window_returns.empty:
        return float("nan")
    corr = window_returns.corr().clip(lower=-1, upper=1).fillna(0.0)
    n = len(corr.columns)
    if n <= 1:
        return float("nan")
    try:
        vals = np.linalg.eigvalsh(corr.to_numpy(dtype=float))
    except np.linalg.LinAlgError:
        return float("nan")
    avg_corr = (corr.to_numpy().sum() - n) / (n * (n - 1))
    return float(vals[-1] / n - avg_corr)
