from __future__ import annotations

import pandas as pd
from sqlalchemy import and_, case, func

from aitrader.infrastructure.db.database_manager import get_db
from aitrader.infrastructure.db.models.models import Trader


class SignalsRepository:
    def __init__(self):
        self.db = get_db()

    def latest(self, limit: int = 10) -> pd.DataFrame:
        return self.db.get_latest_trader_signals(limit=limit)

    def by_date(self, signal_date):
        return self.db.get_trader_signals_by_date(signal_date)

    def by_symbol(self, symbol: str):
        return self.db.get_trader_signals_by_symbol(symbol)

    def grouped_history(self, start_date=None, end_date=None) -> pd.DataFrame:
        with self.db.get_session() as session:
            conditions = []
            if start_date:
                conditions.append(Trader.signal_date >= start_date)
            if end_date:
                conditions.append(Trader.signal_date <= end_date)
            query = session.query(Trader)
            if conditions:
                query = query.filter(and_(*conditions))
            query = query.order_by(
                case((Trader.signal_type == 'sell', 0), else_=1).asc(),
                case((Trader.price < 50, 0), else_=1).asc(),
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc(),
            )
            return pd.read_sql(query.statement, session.bind)

    def latest_ashare(self, limit: int = 50) -> pd.DataFrame:
        with self.db.get_session() as session:
            query = session.query(Trader).filter(Trader.asset_type == 'ashare').order_by(
                case((Trader.signal_type == 'sell', 0), else_=1).asc(),
                case((Trader.price < 50, 0), else_=1).asc(),
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc(),
            ).limit(limit)
            return pd.read_sql(query.statement, session.bind)

    def backtest_by_id(self, backtest_id: int):
        return self.db.get_backtest_by_id(backtest_id)

    def signal_backtest(self, trader_id: int):
        return self.db.get_signal_backtest(trader_id)

    def company_names(self, symbols: list[str]) -> dict[str, str]:
        return self.db.batch_get_company_abbr(symbols)
