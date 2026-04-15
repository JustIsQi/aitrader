"""
Portfolio daily result model and helpers.

This module is intentionally standalone so portfolio engines can integrate
without changing existing tracker/metrics implementations.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

import pandas as pd


HoldingSnapshot = Dict[str, Dict[str, Any]]


def normalize_trade_date(value: Any) -> str:
    """Normalize supported date-like values to `YYYY-MM-DD` string."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("date is required")

        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        try:
            return pd.to_datetime(value).strftime("%Y-%m-%d")
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"unsupported date string: {value}") from exc

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    raise TypeError(f"unsupported date type: {type(value)!r}")


def clone_holdings(holdings: Optional[Mapping[str, Any]]) -> HoldingSnapshot:
    """Clone holdings to avoid shared mutable references."""
    if not holdings:
        return {}

    output: HoldingSnapshot = {}
    for symbol, payload in holdings.items():
        if isinstance(payload, Mapping):
            output[str(symbol)] = dict(payload)
        else:
            output[str(symbol)] = {"value": payload}
    return deepcopy(output)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _holding_market_value(position: Mapping[str, Any]) -> float:
    if "market_value" in position:
        return _to_float(position.get("market_value"))
    if "value" in position:
        return _to_float(position.get("value"))

    shares = _to_float(position.get("shares"))
    for px_key in ("price", "close", "last_price"):
        if px_key in position:
            return shares * _to_float(position.get(px_key))
    return 0.0


def calc_holdings_value(holdings: Optional[Mapping[str, Any]]) -> float:
    """Calculate aggregate holdings market value."""
    if not holdings:
        return 0.0

    total = 0.0
    for payload in holdings.values():
        if isinstance(payload, Mapping):
            total += _holding_market_value(payload)
        else:
            total += _to_float(payload)
    return total


@dataclass(slots=True)
class PortfolioDailyResult:
    """Single-day portfolio result."""

    date: Any
    holding_pnl: float = 0.0
    trading_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    turnover: float = 0.0
    cash: float = 0.0
    holdings: HoldingSnapshot = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.date = normalize_trade_date(self.date)
        self.holding_pnl = _to_float(self.holding_pnl)
        self.trading_pnl = _to_float(self.trading_pnl)
        self.commission = _to_float(self.commission)
        self.slippage = _to_float(self.slippage)
        self.turnover = _to_float(self.turnover)
        self.cash = _to_float(self.cash)
        self.holdings = clone_holdings(self.holdings)

    @property
    def gross_pnl(self) -> float:
        return self.holding_pnl + self.trading_pnl

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.commission - self.slippage

    @property
    def holdings_value(self) -> float:
        return calc_holdings_value(self.holdings)

    @property
    def equity(self) -> float:
        return self.cash + self.holdings_value

    @property
    def holdings_count(self) -> int:
        return len(self.holdings)

    def accumulate(
        self,
        *,
        holding_pnl: float = 0.0,
        trading_pnl: float = 0.0,
        commission: float = 0.0,
        slippage: float = 0.0,
        turnover: float = 0.0,
    ) -> None:
        """Accumulate same-day incremental values."""
        self.holding_pnl += _to_float(holding_pnl)
        self.trading_pnl += _to_float(trading_pnl)
        self.commission += _to_float(commission)
        self.slippage += _to_float(slippage)
        self.turnover += _to_float(turnover)

    def update_snapshot(
        self,
        *,
        cash: Optional[float] = None,
        holdings: Optional[Mapping[str, Any]] = None,
        replace_holdings: bool = True,
    ) -> None:
        """Update end-of-day cash/holdings snapshot."""
        if cash is not None:
            self.cash = _to_float(cash)

        if holdings is None:
            return

        incoming = clone_holdings(holdings)
        if replace_holdings:
            self.holdings = incoming
        else:
            merged = clone_holdings(self.holdings)
            merged.update(incoming)
            self.holdings = merged

    def to_dict(self, include_holdings: bool = True) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "date": self.date,
            "holding_pnl": self.holding_pnl,
            "trading_pnl": self.trading_pnl,
            "commission": self.commission,
            "slippage": self.slippage,
            "gross_pnl": self.gross_pnl,
            "net_pnl": self.net_pnl,
            "turnover": self.turnover,
            "cash": self.cash,
            "holdings_value": self.holdings_value,
            "equity": self.equity,
            "holdings_count": self.holdings_count,
        }
        if include_holdings:
            payload["holdings"] = clone_holdings(self.holdings)
        return payload


