"""
SQLAlchemy ORM Models for AITrader Database Database
All models mirror the existing DuckDB schema
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text, UniqueConstraint, Index, ForeignKey, JSON
from sqlalchemy.sql import func
from aitrader.infrastructure.db.models.base import Base


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
    asset_type = Column(String(20), nullable=False)  # 'ashare'
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
    asset_type = Column(String(20), nullable=False)  # 'ashare'

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
    final_holdings = Column(JSON)  # 最后一天持仓 [{'symbol': '000001.SZ', 'shares': 100, 'weight': 0.25}]

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


# ==================== 短线选股量化分析系统数据表 ====================

class SectorData(Base):
    """板块数据表 - 短线选股系统"""
    __tablename__ = 'sector_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    sector_code = Column(String(20), nullable=False)
    sector_name = Column(String(100))

    # 资金指标
    main_net_inflow_1d = Column(Float)  # 1日主力净流入(万元)
    main_net_inflow_3d = Column(Float)  # 3日主力净流入(万元)
    main_net_inflow_5d = Column(Float)  # 5日主力净流入(万元)
    volume_expansion_ratio = Column(Float)  # 成交额放量率 (当日/近5日均值)
    northbound_buy_ratio = Column(Float)  # 北向增持比例

    # 情绪指标
    limit_up_count = Column(Integer)  # 当日涨停家数
    consecutive_board_count = Column(Integer)  # 连板家数
    rank_3d_gain = Column(Integer)  # 3日涨跌幅排名

    # 技术指标
    close = Column(Float)  # 板块指数收盘价
    ma5 = Column(Float)  # 5日均线
    ma10 = Column(Float)  # 10日均线
    rsi = Column(Float)  # RSI指标

    # 综合评分
    strength_score = Column(Float)  # 综合强度得分

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'sector_code', name='uix_sector_date'),
        Index('idx_sector_date', 'date'),
        Index('idx_sector_score', 'strength_score'),
    )


class DailyOperationList(Base):
    """每日操作清单表 - 短线选股系统核心输出"""
    __tablename__ = 'daily_operation_list'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)

    # 板块信息
    sector_name = Column(String(100), nullable=False)
    sector_rank = Column(Integer)  # 板块强度排名 (1-5)

    # 股票信息
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))

    # 策略信息
    strategy_type = Column(String(20))  # 'chase'(追涨) or 'dip'(低吸)

    # 仓位与风险管理
    position_ratio = Column(Float)  # 仓位比例 (0-1)
    stop_loss_price = Column(Float)  # 止损价
    take_profit_price = Column(Float)  # 止盈价

    # 开盘触发阈值
    open_trigger_high_pct = Column(Float)  # 高开阈值 (%)
    open_trigger_seal_ratio = Column(Float)  # 封单量占流通盘比例
    open_trigger_auction_amount = Column(Float)  # 竞价成交额(元)

    # 信号强度
    strength_score = Column(Float)  # 选股得分

    # 执行状态
    is_executed = Column(Boolean, default=False)  # 是否已执行
    executed_price = Column(Float)  # 实际执行价格
    executed_time = Column(DateTime)  # 执行时间

    # 结果追踪
    actual_return_pct = Column(Float)  # 实际收益率(平仓时填写)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'stock_code', name='uix_daily_op_stock'),
        Index('idx_daily_op_date', 'date'),
        Index('idx_daily_op_sector', 'sector_name'),
        Index('idx_daily_op_executed', 'is_executed'),
    )


class StockRiskData(Base):
    """个股风险数据表 - 短线选股系统"""
    __tablename__ = 'stock_risk_data'

    stock_code = Column(String(20), primary_key=True)

    # 风险标记
    is_loss_maker = Column(Boolean, default=False)  # 业绩亏损
    has_reduction_announcement = Column(Boolean, default=False)  # 减持公告
    is_suspended = Column(Boolean, default=False)  # 停牌

    # 公告详情
    latest_announcement_date = Column(Date)
    announcement_summary = Column(Text)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockSelectionDetail(Base):
    """个股选股详情表 - 短线选股系统"""
    __tablename__ = 'stock_selection_detail'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    stock_code = Column(String(20), nullable=False)

    # 选股指标
    close_price_5d_high = Column(Boolean)  # 收盘价创5日新高
    is_limit_up = Column(Boolean)  # 涨停状态
    consecutive_boards = Column(Integer)  # 连板数(1-2)
    main_net_inflow = Column(Float)  # 主力净流入(万元)
    volume_ratio = Column(Float)  # 量比

    # 低吸策略指标
    close_ma_deviation_5d = Column(Float)  # 收盘价偏离5日线幅度(%)
    macd_golden_cross = Column(Boolean)  # MACD金叉
    volume_ratio_5d = Column(Float)  # 成交量与5日均值比值

    # 市值数据
    float_market_cap = Column(Float)  # 流通市值(亿元)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('date', 'stock_code', name='uix_selection_detail'),
        Index('idx_selection_date', 'date'),
    )


class ShortTermBacktest(Base):
    """短线回测结果表 - 短线选股系统"""
    __tablename__ = 'short_term_backtests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(100), nullable=False)

    # 回测周期
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # 配置 (JSON存储)
    sector_config = Column(JSON)  # 板块筛选配置
    stock_config = Column(JSON)  # 个股选股配置
    position_config = Column(JSON)  # 仓位管理配置
    risk_config = Column(JSON)  # 风险过滤配置

    # 绩效指标
    win_rate = Column(Float)  # 胜率
    profit_loss_ratio = Column(Float)  # 盈亏比
    max_drawdown = Column(Float)  # 最大回撤
    avg_return_per_trade = Column(Float)  # 单笔平均收益
    total_trades = Column(Integer)  # 总交易次数
    avg_holding_days = Column(Float)  # 平均持仓天数

    # 无效场景统计
    invalid_no_signal = Column(Integer)  # 无信号次数
    invalid_risk_filter = Column(Integer)  # 风险过滤次数
    invalid_sector_not_selected = Column(Integer)  # 板块未入选次数

    # 详细结果
    equity_curve = Column(JSON)  # 权益曲线 [{date, value}]
    trade_list = Column(JSON)  # 交易列表

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('strategy_name', 'start_date', 'end_date', name='uix_short_backtest'),
        Index('idx_short_backtest_date', 'start_date', 'end_date'),
    )
