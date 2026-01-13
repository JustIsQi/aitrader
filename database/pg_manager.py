"""
PostgreSQL 数据库管理器
使用 SQLAlchemy ORM 替代 DuckDB
"""
import pandas as pd
import time
import uuid
from datetime import datetime, date
from typing import Optional, List
from contextlib import contextmanager
from loguru import logger

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func as sql_func, text, distinct
from sqlalchemy.exc import IntegrityError

from database.models import (
    EtfHistory, StockHistory, StockMetadata, StockFundamentalDaily,
    Trader, Transaction, Position, FactorCache, EtfCode, StockCode,
    StrategyBacktest, SignalBacktestAssociation, AShareStockInfo,
    EtfHistoryQfq, StockHistoryQfq
)
from database.models.base import SessionLocal, engine


# ==================== Performance Monitoring ====================

@contextmanager
def query_timer(query_name: str):
    """
    Context manager to time query execution

    Usage:
        with query_timer("batch_stock_500"):
            # execute query
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        if elapsed > 1.0:
            logger.warning(f'🐌 慢查询 [{query_name}]: {elapsed:.2f}秒')
        else:
            logger.debug(f'⚡ 查询 [{query_name}]: {elapsed:.3f}秒')


class PostgreSQLManager:
    """PostgreSQL 数据库管理器 (使用 SQLAlchemy ORM)"""

    def __init__(self):
        """初始化数据库连接"""
        self.engine = engine
        self._session_local = SessionLocal
        logger.info('PostgreSQL 数据库已连接')

    @contextmanager
    def get_session(self):
        """
        获取数据库会话的上下文管理器

        使用示例:
            with db.get_session() as session:
                # 执行数据库操作
                query = session.query(Model).filter(...)
        """
        session = self._session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== ETF 操作 ====================

    def upsert_etf_history(self, df: pd.DataFrame, symbol: str = None) -> bool:
        """
        插入或更新 ETF 历史数据

        Args:
            df: 包含历史数据的 DataFrame
            symbol: ETF 代码（如果 df 中没有 symbol 列）
        """
        try:
            if symbol and 'symbol' not in df.columns:
                df = df.copy()
                df['symbol'] = symbol

            df['date'] = pd.to_datetime(df['date']).dt.date

            with self.get_session() as session:
                # 删除原有数据
                if symbol:
                    session.query(EtfHistory).filter(EtfHistory.symbol == symbol).delete()
                else:
                    for sym in df['symbol'].unique():
                        session.query(EtfHistory).filter(EtfHistory.symbol == sym).delete()

                # 插入新数据
                records = df.to_dict('records')
                session.bulk_insert_mappings(EtfHistory, records)

                logger.info(f'成功插入 {len(df)} 条ETF历史数据')
                return True
        except Exception as e:
            logger.error(f'插入ETF数据失败: {e}')
            return False

    def append_etf_history(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的历史数据（只插入不存在的记录）

        Args:
            df: 新的数据 DataFrame
            symbol: ETF 代码
        """
        try:
            df = df.copy()
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_etf_insert_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 使用临时表和 ON CONFLICT DO NOTHING
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                session.execute(text(f"""
                    INSERT INTO etf_history
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text(f"DROP TABLE {temp_table_name}"))

                logger.info(f'成功追加 {len(df)} 条ETF数据')
                return True
        except Exception as e:
            logger.error(f'追加ETF数据失败: {e}')
            return False

    def get_etf_history(self, symbol: str, start_date: date = None,
                       end_date: date = None) -> pd.DataFrame:
        """
        获取 ETF 历史数据

        Args:
            symbol: ETF 代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 历史数据
        """
        with self.get_session() as session:
            query = session.query(EtfHistory).filter(EtfHistory.symbol == symbol)

            if start_date:
                query = query.filter(EtfHistory.date >= start_date)
            if end_date:
                query = query.filter(EtfHistory.date <= end_date)

            query = query.order_by(EtfHistory.date.asc())

            return pd.read_sql(query.statement, session.bind)

    def batch_get_etf_history(self, symbols: List[str], start_date: date = None,
                             end_date: date = None) -> pd.DataFrame:
        """
        批量获取多个ETF的历史数据（性能优化 + 性能监控）

        一次查询返回所有ETF数据，而不是每个ETF单独查询

        Args:
            symbols: ETF代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 包含所有ETF的历史数据
        """
        query_name = f"batch_etf_{len(symbols)}_symbols"
        with query_timer(query_name):
            with self.get_session() as session:
                query = session.query(EtfHistory).filter(
                    EtfHistory.symbol.in_(symbols)
                )

                if start_date:
                    query = query.filter(EtfHistory.date >= start_date)
                if end_date:
                    query = query.filter(EtfHistory.date <= end_date)

                query = query.order_by(EtfHistory.symbol.asc(), EtfHistory.date.asc())

                return pd.read_sql(query.statement, session.bind)

    def get_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定 ETF 的最新数据日期

        Args:
            symbol: ETF 代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        with self.get_session() as session:
            result = session.query(sql_func.max(EtfHistory.date)).filter(
                EtfHistory.symbol == symbol
            ).scalar()
            return result

    # ==================== 股票操作 ====================

    def insert_stock_history(self, df: pd.DataFrame, symbol: str = None) -> bool:
        """
        插入或更新股票历史数据

        Args:
            df: 包含历史数据的 DataFrame
            symbol: 股票代码
        """
        try:
            if symbol and 'symbol' not in df.columns:
                df = df.copy()
                df['symbol'] = symbol

            df['date'] = pd.to_datetime(df['date']).dt.date

            with self.get_session() as session:
                # 删除原有数据
                if symbol:
                    session.query(StockHistory).filter(StockHistory.symbol == symbol).delete()
                else:
                    for sym in df['symbol'].unique():
                        session.query(StockHistory).filter(StockHistory.symbol == sym).delete()

                # 插入新数据
                records = df.to_dict('records')
                session.bulk_insert_mappings(StockHistory, records)

                logger.info(f'成功插入 {len(df)} 条股票历史数据')
                return True
        except Exception as e:
            logger.error(f'插入股票数据失败: {e}')
            return False

    def append_stock_history(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的股票历史数据

        Args:
            df: 新的数据 DataFrame
            symbol: 股票代码
        """
        try:
            df = df.copy()
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['date']).dt.date

            with self.get_session() as session:
                df.to_sql('temp_stock_insert', self.engine, if_exists='replace', index=False)

                session.execute(text("""
                    INSERT INTO stock_history
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM temp_stock_insert
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text("DROP TABLE temp_stock_insert"))

                logger.info(f'成功追加 {len(df)} 条股票数据')
                return True
        except Exception as e:
            logger.error(f'追加股票数据失败: {e}')
            return False

    def batch_append_stock_history(self, df: pd.DataFrame) -> int:
        """
        批量追加多个股票的历史数据（优化版）

        一次性插入多个股票的数据，减少数据库操作次数

        Args:
            df: 包含多个股票数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        try:
            df = df.copy()
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_stock_batch_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 创建临时表
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                # 先检查有多少记录是重复的
                duplicate_check = session.execute(text(f"""
                    SELECT COUNT(*) FROM {temp_table_name} t
                    INNER JOIN stock_history s ON t.symbol = s.symbol AND t.date = s.date
                """))
                duplicate_count = duplicate_check.scalar() or 0

                # 批量插入，忽略重复记录
                result = session.execute(text(f"""
                    INSERT INTO stock_history
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                # 删除临时表
                session.execute(text(f"DROP TABLE {temp_table_name}"))

                # 计算实际插入的记录数（总记录数 - 重复记录数）
                inserted_count = len(df) - duplicate_count

                logger.info(f'批量追加股票数据: {inserted_count} 条新增, {duplicate_count} 条重复 ({len(df)} 个股票)')
                return inserted_count

        except Exception as e:
            logger.error(f'批量追加股票数据失败: {e}')
            return 0

    def batch_append_etf_history(self, df: pd.DataFrame) -> int:
        """
        批量追加多个ETF的历史数据（优化版）

        一次性插入多个ETF的数据，减少数据库操作次数

        Args:
            df: 包含多个ETF数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        try:
            df = df.copy()
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_etf_batch_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 创建临时表
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                # 先检查有多少记录是重复的
                duplicate_check = session.execute(text(f"""
                    SELECT COUNT(*) FROM {temp_table_name} t
                    INNER JOIN etf_history e ON t.symbol = e.symbol AND t.date = e.date
                """))
                duplicate_count = duplicate_check.scalar() or 0

                # 批量插入，忽略重复记录
                result = session.execute(text(f"""
                    INSERT INTO etf_history
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                # 删除临时表
                session.execute(text(f"DROP TABLE {temp_table_name}"))

                # 计算实际插入的记录数（总记录数 - 重复记录数）
                inserted_count = len(df) - duplicate_count

                logger.info(f'批量追加ETF数据: {inserted_count} 条新增, {duplicate_count} 条重复 ({len(df)} 个ETF)')
                return inserted_count

        except Exception as e:
            logger.error(f'批量追加ETF数据失败: {e}')
            return 0

    def get_stock_completeness_info(self, symbols: List[str], target_start: str) -> dict:
        """
        批量检查股票数据的完整性（优化版）

        一次查询获取所有股票的完整性信息，避免逐个查询

        Args:
            symbols: 股票代码列表
            target_start: 目标起始日期 (YYYYMMDD)

        Returns:
            dict: {symbol: {'needs_download': bool, 'latest_date': date, 'record_count': int}}
        """
        try:
            target_start_dt = datetime.strptime(target_start, '%Y%m%d')

            with self.get_session() as session:
                # 一次查询获取所有股票的统计信息
                results = session.query(
                    StockHistory.symbol,
                    sql_func.max(StockHistory.date).label('latest_date'),
                    sql_func.count(StockHistory.id).label('record_count')
                ).filter(
                    StockHistory.symbol.in_(symbols)
                ).group_by(StockHistory.symbol).all()

                completeness_map = {}

                # 计算期望的记录数（考虑周末和节假日，约为70%）
                days_since_target = (datetime.now() - target_start_dt).days
                expected_records = int(days_since_target * 0.7)

                for symbol, latest_date, record_count in results:
                    # 确保 latest_date 是 datetime 类型（可能是 date 或 datetime）
                    if latest_date is not None and isinstance(latest_date, date):
                        latest_date_dt = datetime.combine(latest_date, datetime.min.time())
                    else:
                        latest_date_dt = latest_date

                    # 判断是否需要下载：
                    # 1. 最新日期早于目标起始日期
                    # 2. 记录数少于期望值（考虑周末和节假日）
                    needs_download = (
                        latest_date is None or
                        latest_date_dt < target_start_dt or
                        record_count < expected_records
                    )

                    completeness_map[symbol] = {
                        'needs_download': needs_download,
                        'latest_date': latest_date,
                        'record_count': record_count,
                        'reason': 'incomplete' if needs_download else 'complete'
                    }

                # 补充没有数据的股票
                for symbol in symbols:
                    if symbol not in completeness_map:
                        completeness_map[symbol] = {
                            'needs_download': True,
                            'latest_date': None,
                            'record_count': 0,
                            'reason': 'no_data'
                        }

                return completeness_map

        except Exception as e:
            logger.error(f'批量检查股票完整性失败: {e}')
            # 出错时返回所有股票都需要下载
            return {symbol: {'needs_download': True, 'latest_date': None,
                            'record_count': 0, 'reason': 'error'} for symbol in symbols}

    def get_etf_completeness_info(self, symbols: List[str], target_start: str) -> dict:
        """
        批量检查ETF数据的完整性（优化版）

        一次查询获取所有ETF的完整性信息，避免逐个查询

        Args:
            symbols: ETF代码列表
            target_start: 目标起始日期 (YYYYMMDD)

        Returns:
            dict: {symbol: {'needs_download': bool, 'latest_date': date, 'record_count': int}}
        """
        try:
            target_start_dt = datetime.strptime(target_start, '%Y%m%d')

            with self.get_session() as session:
                # 一次查询获取所有ETF的统计信息
                results = session.query(
                    EtfHistory.symbol,
                    sql_func.max(EtfHistory.date).label('latest_date'),
                    sql_func.count(EtfHistory.id).label('record_count')
                ).filter(
                    EtfHistory.symbol.in_(symbols)
                ).group_by(EtfHistory.symbol).all()

                completeness_map = {}

                # 计算期望的记录数（考虑周末和节假日，约为70%）
                days_since_target = (datetime.now() - target_start_dt).days
                expected_records = int(days_since_target * 0.7)

                for symbol, latest_date, record_count in results:
                    # 确保 latest_date 是 datetime 类型（可能是 date 或 datetime）
                    if latest_date is not None and isinstance(latest_date, date):
                        latest_date_dt = datetime.combine(latest_date, datetime.min.time())
                    else:
                        latest_date_dt = latest_date

                    # 判断是否需要下载
                    needs_download = (
                        latest_date is None or
                        latest_date_dt < target_start_dt or
                        record_count < expected_records
                    )

                    completeness_map[symbol] = {
                        'needs_download': needs_download,
                        'latest_date': latest_date,
                        'record_count': record_count,
                        'reason': 'incomplete' if needs_download else 'complete'
                    }

                # 补充没有数据的ETF
                for symbol in symbols:
                    if symbol not in completeness_map:
                        completeness_map[symbol] = {
                            'needs_download': True,
                            'latest_date': None,
                            'record_count': 0,
                            'reason': 'no_data'
                        }

                return completeness_map

        except Exception as e:
            logger.error(f'批量检查ETF完整性失败: {e}')
            # 出错时返回所有ETF都需要下载
            return {symbol: {'needs_download': True, 'latest_date': None,
                            'record_count': 0, 'reason': 'error'} for symbol in symbols}

    def get_stock_history(self, symbol: str, start_date: date = None,
                         end_date: date = None) -> pd.DataFrame:
        """
        获取股票历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 历史数据
        """
        with self.get_session() as session:
            query = session.query(StockHistory).filter(StockHistory.symbol == symbol)

            if start_date:
                query = query.filter(StockHistory.date >= start_date)
            if end_date:
                query = query.filter(StockHistory.date <= end_date)

            query = query.order_by(StockHistory.date.asc())

            return pd.read_sql(query.statement, session.bind)

    def batch_get_stock_history(self, symbols: List[str], start_date: date = None,
                               end_date: date = None) -> pd.DataFrame:
        """
        批量获取多个股票的历史数据（性能优化 + 性能监控）

        一次查询返回所有股票数据，而不是每个股票单独查询

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 包含所有股票的历史数据
        """
        query_name = f"batch_stock_{len(symbols)}_symbols"
        with query_timer(query_name):
            with self.get_session() as session:
                query = session.query(StockHistory).filter(
                    StockHistory.symbol.in_(symbols)
                )

                if start_date:
                    query = query.filter(StockHistory.date >= start_date)
                if end_date:
                    query = query.filter(StockHistory.date <= end_date)

                query = query.order_by(StockHistory.symbol.asc(), StockHistory.date.asc())

                return pd.read_sql(query.statement, session.bind)

    def get_stock_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定股票的最新数据日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        with self.get_session() as session:
            result = session.query(sql_func.max(StockHistory.date)).filter(
                StockHistory.symbol == symbol
            ).scalar()
            return result

    # ==================== 前复权数据操作 ====================

    def get_stock_history_qfq(self, symbol: str, start_date: date = None,
                             end_date: date = None) -> pd.DataFrame:
        """
        获取股票前复权历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 前复权历史数据
        """
        with self.get_session() as session:
            query = session.query(StockHistoryQfq).filter(StockHistoryQfq.symbol == symbol)

            if start_date:
                query = query.filter(StockHistoryQfq.date >= start_date)
            if end_date:
                query = query.filter(StockHistoryQfq.date <= end_date)

            query = query.order_by(StockHistoryQfq.date.asc())

            return pd.read_sql(query.statement, session.bind)

    def batch_get_stock_history_qfq(self, symbols: List[str], start_date: date = None,
                                   end_date: date = None) -> pd.DataFrame:
        """
        批量获取多个股票的前复权历史数据（性能优化）

        一次查询返回所有股票数据，而不是每个股票单独查询

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 包含所有股票的前复权历史数据
        """
        query_name = f"batch_stock_qfq_{len(symbols)}_symbols"
        with query_timer(query_name):
            with self.get_session() as session:
                query = session.query(StockHistoryQfq).filter(
                    StockHistoryQfq.symbol.in_(symbols)
                )

                if start_date:
                    query = query.filter(StockHistoryQfq.date >= start_date)
                if end_date:
                    query = query.filter(StockHistoryQfq.date <= end_date)

                query = query.order_by(StockHistoryQfq.symbol.asc(), StockHistoryQfq.date.asc())

                return pd.read_sql(query.statement, session.bind)

    def get_stock_qfq_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定股票的前复权最新数据日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        with self.get_session() as session:
            result = session.query(sql_func.max(StockHistoryQfq.date)).filter(
                StockHistoryQfq.symbol == symbol
            ).scalar()
            return result

    def append_stock_history_qfq(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的股票前复权历史数据

        Args:
            df: 新的数据 DataFrame
            symbol: 股票代码
        """
        try:
            df = df.copy()
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['date']).dt.date

            with self.get_session() as session:
                df.to_sql('temp_stock_qfq_insert', self.engine, if_exists='replace', index=False)

                session.execute(text("""
                    INSERT INTO stock_history_qfq
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM temp_stock_qfq_insert
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text("DROP TABLE temp_stock_qfq_insert"))

                logger.info(f'成功追加 {len(df)} 条股票前复权数据')
                return True
        except Exception as e:
            logger.error(f'追加股票前复权数据失败: {e}')
            return False

    def batch_append_stock_history_qfq(self, df: pd.DataFrame) -> int:
        """
        批量追加多个股票的前复权历史数据（优化版）

        一次性插入多个股票的数据，减少数据库操作次数

        Args:
            df: 包含多个股票数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        try:
            df = df.copy()
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_stock_qfq_batch_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 创建临时表
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                # 先检查有多少记录是重复的
                duplicate_check = session.execute(text(f"""
                    SELECT COUNT(*) FROM {temp_table_name} t
                    INNER JOIN stock_history_qfq s ON t.symbol = s.symbol AND t.date = s.date
                """))
                duplicate_count = duplicate_check.scalar() or 0

                # 批量插入，忽略重复记录
                result = session.execute(text(f"""
                    INSERT INTO stock_history_qfq
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                # 删除临时表
                session.execute(text(f"DROP TABLE {temp_table_name}"))

                # 计算实际插入的记录数（总记录数 - 重复记录数）
                inserted_count = len(df) - duplicate_count

                logger.info(f'批量追加股票前复权数据: {inserted_count} 条新增, {duplicate_count} 条重复 ({len(df)} 个股票)')
                return inserted_count

        except Exception as e:
            logger.error(f'批量追加股票前复权数据失败: {e}')
            return 0

    def get_etf_history_qfq(self, symbol: str, start_date: date = None,
                           end_date: date = None) -> pd.DataFrame:
        """
        获取 ETF 前复权历史数据

        Args:
            symbol: ETF 代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 前复权历史数据
        """
        with self.get_session() as session:
            query = session.query(EtfHistoryQfq).filter(EtfHistoryQfq.symbol == symbol)

            if start_date:
                query = query.filter(EtfHistoryQfq.date >= start_date)
            if end_date:
                query = query.filter(EtfHistoryQfq.date <= end_date)

            query = query.order_by(EtfHistoryQfq.date.asc())

            return pd.read_sql(query.statement, session.bind)

    def batch_get_etf_history_qfq(self, symbols: List[str], start_date: date = None,
                                 end_date: date = None) -> pd.DataFrame:
        """
        批量获取多个ETF的前复权历史数据（性能优化）

        一次查询返回所有ETF数据，而不是每个ETF单独查询

        Args:
            symbols: ETF代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 包含所有ETF的前复权历史数据
        """
        query_name = f"batch_etf_qfq_{len(symbols)}_symbols"
        with query_timer(query_name):
            with self.get_session() as session:
                query = session.query(EtfHistoryQfq).filter(
                    EtfHistoryQfq.symbol.in_(symbols)
                )

                if start_date:
                    query = query.filter(EtfHistoryQfq.date >= start_date)
                if end_date:
                    query = query.filter(EtfHistoryQfq.date <= end_date)

                query = query.order_by(EtfHistoryQfq.symbol.asc(), EtfHistoryQfq.date.asc())

                return pd.read_sql(query.statement, session.bind)

    def get_etf_qfq_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定 ETF 的前复权最新数据日期

        Args:
            symbol: ETF 代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        with self.get_session() as session:
            result = session.query(sql_func.max(EtfHistoryQfq.date)).filter(
                EtfHistoryQfq.symbol == symbol
            ).scalar()
            return result

    def append_etf_history_qfq(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的 ETF 前复权历史数据

        Args:
            df: 新的数据 DataFrame
            symbol: ETF 代码
        """
        try:
            df = df.copy()
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_etf_qfq_insert_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 使用临时表和 ON CONFLICT DO NOTHING
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                session.execute(text(f"""
                    INSERT INTO etf_history_qfq
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text(f"DROP TABLE {temp_table_name}"))

                logger.info(f'成功追加 {len(df)} 条ETF前复权数据')
                return True
        except Exception as e:
            logger.error(f'追加ETF前复权数据失败: {e}')
            return False

    def batch_append_etf_history_qfq(self, df: pd.DataFrame) -> int:
        """
        批量追加多个ETF的前复权历史数据（优化版）

        一次性插入多个ETF的数据，减少数据库操作次数

        Args:
            df: 包含多个ETF数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        try:
            df = df.copy()
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 使用唯一的临时表名避免并发冲突
            temp_table_name = f'temp_etf_qfq_batch_{uuid.uuid4().hex[:8]}'

            with self.get_session() as session:
                # 创建临时表
                df.to_sql(temp_table_name, self.engine, if_exists='replace', index=False)

                # 先检查有多少记录是重复的
                duplicate_check = session.execute(text(f"""
                    SELECT COUNT(*) FROM {temp_table_name} t
                    INNER JOIN etf_history_qfq e ON t.symbol = e.symbol AND t.date = e.date
                """))
                duplicate_count = duplicate_check.scalar() or 0

                # 批量插入，忽略重复记录
                result = session.execute(text(f"""
                    INSERT INTO etf_history_qfq
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM {temp_table_name}
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                # 删除临时表
                session.execute(text(f"DROP TABLE {temp_table_name}"))

                # 计算实际插入的记录数（总记录数 - 重复记录数）
                inserted_count = len(df) - duplicate_count

                logger.info(f'批量追加ETF前复权数据: {inserted_count} 条新增, {duplicate_count} 条重复 ({len(df)} 个ETF)')
                return inserted_count

        except Exception as e:
            logger.error(f'批量追加ETF前复权数据失败: {e}')
            return 0

    # ==================== 交易操作 ====================

    def insert_transaction(self, symbol: str, buy_sell: str, quantity: float,
                          price: float, trade_date: str, strategy_name: str = None):
        """
        插入交易记录

        Args:
            symbol: ETF/股票代码
            buy_sell: 'buy' 或 'sell'
            quantity: 数量
            price: 价格
            trade_date: 交易日期
            strategy_name: 策略名称
        """
        with self.get_session() as session:
            transaction = Transaction(
                symbol=symbol,
                buy_sell=buy_sell,
                quantity=quantity,
                price=price,
                trade_date=pd.to_datetime(trade_date).date(),
                strategy_name=strategy_name
            )
            session.add(transaction)
            logger.info(f'记录交易: {buy_sell} {symbol} {quantity}股 @{price}')

    def get_transactions(self, symbol: str = None, start_date: date = None,
                        end_date: date = None) -> pd.DataFrame:
        """
        获取交易记录

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 交易记录
        """
        with self.get_session() as session:
            query = session.query(Transaction)

            if symbol:
                query = query.filter(Transaction.symbol == symbol)
            if start_date:
                query = query.filter(Transaction.trade_date >= start_date)
            if end_date:
                query = query.filter(Transaction.trade_date <= end_date)

            query = query.order_by(Transaction.trade_date.desc(), Transaction.id.desc())

            return pd.read_sql(query.statement, session.bind)

    def update_position(self, symbol: str, quantity: float, avg_cost: float,
                       current_price: float = None):
        """
        更新持仓信息

        Args:
            symbol: 股票代码
            quantity: 持仓数量
            avg_cost: 平均成本
            current_price: 当前价格
        """
        market_value = quantity * current_price if current_price else None

        with self.get_session() as session:
            position = session.query(Position).filter(Position.symbol == symbol).first()

            if position:
                position.quantity = quantity
                position.avg_cost = avg_cost
                position.current_price = current_price
                position.market_value = market_value
            else:
                new_position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price,
                    market_value=market_value
                )
                session.add(new_position)

    def get_positions(self) -> pd.DataFrame:
        """
        获取当前所有持仓

        Returns:
            DataFrame: 持仓数据
        """
        with self.get_session() as session:
            query = session.query(Position).filter(Position.quantity > 0).order_by(
                Position.market_value.desc()
            )
            return pd.read_sql(query.statement, session.bind)

    def clear_transactions(self):
        """清空交易记录表"""
        with self.get_session() as session:
            session.query(Transaction).delete()
            logger.info('已清空交易记录表')

    def clear_positions(self):
        """清空持仓表"""
        with self.get_session() as session:
            session.query(Position).delete()
            logger.info('已清空持仓表')

    def clear_trading_data(self):
        """清空所有交易相关数据"""
        self.clear_positions()
        self.clear_transactions()
        logger.info('已清空所有交易数据')

    def _update_positions_latest_price(self, session):
        """
        更新所有持仓的当前价格（从 qfq 表读取最新数据）

        Args:
            session: SQLAlchemy session
        """
        positions = session.query(Position).filter(Position.quantity > 0).all()

        for pos in positions:
            # 获取最新价格
            latest_price = self._get_latest_price_for_symbol(session, pos.symbol)

            # 更新持仓的当前价格和市值
            if latest_price is not None:
                pos.current_price = latest_price
                pos.market_value = pos.quantity * latest_price
                logger.debug(f'更新 {pos.symbol} 最新价格: {latest_price}')

    def recalculate_positions(self) -> dict:
        """
        从 transactions 表重新计算所有持仓

        计算规则:
        - 买入: quantity 增加,使用加权平均计算 avg_cost
        - 卖出: quantity 减少,avg_cost 不变
        - 最终 quantity 为 0 的记录将被删除

        Returns:
            dict: {
                'updated_count': int,      # 创建的持仓数量
                'deleted_count': int,      # 删除的旧持仓数量
                'details': List[dict]      # 每个symbol的详细信息
            }
        """
        try:
            with self.get_session() as session:
                # 1. 清空 positions 表
                deleted_count = session.query(Position).delete()
                logger.info(f'清空positions表: 删除 {deleted_count} 条旧记录')

                # 2. 读取所有交易记录，按 symbol 和 trade_date 排序
                transactions = session.query(Transaction).order_by(
                    Transaction.symbol,
                    Transaction.trade_date.asc(),
                    Transaction.id.asc()
                ).all()

                if not transactions:
                    logger.info('没有交易记录，跳过重新计算')
                    return {'updated_count': 0, 'deleted_count': deleted_count, 'details': []}

                # 3. 按 symbol 分组计算
                positions_dict = {}  # {symbol: {'quantity': float, 'avg_cost': float, 'current_price': float}}

                for txn in transactions:
                    symbol = txn.symbol

                    # 初始化该 symbol 的持仓
                    if symbol not in positions_dict:
                        positions_dict[symbol] = {
                            'quantity': 0.0,
                            'avg_cost': 0.0,
                            'current_price': txn.price
                        }

                    pos = positions_dict[symbol]

                    if txn.buy_sell == 'buy':
                        # 买入：加权平均计算成本
                        total_quantity = pos['quantity'] + txn.quantity
                        if total_quantity > 0:
                            total_cost = (pos['avg_cost'] * pos['quantity'] +
                                         txn.price * txn.quantity)
                            pos['avg_cost'] = total_cost / total_quantity
                            pos['quantity'] = total_quantity
                        pos['current_price'] = txn.price

                    elif txn.buy_sell == 'sell':
                        # 卖出：减少数量，avg_cost 不变
                        pos['quantity'] = max(0, pos['quantity'] - txn.quantity)
                        pos['current_price'] = txn.price

                # 4. 创建新的持仓记录
                updated_count = 0
                details = []

                for symbol, pos_data in positions_dict.items():
                    if pos_data['quantity'] > 0:
                        market_value = pos_data['quantity'] * pos_data['current_price']

                        new_position = Position(
                            symbol=symbol,
                            quantity=pos_data['quantity'],
                            avg_cost=pos_data['avg_cost'],
                            current_price=pos_data['current_price'],
                            market_value=market_value
                        )
                        session.add(new_position)

                        updated_count += 1
                        details.append({
                            'symbol': symbol,
                            'quantity': pos_data['quantity'],
                            'avg_cost': pos_data['avg_cost'],
                            'action': 'created'
                        })

                # 5. 立即刷新到数据库
                session.flush()

                # 6. 从 qfq 表更新最新价格
                self._update_positions_latest_price(session)

                logger.info(f'重新计算持仓完成: 清空 {deleted_count} 条旧记录, 创建 {updated_count} 个新持仓')

                return {
                    'updated_count': updated_count,
                    'deleted_count': deleted_count,
                    'details': details
                }

        except Exception as e:
            logger.error(f'重新计算持仓失败: {e}')
            raise

    # ==================== 信号操作 ====================

    def insert_trader_signal(self, symbol: str, signal_type: str,
                            strategies: List[str], signal_date: date,
                            price: float = None, score: float = None,
                            rank: int = None, quantity: int = None,
                            asset_type: str = None):
        """
        插入或更新交易信号

        Args:
            symbol: 股票代码
            signal_type: 'buy' 或 'sell'
            strategies: 策略名称列表
            signal_date: 信号日期
            price: 当前价格
            score: 信号评分
            rank: 信号排名
            quantity: 建议数量
            asset_type: 资产类型 ('etf' or 'ashare')，如果为None则自动检测
        """
        import numpy as np

        # Convert numpy types to native Python types
        def convert_value(value):
            if isinstance(value, np.floating):
                return float(value)
            elif isinstance(value, np.integer):
                return int(value)
            return value

        price = convert_value(price)
        score = convert_value(score)
        rank = convert_value(rank)
        quantity = convert_value(quantity)

        # Auto-detect asset_type if not provided
        if asset_type is None:
            # ETF: symbol contains '.', A-share: 6-digit code (no dot)
            if '.' in symbol:
                asset_type = 'etf'
            else:
                asset_type = 'ashare'
            logger.debug(f'Auto-detected asset_type for {symbol}: {asset_type}')

        with self.get_session() as session:
            strategies_str = ','.join(strategies) if strategies else None

            # 查找现有信号
            signal = session.query(Trader).filter(
                Trader.symbol == symbol,
                Trader.signal_date == signal_date,
                Trader.signal_type == signal_type
            ).first()

            if signal:
                # 更新现有信号
                signal.strategies = strategies_str
                signal.price = price
                signal.score = score
                signal.rank = rank
                signal.quantity = quantity
                signal.asset_type = asset_type
                trader_id = signal.id
            else:
                # 插入新信号
                new_signal = Trader(
                    symbol=symbol,
                    signal_type=signal_type,
                    strategies=strategies_str,
                    signal_date=signal_date,
                    price=price,
                    score=score,
                    rank=rank,
                    quantity=quantity,
                    asset_type=asset_type
                )
                session.add(new_signal)
                session.flush()  # Get the ID
                trader_id = new_signal.id

            logger.info(f'记录交易信号: {signal_type} {symbol} ({asset_type}) - {strategies_str}')
            return trader_id

    def get_latest_trader_signals(self, limit: int = 10) -> pd.DataFrame:
        """
        获取最新的交易信号

        Args:
            limit: 返回的最大信号数量

        Returns:
            DataFrame: 包含最新信号
        """
        with self.get_session() as session:
            query = session.query(Trader).order_by(
                Trader.signal_date.desc(), Trader.created_at.desc()
            ).limit(limit)

            return pd.read_sql(query.statement, session.bind)

    def get_trader_signals_by_date(self, signal_date: date) -> pd.DataFrame:
        """
        获取指定日期的交易信号

        Args:
            signal_date: 信号日期

        Returns:
            DataFrame: 交易信号
        """
        with self.get_session() as session:
            query = session.query(Trader).filter(
                Trader.signal_date == signal_date
            ).order_by(Trader.signal_type, Trader.symbol)

            return pd.read_sql(query.statement, session.bind)

    def get_trader_signals_by_symbol(self, symbol: str) -> pd.DataFrame:
        """
        获取指定股票的交易信号

        Args:
            symbol: 股票代码

        Returns:
            DataFrame: 交易信号
        """
        with self.get_session() as session:
            query = session.query(Trader).filter(
                Trader.symbol == symbol
            ).order_by(Trader.signal_date.desc())

            return pd.read_sql(query.statement, session.bind)

    def get_stock_qfq_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取股票在前复权表中的最新收盘价

        Args:
            symbol: 股票代码

        Returns:
            最新收盘价，如果没有数据返回 None
        """
        with self.get_session() as session:
            latest = session.query(StockHistoryQfq.close).filter(
                StockHistoryQfq.symbol == symbol
            ).order_by(StockHistoryQfq.date.desc()).first()

            return latest[0] if latest else None

    def get_etf_qfq_latest_price(self, symbol: str) -> Optional[float]:
        """
        获取ETF在前复权表中的最新收盘价

        Args:
            symbol: ETF代码

        Returns:
            最新收盘价，如果没有数据返回 None
        """
        with self.get_session() as session:
            latest = session.query(EtfHistoryQfq.close).filter(
                EtfHistoryQfq.symbol == symbol
            ).order_by(EtfHistoryQfq.date.desc()).first()

            return latest[0] if latest else None

    def get_qfq_latest_prices(self, symbols: List[str]) -> dict:
        """
        批量获取股票/ETF的最新价格

        Args:
            symbols: 代码列表

        Returns:
            dict: {symbol: latest_price}
        """
        prices = {}
        with self.get_session() as session:
            for symbol in symbols:
                # 使用辅助方法获取最新价格（自动判断股票或ETF）
                prices[symbol] = self._get_latest_price_for_symbol(session, symbol)

        return prices

    def _get_latest_price_for_symbol(self, session, symbol: str) -> Optional[float]:
        """
        获取指定代码的最新价格（自动判断股票或ETF）

        Args:
            session: SQLAlchemy session
            symbol: 股票/ETF代码

        Returns:
            最新收盘价，如果没有数据返回 None
        """
        # 先尝试从 stock_history_qfq 获取
        latest = session.query(StockHistoryQfq.close).filter(
            StockHistoryQfq.symbol == symbol
        ).order_by(StockHistoryQfq.date.desc()).first()

        if latest:
            return latest[0]

        # 再尝试从 etf_history_qfq 获取
        latest = session.query(EtfHistoryQfq.close).filter(
            EtfHistoryQfq.symbol == symbol
        ).order_by(EtfHistoryQfq.date.desc()).first()

        return latest[0] if latest else None

    def calculate_realized_pl(self) -> float:
        """
        计算已实现盈亏（从交易历史中已完成的买卖交易）

        通过分析交易记录，按时间顺序处理每一笔交易，使用FIFO方法
        计算每一对买卖交易的盈亏。

        Returns:
            float: 已实现盈亏总额
        """
        from database.models.models import Transaction

        with self.get_session() as session:
            # 获取所有交易记录，按symbol和日期排序
            transactions = session.query(Transaction).order_by(
                Transaction.symbol,
                Transaction.trade_date.asc(),
                Transaction.id.asc()
            ).all()

            realized_pl = 0.0

            # 按symbol分组跟踪持仓和成本
            positions_tracker = {}  # {symbol: {'quantity': float, 'total_cost': float}}

            for txn in transactions:
                symbol = txn.symbol

                if symbol not in positions_tracker:
                    positions_tracker[symbol] = {'quantity': 0.0, 'total_cost': 0.0}

                tracker = positions_tracker[symbol]

                if txn.buy_sell == 'buy':
                    # 买入：增加持仓数量和总成本
                    tracker['quantity'] += txn.quantity
                    tracker['total_cost'] += txn.price * txn.quantity

                elif txn.buy_sell == 'sell':
                    # 卖出：计算已实现盈亏
                    if tracker['quantity'] > 0:
                        # 计算这批卖出的平均成本
                        avg_cost = tracker['total_cost'] / tracker['quantity']

                        # 计算卖出部分的盈亏
                        sell_revenue = txn.price * txn.quantity
                        sell_cost = avg_cost * txn.quantity
                        profit = sell_revenue - sell_cost

                        realized_pl += profit

                        # 减少持仓数量和总成本
                        tracker['quantity'] -= txn.quantity
                        tracker['total_cost'] -= sell_cost

                        # 防止浮点数精度问题
                        if tracker['quantity'] < 0.001:
                            tracker['quantity'] = 0.0
                            tracker['total_cost'] = 0.0

            return realized_pl

    def calculate_profit_loss(self) -> dict:
        """
        计算总体盈亏（使用 qfq 表的最新价格）

        Returns:
            dict: 盈亏统计，包含已实现和未实现盈亏
        """
        with self.get_session() as session:
            positions = session.query(Position).filter(Position.quantity > 0).all()

            total_cost = 0
            total_market_value = 0
            price_details = []  # 记录价格更新详情

            for pos in positions:
                # 从 qfq 表获取最新价格
                latest_price = self._get_latest_price_for_symbol(session, pos.symbol)

                if latest_price is not None:
                    current_market_value = latest_price * pos.quantity
                else:
                    # 如果没有最新价格，使用 positions 表中的价格
                    current_market_value = pos.market_value if pos.market_value else 0
                    latest_price = pos.current_price

                total_cost += pos.avg_cost * pos.quantity
                total_market_value += current_market_value

                price_details.append({
                    'symbol': pos.symbol,
                    'avg_cost': pos.avg_cost,
                    'latest_price': latest_price,
                    'quantity': pos.quantity,
                    'market_value': current_market_value
                })

            # 未实现盈亏（持仓浮动盈亏）= 当前市值 - 总成本
            total_unrealized_pl = total_market_value - total_cost

            # 已实现盈亏（不计算历史已实现盈亏，只显示当前持仓盈亏）
            realized_pl = 0

            # 总盈亏 = 当前持仓盈亏
            total_pl = total_unrealized_pl

            # 盈亏百分比
            pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

            return {
                'realized_pl': realized_pl,
                'total_unrealized_pl': total_unrealized_pl,
                'total_market_value': total_market_value,
                'total_cost': total_cost,
                'total_pl': total_pl,
                'pl_pct': pl_pct,
                'price_details': price_details
            }

    def calculate_historical_pl_by_symbol(self) -> list:
        """
        计算按标的分组的历史盈亏

        对每个标的统计：
        - 买入数量和平均买入价
        - 卖出数量和平均卖出价
        - 当前持仓数量和市值
        - 已实现盈亏（卖出交易）
        - 未实现盈亏（当前持仓）
        - 总盈亏

        Returns:
            list: 每个标的的盈亏详情
        """
        from database.models.models import Transaction

        with self.get_session() as session:
            # 获取所有交易记录，按symbol和日期排序
            transactions = session.query(Transaction).order_by(
                Transaction.symbol,
                Transaction.trade_date.asc(),
                Transaction.id.asc()
            ).all()

            # 按symbol分组统计数据
            symbol_stats = {}  # {symbol: {...}}

            for txn in transactions:
                symbol = txn.symbol

                if symbol not in symbol_stats:
                    symbol_stats[symbol] = {
                        'symbol': symbol,
                        'bought_qty': 0.0,
                        'total_buy_cost': 0.0,
                        'sold_qty': 0.0,
                        'total_sell_revenue': 0.0,
                        'current_qty': 0.0,
                        'realized_pl': 0.0,
                        'queue': []  # FIFO queue for tracking buy lots
                    }

                stats = symbol_stats[symbol]

                if txn.buy_sell == 'buy':
                    # 买入：增加持仓，加入FIFO队列
                    stats['bought_qty'] += txn.quantity
                    stats['total_buy_cost'] += txn.price * txn.quantity
                    stats['current_qty'] += txn.quantity
                    # 加入FIFO队列：{quantity, avg_cost}
                    stats['queue'].append({
                        'quantity': txn.quantity,
                        'avg_cost': txn.price
                    })

                elif txn.buy_sell == 'sell':
                    # 卖出：使用FIFO计算已实现盈亏
                    remaining_sell = txn.quantity
                    sell_revenue = txn.price * txn.quantity
                    stats['sold_qty'] += txn.quantity
                    stats['total_sell_revenue'] += sell_revenue

                    # 从FIFO队列中扣除
                    while remaining_sell > 0.001 and stats['queue']:
                        lot = stats['queue'][0]
                        if lot['quantity'] <= remaining_sell + 0.001:
                            # 整个lot都卖出
                            stats['realized_pl'] += (txn.price - lot['avg_cost']) * lot['quantity']
                            remaining_sell -= lot['quantity']
                            stats['current_qty'] -= lot['quantity']
                            stats['queue'].pop(0)
                        else:
                            # 部分卖出
                            sell_qty = remaining_sell
                            stats['realized_pl'] += (txn.price - lot['avg_cost']) * sell_qty
                            lot['quantity'] -= sell_qty
                            stats['current_qty'] -= sell_qty
                            remaining_sell = 0

            # 获取所有有持仓或曾经有交易的标的
            symbols = list(symbol_stats.keys())

            # 批量获取公司简称
            company_abbr_map = self.batch_get_company_abbr(symbols)

            # 为每个标的获取当前价格并计算未实现盈亏
            results = []
            for symbol, stats in symbol_stats.items():
                # 跳过没有任何交易的标的
                if stats['bought_qty'] == 0 and stats['sold_qty'] == 0:
                    continue

                # 计算平均买入价
                avg_buy_price = stats['total_buy_cost'] / stats['bought_qty'] if stats['bought_qty'] > 0 else 0

                # 计算平均卖出价
                avg_sell_price = stats['total_sell_revenue'] / stats['sold_qty'] if stats['sold_qty'] > 0 else 0

                # 获取当前价格（如果有持仓）
                current_price = None
                current_market_value = 0.0
                unrealized_pl = 0.0

                if stats['current_qty'] > 0:
                    latest_price = self._get_latest_price_for_symbol(session, symbol)
                    if latest_price is not None:
                        current_price = latest_price
                        current_market_value = latest_price * stats['current_qty']

                        # 计算未实现盈亏：使用FIFO剩余持仓的成本
                        remaining_cost = sum(lot['quantity'] * lot['avg_cost'] for lot in stats['queue'])
                        unrealized_pl = (current_price * stats['current_qty']) - remaining_cost
                    else:
                        # 没有最新价格，使用队列中的平均成本估算
                        if stats['queue']:
                            avg_cost = sum(lot['quantity'] * lot['avg_cost'] for lot in stats['queue']) / stats['current_qty']
                            current_price = avg_cost
                            current_market_value = avg_cost * stats['current_qty']
                            unrealized_pl = 0

                # 总盈亏
                total_pl = stats['realized_pl'] + unrealized_pl

                # 总盈亏百分比（相对于总买入成本）
                total_pl_pct = (total_pl / stats['total_buy_cost'] * 100) if stats['total_buy_cost'] > 0 else 0

                results.append({
                    'symbol': symbol,
                    'zh_name': company_abbr_map.get(symbol, ''),
                    'bought_qty': round(stats['bought_qty'], 2),
                    'avg_buy_price': round(avg_buy_price, 3),
                    'total_buy_cost': round(stats['total_buy_cost'], 2),
                    'sold_qty': round(stats['sold_qty'], 2),
                    'avg_sell_price': round(avg_sell_price, 3),
                    'total_sell_revenue': round(stats['total_sell_revenue'], 2),
                    'current_qty': round(stats['current_qty'], 2),
                    'current_price': round(current_price, 3) if current_price is not None else None,
                    'current_market_value': round(current_market_value, 2),
                    'realized_pl': round(stats['realized_pl'], 2),
                    'unrealized_pl': round(unrealized_pl, 2),
                    'total_pl': round(total_pl, 2),
                    'total_pl_pct': round(total_pl_pct, 2)
                })

            # 按总盈亏排序
            results.sort(key=lambda x: x['total_pl'], reverse=True)

            return results

    # ==================== 基本面数据操作 ====================

    def upsert_stock_metadata(self, symbol: str, name: str = None,
                              sector: str = None, industry: str = None,
                              list_date: str = None, is_st: bool = False,
                              is_suspend: bool = False, is_new_ipo: bool = False):
        """
        更新股票元数据

        Args:
            symbol: 股票代码
            name: 股票名称
            sector: 板块
            industry: 行业
            list_date: 上市日期
            is_st: 是否ST股票
            is_suspend: 是否停牌
            is_new_ipo: 是否新股
        """
        with self.get_session() as session:
            metadata = session.query(StockMetadata).filter(
                StockMetadata.symbol == symbol
            ).first()

            if metadata:
                metadata.name = name
                metadata.sector = sector
                metadata.industry = industry
                metadata.list_date = pd.to_datetime(list_date).date() if list_date else None
                metadata.is_st = is_st
                metadata.is_suspend = is_suspend
                metadata.is_new_ipo = is_new_ipo
            else:
                new_metadata = StockMetadata(
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    industry=industry,
                    list_date=pd.to_datetime(list_date).date() if list_date else None,
                    is_st=is_st,
                    is_suspend=is_suspend,
                    is_new_ipo=is_new_ipo
                )
                session.add(new_metadata)

            logger.debug(f'更新股票元数据: {symbol} - {name}')

    def get_stock_metadata(self, symbol: str) -> dict:
        """
        查询股票元数据

        Args:
            symbol: 股票代码

        Returns:
            dict: 包含元数据的字典
        """
        with self.get_session() as session:
            metadata = session.query(StockMetadata).filter(
                StockMetadata.symbol == symbol
            ).first()

            if metadata:
                return {
                    'symbol': metadata.symbol,
                    'name': metadata.name,
                    'sector': metadata.sector,
                    'industry': metadata.industry,
                    'list_date': metadata.list_date,
                    'is_st': metadata.is_st,
                    'is_suspend': metadata.is_suspend,
                    'is_new_ipo': metadata.is_new_ipo,
                }
            return None

    def get_company_abbr(self, symbol: str) -> Optional[str]:
        """
        查询股票的中文简称

        Args:
            symbol: 股票代码（格式: 002788.SZ）

        Returns:
            Optional[str]: 中文简称，如果未找到返回None
        """
        with self.get_session() as session:
            stock_info = session.query(AShareStockInfo).filter(
                AShareStockInfo.symbol == symbol
            ).first()

            if stock_info:
                return stock_info.zh_company_abbr
            return None

    def batch_get_company_abbr(self, symbols: List[str]) -> dict:
        """
        批量查询股票的中文简称

        Args:
            symbols: 股票代码列表

        Returns:
            dict: {symbol: zh_company_abbr} 映射字典
        """
        if not symbols:
            return {}

        with self.get_session() as session:
            results = session.query(
                AShareStockInfo.symbol,
                AShareStockInfo.zh_company_abbr
            ).filter(
                AShareStockInfo.symbol.in_(symbols)
            ).all()

            return {row.symbol: row.zh_company_abbr for row in results}

    def update_stock_metadata(self, symbol: str, **fields):
        """
        更新单个股票的元数据字段（灵活更新）

        Args:
            symbol: 股票代码
            **fields: 要更新的字段，如 list_date=..., is_st=..., name=...

        Example:
            db.update_stock_metadata('000001.SZ', list_date='2020-01-01')
            db.update_stock_metadata('000001.SZ', is_st=True, name='新名称')
        """
        with self.get_session() as session:
            metadata = session.query(StockMetadata).filter(
                StockMetadata.symbol == symbol
            ).first()

            if not metadata:
                logger.debug(f'股票不存在: {symbol}')
                return

            # 更新指定字段
            for key, value in fields.items():
                if hasattr(metadata, key):
                    # 特殊处理 list_date
                    if key == 'list_date' and value:
                        if isinstance(value, str):
                            metadata.list_date = pd.to_datetime(value).date()
                        else:
                            metadata.list_date = value
                    else:
                        setattr(metadata, key, value)
                else:
                    logger.warning(f'无效的字段: {key}')

            logger.debug(f'更新股票元数据: {symbol}')

    def batch_upsert_stock_metadata(self, df: pd.DataFrame):
        """
        批量更新股票元数据

        Args:
            df: DataFrame,包含列: symbol, name, sector, industry, list_date, is_st, is_suspend, is_new_ipo
        """
        with self.get_session() as session:
            # 清空旧数据
            session.query(StockMetadata).delete()

            # 插入新数据
            records = df.to_dict('records')
            session.bulk_insert_mappings(StockMetadata, records)

            logger.info(f'批量更新股票元数据: {len(df)}条')

    def upsert_fundamental_daily(self, symbol: str, date_str: str,
                                 pe_ratio: float = None, pb_ratio: float = None,
                                 ps_ratio: float = None, roe: float = None,
                                 roa: float = None, profit_margin: float = None,
                                 operating_margin: float = None, debt_ratio: float = None,
                                 current_ratio: float = None, total_mv: float = None,
                                 circ_mv: float = None):
        """
        更新单日基本面数据

        Args:
            symbol: 股票代码
            date_str: 日期字符串
            pe_ratio: 市盈率
            pb_ratio: 市净率
            ps_ratio: 市销率
            roe: 净资产收益率
            roa: 总资产收益率
            profit_margin: 利润率
            operating_margin: 营业利润率
            debt_ratio: 资产负债率
            current_ratio: 流动比率
            total_mv: 总市值
            circ_mv: 流通市值
        """
        with self.get_session() as session:
            fundamental = session.query(StockFundamentalDaily).filter(
                StockFundamentalDaily.symbol == symbol,
                StockFundamentalDaily.date == pd.to_datetime(date_str).date()
            ).first()

            if fundamental:
                fundamental.pe_ratio = pe_ratio
                fundamental.pb_ratio = pb_ratio
                fundamental.ps_ratio = ps_ratio
                fundamental.roe = roe
                fundamental.roa = roa
                fundamental.profit_margin = profit_margin
                fundamental.operating_margin = operating_margin
                fundamental.debt_ratio = debt_ratio
                fundamental.current_ratio = current_ratio
                fundamental.total_mv = total_mv
                fundamental.circ_mv = circ_mv
            else:
                new_fundamental = StockFundamentalDaily(
                    symbol=symbol,
                    date=pd.to_datetime(date_str).date(),
                    pe_ratio=pe_ratio,
                    pb_ratio=pb_ratio,
                    ps_ratio=ps_ratio,
                    roe=roe,
                    roa=roa,
                    profit_margin=profit_margin,
                    operating_margin=operating_margin,
                    debt_ratio=debt_ratio,
                    current_ratio=current_ratio,
                    total_mv=total_mv,
                    circ_mv=circ_mv
                )
                session.add(new_fundamental)

            logger.debug(f'更新基本面数据: {symbol} @ {date_str}')

    def batch_upsert_fundamental(self, df: pd.DataFrame):
        """
        批量更新基本面数据

        Args:
            df: DataFrame,包含基本面数据列
        """
        df['date'] = pd.to_datetime(df['date']).dt.date

        with self.get_session() as session:
            # 使用临时表和 ON CONFLICT DO UPDATE
            df.to_sql('temp_fundamental_insert', self.engine, if_exists='replace', index=False)

            session.execute(text("""
                INSERT INTO stock_fundamental_daily
                (symbol, date, pe_ratio, pb_ratio, ps_ratio, roe, roa,
                 profit_margin, operating_margin, debt_ratio, current_ratio,
                 total_mv, circ_mv)
                SELECT symbol, date, pe_ratio, pb_ratio, ps_ratio, roe, roa,
                       profit_margin, operating_margin, debt_ratio, current_ratio,
                       total_mv, circ_mv
                FROM temp_fundamental_insert
                ON CONFLICT (symbol, date) DO UPDATE SET
                    pe_ratio = EXCLUDED.pe_ratio,
                    pb_ratio = EXCLUDED.pb_ratio,
                    ps_ratio = EXCLUDED.ps_ratio,
                    roe = EXCLUDED.roe,
                    roa = EXCLUDED.roa,
                    profit_margin = EXCLUDED.profit_margin,
                    operating_margin = EXCLUDED.operating_margin,
                    debt_ratio = EXCLUDED.debt_ratio,
                    current_ratio = EXCLUDED.current_ratio,
                    total_mv = EXCLUDED.total_mv,
                    circ_mv = EXCLUDED.circ_mv
            """))

            session.execute(text("DROP TABLE temp_fundamental_insert"))

            logger.info(f'批量更新基本面数据: {len(df)}条')

    def batch_insert_fundamental_if_not_exists(self, df: pd.DataFrame) -> int:
        """
        批量插入基本面数据，跳过已存在的记录

        Args:
            df: DataFrame,包含基本面数据列

        Returns:
            实际插入的新记录数
        """
        try:
            df['date'] = pd.to_datetime(df['date']).dt.date

            # 确保数值列类型正确
            numeric_columns = [
                'pe_ratio', 'pb_ratio', 'ps_ratio', 'roe', 'roa',
                'profit_margin', 'operating_margin', 'debt_ratio', 'current_ratio',
                'total_mv', 'circ_mv'
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

            with self.get_session() as session:
                # 使用临时表和 ON CONFLICT DO NOTHING
                df.to_sql('temp_fundamental_insert', self.engine, if_exists='replace', index=False)

                result = session.execute(text("""
                    INSERT INTO stock_fundamental_daily
                    (symbol, date, pe_ratio, pb_ratio, ps_ratio, roe, roa,
                     profit_margin, operating_margin, debt_ratio, current_ratio,
                     total_mv, circ_mv)
                    SELECT symbol, date, pe_ratio, pb_ratio, ps_ratio, roe, roa,
                           profit_margin, operating_margin, debt_ratio, current_ratio,
                           total_mv, circ_mv
                    FROM temp_fundamental_insert
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text("DROP TABLE temp_fundamental_insert"))

                inserted_count = result.rowcount
                logger.info(f'批量插入基本面数据: {inserted_count} 条新记录, 总计 {len(df)} 条')
                return inserted_count

        except Exception as e:
            logger.error(f'批量插入基本面数据失败: {e}')
            return 0

    def get_fundamental_daily(self, symbol: str, start_date: date = None,
                             end_date: date = None) -> pd.DataFrame:
        """
        查询历史基本面数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame: 基本面数据
        """
        with self.get_session() as session:
            query = session.query(StockFundamentalDaily).filter(
                StockFundamentalDaily.symbol == symbol
            )

            if start_date:
                query = query.filter(StockFundamentalDaily.date >= start_date)
            if end_date:
                query = query.filter(StockFundamentalDaily.date <= end_date)

            query = query.order_by(StockFundamentalDaily.date.desc())

            return pd.read_sql(query.statement, session.bind)

    def get_latest_fundamental(self, symbol: str) -> dict:
        """
        获取最新一期基本面数据

        Args:
            symbol: 股票代码

        Returns:
            dict: 最新基本面数据
        """
        with self.get_session() as session:
            fundamental = session.query(StockFundamentalDaily).filter(
                StockFundamentalDaily.symbol == symbol
            ).order_by(StockFundamentalDaily.date.desc()).first()

            if fundamental:
                return {
                    'symbol': fundamental.symbol,
                    'date': fundamental.date,
                    'pe_ratio': fundamental.pe_ratio,
                    'pb_ratio': fundamental.pb_ratio,
                    'ps_ratio': fundamental.ps_ratio,
                    'roe': fundamental.roe,
                    'roa': fundamental.roa,
                    'profit_margin': fundamental.profit_margin,
                    'operating_margin': fundamental.operating_margin,
                    'debt_ratio': fundamental.debt_ratio,
                    'current_ratio': fundamental.current_ratio,
                    'total_mv': fundamental.total_mv,
                    'circ_mv': fundamental.circ_mv,
                }
            return None

    def get_stock_latest_fundamental_date(self, symbol: str) -> Optional[date]:
        """
        获取指定股票的基本面数据最新日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        with self.get_session() as session:
            result = session.query(sql_func.max(StockFundamentalDaily.date)).filter(
                StockFundamentalDaily.symbol == symbol
            ).scalar()
            return result

    def get_stock_fundamental_count(self, symbol: str) -> int:
        """
        获取指定股票的基本面数据记录数量

        Args:
            symbol: 股票代码

        Returns:
            记录数量
        """
        with self.get_session() as session:
            result = session.query(sql_func.count(StockFundamentalDaily.id)).filter(
                StockFundamentalDaily.symbol == symbol
            ).scalar()
            return result or 0

    def batch_get_latest_fundamental(self, symbols: List[str]) -> pd.DataFrame:
        """
        批量获取多只股票的最新基本面数据（仅PE和PB）

        Args:
            symbols: 股票代码列表

        Returns:
            DataFrame: 包含 symbol, pe, pb 列的基本面数据
        """
        if not symbols:
            return pd.DataFrame()

        with self.get_session() as session:
            # 使用子查询获取每只股票的最新日期
            subquery = session.query(
                StockFundamentalDaily.symbol,
                sql_func.max(StockFundamentalDaily.date).label('max_date')
            ).filter(
                StockFundamentalDaily.symbol.in_(symbols)
            ).group_by(StockFundamentalDaily.symbol).subquery()

            # 联接获取最新数据
            query = session.query(
                StockFundamentalDaily.symbol,
                StockFundamentalDaily.pe_ratio,
                StockFundamentalDaily.pb_ratio
            ).join(
                subquery,
                (StockFundamentalDaily.symbol == subquery.c.symbol) &
                (StockFundamentalDaily.date == subquery.c.max_date)
            )

            df = pd.read_sql(query.statement, session.bind)

            # 重命名列为简短名称（便于公式使用）
            df.rename(columns={
                'pe_ratio': 'pe',
                'pb_ratio': 'pb'
            }, inplace=True)

            return df

    def cleanup_old_fundamental(self, keep_days: int = 30):
        """
        清理旧的基本面数据

        Args:
            keep_days: 保留天数
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        with self.get_session() as session:
            deleted = session.query(StockFundamentalDaily).filter(
                StockFundamentalDaily.date < cutoff_date.date()
            ).delete()

            logger.info(f'清理了 {deleted} 条旧基本面数据')

    # ==================== 代码管理 ====================

    def get_etf_codes(self) -> List[str]:
        """
        获取所有 ETF 代码

        Returns:
            List[str]: ETF 代码列表
        """
        with self.get_session() as session:
            result = session.query(EtfCode.symbol).order_by(EtfCode.symbol).all()
            return [r[0] for r in result]

    def get_stock_codes(self) -> List[str]:
        """
        获取所有股票代码

        Returns:
            List[str]: 股票代码列表
        """
        with self.get_session() as session:
            result = session.query(StockCode.symbol).order_by(StockCode.symbol).all()
            return [r[0] for r in result]

    def search_codes(self, search: str = None, limit: int = 100) -> List[str]:
        """
        搜索 ETF 和股票代码

        Args:
            search: 搜索关键词（模糊匹配 symbol）
            limit: 最大返回数量（默认100）

        Returns:
            List[str]: 匹配的代码列表（合并 ETF 和股票）
        """
        with self.get_session() as session:
            codes = []

            # 搜索 ETF 代码
            etf_query = session.query(EtfCode.symbol)
            if search:
                etf_query = etf_query.filter(EtfCode.symbol.ilike(f'%{search}%'))
            etf_query = etf_query.order_by(EtfCode.symbol).limit(limit)

            codes.extend([r[0] for r in etf_query.all()])

            # 搜索股票代码
            stock_query = session.query(StockCode.symbol)
            if search:
                stock_query = stock_query.filter(StockCode.symbol.ilike(f'%{search}%'))
            stock_query = stock_query.order_by(StockCode.symbol).limit(limit)

            codes.extend([r[0] for r in stock_query.all()])

            # 去重并排序
            codes = sorted(list(set(codes)))

            return codes[:limit]

    def add_etf_code(self, symbol: str):
        """
        添加单个 ETF 代码

        Args:
            symbol: ETF 代码
        """
        with self.get_session() as session:
            existing = session.query(EtfCode).filter(EtfCode.symbol == symbol).first()
            if not existing:
                session.add(EtfCode(symbol=symbol))

    def add_stock_code(self, symbol: str):
        """
        添加单个股票代码

        Args:
            symbol: 股票代码
        """
        with self.get_session() as session:
            existing = session.query(StockCode).filter(StockCode.symbol == symbol).first()
            if not existing:
                session.add(StockCode(symbol=symbol))

    def batch_add_etf_codes(self, symbols: List[str]) -> int:
        """
        批量添加 ETF 代码

        Args:
            symbols: ETF 代码列表

        Returns:
            成功插入的数量
        """
        try:
            with self.get_session() as session:
                inserted = 0
                for symbol in symbols:
                    existing = session.query(EtfCode).filter(
                        EtfCode.symbol == symbol
                    ).first()
                    if not existing:
                        session.add(EtfCode(symbol=symbol))
                        inserted += 1

                logger.info(f'批量插入ETF代码: {inserted}/{len(symbols)}')
                return inserted
        except Exception as e:
            logger.error(f'批量插入ETF代码失败: {e}')
            return 0

    def batch_add_stock_codes(self, symbols: List[str]) -> int:
        """
        批量添加股票代码

        Args:
            symbols: 股票代码列表

        Returns:
            成功插入的数量
        """
        try:
            with self.get_session() as session:
                inserted = 0
                for symbol in symbols:
                    existing = session.query(StockCode).filter(
                        StockCode.symbol == symbol
                    ).first()
                    if not existing:
                        session.add(StockCode(symbol=symbol))
                        inserted += 1

                logger.info(f'批量插入股票代码: {inserted}/{len(symbols)}')
                return inserted
        except Exception as e:
            logger.error(f'批量插入股票代码失败: {e}')
            return 0

    def clear_etf_codes(self):
        """清空ETF代码表(用于强制重新初始化)"""
        with self.get_session() as session:
            count = session.query(EtfCode).delete()
            logger.info(f'清空ETF代码表: {count}条记录')

    def clear_stock_codes(self):
        """清空股票代码表(用于强制重新初始化)"""
        with self.get_session() as session:
            count = session.query(StockCode).delete()
            logger.info(f'清空股票代码表: {count}条记录')

    def get_code_count(self, table: str = 'both') -> dict:
        """
        获取代码表记录数

        Args:
            table: 'etf', 'stock', 或 'both'

        Returns:
            dict: {'etf': N, 'stock': M}
        """
        result = {}
        with self.get_session() as session:
            if table in ['etf', 'both']:
                result['etf'] = session.query(EtfCode).count()
            if table in ['stock', 'both']:
                result['stock'] = session.query(StockCode).count()
        return result

    # ==================== 因子缓存 ====================

    def cache_factor(self, symbol: str, date: date, factor_name: str, factor_value: float):
        """
        缓存因子值

        Args:
            symbol: 股票代码
            date: 日期
            factor_name: 因子名称
            factor_value: 因子值
        """
        with self.get_session() as session:
            factor = session.query(FactorCache).filter(
                FactorCache.symbol == symbol,
                FactorCache.date == date,
                FactorCache.factor_name == factor_name
            ).first()

            if factor:
                factor.factor_value = factor_value
            else:
                new_factor = FactorCache(
                    symbol=symbol,
                    date=date,
                    factor_name=factor_name,
                    factor_value=factor_value
                )
                session.add(new_factor)

    def get_cached_factor(self, symbol: str, date: date, factor_name: str) -> Optional[float]:
        """
        获取缓存的因子值

        Args:
            symbol: 股票代码
            date: 日期
            factor_name: 因子名称

        Returns:
            float: 因子值，如果不存在返回 None
        """
        with self.get_session() as session:
            factor = session.query(FactorCache).filter(
                FactorCache.symbol == symbol,
                FactorCache.date == date,
                FactorCache.factor_name == factor_name
            ).first()

            return factor.factor_value if factor else None

    def clear_factor_cache(self, before_date: date = None):
        """
        清理因子缓存

        Args:
            before_date: 清理此日期之前的缓存
        """
        with self.get_session() as session:
            query = session.query(FactorCache)

            if before_date:
                query = query.filter(FactorCache.date < before_date)

            deleted = query.delete()
            logger.info(f'清理了 {deleted} 条因子缓存')

    # ==================== 统计信息 ====================

    def get_all_symbols(self) -> List[str]:
        """
        获取数据库中所有 ETF 代码

        Returns:
            List[str]: ETF 代码列表
        """
        with self.get_session() as session:
            result = session.query(EtfHistory.symbol).distinct().order_by(
                EtfHistory.symbol
            ).all()
            return [r[0] for r in result]

    def get_statistics(self) -> dict:
        """
        获取数据库统计信息

        Returns:
            dict: 统计信息
        """
        with self.get_session() as session:
            stats = session.query(
                sql_func.countDistinct(EtfHistory.symbol).label('total_symbols'),
                sql_func.count().label('total_records'),
                sql_func.min(EtfHistory.date).label('earliest_date'),
                sql_func.max(EtfHistory.date).label('latest_date')
            ).first()

            return {
                'total_symbols': stats.total_symbols,
                'total_records': stats.total_records,
                'earliest_date': stats.earliest_date,
                'latest_date': stats.latest_date
            }

    # ==================== 回测和报告 ====================

    def save_backtest_transactions(self, transactions_df: pd.DataFrame,
                                   strategy_name: str = None) -> bool:
        """
        批量保存回测交易记录到数据库

        Args:
            transactions_df: 交易记录DataFrame，必须包含列:
                            [symbol, buy_sell, quantity, price, date]
            strategy_name: 策略名称

        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            with self.get_session() as session:
                for _, row in transactions_df.iterrows():
                    transaction = Transaction(
                        symbol=row['symbol'],
                        buy_sell=row['buy_sell'],
                        quantity=float(row['quantity']),
                        price=float(row['price']),
                        trade_date=pd.to_datetime(row['date']).date(),
                        strategy_name=strategy_name or 'backtest'
                    )
                    session.add(transaction)

                session.commit()
                logger.info(f'✓ 保存 {len(transactions_df)} 条回测交易记录到数据库')
                return True

        except Exception as e:
            logger.error(f'✗ 保存回测交易记录失败: {e}')
            return False

    def save_strategy_report_summary(self, report_date: date,
                                     total_signals: int = 0,
                                     buy_signals: int = 0,
                                     sell_signals: int = 0,
                                     positions_count: int = 0) -> bool:
        """
        保存策略报告摘要到数据库

        Args:
            report_date: 报告日期
            total_signals: 总信号数
            buy_signals: 买入信号数
            sell_signals: 卖出信号数
            positions_count: 持仓数量

        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 简化版本：仅记录日志
            # TODO: 创建专门的StrategyReport表来存储统计信息
            logger.info(f'✓ 策略报告摘要: {report_date}')
            logger.info(f'  总信号数: {total_signals}, 买入: {buy_signals}, 卖出: {sell_signals}, 持仓: {positions_count}')
            return True

        except Exception as e:
            logger.error(f'✗ 保存报告摘要失败: {e}')
            return False

    # ==================== 回测结果操作 ====================

    def save_backtest_result(self, strategy_name: str, asset_type: str,
                             start_date: str, end_date: str,
                             total_return: float, annual_return: float,
                             sharpe_ratio: float, max_drawdown: float,
                             equity_curve: list, trade_list: list,
                             strategy_version: str = None,
                             initial_capital: float = 1000000,
                             **kwargs) -> Optional[int]:
        """
        保存回测结果到数据库

        Args:
            strategy_name: 策略名称
            asset_type: 'etf' or 'ashare'
            start_date: 回测开始日期
            end_date: 回测结束日期
            total_return: 总收益率
            annual_return: 年化收益率
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            equity_curve: 权益曲线数据 [{date, value}, ...]
            trade_list: 交易列表
            strategy_version: 策略版本
            initial_capital: 初始资金
            **kwargs: 其他指标

        Returns:
            int: 新创建的backtest记录ID，失败返回None
        """
        import json

        try:
            with self.get_session() as session:
                backtest = StrategyBacktest(
                    strategy_name=strategy_name,
                    strategy_version=strategy_version,
                    asset_type=asset_type,
                    start_date=pd.to_datetime(start_date).date(),
                    end_date=pd.to_datetime(end_date).date(),
                    initial_capital=initial_capital,
                    total_return=total_return,
                    annual_return=annual_return,
                    sharpe_ratio=sharpe_ratio,
                    max_drawdown=max_drawdown,
                    equity_curve=json.dumps(equity_curve, default=str),
                    trade_list=json.dumps(trade_list, default=str),
                    **kwargs
                )
                session.add(backtest)
                session.flush()  # Get the ID without committing
                backtest_id = backtest.id
                session.commit()
                logger.info(f'✓ 回测结果已保存: {strategy_name} (ID: {backtest_id})')
                return backtest_id
        except Exception as e:
            logger.error(f"Failed to save backtest result: {e}")
            return None

    def get_latest_backtest(self, strategy_name: str,
                            asset_type: str = 'ashare') -> Optional[dict]:
        """
        获取指定策略的最新回测结果

        Args:
            strategy_name: 策略名称
            asset_type: 资产类型 ('etf' or 'ashare')

        Returns:
            dict: 回测结果字典，不存在返回None
        """
        import json

        try:
            with self.get_session() as session:
                backtest = session.query(StrategyBacktest).filter(
                    StrategyBacktest.strategy_name == strategy_name,
                    StrategyBacktest.asset_type == asset_type
                ).order_by(StrategyBacktest.backtest_date.desc()).first()

                if backtest:
                    return {
                        'id': backtest.id,
                        'strategy_name': backtest.strategy_name,
                        'strategy_version': backtest.strategy_version,
                        'asset_type': backtest.asset_type,
                        'start_date': backtest.start_date.strftime('%Y-%m-%d'),
                        'end_date': backtest.end_date.strftime('%Y-%m-%d'),
                        'total_return': float(backtest.total_return) if backtest.total_return else 0.0,
                        'annual_return': float(backtest.annual_return) if backtest.annual_return else 0.0,
                        'sharpe_ratio': float(backtest.sharpe_ratio) if backtest.sharpe_ratio else 0.0,
                        'max_drawdown': float(backtest.max_drawdown) if backtest.max_drawdown else 0.0,
                        'win_rate': float(backtest.win_rate) if backtest.win_rate else None,
                        'profit_factor': float(backtest.profit_factor) if backtest.profit_factor else None,
                        'total_trades': backtest.total_trades,
                        'benchmark_return': float(backtest.benchmark_return) if backtest.benchmark_return else None,
                        'equity_curve': json.loads(backtest.equity_curve) if backtest.equity_curve else [],
                        'trade_list': json.loads(backtest.trade_list) if backtest.trade_list else [],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get latest backtest: {e}")
            return None

    def get_backtest_by_id(self, backtest_id: int) -> Optional[dict]:
        """
        通过ID获取回测详情

        Args:
            backtest_id: 回测ID

        Returns:
            dict: 回测详情字典，不存在返回None
        """
        import json

        try:
            with self.get_session() as session:
                backtest = session.query(StrategyBacktest).filter(
                    StrategyBacktest.id == backtest_id
                ).first()

                if backtest:
                    return {
                        'id': backtest.id,
                        'strategy_name': backtest.strategy_name,
                        'strategy_version': backtest.strategy_version,
                        'asset_type': backtest.asset_type,
                        'start_date': backtest.start_date.strftime('%Y-%m-%d'),
                        'end_date': backtest.end_date.strftime('%Y-%m-%d'),
                        'total_return': float(backtest.total_return) if backtest.total_return else 0.0,
                        'annual_return': float(backtest.annual_return) if backtest.annual_return else 0.0,
                        'sharpe_ratio': float(backtest.sharpe_ratio) if backtest.sharpe_ratio else 0.0,
                        'max_drawdown': float(backtest.max_drawdown) if backtest.max_drawdown else 0.0,
                        'win_rate': float(backtest.win_rate) if backtest.win_rate else None,
                        'profit_factor': float(backtest.profit_factor) if backtest.profit_factor else None,
                        'total_trades': backtest.total_trades,
                        'benchmark_return': float(backtest.benchmark_return) if backtest.benchmark_return else None,
                        'equity_curve': json.loads(backtest.equity_curve) if backtest.equity_curve else [],
                        'trade_list': json.loads(backtest.trade_list) if backtest.trade_list else [],
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get backtest by ID: {e}")
            return None

    def associate_signal_with_backtest(self, trader_id: int, backtest_id: int,
                                       strategy_name: str) -> bool:
        """
        关联信号与回测结果

        Args:
            trader_id: 信号ID (trader表)
            backtest_id: 回测ID
            strategy_name: 策略名称

        Returns:
            bool: 成功返回True
        """
        try:
            with self.get_session() as session:
                # Check if association already exists
                existing = session.query(SignalBacktestAssociation).filter(
                    SignalBacktestAssociation.trader_id == trader_id,
                    SignalBacktestAssociation.backtest_id == backtest_id
                ).first()

                if existing:
                    return True  # Already associated

                association = SignalBacktestAssociation(
                    trader_id=trader_id,
                    backtest_id=backtest_id,
                    strategy_name=strategy_name
                )
                session.add(association)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to associate signal with backtest: {e}")
            return False

    def get_signal_backtest(self, trader_id: int) -> Optional[dict]:
        """
        获取信号关联的回测信息

        Args:
            trader_id: 信号ID

        Returns:
            dict: 回测信息字典
        """
        import json

        try:
            with self.get_session() as session:
                association = session.query(SignalBacktestAssociation).filter(
                    SignalBacktestAssociation.trader_id == trader_id
                ).first()

                if association:
                    backtest = session.query(StrategyBacktest).filter(
                        StrategyBacktest.id == association.backtest_id
                    ).first()

                    if backtest:
                        return {
                            'id': backtest.id,
                            'strategy_name': backtest.strategy_name,
                            'strategy_version': backtest.strategy_version,
                            'total_return': float(backtest.total_return) if backtest.total_return else 0.0,
                            'annual_return': float(backtest.annual_return) if backtest.annual_return else 0.0,
                            'sharpe_ratio': float(backtest.sharpe_ratio) if backtest.sharpe_ratio else 0.0,
                            'max_drawdown': float(backtest.max_drawdown) if backtest.max_drawdown else 0.0,
                        }
                return None
        except Exception as e:
            logger.error(f"Failed to get signal backtest: {e}")
            return None


# ==================== 全局单例 ====================

_pg_instance = None


def get_db() -> PostgreSQLManager:
    """
    获取 PostgreSQL 数据库单例

    Returns:
        PostgreSQLManager: 数据库管理器实例
    """
    global _pg_instance
    if _pg_instance is None:
        _pg_instance = PostgreSQLManager()
    return _pg_instance


def close_all_connections():
    """关闭所有数据库连接"""
    global _pg_instance
    if _pg_instance:
        _pg_instance = None
    logger.info('所有数据库连接已关闭')
