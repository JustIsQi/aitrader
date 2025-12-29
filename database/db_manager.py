"""
DuckDB 数据库管理器
用于存储和管理 ETF/股票历史数据
"""
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger
import time


class DuckDBManager:
    """DuckDB 数据库管理器"""

    def __init__(self, db_path='/data/home/yy/data/duckdb/trading.db', read_only=False, max_retries=3, retry_delay=2):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
            read_only: 是否以只读模式连接
            max_retries: 写入连接的最大重试次数
            retry_delay: 重试间隔(秒)
        """
        self.db_path = db_path
        self.read_only = read_only
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 创建连接，带重试机制
        if read_only:
            # 只读连接不需要重试
            self.conn = duckdb.connect(db_path, read_only=True)
            logger.info(f'DuckDB 数据库已连接: {db_path} (read_only=True)')
        else:
            # 读写连接需要获取锁，可能需要重试
            for attempt in range(max_retries):
                try:
                    # DuckDB 不支持真正的并发写入
                    # 使用默认配置，单写入者模式
                    self.conn = duckdb.connect(db_path)
                    logger.info(f'DuckDB 数据库已连接: {db_path} (read_only=False)')
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f'数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}')
                        logger.info(f'{retry_delay}秒后重试...')
                        time.sleep(retry_delay)
                    else:
                        logger.error(f'数据库连接失败，已达最大重试次数: {e}')
                        raise

        # 初始化表结构 (只在非只读模式下)
        if not read_only:
            self._init_tables()

    def _init_tables(self):
        """初始化数据库表结构"""
        # 创建 ETF 历史数据表
        self.conn.sql("""
            CREATE SEQUENCE IF NOT EXISTS seq_etf_history START 1;
        """)

        self.conn.sql("""
            CREATE TABLE IF NOT EXISTS etf_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_etf_history'),
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount DOUBLE,
                amplitude DOUBLE,
                change_pct DOUBLE,
                change_amount DOUBLE,
                turnover_rate DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            );
        """)

        # 创建索引以提高查询性能
        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_etf_history_symbol_date
            ON etf_history(symbol, date DESC);
        """)

        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_etf_history_date
            ON etf_history(date DESC);
        """)

        # 创建股票历史数据表
        self.conn.sql("""
            CREATE SEQUENCE IF NOT EXISTS seq_stock_history START 1;
        """)

        self.conn.sql("""
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_stock_history'),
                symbol VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount DOUBLE,
                amplitude DOUBLE,
                change_pct DOUBLE,
                change_amount DOUBLE,
                turnover_rate DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            );
        """)

        # 创建股票表索引
        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_stock_history_symbol_date
            ON stock_history(symbol, date DESC);
        """)

        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_stock_history_date
            ON stock_history(date DESC);
        """)

        # 创建交易记录表
        self.conn.sql("""
            CREATE SEQUENCE IF NOT EXISTS seq_transactions START 1;
        """)

        self.conn.sql("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_transactions'),
                symbol VARCHAR(20) NOT NULL,
                buy_sell VARCHAR(10) NOT NULL,
                quantity DOUBLE NOT NULL,
                price DOUBLE NOT NULL,
                trade_date DATE NOT NULL,
                strategy_name VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_transactions_symbol_date
            ON transactions(symbol, trade_date DESC);
        """)

        # 创建持仓表
        self.conn.sql("""
            CREATE TABLE IF NOT EXISTS positions (
                symbol VARCHAR(20) PRIMARY KEY,
                quantity DOUBLE NOT NULL,
                avg_cost DOUBLE NOT NULL,
                current_price DOUBLE,
                market_value DOUBLE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 创建交易信号表
        self.conn.sql("""
            CREATE SEQUENCE IF NOT EXISTS seq_trader START 1;
        """)

        self.conn.sql("""
            CREATE TABLE IF NOT EXISTS trader (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_trader'),
                symbol VARCHAR(20) NOT NULL,
                signal_type VARCHAR(10) NOT NULL,
                strategies VARCHAR(500),
                signal_date DATE NOT NULL,
                price DOUBLE,
                score DOUBLE,
                rank INTEGER,
                quantity INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, signal_date, signal_type)
            );
        """)

        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_trader_signal_date
            ON trader(signal_date DESC);
        """)

        self.conn.sql("""
            CREATE INDEX IF NOT EXISTS idx_trader_symbol_date
            ON trader(symbol, signal_date DESC);
        """)

        logger.info('数据库表结构初始化完成')

    # ==================== 股票数据操作 ====================

    def insert_stock_history(self, df: pd.DataFrame, symbol: str = None):
        """
        插入或更新股票历史数据

        Args:
            df: 包含历史数据的 DataFrame
                  列名要求: date, open, high, low, close, volume, amount
            symbol: 股票代码（如果 df 中没有 symbol 列）
        """
        try:
            # 确保有 symbol 列
            if symbol and 'symbol' not in df.columns:
                df = df.copy()
                df['symbol'] = symbol

            # 转换日期格式（自动检测格式）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['date'] = df['date'].dt.date

            # 删除原有的重复数据
            if symbol:
                self.conn.sql(f"DELETE FROM stock_history WHERE symbol = '{symbol}'")

            # 确保只包含表中存在的列（排除 id 和 created_at）
            required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                              'amplitude', 'change_pct', 'change_amount', 'turnover_rate']

            # 过滤出实际存在的列
            available_columns = [col for col in required_columns if col in df.columns]

            # 构建插入语句，明确指定列名
            columns_str = ', '.join(available_columns)
            self.conn.sql(f'INSERT INTO stock_history ({columns_str}) SELECT {columns_str} FROM df')

            logger.info(f'成功插入 {len(df)} 条 {symbol} 历史数据')
            return True

        except Exception as e:
            logger.error(f'插入数据失败: {e}')
            return False

    def append_stock_history(self, df: pd.DataFrame, symbol: str):
        """
        追加新的股票历史数据（只插入不存在的记录）

        Args:
            df: 新的数据 DataFrame
            symbol: 股票代码
        """
        try:
            # 确保有 symbol 列
            df = df.copy()
            df['symbol'] = symbol

            # 转换日期格式（自动检测格式）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['date'] = df['date'].dt.date

            # 选择所有可能的列
            all_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                          'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
            df = df[[col for col in all_columns if col in df.columns]]

            # 使用 INSERT OR IGNORE 避免重复，明确指定列名
            self.conn.sql("""
                INSERT OR IGNORE INTO stock_history
                (symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate)
                SELECT symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate FROM df
            """)

            logger.info(f'成功追加 {len(df)} 条 {symbol} 数据')
            return True

        except Exception as e:
            logger.error(f'追加数据失败: {e}')
            return False

    def get_stock_history(self, symbol: str, start_date=None, end_date=None) -> pd.DataFrame:
        """
        获取股票历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame: 历史数据
        """
        query = f"SELECT * FROM stock_history WHERE symbol = '{symbol}'"

        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"

        query += " ORDER BY date ASC"

        return self.conn.sql(query).df()

    def get_stock_latest_date(self, symbol: str) -> datetime:
        """
        获取指定股票的最新数据日期

        Args:
            symbol: 股票代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        result = self.conn.sql(f"""
            SELECT MAX(date) as latest_date
            FROM stock_history
            WHERE symbol = '{symbol}'
        """).df()

        latest_date = result['latest_date'].iloc[0]
        if pd.notna(latest_date):
            return pd.to_datetime(latest_date)
        return None

    def insert_etf_history(self, df: pd.DataFrame, symbol: str = None):
        """
        插入或更新 ETF 历史数据

        Args:
            df: 包含历史数据的 DataFrame
                  列名要求: date, open, high, low, close, volume, amount
            symbol: ETF 代码（如果 df 中没有 symbol 列）
        """
        try:
            # 确保有 symbol 列
            if symbol and 'symbol' not in df.columns:
                df = df.copy()
                df['symbol'] = symbol

            # 转换日期格式（自动检测格式）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['date'] = df['date'].dt.date

            # 删除原有的重复数据（使用 INSERT OR REPLACE 的逻辑）
            if symbol:
                self.conn.sql(f"DELETE FROM etf_history WHERE symbol = '{symbol}'")

            # 确保只包含表中存在的列（排除 id 和 created_at）
            required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                              'amplitude', 'change_pct', 'change_amount', 'turnover_rate']

            # 过滤出实际存在的列
            available_columns = [col for col in required_columns if col in df.columns]

            # 构建插入语句，明确指定列名
            columns_str = ', '.join(available_columns)
            self.conn.sql(f'INSERT INTO etf_history ({columns_str}) SELECT {columns_str} FROM df')

            logger.info(f'成功插入 {len(df)} 条 {symbol} 历史数据')
            return True

        except Exception as e:
            logger.error(f'插入数据失败: {e}')
            return False

    def append_etf_history(self, df: pd.DataFrame, symbol: str):
        """
        追加新的历史数据（只插入不存在的记录）

        Args:
            df: 新的数据 DataFrame
            symbol: ETF 代码
        """
        try:
            # 确保有 symbol 列
            df = df.copy()
            df['symbol'] = symbol

            # 转换日期格式（自动检测格式）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['date'] = df['date'].dt.date

            # 选择所有可能的列
            all_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount',
                          'amplitude', 'change_pct', 'change_amount', 'turnover_rate']
            df = df[[col for col in all_columns if col in df.columns]]

            # 使用 INSERT OR IGNORE 避免重复，明确指定列名
            self.conn.sql("""
                INSERT OR IGNORE INTO etf_history
                (symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate)
                SELECT symbol, date, open, high, low, close, volume, amount, amplitude, change_pct, change_amount, turnover_rate FROM df
            """)

            logger.info(f'成功追加 {len(df)} 条 {symbol} 数据')
            return True

        except Exception as e:
            logger.error(f'追加数据失败: {e}')
            return False

    def get_etf_history(self, symbol: str, start_date=None, end_date=None) -> pd.DataFrame:
        """
        获取 ETF 历史数据

        Args:
            symbol: ETF 代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            DataFrame: 历史数据
        """
        query = f"SELECT * FROM etf_history WHERE symbol = '{symbol}'"

        if start_date:
            query += f" AND date >= '{start_date}'"
        if end_date:
            query += f" AND date <= '{end_date}'"

        query += " ORDER BY date ASC"

        return self.conn.sql(query).df()

    def get_latest_date(self, symbol: str) -> datetime:
        """
        获取指定 ETF 的最新数据日期

        Args:
            symbol: ETF 代码

        Returns:
            最新日期，如果没有数据则返回 None
        """
        result = self.conn.sql(f"""
            SELECT MAX(date) as latest_date
            FROM etf_history
            WHERE symbol = '{symbol}'
        """).df()

        latest_date = result['latest_date'].iloc[0]
        if pd.notna(latest_date):
            return pd.to_datetime(latest_date)
        return None

    def get_all_symbols(self) -> list:
        """获取数据库中所有 ETF 代码"""
        result = self.conn.sql("""
            SELECT DISTINCT symbol
            FROM etf_history
            ORDER BY symbol
        """).df()
        return result['symbol'].tolist()

    def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        stats = self.conn.sql("""
            SELECT
                COUNT(DISTINCT symbol) as total_symbols,
                COUNT(*) as total_records,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM etf_history
        """).df()

        return {
            'total_symbols': stats['total_symbols'].iloc[0],
            'total_records': stats['total_records'].iloc[0],
            'earliest_date': stats['earliest_date'].iloc[0],
            'latest_date': stats['latest_date'].iloc[0]
        }

    def insert_transaction(self, symbol: str, buy_sell: str, quantity: float,
                          price: float, trade_date: str, strategy_name: str = None):
        """
        插入交易记录

        Args:
            symbol: ETF 代码
            buy_sell: 'buy' 或 'sell'
            quantity: 数量
            price: 价格
            trade_date: 交易日期 (YYYY-MM-DD)
            strategy_name: 策略名称
        """
        self.conn.sql(f"""
            INSERT INTO transactions
            (symbol, buy_sell, quantity, price, trade_date, strategy_name)
            VALUES
            ('{symbol}', '{buy_sell}', {quantity}, {price}, '{trade_date}', '{strategy_name or ''}')
        """)
        logger.info(f'记录交易: {buy_sell} {symbol} {quantity}股 @{price}')

    def get_transactions(self, symbol: str = None, start_date=None, end_date=None) -> pd.DataFrame:
        """获取交易记录"""
        query = "SELECT * FROM transactions WHERE 1=1"

        if symbol:
            query += f" AND symbol = '{symbol}'"
        if start_date:
            query += f" AND trade_date >= '{start_date}'"
        if end_date:
            query += f" AND trade_date <= '{end_date}'"

        query += " ORDER BY trade_date DESC, id DESC"

        return self.conn.sql(query).df()

    def update_position(self, symbol: str, quantity: float, avg_cost: float, current_price: float = None):
        """
        更新持仓信息

        Args:
            symbol: ETF 代码
            quantity: 持仓数量
            avg_cost: 平均成本
            current_price: 当前价格
        """
        market_value = quantity * current_price if current_price else None
        updated_at = datetime.now()

        self.conn.sql(f"""
            INSERT INTO positions (symbol, quantity, avg_cost, current_price, market_value, updated_at)
            VALUES ('{symbol}', {quantity}, {avg_cost}, {current_price or 'NULL'}, {market_value or 'NULL'}, '{updated_at}')
            ON CONFLICT (symbol) DO UPDATE SET
                quantity = excluded.quantity,
                avg_cost = excluded.avg_cost,
                current_price = excluded.current_price,
                market_value = excluded.market_value,
                updated_at = excluded.updated_at
        """)

    def get_positions(self) -> pd.DataFrame:
        """获取当前所有持仓"""
        return self.conn.sql("""
            SELECT * FROM positions
            WHERE quantity > 0
            ORDER BY market_value DESC
        """).df()

    def clear_transactions(self):
        """清空交易记录表"""
        self.conn.sql("DELETE FROM transactions")
        logger.info('已清空交易记录表')

    def clear_positions(self):
        """清空持仓表"""
        self.conn.sql("DELETE FROM positions")
        logger.info('已清空持仓表')

    def clear_trading_data(self):
        """清空所有交易相关数据（交易记录和持仓）"""
        self.clear_positions()
        self.clear_transactions()
        logger.info('已清空所有交易数据')

    # ==================== 交易信号操作 ====================

    def insert_trader_signal(self, symbol: str, signal_type: str,
                          strategies: list, signal_date: str,
                          price: float = None, score: float = None,
                          rank: int = None, quantity: int = None):
        """
        插入或更新交易信号

        Args:
            symbol: ETF代码
            signal_type: 'buy' 或 'sell'
            strategies: 策略名称列表
            signal_date: 信号日期 (YYYY-MM-DD)
            price: 当前价格
            score: 信号评分（买入信号）
            rank: 信号排名（买入信号）
            quantity: 建议数量（买入信号）
        """
        from typing import List

        strategies_str = ','.join(strategies) if strategies else None

        self.conn.sql(f"""
            INSERT INTO trader
            (symbol, signal_type, strategies, signal_date, price, score, rank, quantity)
            VALUES ('{symbol}', '{signal_type}', '{strategies_str or ''}',
                    '{signal_date}', {price or 'NULL'}, {score or 'NULL'},
                    {rank or 'NULL'}, {quantity or 'NULL'})
            ON CONFLICT (symbol, signal_date, signal_type) DO UPDATE SET
                strategies = excluded.strategies,
                price = excluded.price,
                score = excluded.score,
                rank = excluded.rank,
                quantity = excluded.quantity,
                created_at = excluded.created_at
        """)
        logger.info(f'记录交易信号: {signal_type} {symbol} - {strategies_str}')

    def get_latest_trader_signals(self, limit: int = 10) -> pd.DataFrame:
        """
        获取最新的交易信号

        Args:
            limit: 返回的最大信号数量

        Returns:
            包含最新信号的DataFrame
        """
        return self.conn.sql(f"""
            SELECT * FROM trader
            ORDER BY signal_date DESC, created_at DESC
            LIMIT {limit}
        """).df()

    def get_trader_signals_by_date(self, signal_date: str) -> pd.DataFrame:
        """
        获取指定日期的交易信号

        Args:
            signal_date: 信号日期 (YYYY-MM-DD)

        Returns:
            包含指定日期信号的DataFrame
        """
        return self.conn.sql(f"""
            SELECT * FROM trader
            WHERE signal_date = '{signal_date}'
            ORDER BY signal_type, symbol
        """).df()

    def get_trader_signals_by_symbol(self, symbol: str,
                                     start_date: str = None,
                                     end_date: str = None) -> pd.DataFrame:
        """
        获取指定标的的交易信号

        Args:
            symbol: ETF代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            包含指定标的信号的DataFrame
        """
        query = f"SELECT * FROM trader WHERE symbol = '{symbol}'"

        if start_date:
            query += f" AND signal_date >= '{start_date}'"
        if end_date:
            query += f" AND signal_date <= '{end_date}'"

        query += " ORDER BY signal_date DESC"

        return self.conn.sql(query).df()

    def calculate_profit_loss(self) -> dict:
        """
        计算盈亏统计

        Returns:
            包含盈亏指标的字典
        """
        # 已实现盈亏（来自已平仓交易）
        realized_pl = self.conn.sql("""
            SELECT
                SUM(CASE WHEN buy_sell = 'sell'
                    THEN quantity * price
                    ELSE 0 END) as total_sold,
                SUM(CASE WHEN buy_sell = 'buy'
                    THEN quantity * price
                    ELSE 0 END) as total_bought
            FROM transactions
        """).df()

        # 未实现盈亏（来自当前持仓）
        positions = self.get_positions()
        if not positions.empty:
            unrealized_pl = {
                'total_unrealized_pl': ((positions['current_price'] - positions['avg_cost']) *
                                       positions['quantity']).sum(),
                'total_market_value': positions['market_value'].sum(),
                'total_cost': (positions['avg_cost'] * positions['quantity']).sum()
            }
        else:
            unrealized_pl = {
                'total_unrealized_pl': 0,
                'total_market_value': 0,
                'total_cost': 0
            }

        return {
            'realized_pl': realized_pl['total_sold'].iloc[0] - realized_pl['total_bought'].iloc[0],
            **unrealized_pl
        }

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
        logger.info('数据库连接已关闭')

    def __del__(self):
        """析构函数，自动关闭连接"""
        try:
            self.close()
        except:
            pass


# 全局连接管理（单例模式）
_db_instance = None


def get_db(db_path='/data/home/yy/data/duckdb/trading.db') -> DuckDBManager:
    """
    获取数据库单例实例

    Args:
        db_path: 数据库文件路径

    Returns:
        DuckDBManager 实例

    Note:
        由于 DuckDB 的限制，使用全局单例模式
        所有连接共享同一个数据库实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DuckDBManager(db_path)
    return _db_instance


def close_all_connections():
    """关闭数据库连接"""
    global _db_instance
    if _db_instance:
        try:
            _db_instance.close()
        except:
            pass
        _db_instance = None
        logger.info('数据库连接已关闭')


if __name__ == '__main__':
    # 测试代码
    db = get_db()

    # 打印统计信息
    stats = db.get_statistics()
    print('数据库统计信息:')
    print(f"  ETF 数量: {stats['total_symbols']}")
    print(f"  总记录数: {stats['total_records']}")
    print(f"  数据范围: {stats['earliest_date']} ~ {stats['latest_date']}")

    # 获取所有 ETF
    symbols = db.get_all_symbols()
    print(f'\n所有 ETF: {symbols}')
