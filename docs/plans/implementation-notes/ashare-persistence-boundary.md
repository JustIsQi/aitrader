# A-share Persistence Boundary

Created: 2026-04-13

## Decision

Historical A-share prices move to Wind MySQL through `datafeed/mysql_ashare_reader.py`.
Application persistence remains a separate concern and should not use the Wind price
database unless that database is explicitly provisioned for AITrader application tables.

To remove PostgreSQL as a runtime dependency without deleting signal/backtest/Web
state outright, the persistence facade moves from PostgreSQL-specific naming to a
neutral database manager. The default local persistence target is SQLite via
`DATABASE_URL=sqlite:///aitrader.db`, while deployments may provide another
SQLAlchemy-compatible URL if needed.

## Call-Site Buckets

### Historical Price Reads

- `datafeed/db_dataloader.py`: replaced with MySQL/Wind reader.
- `core/backtest_utils.py`: replaced direct PostgreSQL price reads with MySQL/Wind reader.

Disposition: MySQL/Wind price source.

### Stock Universe And Reference Data

- `core/stock_universe.py`
- `core/smart_stock_filter.py`
- `scripts/init_codes.py`
- `scripts/sync_strategy_codes.py`
- `datafeed/downloaders/stock_downloader.py`

Disposition: keep behind neutral persistence for now. These call sites use stock
codes, metadata, and fundamentals rather than historical price storage.

### Signal, Backtest, Position, And Trading State

- `run_ashare_signals.py`
- `signals/multi_strategy_signals.py`
- `web/main.py`
- `web/routers/signals.py`
- `web/routers/trading.py`
- `web/routers/analytics.py`

Disposition: keep behind neutral persistence. Removing this state would break the
dashboard and signal workflow, which is outside the requested price-source change.

### Short-Term Operation Lists

- `run_short_term_signals.py`
- `core/sector_analyzer.py`
- `core/stock_selector.py`
- `core/position_manager.py`
- `web/routers/short_term_signals.py`

Disposition: keep behind neutral persistence. Sector/fundamental data source
replacement is deferred; PostgreSQL-specific configuration is removed first.

### Monitoring And Maintenance

- `monitoring/system_monitor.py`
- `core/resource_manager.py`
- scripts that update list dates or sectors

Disposition: update imports to the neutral manager and keep behavior where it does
not depend on PostgreSQL-only SQL.

## Follow-Up Constraints

- Do not reintroduce `database.pg_manager` imports in active code.
- Do not read historical prices through the persistence manager.
- Do not copy MySQL credentials from `update.md` into source or docs.
