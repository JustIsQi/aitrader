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
variables. These settings are only for historical price reads:

```bash
MYSQL_HOST=...
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE=winddb
```

Application state uses `DATABASE_URL` and defaults to SQLite when unset:

```bash
DATABASE_URL=sqlite:///aitrader.db
```

Do not commit real database credentials.

## Main Workflows

### A-share Signals

Recommended entrypoints:

```bash
python -m aitrader.app.cli.ashare_signals
aitrader-ashare-signals
```

Useful flags:

```bash
python -m aitrader.app.cli.ashare_signals --workers 2
python -m aitrader.app.cli.ashare_signals --force-backtest
python -m aitrader.app.cli.ashare_signals --weekly
python -m aitrader.app.cli.ashare_signals --monthly
```

### Short-Term Workflow

```bash
python -m aitrader.app.cli.short_term_signals
aitrader-short-term
python -m aitrader.app.cli.short_term_signals 20260120
python -m aitrader.app.cli.short_term_signals 20260120 --fetch-only
python -m aitrader.app.cli.short_term_signals 20260120 --signals-only
```

### Backtests And API

```bash
python -m aitrader.app.cli.stock_backtests
aitrader-stock-backtests
uvicorn --app-dir src aitrader.interfaces.api.main:app --reload
```

Start the Web UI:

```bash
./web_server.sh
```

## Backtest Optimization

Current speedup path:

- Batch backtests now go through `ParallelBacktestRunner`, and the parent process prewarms raw行情 and benchmark caches before forking workers.
- Hot data loads use `DbDataLoader.read_dfs(..., copy_result=False)` so forked workers can reuse inherited cache state without extra dataframe copies.
- `FactorExpr` now computes factors per symbol in parallel, which better saturates CPU cores on Linux.
- `trend_score` and RSRS-related helpers in `factor_extends.py` were vectorized to reduce Python-loop overhead.

## Verification Commands

Syntax check:

```bash
/home/yy/anaconda3/bin/python -m py_compile \
  src/aitrader/domain/backtest/engine.py \
  src/aitrader/domain/backtest/bt_engine.py \
  src/aitrader/domain/backtest/parallel.py \
  src/aitrader/app/use_cases/stock_backtests.py \
  src/aitrader/infrastructure/db/factor_cache.py \
  src/aitrader/infrastructure/market_data/factor_expr.py \
  src/aitrader/infrastructure/market_data/loaders.py \
  src/aitrader/infrastructure/market_data/factor_extends.py
```

No-DB smoke test for the factor pipeline:

```bash
/home/yy/anaconda3/bin/python - <<'PY'
import numpy as np
import pandas as pd
from aitrader.infrastructure.market_data.factor_expr import FactorExpr

np.random.seed(0)
dates = pd.date_range('2024-01-01', periods=40, freq='D')

def make_df(symbol, base):
    close = base + np.cumsum(np.random.randn(len(dates)))
    return pd.DataFrame({
        'date': dates,
        'symbol': symbol,
        'open': close,
        'high': close,
        'low': close,
        'close': close,
        'volume': np.full(len(dates), 1000),
    })

dfs = {
    '000001.SZ': make_df('000001.SZ', 10),
    '000002.SZ': make_df('000002.SZ', 20),
}

result = FactorExpr().calc_formulas(
    dfs,
    ['trend_score(close,5)', 'MACD(close,12,26,9)'],
    parallel=True,
)
print(result.shape)
print('smoke ok')
PY
```

Real backtest command with MySQL configured:

```bash
MYSQL_HOST=... MYSQL_PORT=3306 MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=... \
/home/yy/anaconda3/bin/python -m aitrader.app.cli.stock_backtests --multi-factor-all
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

`DbDataLoader.read_dfs(symbols, start_date, end_date)` returns one DataFrame per
symbol keyed by Wind-style stock code. Each frame contains at least:

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
`pe_ttm`, `pb`, `ps`, `ps_ttm`, `total_mv`, and `circ_mv` are retained.

| Loader column | Wind source |
| --- | --- |
| `date` | `TRADE_DT` |
| `symbol` | `S_INFO_WINDCODE` |
| `real_open` | `S_DQ_OPEN` |
| `real_close` | `S_DQ_CLOSE` |
| `real_low` | `S_DQ_LOW` |
| `open` | `S_DQ_ADJOPEN` |
| `close` | `S_DQ_ADJCLOSE` |
| `high` | `S_DQ_ADJHIGH` |
| `low` | `S_DQ_ADJLOW` |
| `vwap` | `S_DQ_AVGPRICE` |
| `volume` | `S_DQ_VOLUME` |
| `amount` | `S_DQ_AMOUNT` |
| `change_pct` | `S_DQ_PCTCHANGE` |
| `turnover_rate` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_TURN` |
| `free_turnover_rate` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_FREETURNOVER` |
| `pe` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PE` |
| `pe_ttm` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PE_TTM` |
| `pb` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PB_NEW` |
| `ps` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PS` |
| `ps_ttm` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_PS_TTM` |
| `total_mv` | `ASHAREEODDERIVATIVEINDICATOR.S_VAL_MV` |
| `circ_mv` | `ASHAREEODDERIVATIVEINDICATOR.S_DQ_MV` |

Historical prices are read from Wind MySQL, not a local cache.

## Local Persistence

Signals, backtests, positions, stock metadata, and short-term operation lists
use `src/aitrader/infrastructure/db/db_manager.py` through `DATABASE_URL`.
Price reads stay separate from application persistence.

## Removed Scope

ETF signal generation, ETF portfolio backtests, ETF downloaders, and local
PostgreSQL market-data caching have been removed. Missing MySQL rows are treated
as source-data issues.
