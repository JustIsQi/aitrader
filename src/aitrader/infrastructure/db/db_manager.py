"""
Database 数据库管理器
使用 SQLAlchemy ORM 替代 DuckDB
"""
import pandas as pd
import time
import uuid
from datetime import datetime, date
from typing import Optional, List
from contextlib import contextmanager
from aitrader.infrastructure.config.logging import logger

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func as sql_func, text, distinct
from sqlalchemy.exc import IntegrityError

from aitrader.infrastructure.db.models import (
    Trader, Transaction, Position, FactorCache, StockCode,
    StrategyBacktest, SignalBacktestAssociation, AShareStockInfo,
)
from aitrader.infrastructure.db.models.base import SessionLocal, engine
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader


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


class DatabaseManager:
    """Database 数据库管理器 (使用 SQLAlchemy ORM)"""

    def __init__(self):
        """初始化数据库连接"""
        self.engine = engine
        self._session_local = SessionLocal
        self.wind_reader = MySQLAshareReader()
        logger.info('Database 数据库已连接')

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

    def _mirror_removed(self, feature: str):
        raise RuntimeError(
            f"{feature} 已移除。当前数据链路统一直读 Wind MySQL，不再读写本地镜像表。"
        )

    def _normalize_wind_date(self, value: Optional[date | datetime | str], default: str) -> str:
        if value is None:
            return default
        return pd.to_datetime(value).strftime("%Y%m%d")

    def _normalize_wind_history_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "date", "symbol", "open", "high", "low", "close", "volume",
                    "amount", "change_pct", "turnover_rate",
                ]
            )

        out = df.copy()
        out["date"] = pd.to_datetime(out["date"], format="%Y%m%d", errors="coerce").dt.date
        preferred_columns = [
            "date", "symbol", "real_open", "real_close", "real_low", "open", "close",
            "high", "low", "volume", "amount", "change_pct", "turnover_rate",
        ]
        available = [column for column in preferred_columns if column in out.columns]
        return out[available].sort_values(["symbol", "date"]).reset_index(drop=True)

    # ==================== 股票操作 ====================

    def insert_stock_history(self, df: pd.DataFrame, symbol: str = None) -> bool:
        """
        插入或更新股票历史数据

        Args:
            df: 包含历史数据的 DataFrame
            symbol: 股票代码
        """
        self._mirror_removed("stock_history 写入接口")

    def append_stock_history(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的股票历史数据

        Args:
            df: 新的数据 DataFrame
            symbol: 股票代码
        """
        self._mirror_removed("stock_history 追加写入接口")

    def batch_append_stock_history(self, df: pd.DataFrame) -> int:
        """
        批量追加多个股票的历史数据（优化版）

        一次性插入多个股票的数据，减少数据库操作次数

        Args:
            df: 包含多个股票数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        self._mirror_removed("stock_history 批量写入接口")

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
            if not symbols:
                return {}

            placeholders = ", ".join(["%s"] * len(symbols))
            df = self.wind_reader.read_query(
                f"""
                SELECT
                    S_INFO_WINDCODE AS symbol,
                    MAX(TRADE_DT) AS latest_date,
                    COUNT(*) AS record_count
                FROM ASHAREEODPRICES
                WHERE S_INFO_WINDCODE IN ({placeholders})
                GROUP BY S_INFO_WINDCODE
                """,
                list(symbols),
            )

            completeness_map = {}
            days_since_target = (datetime.now() - target_start_dt).days
            expected_records = int(days_since_target * 0.7)

            for _, row in df.iterrows():
                latest_date = pd.to_datetime(row.get("latest_date"), format="%Y%m%d", errors="coerce")
                latest_date_dt = latest_date.to_pydatetime() if not pd.isna(latest_date) else None
                record_count = int(row.get("record_count") or 0)
                symbol = str(row.get("symbol"))
                needs_download = (
                    latest_date_dt is None or
                    latest_date_dt < target_start_dt or
                    record_count < expected_records
                )
                completeness_map[symbol] = {
                    'needs_download': needs_download,
                    'latest_date': latest_date_dt.date() if latest_date_dt else None,
                    'record_count': record_count,
                    'reason': 'incomplete' if needs_download else 'complete'
                }

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
        start_bound = self._normalize_wind_date(start_date, "19000101")
        end_bound = self._normalize_wind_date(
            end_date,
            self.wind_reader.get_latest_trade_date(),
        )
        df = self.wind_reader.read_prices(
            symbols=[symbol],
            start_date=start_bound,
            end_date=end_bound,
        )
        return self._normalize_wind_history_df(df)

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
            start_bound = self._normalize_wind_date(start_date, "19000101")
            end_bound = self._normalize_wind_date(
                end_date,
                self.wind_reader.get_latest_trade_date(),
            )
            df = self.wind_reader.read_prices(
                symbols=symbols,
                start_date=start_bound,
                end_date=end_bound,
            )
            return self._normalize_wind_history_df(df)

    def get_stock_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定股票的最新数据日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        df = self.wind_reader.read_query(
            """
            SELECT MAX(TRADE_DT) AS latest_date
            FROM ASHAREEODPRICES
            WHERE S_INFO_WINDCODE = %s
            """,
            [symbol],
        )
        if df.empty:
            return None

        latest_date = pd.to_datetime(df.iloc[0].get("latest_date"), format="%Y%m%d", errors="coerce")
        if pd.isna(latest_date):
            return None
        return latest_date.to_pydatetime()

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
        self._mirror_removed("stock_history_qfq 读取接口")

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
        self._mirror_removed("stock_history_qfq 批量读取接口")

    def get_stock_qfq_latest_date(self, symbol: str) -> Optional[datetime]:
        """
        获取指定股票的前复权最新数据日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        self._mirror_removed("stock_history_qfq 最新日期接口")

    def append_stock_history_qfq(self, df: pd.DataFrame, symbol: str) -> bool:
        """
        追加新的股票前复权历史数据

        Args:
            df: 新的数据 DataFrame
            symbol: 股票代码
        """
        self._mirror_removed("stock_history_qfq 写入接口")

    def batch_append_stock_history_qfq(self, df: pd.DataFrame) -> int:
        """
        批量追加多个股票的前复权历史数据（优化版）

        一次性插入多个股票的数据，减少数据库操作次数

        Args:
            df: 包含多个股票数据的 DataFrame，必须有 symbol 列

        Returns:
            int: 实际插入的记录数
        """
        self._mirror_removed("stock_history_qfq 批量写入接口")

    # ==================== 交易操作 ====================

    def insert_transaction(self, symbol: str, buy_sell: str, quantity: float,
                          price: float, trade_date: str, strategy_name: str = None):
        """
        插入交易记录

        Args:
            symbol: 股票代码
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
                            asset_type: str = None, backtest_metrics: dict = None):
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
            asset_type: 资产类型，默认 ashare
            backtest_metrics: 回测指标字典 (可选)
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

        if asset_type is None:
            asset_type = 'ashare'

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
        self._mirror_removed("stock_history_qfq 最新价格接口")

    def get_qfq_latest_prices(self, symbols: List[str]) -> dict:
        """
        批量获取股票的最新价格

        Args:
            symbols: 代码列表

        Returns:
            dict: {symbol: latest_price}
        """
        self._mirror_removed("stock_history_qfq 批量最新价格接口")

    def _get_latest_price_for_symbol(self, session, symbol: str) -> Optional[float]:
        """
        获取指定股票代码的最新价格

        Args:
            session: SQLAlchemy session
            symbol: 股票代码

        Returns:
            最新收盘价，如果没有数据返回 None
        """
        self._mirror_removed("stock_history_qfq 单票最新价格接口")

    def calculate_realized_pl(self) -> float:
        """
        计算已实现盈亏（从交易历史中已完成的买卖交易）

        通过分析交易记录，按时间顺序处理每一笔交易，使用FIFO方法
        计算每一对买卖交易的盈亏。

        Returns:
            float: 已实现盈亏总额
        """
        from aitrader.infrastructure.db.models.models import Transaction

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
        from aitrader.infrastructure.db.models.models import Transaction

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
        self._mirror_removed("stock_metadata 写入接口")

    def get_stock_metadata(self, symbol: str) -> dict:
        """
        查询股票元数据

        Args:
            symbol: 股票代码

        Returns:
            dict: 包含元数据的字典
        """
        metadata = self.wind_reader.read_stock_metadata(symbols=[symbol])
        if metadata.empty:
            return None

        row = metadata.iloc[0]
        list_date = pd.to_datetime(row.get('list_date'), errors='coerce')
        return {
            'symbol': row.get('symbol'),
            'name': row.get('name'),
            'sector': row.get('sector'),
            'industry': row.get('industry'),
            'list_date': list_date.date() if not pd.isna(list_date) else None,
            'list_board_name': row.get('list_board_name'),
            'sw_ind_name': row.get('sw_ind_name'),
            'is_st': None,
            'is_suspend': None,
            'is_new_ipo': None,
        }

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
        self._mirror_removed("stock_metadata 更新接口")

    def batch_upsert_stock_metadata(self, df: pd.DataFrame):
        """
        批量更新股票元数据

        Args:
            df: DataFrame,包含列: symbol, name, sector, industry, list_date, is_st, is_suspend, is_new_ipo
        """
        self._mirror_removed("stock_metadata 批量写入接口")

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
        self._mirror_removed("stock_fundamental_daily 写入接口")

    def batch_upsert_fundamental(self, df: pd.DataFrame):
        """
        批量更新基本面数据

        Args:
            df: DataFrame,包含基本面数据列
        """
        self._mirror_removed("stock_fundamental_daily 批量写入接口")

    def batch_insert_fundamental_if_not_exists(self, df: pd.DataFrame) -> int:
        """
        批量插入基本面数据，跳过已存在的记录

        Args:
            df: DataFrame,包含基本面数据列

        Returns:
            实际插入的新记录数
        """
        self._mirror_removed("stock_fundamental_daily 去重写入接口")

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
        start_bound = self._normalize_wind_date(start_date, "19000101")
        end_bound = self._normalize_wind_date(
            end_date,
            self.wind_reader.get_latest_trade_date(),
        )
        df = self.wind_reader.read_derivative_indicator_history(
            symbols=[symbol],
            start_date=start_bound,
            end_date=end_bound,
        )
        return df.sort_values("date", ascending=False).reset_index(drop=True)

    def get_latest_fundamental(self, symbol: str) -> dict:
        """
        获取最新一期基本面数据

        Args:
            symbol: 股票代码

        Returns:
            dict: 最新基本面数据
        """
        df = self.wind_reader.read_latest_derivative_indicators(symbols=[symbol])
        if df.empty:
            return None

        row = df.iloc[0]
        fundamental_date = pd.to_datetime(row.get('date'), errors='coerce')
        return {
            'symbol': row.get('symbol'),
            'date': fundamental_date.date() if not pd.isna(fundamental_date) else None,
            'pe_ratio': row.get('pe_ratio'),
            'pb_ratio': row.get('pb_ratio'),
            'ps_ratio': row.get('ps_ratio'),
            'roe': None,
            'roa': None,
            'profit_margin': None,
            'operating_margin': None,
            'debt_ratio': None,
            'current_ratio': None,
            'total_mv': row.get('total_mv'),
            'circ_mv': row.get('circ_mv'),
            'pe_ttm': row.get('pe_ttm'),
            'ps_ttm': row.get('ps_ttm'),
            'turnover_rate': row.get('turnover_rate'),
            'free_turnover_rate': row.get('free_turnover_rate'),
        }

    def get_stock_latest_fundamental_date(self, symbol: str) -> Optional[date]:
        """
        获取指定股票的基本面数据最新日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        fundamental = self.get_latest_fundamental(symbol)
        return fundamental.get('date') if fundamental else None

    def get_stock_fundamental_count(self, symbol: str) -> int:
        """
        获取指定股票的基本面数据记录数量

        Args:
            symbol: 股票代码

        Returns:
            记录数量
        """
        df = self.wind_reader.read_query(
            """
            SELECT COUNT(*) AS cnt
            FROM ASHAREEODDERIVATIVEINDICATOR
            WHERE S_INFO_WINDCODE = %s
            """,
            [symbol],
        )
        if df.empty:
            return 0
        return int(df.iloc[0].get("cnt") or 0)

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

        df = self.wind_reader.read_latest_derivative_indicators(symbols=symbols)
        if df.empty:
            return pd.DataFrame(columns=["symbol", "pe", "pb"])

        return (
            df.rename(columns={"pe_ratio": "pe", "pb_ratio": "pb"})[
                ["symbol", "pe", "pb"]
            ]
            .sort_values("symbol")
            .reset_index(drop=True)
        )

    def cleanup_old_fundamental(self, keep_days: int = 30):
        """
        清理旧的基本面数据

        Args:
            keep_days: 保留天数
        """
        self._mirror_removed("stock_fundamental_daily 清理接口")

    # ==================== 代码管理 ====================

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
        搜索股票代码

        Args:
            search: 搜索关键词（模糊匹配 symbol）
            limit: 最大返回数量（默认100）

        Returns:
            List[str]: 匹配的股票代码列表
        """
        with self.get_session() as session:
            stock_query = session.query(StockCode.symbol)
            if search:
                stock_query = stock_query.filter(StockCode.symbol.ilike(f'%{search}%'))
            stock_query = stock_query.order_by(StockCode.symbol).limit(limit)

            return [r[0] for r in stock_query.all()]

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

    def clear_stock_codes(self):
        """清空股票代码表(用于强制重新初始化)"""
        with self.get_session() as session:
            count = session.query(StockCode).delete()
            logger.info(f'清空股票代码表: {count}条记录')

    def get_code_count(self, table: str = 'stock') -> dict:
        """
        获取代码表记录数

        Args:
            table: 兼容参数，目前仅统计 'stock'

        Returns:
            dict: {'stock': M}
        """
        with self.get_session() as session:
            return {'stock': session.query(StockCode).count()}

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
        获取数据库中所有股票代码

        Returns:
            List[str]: 股票代码列表
        """
        df = self.wind_reader.read_query(
            """
            SELECT DISTINCT S_INFO_WINDCODE AS symbol
            FROM ASHAREEODPRICES
            WHERE S_INFO_WINDCODE IS NOT NULL
            ORDER BY S_INFO_WINDCODE
            """,
            [],
        )
        if df.empty:
            return []
        return df["symbol"].dropna().astype(str).tolist()

    def get_statistics(self) -> dict:
        """
        获取数据库统计信息

        Returns:
            dict: 统计信息
        """
        df = self.wind_reader.read_query(
            """
            SELECT
                COUNT(DISTINCT S_INFO_WINDCODE) AS total_symbols,
                COUNT(*) AS total_records,
                MIN(TRADE_DT) AS earliest_date,
                MAX(TRADE_DT) AS latest_date
            FROM ASHAREEODPRICES
            """,
            [],
        )
        if df.empty:
            return {
                'total_symbols': 0,
                'total_records': 0,
                'earliest_date': None,
                'latest_date': None,
            }

        row = df.iloc[0]
        earliest_date = pd.to_datetime(row.get("earliest_date"), format="%Y%m%d", errors="coerce")
        latest_date = pd.to_datetime(row.get("latest_date"), format="%Y%m%d", errors="coerce")
        return {
            'total_symbols': int(row.get('total_symbols') or 0),
            'total_records': int(row.get('total_records') or 0),
            'earliest_date': earliest_date.date() if not pd.isna(earliest_date) else None,
            'latest_date': latest_date.date() if not pd.isna(latest_date) else None,
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
            asset_type: 资产类型，当前使用 'ashare'
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
            asset_type: 资产类型，当前使用 'ashare'

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

_db_instance = None


def get_db(*_args, **_kwargs) -> DatabaseManager:
    """
    获取 Database 数据库单例

    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


def close_all_connections():
    """关闭所有数据库连接"""
    global _db_instance
    if _db_instance:
        _db_instance = None
    logger.info('所有数据库连接已关闭')
