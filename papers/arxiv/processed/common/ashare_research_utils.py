from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from aitrader.domain.market.stock_universe import StockUniverse
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


DEFAULT_START_DATE = "20190101"
DEFAULT_END_DATE = "20241231"
DEFAULT_COST_RATE = 0.001
DEFAULT_CHUNK_SIZE = 200

PRICE_COLUMNS = [
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "change_pct",
]

_PRICE_HISTORY_CACHE: dict[tuple, pd.DataFrame] = {}
_LIQUID_SYMBOL_CACHE: dict[tuple, list[str]] = {}


@dataclass
class ResearchBacktestResult:
    strategy: str
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    volatility: float
    trade_count: int
    first_trade_date: str
    invested_days_pct: float
    avg_holdings: float
    equity_curve: pd.Series
    daily_returns: pd.Series

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "total_return": self.total_return,
            "cagr": self.cagr,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "volatility": self.volatility,
            "trade_count": self.trade_count,
            "first_trade_date": self.first_trade_date,
            "invested_days_pct": self.invested_days_pct,
            "avg_holdings": self.avg_holdings,
        }


def build_mainboard_universe(
    end_date: str = DEFAULT_END_DATE,
    min_data_days: int = 750,
) -> list[str]:
    universe = StockUniverse()
    return universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=365,
        min_data_days=min_data_days,
        exclude_restricted_stocks=True,
        as_of_date=end_date,
    )


def _normalize_date(value: str) -> str:
    return str(value).replace("-", "")


def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def _coerce_numeric(df: pd.DataFrame, exclude: set[str]) -> pd.DataFrame:
    for column in df.columns:
        if column not in exclude:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def read_price_history(
    symbols: list[str],
    start_date: str,
    end_date: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> pd.DataFrame:
    unique_symbols = sorted({symbol for symbol in symbols if symbol})
    if not unique_symbols:
        raise ValueError("没有可读取的股票代码")

    start_norm = _normalize_date(start_date)
    end_norm = _normalize_date(end_date)
    cache_key = (tuple(unique_symbols), start_norm, end_norm)
    cached = _PRICE_HISTORY_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()

    reader = MySQLAshareReader()
    frames: list[pd.DataFrame] = []
    query_template = """
        SELECT
            TRADE_DT AS date,
            S_INFO_WINDCODE AS symbol,
            S_DQ_ADJOPEN AS open,
            S_DQ_ADJHIGH AS high,
            S_DQ_ADJLOW AS low,
            S_DQ_ADJCLOSE AS close,
            S_DQ_VOLUME AS volume,
            S_DQ_AMOUNT AS amount,
            S_DQ_PCTCHANGE AS change_pct
        FROM ASHAREEODPRICES
        WHERE S_INFO_WINDCODE IN ({placeholders})
          AND TRADE_DT >= %s
          AND TRADE_DT <= %s
        ORDER BY S_INFO_WINDCODE ASC, TRADE_DT ASC
    """

    with reader.connect() as connection:
        with connection.cursor() as cursor:
            for batch in _batched(unique_symbols, chunk_size):
                placeholders = ", ".join(["%s"] * len(batch))
                query = query_template.format(placeholders=placeholders)
                cursor.execute(query, [*batch, start_norm, end_norm])
                rows = cursor.fetchall()
                if rows:
                    frames.append(pd.DataFrame(rows))

    if not frames:
        raise ValueError(
            f"价格表中未读取到数据: {start_norm} ~ {end_norm}, 标的数={len(unique_symbols)}"
        )

    all_df = pd.concat(frames, ignore_index=True)
    all_df = _coerce_numeric(all_df, exclude={"date", "symbol"})
    all_df["date"] = pd.to_datetime(all_df["date"], format="%Y%m%d", errors="coerce")
    all_df["symbol"] = all_df["symbol"].astype(str)
    all_df.dropna(subset=["date", "symbol", "close"], inplace=True)
    all_df = all_df[PRICE_COLUMNS].sort_values(["date", "symbol"]).reset_index(drop=True)
    _PRICE_HISTORY_CACHE[cache_key] = all_df
    return all_df.copy()


def pick_liquid_symbols(
    end_date: str = DEFAULT_END_DATE,
    max_symbols: int = 120,
    min_data_days: int = 750,
) -> list[str]:
    cache_key = (_normalize_date(end_date), max_symbols, min_data_days)
    cached = _LIQUID_SYMBOL_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)

    base_symbols = build_mainboard_universe(end_date=end_date, min_data_days=min_data_days)
    snapshot_end = pd.Timestamp(end_date)
    snapshot_start = (snapshot_end - pd.Timedelta(days=45)).strftime("%Y%m%d")
    snapshot_df = read_price_history(
        base_symbols,
        start_date=snapshot_start,
        end_date=end_date,
    )

    rows = []
    for symbol, df in snapshot_df.groupby("symbol", sort=True):
        recent = df.sort_values("date").tail(20)
        if len(recent) < 10:
            continue
        last = recent.iloc[-1]
        rows.append(
            {
                "symbol": symbol,
                "close": float(last.get("close", np.nan)),
                "avg_amount": float(pd.to_numeric(recent.get("amount"), errors="coerce").mean()),
                "avg_volume": float(pd.to_numeric(recent.get("volume"), errors="coerce").mean()),
                "median_amount": float(pd.to_numeric(recent.get("amount"), errors="coerce").median()),
            }
        )

    snapshot = pd.DataFrame(rows)
    if snapshot.empty:
        raise ValueError("无法构建流动性股票池：快照为空")

    filtered = snapshot[
        snapshot["close"].gt(3.0)
        & snapshot["avg_amount"].gt(0)
        & snapshot["avg_volume"].gt(0)
    ].copy()
    if len(filtered) < max_symbols:
        filtered = snapshot[snapshot["avg_amount"].gt(0)].copy()

    filtered.sort_values(
        ["avg_amount", "median_amount", "avg_volume", "close"],
        ascending=[False, False, False, False],
        inplace=True,
    )
    result = filtered["symbol"].head(max_symbols).tolist()
    _LIQUID_SYMBOL_CACHE[cache_key] = result
    return result


