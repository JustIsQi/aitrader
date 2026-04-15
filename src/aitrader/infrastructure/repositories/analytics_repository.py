from aitrader.infrastructure.db.database_manager import get_db


class AnalyticsRepository:
    def __init__(self):
        self.db = get_db()

    def profit_loss(self):
        return self.db.calculate_profit_loss()

    def positions(self):
        return self.db.get_positions()

    def historical_pl_by_symbol(self):
        return self.db.calculate_historical_pl_by_symbol()
