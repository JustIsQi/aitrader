"""
PostgreSQL 数据库管理器
使用 SQLAlchemy ORM 替代 DuckDB
"""
import pandas as pd
from datetime import datetime, date
from typing import Optional, List
from contextlib import contextmanager
from loguru import logger

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func as sql_func, text, distinct
from sqlalchemy.exc import IntegrityError

from database.models import (
    EtfHistory, StockHistory, StockMetadata, StockFundamentalDaily,
    Trader, Transaction, Position, FactorCache, EtfCode, StockCode
)
from database.models.base import SessionLocal, engine


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

            with self.get_session() as session:
                # 使用临时表和 ON CONFLICT DO NOTHING
                df.to_sql('temp_etf_insert', self.engine, if_exists='replace', index=False)

                session.execute(text("""
                    INSERT INTO etf_history
                    (symbol, date, open, high, low, close, volume, amount,
                     amplitude, change_pct, change_amount, turnover_rate)
                    SELECT symbol, date, open, high, low, close, volume, amount,
                           amplitude, change_pct, change_amount, turnover_rate
                    FROM temp_etf_insert
                    ON CONFLICT (symbol, date) DO NOTHING
                """))

                session.execute(text("DROP TABLE temp_etf_insert"))

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

    # ==================== 信号操作 ====================

    def insert_trader_signal(self, symbol: str, signal_type: str,
                            strategies: List[str], signal_date: date,
                            price: float = None, score: float = None,
                            rank: int = None, quantity: int = None):
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
        """
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
                    quantity=quantity
                )
                session.add(new_signal)

            logger.info(f'记录交易信号: {signal_type} {symbol} - {strategies_str}')

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

    def calculate_profit_loss(self) -> dict:
        """
        计算总体盈亏

        Returns:
            dict: 盈亏统计
        """
        with self.get_session() as session:
            positions = session.query(Position).filter(Position.quantity > 0).all()

            total_cost = 0
            total_value = 0
            total_pl = 0

            for pos in positions:
                total_cost += pos.avg_cost * pos.quantity
                total_value += pos.market_value if pos.market_value else 0

            total_pl = total_value - total_cost
            pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0

            return {
                'total_cost': total_cost,
                'total_value': total_value,
                'total_pl': total_pl,
                'pl_pct': pl_pct
            }

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