def load_panels(
    symbols: list[str],
    start_date: str,
    end_date: str,
    fields: Iterable[str],
) -> dict[str, pd.DataFrame]:
    requested_fields = list(dict.fromkeys(fields))
    all_df = read_price_history(symbols, start_date=start_date, end_date=end_date)
    all_df.sort_values(["date", "symbol"], inplace=True)

    panels: dict[str, pd.DataFrame] = {}
    for field in requested_fields:
        if field == "return":
            close_panel = panels.get("close")
            if close_panel is None:
                close_panel = all_df.pivot_table(
                    index="date",
                    columns="symbol",
                    values="close",
                    aggfunc="last",
                ).sort_index().ffill()
                panels["close"] = close_panel
            panels[field] = close_panel.pct_change()
            continue

        if field not in all_df.columns:
            raise KeyError(f"价格面板不支持字段: {field}")
        panel = all_df.pivot_table(
            index="date",
            columns="symbol",
            values=field,
            aggfunc="last",
        ).sort_index()
        if field == "close":
            panel = panel.ffill()
        panels[field] = panel
    return panels


def weekly_rebalance_dates(index: pd.DatetimeIndex, warmup_days: int = 60) -> list[pd.Timestamp]:
    dates: list[pd.Timestamp] = []
    last_week: tuple[int, int] | None = None

    for i, dt in enumerate(index):
        iso = dt.isocalendar()
        week_key = (int(iso.year), int(iso.week))
        if week_key != last_week:
            last_week = week_key
            if i > warmup_days:
                dates.append(dt)
    return dates


def monthly_rebalance_dates(index: pd.DatetimeIndex, warmup_days: int = 60) -> list[pd.Timestamp]:
    dates: list[pd.Timestamp] = []
    last_month: tuple[int, int] | None = None

    for i, dt in enumerate(index):
        month_key = (int(dt.year), int(dt.month))
        if month_key != last_month:
            last_month = month_key
            if i > warmup_days:
                dates.append(dt)
    return dates


def previous_trading_date(index: pd.DatetimeIndex, date: pd.Timestamp) -> pd.Timestamp | None:
    loc = index.get_indexer([date])[0]
    if loc <= 0:
        return None
    return index[loc - 1]


