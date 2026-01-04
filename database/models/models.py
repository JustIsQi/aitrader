"""
SQLAlchemy ORM Models for AITrader PostgreSQL Database
All models mirror the existing DuckDB schema
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, UniqueConstraint, Index
from sqlalchemy.sql import func
from database.models.base import Base


class EtfHistory(Base):
    """ETF历史数据表"""
    __tablename__ = 'etf_history'

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
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('symbol', 'signal_date', 'signal_type', name='uix_trader_signal'),
        Index('idx_trader_signal_date', 'signal_date'),
        Index('idx_trader_symbol_date', 'symbol', 'signal_date'),
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


class StockCode(Base):
    """股票代码表"""
    __tablename__ = 'stock_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True)
