# AITrader

AITrader is now an A-share focused research, backtest, and signal-generation project.
Historical daily prices are read directly from Wind MySQL table `ASHAREEODPRICES`;
PE/PB/PS, turnover, and market-cap fields are joined from
`ASHAREEODDERIVATIVEINDICATOR`.

## Runtime

Install dependencies:

```bash
pip install -r requirements.txt
pip install -e .
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

Recommended package entrypoints:

```bash
python -m aitrader.app.cli.ashare_signals
python -m aitrader.app.cli.short_term_signals
python -m aitrader.app.cli.stock_backtests
aitrader-ashare-signals
aitrader-short-term
aitrader-stock-backtests
uvicorn --app-dir src aitrader.interfaces.api.main:app --reload
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

## Source Layout

Core application code is being migrated into `src/aitrader/`:

- `src/aitrader/app`: CLI entrypoints, use cases, application services
- `src/aitrader/domain`: domain-layer landing zone for strategy, backtest, and portfolio logic
- `src/aitrader/infrastructure`: database, market data, repositories, configuration
- `src/aitrader/interfaces`: FastAPI/Web entrypoints and schemas
- `src/aitrader/shared`: shared helpers

Key modules:

- `src/aitrader/infrastructure/market_data/mysql_reader.py`: reads Wind MySQL
  A-share daily prices and derivative indicators.
- `src/aitrader/infrastructure/market_data/loaders.py`: preserves the existing
  `{symbol: DataFrame}` loader contract for engines and factor code.
- `src/aitrader/domain/backtest/engine.py`: executes strategy `Task` objects.
- `src/aitrader/domain/strategy/loader.py`: discovers `strategies/stocks_*.py`.
- `src/aitrader/app/cli/ashare_signals.py`: runs A-share backtests and signal
  generation.
- `src/aitrader/app/cli/short_term_signals.py`: runs the short-term A-share
  selection workflow.
- `src/aitrader/infrastructure/db/db_manager.py`: neutral application
  persistence facade for signals, backtests, positions, reference data, and
  short-term operation lists.

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
