# AITrader Guide

## Run A-share Signals

```bash
python -m aitrader.app.cli.ashare_signals
```

Useful options:

```bash
python -m aitrader.app.cli.ashare_signals --workers 2
python -m aitrader.app.cli.ashare_signals --force-backtest
python -m aitrader.app.cli.ashare_signals --weekly
python -m aitrader.app.cli.ashare_signals --monthly
```

## Run Short-Term A-share Workflow

```bash
python -m aitrader.app.cli.short_term_signals
python -m aitrader.app.cli.short_term_signals 20260120
python -m aitrader.app.cli.short_term_signals 20260120 --fetch-only
python -m aitrader.app.cli.short_term_signals 20260120 --signals-only
```

## Configure MySQL Prices

Set `MYSQL_URL` or the component variables documented in `DATA.md`.

The price reader uses adjusted Wind columns as canonical OHLC values and keeps
raw prices in `real_*` columns.

## Strategy Files

A-share strategies live under:

```text
strategies/stocks_*.py
```

Each strategy returns a configured `Task`. The loader discovers only A-share
strategy files.

## Web UI

```bash
./web_server.sh
```

The dashboard displays A-share weekly/monthly signals and short-term operation
lists.

## Removed Commands

ETF signal generation and ETF portfolio backtests have been removed. Historical
A-share prices are read from MySQL and are not downloaded into a local cache.
