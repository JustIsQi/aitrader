from __future__ import annotations

from datetime import datetime

from aitrader.infrastructure.db.database_manager import get_db
from aitrader.infrastructure.db.models.models import DailyOperationList, SectorData, ShortTermBacktest
from aitrader.shared.utils.serialization import model_to_dict


class ShortTermRepository:
    def __init__(self):
        self.db = get_db()

    def latest_daily_operations(self, limit: int = 50):
        with self.db.get_session() as session:
            latest_date = session.query(DailyOperationList.date).order_by(DailyOperationList.date.desc()).first()
            if not latest_date:
                return []
            query = session.query(DailyOperationList).filter(
                DailyOperationList.date == latest_date[0]
            ).order_by(
                DailyOperationList.sector_rank,
                DailyOperationList.strength_score.desc(),
            ).limit(limit)
            return [model_to_dict(op) for op in query.all()]

    def daily_operations_by_date(self, date_str: str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        with self.db.get_session() as session:
            query = session.query(DailyOperationList).filter(
                DailyOperationList.date == date_obj
            ).order_by(
                DailyOperationList.sector_rank,
                DailyOperationList.strength_score.desc(),
            )
            return [model_to_dict(op) for op in query.all()]

    def latest_sectors(self, limit: int = 10):
        with self.db.get_session() as session:
            latest_date = session.query(SectorData.date).order_by(SectorData.date.desc()).first()
            if not latest_date:
                return []
            query = session.query(SectorData).filter(
                SectorData.date == latest_date[0]
            ).order_by(SectorData.strength_score.desc()).limit(limit)
            return [model_to_dict(item) for item in query.all()]

    def sectors_by_date(self, date_str: str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        with self.db.get_session() as session:
            query = session.query(SectorData).filter(
                SectorData.date == date_obj
            ).order_by(SectorData.strength_score.desc())
            return [model_to_dict(item) for item in query.all()]

    def latest_backtests(self, limit: int = 10):
        with self.db.get_session() as session:
            query = session.query(ShortTermBacktest).order_by(ShortTermBacktest.created_at.desc()).limit(limit)
            return [model_to_dict(item) for item in query.all()]

    def backtest_by_id(self, backtest_id: int):
        with self.db.get_session() as session:
            item = session.query(ShortTermBacktest).filter(ShortTermBacktest.id == backtest_id).first()
            return model_to_dict(item)

    def summary(self):
        with self.db.get_session() as session:
            latest_operation = session.query(DailyOperationList.date).order_by(DailyOperationList.date.desc()).first()
            latest_sector = session.query(SectorData.date).order_by(SectorData.date.desc()).first()
            latest_operation_count = 0
            if latest_operation:
                latest_operation_count = session.query(DailyOperationList).filter(DailyOperationList.date == latest_operation[0]).count()
            latest_sector_count = 0
            if latest_sector:
                latest_sector_count = session.query(SectorData).filter(SectorData.date == latest_sector[0]).count()
            total_backtests = session.query(ShortTermBacktest).count()
            return {
                'latest_operation_date': latest_operation[0] if latest_operation else None,
                'latest_operation_count': latest_operation_count,
                'latest_sector_date': latest_sector[0] if latest_sector else None,
                'latest_sector_count': latest_sector_count,
                'total_backtests': total_backtests,
                'system_status': 'running',
            }
