"""
SQLAlchemy ORM Models for AITrader PostgreSQL Database
All models mirror the existing DuckDB schema
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, UniqueConstraint, Index, ForeignKey, JSON
from sqlalchemy.sql import func
from database.models.base import Base


class EtfHistory(Base):
    """ETF历史数据表"""
    __tablename__ = 'etf_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    amplitude = Column(Float)
    change_pct = Column(Float)
    change_amount = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_etf_symbol_date'),
        Index('idx_etf_symbol_date', 'symbol', 'date'),
        Index('idx_etf_date', 'date'),
    )


class StockHistory(Base):
    """股票历史数据表"""
    __tablename__ = 'stock_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    amplitude = Column(Float)
    change_pct = Column(Float)
    change_amount = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_stock_symbol_date'),
        Index('idx_stock_symbol_date', 'symbol', 'date'),
        Index('idx_stock_date', 'date'),
    )


class StockMetadata(Base):
    """股票元数据表"""
    __tablename__ = 'stock_metadata'

    symbol = Column(String(20), primary_key=True)
    name = Column(String(100))
    sector = Column(String(50))
    industry = Column(String(50))
    list_date = Column(Date)
    is_st = Column(Boolean, default=False)
    is_suspend = Column(Boolean, default=False)
    is_new_ipo = Column(Boolean, default=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockFundamentalDaily(Base):
    """股票基本面数据表"""
    __tablename__ = 'stock_fundamental_daily'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    ps_ratio = Column(Float)
    roe = Column(Float)
    roa = Column(Float)
    profit_margin = Column(Float)
    operating_margin = Column(Float)
    debt_ratio = Column(Float)
    current_ratio = Column(Float)
    total_mv = Column(Float)
    circ_mv = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_fundamental_symbol_date'),
        Index('idx_fundamental_symbol_date', 'symbol', 'date'),
        Index('idx_fundamental_date', 'date'),
    )


class Trader(Base):
    """交易信号表"""
    __tablename__ = 'trader'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    strategies = Column(Text)
    signal_date = Column(Date, nullable=False)
    price = Column(Float)
    score = Column(Float)
    rank = Column(Integer)
    quantity = Column(Integer)
    asset_type = Column(String(20), nullable=False)  # 'etf' or 'ashare'
    backtest_metrics = Column(JSON)  # 回测指标 (可选)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'signal_date', 'signal_type', name='uix_trader_signal'),
        Index('idx_trader_signal_date', 'signal_date'),
        Index('idx_trader_symbol_date', 'symbol', 'signal_date'),
        Index('idx_trader_asset_type', 'asset_type'),
    )


class Transaction(Base):
    """交易记录表"""
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    buy_sell = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    trade_date = Column(Date, nullable=False)
    strategy_name = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_transactions_symbol_date', 'symbol', 'trade_date'),
    )


class Position(Base):
    """持仓表"""
    __tablename__ = 'positions'

    symbol = Column(String(20), primary_key=True)
    quantity = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    current_price = Column(Float)
    market_value = Column(Float)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FactorCache(Base):
    """因子缓存表"""
    __tablename__ = 'factor_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    factor_name = Column(String(50), nullable=False)
    factor_value = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', 'factor_name', name='uix_factor_cache'),
        Index('idx_factor_symbol_date', 'symbol', 'date'),
    )


class EtfCode(Base):
    """ETF代码表"""
    __tablename__ = 'etf_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True)
    name = Column(String(100))


class StockCode(Base):
    """股票代码表"""
    __tablename__ = 'stock_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True)


class AShareStockInfo(Base):
    """A股股票信息表 (from ashare.csv)"""
    __tablename__ = 'ashare_stock_info'

    symbol = Column(String(20), primary_key=True)  # 格式: 002788.SZ
    stock_code = Column(String(20), nullable=False)  # 原始代码: 002788
    zh_company_abbr = Column(String(100), nullable=False)  # 中文简称
    exchange_name = Column(String(50), nullable=False)  # 交易所名称
    exchange_suffix = Column(String(5), nullable=False)  # SH/SZ/BJ
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StrategyBacktest(Base):
    """策略回测结果表"""
    __tablename__ = 'strategy_backtests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False)
    strategy_version = Column(String(50))  # e.g., 'weekly', 'monthly'
    asset_type = Column(String(20), nullable=False)  # 'etf' or 'ashare'

    # Backtest configuration
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Float, default=1000000)

    # Performance metrics
    total_return = Column(Float)
    annual_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)

    # Trading statistics
    total_trades = Column(Integer)
    avg_hold_days = Column(Float)
    turnover_rate = Column(Float)

    # Benchmark comparison
    benchmark_return = Column(Float)
    excess_return = Column(Float)

    # Detailed results (JSON for flexibility)
    equity_curve = Column(JSON)  # Array of {date, value}
    monthly_returns = Column(JSON)
    trade_list = Column(JSON)  # Array of trade objects

    # Portfolio backtest specific fields (组合回测特有字段)
    backtest_type = Column(String(20), default='single')  # 'single' (单一标的轮动) or 'portfolio' (组合回测)
    portfolio_config = Column(JSON)  # 组合配置 {weight_type, rebalance_freq, select_buy, select_sell}

    # Advanced performance metrics (高级绩效指标)
    sortino_ratio = Column(Float)  # Sortino比率（只考虑下行波动）
    calmar_ratio = Column(Float)  # Calmar比率（年化收益/最大回撤）
    var_95 = Column(Float)  # 95% VaR (Value at Risk)
    cvar_95 = Column(Float)  # 95% CVaR (Conditional VaR)
    information_ratio = Column(Float)  # 信息比率（相对基准的超额收益/跟踪误差）
    avg_turnover_rate = Column(Float)  # 平均换手率（滚动20日）
    win_rates = Column(JSON)  # 胜率 {'daily': 60, 'weekly': 65, 'monthly': 70}

    # Portfolio holdings (组合持仓)
    final_holdings = Column(JSON)  # 最后一天持仓 [{'symbol': '510300.SH', 'shares': 100, 'weight': 0.25}]

    # Metadata
    backtest_date = Column(DateTime, server_default=func.now())
    status = Column(String(20), default='completed')  # 'completed', 'failed', 'running'
    error_message = Column(Text)

    __table_args__ = (
        UniqueConstraint('strategy_name', 'strategy_version', 'start_date', 'end_date',
                        name='uix_backtest_strategy_period'),
        Index('idx_backtests_strategy', 'strategy_name', 'asset_type'),
        Index('idx_backtests_date', 'backtest_date'),
        Index('idx_backtests_type', 'backtest_type'),  # 新增索引：按回测类型查询
    )


class SignalBacktestAssociation(Base):
    """信号与回测的关联表"""
    __tablename__ = 'signal_backtest_associations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trader_id = Column(Integer, ForeignKey('trader.id'), nullable=False)
    backtest_id = Column(Integer, ForeignKey('strategy_backtests.id'), nullable=False)
    strategy_name = Column(String(100))  # Denormalized for faster queries
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('trader_id', 'backtest_id', name='uix_signal_backtest'),
    )


class EtfHistoryQfq(Base):
    """ETF前复权历史数据表"""
    __tablename__ = 'etf_history_qfq'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    name = Column(String(100))
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    amplitude = Column(Float)
    change_pct = Column(Float)
    change_amount = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_etf_qfq_symbol_date'),
        Index('idx_etf_qfq_symbol_date', 'symbol', 'date'),
        Index('idx_etf_qfq_date', 'date'),
    )


class StockHistoryQfq(Base):
    """股票前复权历史数据表"""
    __tablename__ = 'stock_history_qfq'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    amount = Column(Float)
    amplitude = Column(Float)
    change_pct = Column(Float)
    change_amount = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_stock_qfq_symbol_date'),
        Index('idx_stock_qfq_symbol_date', 'symbol', 'date'),
        Index('idx_stock_qfq_date', 'date'),
    )
