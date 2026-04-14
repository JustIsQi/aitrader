# Data Guide

## A-share Price And Indicator Sources

Daily A-share prices come from Wind MySQL table `ASHAREEODPRICES`.
Derivative indicators such as PE, PB, PS, turnover, and market value come from
Wind MySQL table `ASHAREEODDERIVATIVEINDICATOR`.

The canonical reader is:

- `datafeed/mysql_ashare_reader.py`
- `datafeed/db_dataloader.py`

`DbDataLoader.read_dfs(symbols, start_date, end_date)` returns a dictionary of
DataFrames keyed by Wind-style stock code, such as `000001.SZ`.

## Required Configuration

Use environment variables:

```bash
MYSQL_HOST=...
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE=winddb
```

or:

```bash
MYSQL_URL=mysql+pymysql://user:password@host:3306/winddb
```

Keep credentials out of source files and docs.

## Output Columns

The loader maps Wind fields into the existing factor/backtest contract:

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

`datafeed/downloaders/fundamental_downloader.py` uses
`ASHAREEODDERIVATIVEINDICATOR` to refresh the local `stock_fundamental_daily`
snapshot table for code paths that still query local fundamentals.

## Local Persistence

Application state such as signals, backtests, positions, stock metadata, and
short-term operation lists uses `database/db_manager.py`. This is separate from
historical price reads.

The default `DATABASE_URL` is SQLite:

```bash
DATABASE_URL=sqlite:///aitrader.db
```

## Removed Data Flows

- ETF historical data download/update
- ETF code tables
- Local historical price cache writes
- PostgreSQL-specific setup scripts and configuration
