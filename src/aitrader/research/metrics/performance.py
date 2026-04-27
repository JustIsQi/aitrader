"""完整绩效统计。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


@dataclass
class PerformanceReport:
    total_return: float = float("nan")
    cagr: float = float("nan")
    volatility: float = float("nan")
    sharpe: float = float("nan")
    sortino: float = float("nan")
    calmar: float = float("nan")
    max_drawdown: float = float("nan")
    max_drawdown_start: str = ""
    max_drawdown_end: str = ""
    max_drawdown_recover_days: int = 0
    var_95: float = float("nan")
    cvar_95: float = float("nan")
    alpha: float = float("nan")
    beta: float = float("nan")
    information_ratio: float = float("nan")
    tracking_error: float = float("nan")
    hit_rate: float = float("nan")
    annual_turnover: float = float("nan")
    avg_holding_period_days: float = float("nan")
    trade_count: int = 0
    avg_holdings: float = float("nan")
    max_holdings: int = 0
    invested_days_pct: float = float("nan")
    yearly_returns: dict[int, float] = field(default_factory=dict)

    def as_table_rows(self) -> list[tuple[str, str]]:
        def pct(v):
            return "NA" if not np.isfinite(v) else f"{v * 100:+.2f}%"

        def num(v):
            return "NA" if not np.isfinite(v) else f"{v:.3f}"

        rows = [
            ("总收益", pct(self.total_return)),
            ("复合年化收益", pct(self.cagr)),
            ("波动率", pct(self.volatility)),
            ("夏普比率", num(self.sharpe)),
            ("Sortino", num(self.sortino)),
            ("Calmar", num(self.calmar)),
            ("最大回撤", pct(self.max_drawdown)),
            ("最大回撤起", self.max_drawdown_start or "NA"),
            ("最大回撤止", self.max_drawdown_end or "NA"),
            ("回撤恢复天数", str(self.max_drawdown_recover_days)),
            ("VaR(95)", pct(self.var_95)),
            ("CVaR(95)", pct(self.cvar_95)),
            ("alpha (年化)", pct(self.alpha)),
            ("beta", num(self.beta)),
            ("信息比率", num(self.information_ratio)),
            ("跟踪误差", pct(self.tracking_error)),
            ("胜率 (vs 基准)", pct(self.hit_rate)),
            ("年化换手", num(self.annual_turnover)),
            ("平均持仓周期(日)", num(self.avg_holding_period_days)),
            ("交易次数", str(self.trade_count)),
            ("平均持仓数", num(self.avg_holdings)),
            ("最大持仓数", str(self.max_holdings)),
            ("持仓天数占比", pct(self.invested_days_pct)),
        ]
        for year, ret in sorted(self.yearly_returns.items()):
            rows.append((f"{year} 年收益", pct(ret)))
        return rows

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "yearly_returns"}
        d["yearly_returns"] = dict(self.yearly_returns)
        return d


def compute_drawdown(equity_curve: pd.Series) -> tuple[pd.Series, float, str, str, int]:
    """返回回撤序列、最大回撤、起止日期、恢复天数。"""
    if equity_curve.empty:
        return pd.Series(dtype=float), float("nan"), "", "", 0
    cummax = equity_curve.cummax()
    drawdown = equity_curve / cummax - 1.0
    max_dd = float(drawdown.min())
    if not np.isfinite(max_dd) or max_dd == 0:
        return drawdown, max_dd, "", "", 0
    end_idx = drawdown.idxmin()
    start_idx = equity_curve.loc[:end_idx].idxmax()
    # 恢复点：最大回撤之后第一次净值回到 cummax 的日期
    recover_idx = None
    after = equity_curve.loc[end_idx:]
    target = float(equity_curve.loc[start_idx])
    rebound = after[after >= target]
    if not rebound.empty:
        recover_idx = rebound.index[0]
        recover_days = int((recover_idx - end_idx).days)
    else:
        recover_days = 0  # 尚未回本
    return (
        drawdown,
        max_dd,
        pd.Timestamp(start_idx).strftime("%Y-%m-%d"),
        pd.Timestamp(end_idx).strftime("%Y-%m-%d"),
        recover_days,
    )


def _safe_std(series: pd.Series, ddof: int = 1) -> float:
    if len(series) < 2:
        return float("nan")
    return float(series.std(ddof=ddof))


def _annualized(daily_value: float, scale: int = TRADING_DAYS_PER_YEAR) -> float:
    return daily_value * scale


def _annualized_vol(daily_returns: pd.Series, ddof: int = 1) -> float:
    std = _safe_std(daily_returns, ddof=ddof)
    return float(std * np.sqrt(TRADING_DAYS_PER_YEAR)) if np.isfinite(std) else float("nan")


def compute_holdings_metrics(
    holdings: pd.DataFrame,
    rebalance_log: pd.DataFrame,
) -> dict:
    if holdings.empty:
        return {
            "avg_holdings": float("nan"),
            "max_holdings": 0,
            "invested_days_pct": float("nan"),
            "annual_turnover": float("nan"),
            "avg_holding_period_days": float("nan"),
        }
    n_holdings = (holdings > 0).sum(axis=1)
    invested_mask = n_holdings > 0
    avg_holdings = float(n_holdings[invested_mask].mean()) if invested_mask.any() else float("nan")
    max_holdings = int(n_holdings.max())
    invested_pct = float(invested_mask.mean()) if len(invested_mask) else float("nan")

    annual_turnover = float("nan")
    avg_holding_period = float("nan")
    if rebalance_log is not None and not rebalance_log.empty and "turnover_pct" in rebalance_log:
        n_days = len(holdings)
        years = max(n_days / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
        total_turnover = float(rebalance_log["turnover_pct"].sum())
        annual_turnover = total_turnover / years
        if annual_turnover > 0:
            avg_holding_period = TRADING_DAYS_PER_YEAR / annual_turnover

    return {
        "avg_holdings": avg_holdings,
        "max_holdings": max_holdings,
        "invested_days_pct": invested_pct,
        "annual_turnover": annual_turnover,
        "avg_holding_period_days": avg_holding_period,
    }


def compute_performance(
    daily_returns: pd.Series,
    *,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_annual: float = 0.02,
    holdings: Optional[pd.DataFrame] = None,
    rebalance_log: Optional[pd.DataFrame] = None,
) -> PerformanceReport:
    daily = daily_returns.dropna().astype(float)
    if daily.empty:
        return PerformanceReport()

    rf_daily = (1.0 + risk_free_annual) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0
    excess = daily - rf_daily

    equity_curve = (1.0 + daily).cumprod()
    total_return = float(equity_curve.iloc[-1] - 1.0)
    years = max((daily.index[-1] - daily.index[0]).days / 365.25, 1 / 365.25)
    cagr = float(equity_curve.iloc[-1] ** (1.0 / years) - 1.0) if equity_curve.iloc[-1] > 0 else float("nan")
    vol = _annualized_vol(daily, ddof=1)
    std_excess = _safe_std(excess, ddof=1)
    sharpe = float(excess.mean() / std_excess * np.sqrt(TRADING_DAYS_PER_YEAR)) if std_excess and std_excess > 0 else float("nan")

    downside = excess[excess < 0]
    downside_std = _safe_std(downside, ddof=1)
    sortino = float(excess.mean() / downside_std * np.sqrt(TRADING_DAYS_PER_YEAR)) if downside_std and downside_std > 0 else float("nan")

    drawdown, max_dd, dd_start, dd_end, dd_recover = compute_drawdown(equity_curve)
    calmar = float("nan")
    if np.isfinite(cagr) and np.isfinite(max_dd) and max_dd < 0:
        calmar = float(cagr / abs(max_dd))

    var_95 = float(np.quantile(daily.values, 0.05))
    cvar_95 = float(daily[daily <= var_95].mean()) if (daily <= var_95).any() else float("nan")

    alpha = float("nan")
    beta = float("nan")
    info_ratio = float("nan")
    tracking_error = float("nan")
    hit_rate = float("nan")
    if benchmark_returns is not None:
        bench = benchmark_returns.reindex(daily.index).dropna()
        common = daily.index.intersection(bench.index)
        if len(common) >= 30:
            d_aligned = daily.loc[common]
            b_aligned = bench.loc[common]
            cov = float(np.cov(d_aligned.values, b_aligned.values, ddof=1)[0, 1])
            var_b = float(np.var(b_aligned.values, ddof=1))
            beta = cov / var_b if var_b > 0 else float("nan")
            if np.isfinite(beta):
                alpha_daily = float(d_aligned.mean() - rf_daily) - beta * float(b_aligned.mean() - rf_daily)
                alpha = alpha_daily * TRADING_DAYS_PER_YEAR
            active = d_aligned - b_aligned
            te_std = _safe_std(active, ddof=1)
            tracking_error = float(te_std * np.sqrt(TRADING_DAYS_PER_YEAR)) if np.isfinite(te_std) else float("nan")
            info_ratio = float(active.mean() / te_std * np.sqrt(TRADING_DAYS_PER_YEAR)) if te_std and te_std > 0 else float("nan")
            hit_rate = float((active > 0).mean())

    yearly = {}
    if not daily.empty:
        for year, group in daily.groupby(daily.index.year):
            yearly[int(year)] = float((1.0 + group).prod() - 1.0)

    holdings_metrics = compute_holdings_metrics(
        holdings if holdings is not None else pd.DataFrame(),
        rebalance_log if rebalance_log is not None else pd.DataFrame(),
    )

    trade_count = int(len(rebalance_log)) if rebalance_log is not None else 0

    return PerformanceReport(
        total_return=total_return,
        cagr=cagr,
        volatility=vol,
        sharpe=sharpe,
        sortino=sortino,
        calmar=calmar,
        max_drawdown=max_dd,
        max_drawdown_start=dd_start,
        max_drawdown_end=dd_end,
        max_drawdown_recover_days=dd_recover,
        var_95=var_95,
        cvar_95=cvar_95,
        alpha=alpha,
        beta=beta,
        information_ratio=info_ratio,
        tracking_error=tracking_error,
        hit_rate=hit_rate,
        annual_turnover=holdings_metrics["annual_turnover"],
        avg_holding_period_days=holdings_metrics["avg_holding_period_days"],
        trade_count=trade_count,
        avg_holdings=holdings_metrics["avg_holdings"],
        max_holdings=holdings_metrics["max_holdings"],
        invested_days_pct=holdings_metrics["invested_days_pct"],
        yearly_returns=yearly,
    )
