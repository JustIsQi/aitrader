"""
组合风控辅助模块（纯函数 + 轻量 dataclass）。

提供能力：
1. 目标波动率缩放（target-vol scaling）
2. risk-off 触发与退出判定（含简单迟滞）
3. 现金回填（将未使用权重补到现金）
4. 风险倍率裁剪（min/max clip）

设计目标：
- 无状态、无 I/O，便于并行集成到 portfolio_bt_engine
- 输入输出均为基础类型 / dataclass，减少耦合
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class TargetVolatilityConfig:
    """目标波动率缩放配置。"""

    enabled: bool = True
    target_annual_vol: float = 0.12
    lookback_days: int = 20
    trading_days: int = 252
    ewma_alpha: Optional[float] = None


@dataclass(frozen=True)
class RiskMultiplierClipConfig:
    """风险倍率裁剪配置。"""

    min_multiplier: float = 0.0
    max_multiplier: float = 1.0
    fallback_multiplier: float = 1.0


@dataclass(frozen=True)
class RiskOffConfig:
    """
    Risk-off 阈值配置。

    约定：
    - drawdown / daily_return 为收益率口径，如 -0.08 表示 -8%
    - vol 为年化波动率口径，如 0.25 表示 25%
    - 若设置了 *_exit，则用于退出阈值；否则使用 trigger 本身
    """

    drawdown_trigger: Optional[float] = -0.10
    drawdown_exit: Optional[float] = -0.05
    vol_trigger: Optional[float] = None
    vol_exit: Optional[float] = None
    daily_loss_trigger: Optional[float] = None
    daily_loss_exit: Optional[float] = None
    risk_off_multiplier: float = 0.0


@dataclass(frozen=True)
class CashRefillConfig:
    """现金回填配置（默认 long-only 组合）。"""

    max_total_weight: float = 1.0
    cash_symbol: str = "CASH"
    enable_cash_refill: bool = True
    min_weight_to_keep: float = 1e-12


@dataclass(frozen=True)
class RiskSnapshot:
    """时点风险快照。"""

    drawdown: float = 0.0
    realized_annual_vol: Optional[float] = None
    daily_return: Optional[float] = None


@dataclass(frozen=True)
class RiskControlResult:
    """组合风控输出。"""

    adjusted_weights: Dict[str, float]
    cash_weight: float
    gross_weight: float
    realized_annual_vol: float
    raw_multiplier: float
    clipped_multiplier: float
    effective_multiplier: float
    is_risk_off: bool
    risk_off_reason: str


def _to_float_array(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return arr
    return arr[np.isfinite(arr)]


def estimate_annualized_volatility(
    daily_returns: Sequence[float],
    *,
    trading_days: int = 252,
    ewma_alpha: Optional[float] = None,
) -> float:
    """
    估算年化波动率。

    Args:
        daily_returns: 日收益序列（建议按时间升序）
        trading_days: 年化交易日
        ewma_alpha: EWMA 衰减参数 (0, 1]，None 表示普通样本标准差
    """
    returns = _to_float_array(daily_returns)
    if returns.size < 2 or trading_days <= 0:
        return 0.0

    if ewma_alpha is None:
        daily_vol = float(np.std(returns, ddof=1))
    else:
        alpha = float(ewma_alpha)
        alpha = min(max(alpha, 1e-6), 1.0)
        # 让最近观测获得更高权重
        exponents = np.arange(returns.size - 1, -1, -1, dtype=float)
        weights = np.power(1.0 - alpha, exponents)
        weights_sum = float(weights.sum())
        if weights_sum <= 0:
            return 0.0
        weights /= weights_sum
        mean = float(np.dot(weights, returns))
        variance = float(np.dot(weights, (returns - mean) ** 2))
        daily_vol = float(np.sqrt(max(variance, 0.0)))

    annual_vol = daily_vol * float(np.sqrt(trading_days))
    return max(annual_vol, 0.0)


def compute_target_vol_multiplier(
    realized_annual_vol: float,
    target_annual_vol: float,
    *,
    fallback_multiplier: float = 1.0,
) -> float:
    """
    计算目标波动率对应的风险倍率。

    公式：target / realized
    """
    if target_annual_vol <= 0:
        return 0.0
    if realized_annual_vol <= 0 or not np.isfinite(realized_annual_vol):
        return float(fallback_multiplier)
    return float(target_annual_vol / realized_annual_vol)


def clip_risk_multiplier(
    risk_multiplier: float,
    clip_config: RiskMultiplierClipConfig,
) -> float:
    """按上下限裁剪风险倍率。"""
    if not np.isfinite(risk_multiplier):
        risk_multiplier = clip_config.fallback_multiplier
    lower = min(clip_config.min_multiplier, clip_config.max_multiplier)
    upper = max(clip_config.min_multiplier, clip_config.max_multiplier)
    return float(np.clip(risk_multiplier, lower, upper))


def evaluate_risk_off(
    snapshot: RiskSnapshot,
    config: RiskOffConfig,
    *,
    was_risk_off: bool = False,
) -> Tuple[bool, str]:
    """
    判定是否进入/维持/退出 risk-off。

    Returns:
        (is_risk_off, reason)
    """
    entry_reasons = []

    if config.drawdown_trigger is not None and snapshot.drawdown <= config.drawdown_trigger:
        entry_reasons.append("drawdown")

    if (
        config.vol_trigger is not None
        and snapshot.realized_annual_vol is not None
        and snapshot.realized_annual_vol >= config.vol_trigger
    ):
        entry_reasons.append("volatility")

    if (
        config.daily_loss_trigger is not None
        and snapshot.daily_return is not None
        and snapshot.daily_return <= config.daily_loss_trigger
    ):
        entry_reasons.append("daily_loss")

    should_enter = len(entry_reasons) > 0

    # 未处于 risk-off：只需要判断是否入场
    if not was_risk_off:
        return should_enter, ",".join(entry_reasons)

    # 已处于 risk-off：若仍触发任一入场条件，则继续维持
    if should_enter:
        return True, ",".join(entry_reasons)

    # 已处于 risk-off 且没有入场条件，判断退出（全部满足恢复条件才退出）
    recovery_checks = []

    if config.drawdown_trigger is not None:
        exit_level = config.drawdown_exit if config.drawdown_exit is not None else config.drawdown_trigger
        recovery_checks.append(snapshot.drawdown >= exit_level)

    if config.vol_trigger is not None and snapshot.realized_annual_vol is not None:
        exit_level = config.vol_exit if config.vol_exit is not None else config.vol_trigger
        recovery_checks.append(snapshot.realized_annual_vol <= exit_level)

    if config.daily_loss_trigger is not None and snapshot.daily_return is not None:
        exit_level = config.daily_loss_exit if config.daily_loss_exit is not None else config.daily_loss_trigger
        recovery_checks.append(snapshot.daily_return >= exit_level)

    if recovery_checks and all(recovery_checks):
        return False, "recovered"

    return True, "hold"


def scale_weights_with_cash_refill(
    base_weights: Mapping[str, float],
    *,
    risk_multiplier: float,
    cash_config: CashRefillConfig,
) -> Tuple[Dict[str, float], float, float]:
    """
    对目标权重进行风险倍率缩放，并执行现金回填。

    约定：long-only 输入（负权重会被忽略）。

    Returns:
        adjusted_weights: 调整后权重（含现金仓位）
        cash_weight: 现金权重
        gross_weight: 风险资产权重和（不含现金）
    """
    scaled: Dict[str, float] = {}
    multiplier = max(float(risk_multiplier), 0.0)
    max_total = max(float(cash_config.max_total_weight), 0.0)

    for symbol, weight in base_weights.items():
        if symbol == cash_config.cash_symbol:
            continue
        w = float(weight)
        if not np.isfinite(w) or w <= 0:
            continue
        new_weight = w * multiplier
        if new_weight > cash_config.min_weight_to_keep:
            scaled[symbol] = new_weight

    gross_weight = float(sum(scaled.values()))

    # 过曝时按比例压缩到上限
    if gross_weight > max_total and gross_weight > 0:
        ratio = max_total / gross_weight
        scaled = {sym: w * ratio for sym, w in scaled.items() if w * ratio > cash_config.min_weight_to_keep}
        gross_weight = float(sum(scaled.values()))

    cash_weight = 0.0
    if cash_config.enable_cash_refill:
        cash_weight = max(max_total - gross_weight, 0.0)
        if cash_weight > cash_config.min_weight_to_keep:
            scaled[cash_config.cash_symbol] = cash_weight
        else:
            cash_weight = 0.0

    return scaled, cash_weight, gross_weight


def apply_portfolio_risk_controls(
    base_weights: Mapping[str, float],
    *,
    recent_daily_returns: Optional[Sequence[float]] = None,
    drawdown: float = 0.0,
    daily_return: Optional[float] = None,
    was_risk_off: bool = False,
    realized_annual_vol: Optional[float] = None,
    target_vol_config: TargetVolatilityConfig = TargetVolatilityConfig(),
    clip_config: RiskMultiplierClipConfig = RiskMultiplierClipConfig(),
    risk_off_config: RiskOffConfig = RiskOffConfig(),
    cash_config: CashRefillConfig = CashRefillConfig(),
) -> RiskControlResult:
    """
    风控总入口：目标波动率 -> 风险倍率裁剪 -> risk-off 判定 -> 现金回填。
    """
    vol = 0.0
    if realized_annual_vol is not None and np.isfinite(realized_annual_vol):
        vol = float(max(realized_annual_vol, 0.0))
    elif recent_daily_returns is not None and len(recent_daily_returns) > 0:
        lookback = max(target_vol_config.lookback_days, 1)
        returns_slice = recent_daily_returns[-lookback:]
        vol = estimate_annualized_volatility(
            returns_slice,
            trading_days=target_vol_config.trading_days,
            ewma_alpha=target_vol_config.ewma_alpha,
        )

    if target_vol_config.enabled:
        raw_multiplier = compute_target_vol_multiplier(
            vol,
            target_vol_config.target_annual_vol,
            fallback_multiplier=clip_config.fallback_multiplier,
        )
    else:
        raw_multiplier = 1.0

    clipped_multiplier = clip_risk_multiplier(raw_multiplier, clip_config)

    snapshot = RiskSnapshot(
        drawdown=drawdown,
        realized_annual_vol=vol,
        daily_return=daily_return,
    )
    is_risk_off, reason = evaluate_risk_off(snapshot, risk_off_config, was_risk_off=was_risk_off)

    effective_multiplier = clipped_multiplier
    if is_risk_off:
        effective_multiplier = min(clipped_multiplier, max(risk_off_config.risk_off_multiplier, 0.0))

    adjusted_weights, cash_weight, gross_weight = scale_weights_with_cash_refill(
        base_weights,
        risk_multiplier=effective_multiplier,
        cash_config=cash_config,
    )

    return RiskControlResult(
        adjusted_weights=adjusted_weights,
        cash_weight=cash_weight,
        gross_weight=gross_weight,
        realized_annual_vol=vol,
        raw_multiplier=raw_multiplier,
        clipped_multiplier=clipped_multiplier,
        effective_multiplier=effective_multiplier,
        is_risk_off=is_risk_off,
        risk_off_reason=reason,
    )


__all__ = [
    "CashRefillConfig",
    "RiskControlResult",
    "RiskMultiplierClipConfig",
    "RiskOffConfig",
    "RiskSnapshot",
    "TargetVolatilityConfig",
    "apply_portfolio_risk_controls",
    "clip_risk_multiplier",
    "compute_target_vol_multiplier",
    "estimate_annualized_volatility",
    "evaluate_risk_off",
    "scale_weights_with_cash_refill",
]