@dataclass
class PortfolioDailyLedger:
    """
    Daily result aggregator.

    Supports:
    - same-day multi-event accumulation
    - sorted daily export (`daily_df`)
    - equity curve export
    """

    results: Dict[str, PortfolioDailyResult] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.results)

    def __iter__(self) -> Iterator[PortfolioDailyResult]:
        for day in sorted(self.results):
            yield self.results[day]

    def get_or_create(
        self,
        date_value: Any,
        *,
        cash: Optional[float] = None,
        holdings: Optional[Mapping[str, Any]] = None,
    ) -> PortfolioDailyResult:
        day = normalize_trade_date(date_value)
        if day not in self.results:
            self.results[day] = PortfolioDailyResult(
                date=day,
                cash=_to_float(cash, 0.0) if cash is not None else 0.0,
                holdings=clone_holdings(holdings),
            )
            return self.results[day]

        result = self.results[day]
        if cash is not None or holdings is not None:
            result.update_snapshot(cash=cash, holdings=holdings, replace_holdings=True)
        return result

    def add_or_update(
        self,
        date_value: Any,
        *,
        holding_pnl: float = 0.0,
        trading_pnl: float = 0.0,
        commission: float = 0.0,
        slippage: float = 0.0,
        turnover: float = 0.0,
        cash: Optional[float] = None,
        holdings: Optional[Mapping[str, Any]] = None,
        replace_holdings: bool = True,
    ) -> PortfolioDailyResult:
        result = self.get_or_create(date_value)
        result.accumulate(
            holding_pnl=holding_pnl,
            trading_pnl=trading_pnl,
            commission=commission,
            slippage=slippage,
            turnover=turnover,
        )
        if cash is not None or holdings is not None:
            result.update_snapshot(cash=cash, holdings=holdings, replace_holdings=replace_holdings)
        return result

    def append(self, daily_result: PortfolioDailyResult) -> PortfolioDailyResult:
        """Append or merge an externally-built `PortfolioDailyResult`."""
        day = normalize_trade_date(daily_result.date)
        existing = self.results.get(day)
        if existing is None:
            self.results[day] = PortfolioDailyResult(
                date=day,
                holding_pnl=daily_result.holding_pnl,
                trading_pnl=daily_result.trading_pnl,
                commission=daily_result.commission,
                slippage=daily_result.slippage,
                turnover=daily_result.turnover,
                cash=daily_result.cash,
                holdings=daily_result.holdings,
            )
            return self.results[day]

        existing.accumulate(
            holding_pnl=daily_result.holding_pnl,
            trading_pnl=daily_result.trading_pnl,
            commission=daily_result.commission,
            slippage=daily_result.slippage,
            turnover=daily_result.turnover,
        )
        existing.update_snapshot(cash=daily_result.cash, holdings=daily_result.holdings, replace_holdings=True)
        return existing

    def to_daily_df(self, include_holdings: bool = True) -> pd.DataFrame:
        return build_daily_df(list(self), include_holdings=include_holdings)

    def to_equity_curve(self) -> List[Dict[str, Any]]:
        return build_equity_curve(list(self))


def build_daily_df(
    daily_results: Iterable[PortfolioDailyResult],
    *,
    include_holdings: bool = True,
) -> pd.DataFrame:
    """
    Export daily result DataFrame with cumulative fields.

    Output columns include daily + cumulative:
    - holding_pnl / cum_holding_pnl
    - trading_pnl / cum_trading_pnl
    - commission / cum_commission
    - slippage / cum_slippage
    - net_pnl / cum_net_pnl
    - turnover / cum_turnover
    """
    rows = [item.to_dict(include_holdings=include_holdings) for item in daily_results]

    base_columns = [
        "date",
        "holding_pnl",
        "trading_pnl",
        "commission",
        "slippage",
        "gross_pnl",
        "net_pnl",
        "turnover",
        "cash",
        "holdings_value",
        "equity",
        "holdings_count",
    ]
    if include_holdings:
        base_columns.append("holdings")

    if not rows:
        columns = base_columns + [
            "cum_holding_pnl",
            "cum_trading_pnl",
            "cum_commission",
            "cum_slippage",
            "cum_net_pnl",
            "cum_turnover",
        ]
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    cumulative_map = {
        "holding_pnl": "cum_holding_pnl",
        "trading_pnl": "cum_trading_pnl",
        "commission": "cum_commission",
        "slippage": "cum_slippage",
        "net_pnl": "cum_net_pnl",
        "turnover": "cum_turnover",
    }
    for src, dst in cumulative_map.items():
        df[dst] = df[src].cumsum()

    ordered_columns = base_columns + list(cumulative_map.values())
    return df[ordered_columns]


def build_equity_curve(daily_results: Iterable[PortfolioDailyResult]) -> List[Dict[str, Any]]:
    """
    Export equity curve friendly list.

    Kept compatible with existing project conventions:
    - `value` is an alias of `equity`
    """
    df = build_daily_df(daily_results, include_holdings=False)
    if df.empty:
        return []

    output_cols = [
        "date",
        "equity",
        "cash",
        "holdings_value",
        "net_pnl",
        "cum_net_pnl",
        "turnover",
        "cum_turnover",
    ]
    curve: List[Dict[str, Any]] = []
    for row in df[output_cols].to_dict(orient="records"):
        row["value"] = row["equity"]
        curve.append(row)
    return curve


__all__ = [
    "HoldingSnapshot",
    "PortfolioDailyResult",
    "PortfolioDailyLedger",
    "normalize_trade_date",
    "clone_holdings",
    "calc_holdings_value",
    "build_daily_df",
    "build_equity_curve",
]
