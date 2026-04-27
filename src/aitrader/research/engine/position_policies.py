"""仓位政策：把"信号 + 选股"映射成目标权重。

等权 / 多档 / 信号加权三种映射，配合 ``vectorized_simulator.simulate``
共同决定每日的 ``target_weights`` 矩阵。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


@dataclass
class PositionPolicy:
    """仓位政策的轻量包装。

    在 runner 层把 ``select_fn`` 的输出（list[symbol] 或 Series[signal]）
    转成具体的 ``target_weights`` 行。
    """

    name: str
    max_single_weight: float = 0.5

    def to_weights(
        self,
        symbols_or_signal: Sequence[str] | pd.Series,
        *,
        symbol_universe: list[str],
        gross_exposure: float = 1.0,
    ) -> pd.Series:
        raise NotImplementedError


@dataclass
class equal_weight(PositionPolicy):  # noqa: N801 - 使用函数式名以呼应导入风格
    """等权：选中 N 只股票，每只权重 = gross_exposure / N，受 max_single_weight 限制。"""

    name: str = "equal_weight"
    max_single_weight: float = 0.5

    def to_weights(
        self,
        symbols_or_signal: Sequence[str] | pd.Series,
        *,
        symbol_universe: list[str],
        gross_exposure: float = 1.0,
    ) -> pd.Series:
        if isinstance(symbols_or_signal, pd.Series):
            selected = list(symbols_or_signal.dropna().index)
        else:
            selected = list(symbols_or_signal or [])

        weights = pd.Series(0.0, index=symbol_universe, dtype=float)
        valid = [s for s in selected if s in weights.index]
        if not valid or gross_exposure <= 0:
            return weights

        per_weight = gross_exposure / len(valid)
        per_weight = min(per_weight, self.max_single_weight)
        weights.loc[valid] = per_weight
        return weights


@dataclass
class tiered_weight(PositionPolicy):  # noqa: N801
    """多档仓位：把连续 ``gross_exposure ∈ [0, 1]`` 离散化到几档，再等权分配。

    ``levels`` 形如 ``[(0.0, 0.0), (0.5, 0.5), (0.8, 1.0)]``：
    阈值越高，对应仓位越大。例如 0.5 → 0.5 仓位，0.8 → 满仓。
    """

    name: str = "tiered_weight"
    levels: tuple[tuple[float, float], ...] = ((0.0, 0.0), (0.5, 0.5), (0.8, 1.0))
    max_single_weight: float = 0.5

    def discretize(self, exposure: float) -> float:
        result = 0.0
        for threshold, weight in self.levels:
            if exposure >= threshold:
                result = weight
        return result

    def to_weights(
        self,
        symbols_or_signal: Sequence[str] | pd.Series,
        *,
        symbol_universe: list[str],
        gross_exposure: float = 1.0,
    ) -> pd.Series:
        if isinstance(symbols_or_signal, pd.Series):
            selected = list(symbols_or_signal.dropna().index)
        else:
            selected = list(symbols_or_signal or [])

        weights = pd.Series(0.0, index=symbol_universe, dtype=float)
        valid = [s for s in selected if s in weights.index]
        if not valid:
            return weights

        gross = float(np.clip(gross_exposure, 0.0, 1.0))
        gross = self.discretize(gross)
        if gross <= 0:
            return weights

        per_weight = gross / len(valid)
        per_weight = min(per_weight, self.max_single_weight)
        weights.loc[valid] = per_weight
        return weights


@dataclass
class signal_weighted(PositionPolicy):  # noqa: N801
    """信号加权：直接根据信号强度（已归一化 ∈ [0, 1]）分配权重。"""

    name: str = "signal_weighted"
    max_single_weight: float = 0.2

    def to_weights(
        self,
        symbols_or_signal: Sequence[str] | pd.Series,
        *,
        symbol_universe: list[str],
        gross_exposure: float = 1.0,
    ) -> pd.Series:
        if not isinstance(symbols_or_signal, pd.Series):
            raise TypeError("signal_weighted 仅支持 pd.Series 形式的信号")

        weights = pd.Series(0.0, index=symbol_universe, dtype=float)
        cleaned = symbols_or_signal.dropna()
        if cleaned.empty or gross_exposure <= 0:
            return weights

        cleaned = cleaned.clip(lower=0)
        if cleaned.sum() <= 0:
            return weights

        normalized = cleaned / cleaned.sum() * gross_exposure
        normalized = normalized.clip(upper=self.max_single_weight)
        # 重新归一化到目标暴露
        if normalized.sum() > 0:
            normalized = normalized / normalized.sum() * gross_exposure
        weights.loc[normalized.index] = normalized.values
        return weights
