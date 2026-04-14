# AITrader

AITrader is now an A-share focused research, backtest, and signal-generation project.
Historical daily prices are read directly from Wind MySQL table `ASHAREEODPRICES`;
PE/PB/PS, turnover, and market-cap fields are joined from
`ASHAREEODDERIVATIVEINDICATOR`.

## Runtime

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the Wind MySQL price source with either `MYSQL_URL` or component
variables:

```bash
MYSQL_HOST=...
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE=winddb
```

Do not commit real database credentials. `update.md` documents the table/query
shape, not application configuration.

## Main Workflows

Run A-share strategy signals:

```bash
python run_ashare_signals.py
python run_ashare_signals.py --workers 2
python run_ashare_signals.py --force-backtest
```

Run short-term A-share operation list generation:

```bash
python run_short_term_signals.py
python run_short_term_signals.py 20260120
python run_short_term_signals.py 20260120 --fetch-only
python run_short_term_signals.py 20260120 --signals-only
```

Start the Web UI:

```bash
./web_server.sh
```

## Architecture

```text
A-share strategies -> Task -> Engine -> DbDataLoader -> MySQLAshareReader -> Wind MySQL
                                      -> FactorExpr / FactorCache -> signals
```

Key modules:

- `datafeed/mysql_ashare_reader.py`: reads Wind MySQL A-share daily prices and
  derivative indicators.
- `datafeed/db_dataloader.py`: preserves the existing `{symbol: DataFrame}`
  loader contract for engines and factor code.
- `core/backtrader_engine.py`: executes strategy `Task` objects.
- `core/strategy_loader.py`: discovers `strategies/stocks_*.py`.
- `run_ashare_signals.py`: runs A-share backtests and signal generation.
- `run_short_term_signals.py`: runs the short-term A-share selection workflow.
- `database/db_manager.py`: neutral application persistence facade for signals,
  backtests, positions, reference data, and short-term operation lists.

## Data Contract

The historical price loader returns one DataFrame per symbol with at least:

- `date`
- `symbol`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap`
- `real_open`
- `real_close`
- `real_low`

Compatibility columns such as `amount`, `change_pct`, `turnover_rate`, `pe`,
`pe_ttm`, `pb`, `ps`, `ps_ttm`, `total_mv`, and `circ_mv` are retained. Price
columns come from `ASHAREEODPRICES`; valuation, turnover, and market-cap columns
come from `ASHAREEODDERIVATIVEINDICATOR`.

## Removed Scope

ETF signal generation, ETF portfolio backtests, ETF downloaders, and local
PostgreSQL market-data caching have been removed. Historical A-share prices are
not downloaded into a local cache; missing MySQL rows are treated as source-data
issues.
