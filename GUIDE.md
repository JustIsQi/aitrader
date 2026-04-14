# AITrader Guide

## Run A-share Signals

```bash
python run_ashare_signals.py
```

Useful options:

```bash
python run_ashare_signals.py --workers 2
python run_ashare_signals.py --force-backtest
python run_ashare_signals.py --mode weekly
python run_ashare_signals.py --mode monthly
```

## Run Short-Term A-share Workflow

```bash
python run_short_term_signals.py
python run_short_term_signals.py 20260120
python run_short_term_signals.py 20260120 --fetch-only
python run_short_term_signals.py 20260120 --signals-only
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
