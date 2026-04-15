from __future__ import annotations

from pathlib import Path

from aitrader.infrastructure.db.database_manager import get_db
from aitrader.shared.utils.paths import project_root


class TradingRepository:
    def __init__(self):
        self.db = get_db()

    def insert_transaction(self, **kwargs):
        return self.db.insert_transaction(**kwargs)

    def get_transactions(self, symbol=None, start_date=None, end_date=None):
        return self.db.get_transactions(symbol, start_date, end_date)

    def get_positions(self):
        return self.db.get_positions()

    def update_position(self, **kwargs):
        return self.db.update_position(**kwargs)

    def recalculate_positions(self):
        return self.db.recalculate_positions()

    def search_codes(self, search=None, limit: int = 100):
        return self.db.search_codes(search=search, limit=limit)

    def strategy_dir(self) -> Path:
        return project_root() / 'strategies'
