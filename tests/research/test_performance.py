"""绩效指标单元测试。

验证 sharpe / sortino / max_drawdown / alpha / beta / VaR 数值正确。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aitrader.research.metrics import compute_performance, rolling_alpha, rolling_sharpe


@pytest.fixture
def rets() -> pd.Series:
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.0008, 0.012, len(dates)), index=dates)


@pytest.fixture
def bench(rets: pd.Series) -> pd.Series:
    rng = np.random.default_rng(7)
    noise = pd.Series(rng.normal(0.0, 0.005, len(rets)), index=rets.index)
    return 0.5 * rets + noise + 0.0003


def test_total_return_and_cagr() -> None:
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    r = pd.Series(np.full(252, 0.001), index=dates)
    rep = compute_performance(r, risk_free_annual=0.0)
    assert rep.total_return == pytest.approx((1.001 ** 252) - 1, rel=1e-6)
    assert rep.cagr > 0
    assert rep.volatility == pytest.approx(0.0, abs=1e-9)


def test_sharpe_uses_rf_and_ddof1() -> None:
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.001, 0.02, 252), index=dates)
    rep = compute_performance(r, risk_free_annual=0.0)
    expected = r.mean() / r.std(ddof=1) * np.sqrt(252)
    assert rep.sharpe == pytest.approx(expected, rel=1e-6)
    rep_rf = compute_performance(r, risk_free_annual=0.05)
    rf_daily = (1.05) ** (1 / 252) - 1
    excess = r - rf_daily
    expected_rf = excess.mean() / excess.std(ddof=1) * np.sqrt(252)
    assert rep_rf.sharpe == pytest.approx(expected_rf, rel=1e-6)


def test_max_drawdown() -> None:
    eq = pd.Series(
        [1.0, 1.2, 1.5, 1.0, 0.9, 1.1, 1.6],
        index=pd.date_range("2020-01-01", periods=7, freq="B"),
    )
    r = eq.pct_change().fillna(0.0)
    rep = compute_performance(r, risk_free_annual=0.0)
    assert rep.max_drawdown == pytest.approx((0.9 - 1.5) / 1.5, abs=1e-9)
    assert rep.max_drawdown_start == "2020-01-03"
    assert rep.max_drawdown_end == "2020-01-07"


def test_sortino_only_downside() -> None:
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    r = pd.Series(
        np.where(np.arange(252) % 2 == 0, 0.01, -0.005),
        index=dates,
    ).astype(float)
    rep = compute_performance(r, risk_free_annual=0.0)
    excess = r - 0.0
    downside = excess[excess < 0]
    expected = excess.mean() / downside.std(ddof=1) * np.sqrt(252)
    assert rep.sortino == pytest.approx(expected, rel=1e-6)


def test_var_cvar_signs() -> None:
    dates = pd.date_range("2020-01-01", periods=252, freq="B")
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.0, 0.01, 252), index=dates)
    rep = compute_performance(r, risk_free_annual=0.0)
    expected_var = float(np.quantile(r.values, 0.05))
    assert rep.var_95 == pytest.approx(expected_var, rel=1e-6)
    expected_cvar = float(r[r <= expected_var].mean())
    assert rep.cvar_95 == pytest.approx(expected_cvar, rel=1e-6)
    assert rep.var_95 < 0
    assert rep.cvar_95 < rep.var_95


def test_alpha_beta_information_ratio(rets: pd.Series, bench: pd.Series) -> None:
    rep = compute_performance(rets, benchmark_returns=bench, risk_free_annual=0.0)
    cov = np.cov(rets.values, bench.values, ddof=1)
    expected_beta = cov[0, 1] / cov[1, 1]
    assert rep.beta == pytest.approx(expected_beta, rel=1e-6)
    expected_alpha = (rets.mean() - expected_beta * bench.mean()) * 252
    assert rep.alpha == pytest.approx(expected_alpha, rel=1e-6)
    active = rets - bench
    expected_ir = active.mean() / active.std(ddof=1) * np.sqrt(252)
    assert rep.information_ratio == pytest.approx(expected_ir, rel=1e-6)
    expected_te = active.std(ddof=1) * np.sqrt(252)
    assert rep.tracking_error == pytest.approx(expected_te, rel=1e-6)


def test_rolling_metrics(rets: pd.Series, bench: pd.Series) -> None:
    rs = rolling_sharpe(rets, window=60)
    assert rs.dropna().shape[0] > 0
    ra = rolling_alpha(rets, bench, window=60)
    assert ra.dropna().shape[0] > 0


def test_yearly_returns() -> None:
    dates = pd.date_range("2020-01-01", "2022-12-31", freq="B")
    r = pd.Series(0.001, index=dates)
    rep = compute_performance(r, risk_free_annual=0.0)
    assert 2020 in rep.yearly_returns
    assert 2021 in rep.yearly_returns
    assert 2022 in rep.yearly_returns
    assert rep.yearly_returns[2020] > 0


def test_holdings_metrics_shape() -> None:
    dates = pd.date_range("2020-01-01", periods=120, freq="B")
    r = pd.Series(0.0005, index=dates)
    holdings = pd.DataFrame(
        np.tile([0.5, 0.5, 0.0], (len(dates), 1)),
        index=dates,
        columns=["A", "B", "C"],
    )
    rebal = pd.DataFrame({"date": [dates[10], dates[60]], "turnover_pct": [0.5, 0.3]})
    rep = compute_performance(r, holdings=holdings, rebalance_log=rebal, risk_free_annual=0.0)
    assert rep.avg_holdings == pytest.approx(2.0, abs=1e-9)
    assert rep.max_holdings == 2
    assert rep.invested_days_pct == pytest.approx(1.0, abs=1e-9)
    assert rep.trade_count == 2
    assert rep.annual_turnover > 0
    assert rep.avg_holding_period_days > 0