def leading_eigenvector_scores(matrix: pd.DataFrame) -> pd.Series:
    arr = matrix.fillna(0.0).to_numpy(dtype=float, copy=True)
    if arr.shape[0] == 0:
        return pd.Series(dtype=float)
    np.fill_diagonal(arr, 0.0)
    if not np.isfinite(arr).all():
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    try:
        vals, vecs = np.linalg.eigh(arr)
        vec = np.abs(vecs[:, -1])
    except np.linalg.LinAlgError:
        vec = np.abs(arr).sum(axis=1)

    scores = pd.Series(vec, index=matrix.index, dtype=float)
    if scores.sum() > 0:
        scores /= scores.sum()
    return scores.sort_values(ascending=False)


def complexity_gap(window_returns: pd.DataFrame) -> float:
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


def simulate_equal_weight_strategy(
    close: pd.DataFrame,
    selections_by_date: dict[pd.Timestamp, list[str]],
    cost_rate: float = DEFAULT_COST_RATE,
) -> ResearchBacktestResult:
    symbols = close.columns.tolist()
    returns = close.pct_change().fillna(0.0)
    current = pd.Series(0.0, index=symbols, dtype=float)
    daily_returns = []
    trade_dates = []
    holdings = []

    for dt in returns.index:
        turnover = 0.0
        selection = selections_by_date.get(dt)
        if selection is not None:
            target = pd.Series(0.0, index=symbols, dtype=float)
            valid = [s for s in selection if s in target.index]
            if valid:
                target.loc[valid] = 1.0 / len(valid)
            turnover = float((target - current).abs().sum() / 2.0)
            current = target
            if turnover > 1e-9:
                trade_dates.append(dt.strftime("%Y-%m-%d"))

        portfolio_return = float((current * returns.loc[dt].fillna(0.0)).sum()) - turnover * cost_rate
        daily_returns.append(portfolio_return)
        holdings.append(int((current > 0).sum()))

    daily_returns = pd.Series(daily_returns, index=returns.index, name="strategy")
    equity = (1.0 + daily_returns).cumprod()

    total_return = float(equity.iloc[-1] - 1.0)
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    cagr = float(equity.iloc[-1] ** (1.0 / years) - 1.0)
    vol = float(daily_returns.std(ddof=0) * np.sqrt(252))
    sharpe = float(daily_returns.mean() / daily_returns.std(ddof=0) * np.sqrt(252)) if daily_returns.std(ddof=0) > 0 else 0.0
    drawdown = equity / equity.cummax() - 1.0
    max_drawdown = float(drawdown.min())

    holdings_series = pd.Series(holdings, index=returns.index, dtype=float)
    invested_mask = holdings_series > 0
    invested_days_pct = float(invested_mask.mean()) if len(invested_mask) else 0.0
    avg_holdings = float(holdings_series[invested_mask].mean()) if invested_mask.any() else 0.0

    return ResearchBacktestResult(
        strategy="",
        total_return=total_return,
        cagr=cagr,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
        volatility=vol,
        trade_count=len(trade_dates),
        first_trade_date=trade_dates[0] if trade_dates else "",
        invested_days_pct=invested_days_pct,
        avg_holdings=avg_holdings,
        equity_curve=equity,
        daily_returns=daily_returns,
    )


def format_pct(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value * 100:+.2f}%"


def format_num(value: float) -> str:
    if not np.isfinite(value):
        return "NA"
    return f"{value:.2f}"


def write_markdown_summary(
    output_path: Path,
    title: str,
    paper_id: str,
    paper_title: str,
    methodology: str,
    result: ResearchBacktestResult,
    notes: list[str],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 回测摘要：{title}",
        "",
        f"- 论文ID: `{paper_id}`",
        f"- 论文标题: {paper_title}",
        f"- 方法映射: {methodology}",
        "",
        "## 核心指标",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 总收益 | {format_pct(result.total_return)} |",
        f"| 复合年化收益 | {format_pct(result.cagr)} |",
        f"| 夏普比率 | {format_num(result.sharpe)} |",
        f"| 最大回撤 | {format_pct(result.max_drawdown)} |",
        f"| 波动率 | {format_pct(result.volatility)} |",
        f"| 交易次数 | {result.trade_count} |",
        f"| 首次交易日 | {result.first_trade_date or 'NA'} |",
        f"| 持仓天数占比 | {format_pct(result.invested_days_pct)} |",
        f"| 平均持仓数 | {result.avg_holdings:.1f} |",
        "",
        "## 结论",
        "",
    ]
    lines.extend([f"- {note}" for note in notes])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
