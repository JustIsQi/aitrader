"""
Unified backtest result object for aitrader.

This module defines:
1. TradeRecord: normalized transaction/round-trip trade record.
2. BacktestResult: standard backtest output container.

The structure is designed for A-share formula backtests and can absorb
results from common sources (dict payloads, portfolio metrics, backtrader
engine objects, pandas inputs).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None


_TRADE_SYMBOL_KEYS = (
    "symbol",
    "ticker",
    "code",
    "security",
    "asset",
    "name",
    "标的",
    "证券",
)
_TRADE_ACTION_KEYS = (
    "action",
    "side",
    "type",
    "direction",
    "signal",
    "交易方向",
    "方向",
)
_TRADE_DATE_KEYS = (
    "date",
    "datetime",
    "time",
    "trade_date",
    "交易日期",
    "成交日期",
    "日期",
)
_TRADE_SHARES_KEYS = (
    "shares",
    "size",
    "quantity",
    "qty",
    "amount_shares",
    "成交数量",
    "股数",
    "数量",
)
_TRADE_PRICE_KEYS = (
    "price",
    "trade_price",
    "成交价",
    "成交均价",
)
_TRADE_AMOUNT_KEYS = (
    "amount",
    "value",
    "成交额",
    "金额",
    "成交金额",
)
_TRADE_FEE_KEYS = (
    "commission",
    "comm",
    "fee",
    "手续费",
    "佣金",
)
_TRADE_PNL_KEYS = (
    "pnl",
    "profit",
    "收益",
    "盈亏",
)
_TRADE_PNL_COMM_KEYS = (
    "pnl_comm",
    "net_pnl",
    "盈亏（含佣金）",
)
_TRADE_BUY_PRICE_KEYS = ("buy_price", "entry_price", "买入价", "open_price")
_TRADE_SELL_PRICE_KEYS = ("sell_price", "exit_price", "卖出价", "close_price")
_TRADE_BUY_DATE_KEYS = ("buy_date", "entry_date", "open_date", "买入日期", "开仓日期")
_TRADE_SELL_DATE_KEYS = ("sell_date", "exit_date", "close_date", "卖出日期", "平仓日期")
_TRADE_HOLDING_DAYS_KEYS = ("holding_days", "hold_days", "持仓天数")

_CURVE_DATE_KEYS = ("date", "datetime", "time", "index")
_CURVE_VALUE_KEYS = (
    "value",
    "equity",
    "portfolio_value",
    "net_value",
    "close",
    "cumulative_return",
    "benchmark",
    "策略",
)


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _to_native_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _to_float(value: Any, default: float = 0.0) -> float:
    value = _to_native_scalar(value)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    value = _to_native_scalar(value)
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if pd is not None and isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10**12:  # millisecond timestamp
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except Exception:
        pass

    formats = (
        "%Y%m%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _to_iso_date(value: Any) -> str:
    dt = _parse_datetime(value)
    return dt.strftime("%Y-%m-%d") if dt else ""


def _normalize_action(value: Any) -> str:
    if value is None:
        return "unknown"
    text = str(value).strip().lower()
    if not text:
        return "unknown"

    mapping = {
        "buy": "buy",
        "b": "buy",
        "long": "buy",
        "open": "buy",
        "买入": "buy",
        "开仓": "buy",
        "sell": "sell",
        "s": "sell",
        "short": "sell",
        "close": "sell",
        "卖出": "sell",
        "平仓": "sell",
        "roundtrip": "roundtrip",
    }
    return mapping.get(text, text)


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return {}


def _pick_value(record: Mapping[str, Any], keys: Iterable[str], default: Any = None) -> Any:
    if not record:
        return default

    for key in keys:
        if key in record and record[key] is not None:
            return record[key]

    lowered: Dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(key, str):
            lowered[key.lower()] = value

    for key in keys:
        if isinstance(key, str):
            lowered_value = lowered.get(key.lower())
            if lowered_value is not None:
                return lowered_value
    return default


def _to_builtin_data(value: Any) -> Any:
    value = _to_native_scalar(value)

    if value is None:
        return None

    if pd is not None:
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if isinstance(value, pd.Series):
            return {str(k): _to_builtin_data(v) for k, v in value.to_dict().items()}
        if isinstance(value, pd.DataFrame):
            return [_to_builtin_data(item) for item in value.to_dict("records")]

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _to_builtin_data(v) for k, v in value.items()}
    if _is_sequence(value):
        return [_to_builtin_data(item) for item in value]
    return value


def _normalize_curve(curve: Any, value_key: str = "value") -> List[Dict[str, Any]]:
    if curve is None:
        return []

    if pd is not None and isinstance(curve, pd.Series):
        records: List[Dict[str, Any]] = []
        for idx, val in curve.items():
            records.append({"date": _to_iso_date(idx), value_key: _to_float(val, 0.0)})
        return records

    if pd is not None and isinstance(curve, pd.DataFrame):
        if curve.empty:
            return []

        df = curve.copy()
        if "date" not in df.columns:
            if isinstance(df.index, pd.DatetimeIndex) or df.index.name is not None:
                df = df.reset_index()

        date_col = None
        value_col = None
        for key in _CURVE_DATE_KEYS:
            if key in df.columns:
                date_col = key
                break
        for key in (value_key,) + _CURVE_VALUE_KEYS:
            if key in df.columns:
                value_col = key
                break
        if value_col is None:
            numeric_cols = [c for c in df.columns if c != date_col]
            if not numeric_cols:
                return []
            value_col = numeric_cols[0]

        records = []
        for _, row in df.iterrows():
            item = {
                "date": _to_iso_date(row[date_col]) if date_col else "",
                value_key: _to_float(row[value_col], 0.0),
            }
            records.append(item)
        return records

    if isinstance(curve, Mapping):
        curve_map = dict(curve)

        date_seq = _pick_value(curve_map, ("dates", "date", "datetime", "time"))
        value_seq = _pick_value(curve_map, (value_key, "values", "value", "equity", "benchmark"))
        if _is_sequence(date_seq) and _is_sequence(value_seq):
            length = min(len(date_seq), len(value_seq))
            return [
                {
                    "date": _to_iso_date(date_seq[i]),
                    value_key: _to_float(value_seq[i], 0.0),
                }
                for i in range(length)
            ]

        if all(not isinstance(v, (Mapping, list, tuple, set)) for v in curve_map.values()):
            # {date: value}
            return [
                {
                    "date": _to_iso_date(k) if _to_iso_date(k) else str(k),
                    value_key: _to_float(v, 0.0),
                }
                for k, v in curve_map.items()
            ]

        return []

    if _is_sequence(curve):
        records = []
        for idx, item in enumerate(curve):
            if isinstance(item, Mapping):
                item_map = dict(item)
                item_date = _pick_value(item_map, _CURVE_DATE_KEYS, "")
                item_val = _pick_value(item_map, (value_key,) + _CURVE_VALUE_KEYS, 0.0)
                records.append(
                    {
                        "date": _to_iso_date(item_date),
                        value_key: _to_float(item_val, 0.0),
                    }
                )
                continue

            if _is_sequence(item) and len(item) >= 2:
                records.append(
                    {
                        "date": _to_iso_date(item[0]),
                        value_key: _to_float(item[1], 0.0),
                    }
                )
                continue

            records.append(
                {
                    "date": str(idx),
                    value_key: _to_float(item, 0.0),
                }
            )
        return records

    return []


def _normalize_positions(positions: Any) -> List[Dict[str, Any]]:
    if positions is None:
        return []

    if pd is not None and isinstance(positions, pd.DataFrame):
        return [_to_builtin_data(item) for item in positions.to_dict("records")]
    if pd is not None and isinstance(positions, pd.Series):
        return [{"symbol": str(k), "value": _to_builtin_data(v)} for k, v in positions.items()]

    if isinstance(positions, Mapping):
        normalized: List[Dict[str, Any]] = []
        for symbol, detail in positions.items():
            if isinstance(detail, Mapping):
                item = dict(detail)
                item.setdefault("symbol", str(symbol))
                normalized.append(_to_builtin_data(item))
            else:
                normalized.append({"symbol": str(symbol), "value": _to_builtin_data(detail)})
        return normalized

    if _is_sequence(positions):
        out = []
        for item in positions:
            if isinstance(item, Mapping):
                out.append(_to_builtin_data(item))
            else:
                out.append({"value": _to_builtin_data(item)})
        return out

    return []


def _normalize_mapping(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if pd is not None and isinstance(value, pd.Series):
        return {str(k): _to_builtin_data(v) for k, v in value.items()}
    if isinstance(value, Mapping):
        return {str(k): _to_builtin_data(v) for k, v in value.items()}
    if _is_sequence(value):
        try:
            return {str(k): _to_builtin_data(v) for k, v in value}  # sequence of pairs
        except Exception:
            return {"items": _to_builtin_data(value)}
    return {"value": _to_builtin_data(value)}


def _normalize_statistics(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if pd is not None and isinstance(value, pd.Series):
        return {str(k): _to_builtin_data(v) for k, v in value.items()}
    if pd is not None and isinstance(value, pd.DataFrame):
        if value.empty:
            return {}
        if len(value.columns) == 1:
            col = value.columns[0]
            return {str(idx): _to_builtin_data(val) for idx, val in value[col].items()}
        return {
            str(idx): _to_builtin_data(row.to_dict())
            for idx, row in value.iterrows()
        }
    if isinstance(value, Mapping):
        return {str(k): _to_builtin_data(v) for k, v in value.items()}
    return {"value": _to_builtin_data(value)}


@dataclass
class TradeRecord:
    """Normalized trade record."""

    symbol: str = ""
    action: str = "unknown"
    date: str = ""
    shares: int = 0
    price: float = 0.0
    amount: float = 0.0
    commission: float = 0.0
    pnl: float = 0.0
    pnl_comm: float = 0.0
    buy_price: float = 0.0
    sell_price: float = 0.0
    buy_date: str = ""
    sell_date: str = ""
    holding_days: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def normalize(cls, trade: Any, default_date: Optional[str] = None) -> "TradeRecord":
        """
        Normalize a single trade record into the standard structure.

        Supported input:
        - dict-like trade records
        - dataclass/object instances with attributes
        - tuple/list style rows
        """
        if trade is None:
            return cls(date=default_date or "")

        record = _coerce_mapping(trade)
        if not record and _is_sequence(trade):
            seq = list(trade)
            if len(seq) >= 5:
                record = {
                    "date": seq[0],
                    "symbol": seq[1],
                    "action": seq[2],
                    "shares": seq[3],
                    "price": seq[4],
                }
            elif len(seq) >= 2:
                record = {
                    "symbol": seq[0],
                    "price": seq[1],
                }
            else:
                record = {"value": seq[0]} if seq else {}

        symbol = str(_pick_value(record, _TRADE_SYMBOL_KEYS, "") or "")
        action = _normalize_action(_pick_value(record, _TRADE_ACTION_KEYS, "unknown"))

        buy_price = _to_float(_pick_value(record, _TRADE_BUY_PRICE_KEYS, 0.0), 0.0)
        sell_price = _to_float(_pick_value(record, _TRADE_SELL_PRICE_KEYS, 0.0), 0.0)
        price = _to_float(_pick_value(record, _TRADE_PRICE_KEYS, 0.0), 0.0)

        if price == 0.0:
            if action == "buy" and buy_price > 0:
                price = buy_price
            elif action == "sell" and sell_price > 0:
                price = sell_price
            elif sell_price > 0:
                price = sell_price
            elif buy_price > 0:
                price = buy_price

        shares = _to_int(_pick_value(record, _TRADE_SHARES_KEYS, 0), 0)
        if shares < 0:
            shares = abs(shares)
            if action == "unknown":
                action = "sell"

        amount = _to_float(_pick_value(record, _TRADE_AMOUNT_KEYS, 0.0), 0.0)
        if amount == 0.0 and shares > 0 and price > 0:
            amount = shares * price

        commission = _to_float(_pick_value(record, _TRADE_FEE_KEYS, 0.0), 0.0)
        pnl = _to_float(_pick_value(record, _TRADE_PNL_KEYS, 0.0), 0.0)
        pnl_comm = _to_float(_pick_value(record, _TRADE_PNL_COMM_KEYS, pnl), pnl)

        buy_date = _to_iso_date(_pick_value(record, _TRADE_BUY_DATE_KEYS, ""))
        sell_date = _to_iso_date(_pick_value(record, _TRADE_SELL_DATE_KEYS, ""))
        trade_date = _to_iso_date(_pick_value(record, _TRADE_DATE_KEYS, ""))
        if not trade_date:
            trade_date = sell_date or buy_date or (default_date or "")

        holding_days_raw = _pick_value(record, _TRADE_HOLDING_DAYS_KEYS, None)
        holding_days = _to_int(holding_days_raw, 0) if holding_days_raw is not None else None
        if holding_days is None and buy_date and sell_date:
            buy_dt = _parse_datetime(buy_date)
            sell_dt = _parse_datetime(sell_date)
            if buy_dt and sell_dt:
                holding_days = (sell_dt - buy_dt).days

        if action == "unknown" and buy_price > 0 and sell_price > 0:
            action = "roundtrip"

        return cls(
            symbol=symbol,
            action=action,
            date=trade_date,
            shares=shares,
            price=price,
            amount=amount,
            commission=commission,
            pnl=pnl,
            pnl_comm=pnl_comm,
            buy_price=buy_price,
            sell_price=sell_price,
            buy_date=buy_date,
            sell_date=sell_date,
            holding_days=holding_days,
            raw=_to_builtin_data(record) or {},
        )

    @classmethod
    def normalize_many(
        cls,
        trades: Any,
        default_date: Optional[str] = None,
    ) -> List["TradeRecord"]:
        """Normalize batch trade inputs."""
        if trades is None:
            return []

        if pd is not None and isinstance(trades, pd.DataFrame):
            rows: List[Any] = trades.to_dict("records")
        elif isinstance(trades, Mapping):
            # If caller directly passes a dict-style record, normalize as one item.
            rows = [trades]
        elif _is_sequence(trades):
            rows = list(trades)
        else:
            rows = [trades]

        normalized: List[TradeRecord] = []
        for item in rows:
            if item is None:
                continue
            normalized.append(cls.normalize(item, default_date=default_date))
        return normalized

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "symbol": self.symbol,
            "action": self.action,
            "date": self.date,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "commission": self.commission,
            "pnl": self.pnl,
            "pnl_comm": self.pnl_comm,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "buy_date": self.buy_date,
            "sell_date": self.sell_date,
            "holding_days": self.holding_days,
            "raw": self.raw,
        }


@dataclass
class BacktestResult:
    """
    Standardized backtest result container.

    Required major fields:
    - statistics
    - equity_curve
    - benchmark_curve
    - trades
    - positions
    - signals
    - weights
    - analyzers
    - raw
    """

    statistics: Dict[str, Any] = field(default_factory=dict)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    benchmark_curve: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    positions: List[Dict[str, Any]] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=dict)
    weights: Dict[str, Any] = field(default_factory=dict)
    analyzers: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def get_stat(self, key: str, default: Any = None) -> Any:
        """Best-effort access to a statistic item."""
        value = self.statistics.get(key, default)
        if isinstance(value, Mapping):
            for candidate in ("策略", "strategy", "value"):
                if candidate in value:
                    return value[candidate]
            for item in value.values():
                return item
        return value

    @staticmethod
    def normalize_trade_record(trade: Any, default_date: Optional[str] = None) -> TradeRecord:
        """Helper: normalize one trade record."""
        return TradeRecord.normalize(trade, default_date=default_date)

    @staticmethod
    def normalize_trade_records(trades: Any, default_date: Optional[str] = None) -> List[TradeRecord]:
        """Helper: normalize multiple trade records."""
        return TradeRecord.normalize_many(trades, default_date=default_date)

    def append_trades(self, trades: Any, default_date: Optional[str] = None) -> None:
        """Append normalized trade records."""
        self.trades.extend(TradeRecord.normalize_many(trades, default_date=default_date))

    def to_dict(self, include_raw: bool = True, trade_as_dict: bool = True) -> Dict[str, Any]:
        """Serialize the standardized object."""
        trade_payload: List[Any]
        if trade_as_dict:
            trade_payload = [trade.to_dict() for trade in self.trades]
        else:
            trade_payload = list(self.trades)

        payload = {
            "statistics": _to_builtin_data(self.statistics),
            "equity_curve": _to_builtin_data(self.equity_curve),
            "benchmark_curve": _to_builtin_data(self.benchmark_curve),
            "trades": trade_payload,
            "positions": _to_builtin_data(self.positions),
            "signals": _to_builtin_data(self.signals),
            "weights": _to_builtin_data(self.weights),
            "analyzers": _to_builtin_data(self.analyzers),
        }
        if include_raw:
            payload["raw"] = _to_builtin_data(self.raw)
        return payload

    def stats(self) -> Any:
        """
        Print a compact statistics table and return it.

        Kept for compatibility with existing scripts that expect
        `engine.run(task).stats()`.
        """
        if pd is None:
            print(self.statistics)
            return self.statistics

        if not self.statistics:
            print("No backtest statistics available.")
            return pd.DataFrame()

        rows = []
        for key, value in self.statistics.items():
            if isinstance(value, Mapping):
                row = {"metric": key}
                row.update(value)
            else:
                row = {"metric": key, "value": value}
            rows.append(row)

        df = pd.DataFrame(rows)
        print(df.to_string(index=False))
        return df

    def plot(self) -> None:
        """
        Plot strategy and benchmark curves if available.

        Uses matplotlib only when the caller explicitly invokes it.
        """
        if pd is None:
            raise RuntimeError("pandas is required for plotting")
        if not self.equity_curve:
            raise ValueError("No equity curve available to plot")

        import matplotlib.pyplot as plt

        equity_df = pd.DataFrame(self.equity_curve)
        equity_df["date"] = pd.to_datetime(equity_df["date"])
        equity_df = equity_df.sort_values("date")

        plt.figure(figsize=(12, 6))
        plt.plot(equity_df["date"], equity_df["value"], label="strategy", linewidth=2)

        if self.benchmark_curve:
            benchmark_df = pd.DataFrame(self.benchmark_curve)
            benchmark_df["date"] = pd.to_datetime(benchmark_df["date"])
            benchmark_df = benchmark_df.sort_values("date")
            plt.plot(benchmark_df["date"], benchmark_df["value"], label="benchmark", linewidth=1.5)

        plt.legend()
        plt.tight_layout()
        plt.show()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "BacktestResult":
        """
        Build standardized result from a dict-like payload.

        Compatible with common keys:
        - statistics/stats/metrics
        - equity_curve/equity
        - benchmark_curve/benchmark
        - trades/trade_list/hist_trades/transaction_history
        - positions/final_holdings/holdings
        - signals
        - weights
        - analyzers
        - raw/raw_data
        """
        payload = dict(data)

        stats_src = _pick_value(payload, ("statistics", "stats", "metrics"), None)
        stats = _normalize_statistics(stats_src)
        if not stats:
            excluded = {
                "statistics",
                "stats",
                "metrics",
                "equity_curve",
                "equity",
                "benchmark_curve",
                "benchmark",
                "trades",
                "trade_list",
                "hist_trades",
                "transaction_history",
                "positions",
                "final_holdings",
                "holdings",
                "signals",
                "weights",
                "analyzers",
                "raw",
                "raw_data",
            }
            stats = {
                str(k): _to_builtin_data(v)
                for k, v in payload.items()
                if str(k) not in excluded
            }

        equity_input = _pick_value(payload, ("equity_curve", "equity", "equityCurve"), None)
        benchmark_input = _pick_value(
            payload,
            ("benchmark_curve", "benchmark", "benchmarkCurve"),
            None,
        )

        trades_input = _pick_value(
            payload,
            ("trades", "trade_list", "hist_trades", "transaction_history"),
            None,
        )
        positions_input = _pick_value(payload, ("positions", "final_holdings", "holdings"), None)
        signals_input = _pick_value(payload, ("signals",), None)
        weights_input = _pick_value(payload, ("weights",), None)
        analyzers_input = _pick_value(payload, ("analyzers", "analysis"), None)

        raw_input = _pick_value(payload, ("raw", "raw_data"), None)
        if raw_input is None:
            raw_input = payload

        return cls(
            statistics=stats,
            equity_curve=_normalize_curve(equity_input, value_key="value"),
            benchmark_curve=_normalize_curve(benchmark_input, value_key="value"),
            trades=TradeRecord.normalize_many(trades_input),
            positions=_normalize_positions(positions_input),
            signals=_normalize_mapping(signals_input),
            weights=_normalize_mapping(weights_input),
            analyzers=_normalize_mapping(analyzers_input),
            raw=_normalize_mapping(raw_input),
        )

    @classmethod
    def from_backtrader_engine(cls, engine: Any) -> "BacktestResult":
        """
        Build standardized result from Backtrader engine instance.

        Expected attrs on engine (best effort):
        - perf.stats / perf.prices
        - hist_trades
        - positions
        - signals
        - weights
        - results[0].analyzers
        """
        existing = getattr(engine, "backtest_result", None)
        if isinstance(existing, cls):
            return existing

        stats: Dict[str, Any] = {}
        equity_curve: List[Dict[str, Any]] = []
        benchmark_curve: List[Dict[str, Any]] = []

        perf = getattr(engine, "perf", None)
        perf_stats = getattr(perf, "stats", None)
        perf_prices = getattr(perf, "prices", None)

        if perf_stats is not None:
            stats = _normalize_statistics(perf_stats)

        if perf_prices is not None and pd is not None and isinstance(perf_prices, pd.DataFrame):
            strategy_col = None
            benchmark_col = None

            for col in perf_prices.columns:
                col_text = str(col).lower()
                if strategy_col is None and (str(col) == "策略" or col_text == "strategy"):
                    strategy_col = col
                if benchmark_col is None and "benchmark" in col_text:
                    benchmark_col = col

            if strategy_col is None and len(perf_prices.columns) >= 1:
                strategy_col = perf_prices.columns[0]
            if benchmark_col is None and len(perf_prices.columns) >= 2:
                for col in perf_prices.columns[1:]:
                    if str(col) != str(strategy_col):
                        benchmark_col = col
                        break

            if strategy_col is not None:
                equity_curve = _normalize_curve(perf_prices[strategy_col], value_key="value")
            if benchmark_col is not None:
                benchmark_curve = _normalize_curve(perf_prices[benchmark_col], value_key="value")

        trades_input = getattr(engine, "hist_trades", None)
        positions_input = getattr(engine, "positions", None)
        signals_input = getattr(engine, "signals", None)
        weights_input = getattr(engine, "weights", None)

        analyzer_holder = {}
        results = getattr(engine, "results", None)
        if _is_sequence(results) and len(results) > 0:
            first_result = results[0]
            analyzers = getattr(first_result, "analyzers", None)
            if analyzers is not None:
                analyzer_holder["backtrader"] = analyzers

        raw_payload = {
            "perf_stats": perf_stats,
            "perf_prices": perf_prices,
            "hist_trades": trades_input,
            "positions": positions_input,
        }

        return cls(
            statistics=stats,
            equity_curve=equity_curve,
            benchmark_curve=benchmark_curve,
            trades=TradeRecord.normalize_many(trades_input),
            positions=_normalize_positions(positions_input),
            signals=_normalize_mapping(signals_input),
            weights=_normalize_mapping(weights_input),
            analyzers=analyzer_holder,
            raw=_normalize_mapping(raw_payload),
        )

    @classmethod
    def from_common_inputs(
        cls,
        statistics: Optional[Any] = None,
        equity_curve: Optional[Any] = None,
        benchmark_curve: Optional[Any] = None,
        trades: Optional[Any] = None,
        positions: Optional[Any] = None,
        signals: Optional[Any] = None,
        weights: Optional[Any] = None,
        analyzers: Optional[Any] = None,
        raw: Optional[Any] = None,
    ) -> "BacktestResult":
        """
        Build standardized result from explicit field inputs.
        """
        return cls(
            statistics=_normalize_statistics(statistics),
            equity_curve=_normalize_curve(equity_curve, value_key="value"),
            benchmark_curve=_normalize_curve(benchmark_curve, value_key="value"),
            trades=TradeRecord.normalize_many(trades),
            positions=_normalize_positions(positions),
            signals=_normalize_mapping(signals),
            weights=_normalize_mapping(weights),
            analyzers=_normalize_mapping(analyzers),
            raw=_normalize_mapping(raw),
        )


__all__ = ["TradeRecord", "BacktestResult"]
