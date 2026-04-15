from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TradingRecord(BaseModel):
    symbol: str = Field(..., description='股票代码')
    buy_sell: str = Field(..., description='buy 或 sell')
    quantity: float = Field(..., gt=0, description='数量')
    price: float = Field(..., gt=0, description='单价')
    trade_date: date = Field(..., description='交易日期')
    strategy_name: Optional[str] = Field(None, description='策略名称')


class SignalResponse(BaseModel):
    id: int
    symbol: str
    signal_type: str
    strategies: str
    signal_date: date
    price: Optional[float]
    score: Optional[float]
    rank: Optional[int]
    quantity: Optional[int]
    created_at: str


class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    updated_at: str


class TransactionResponse(BaseModel):
    id: int
    symbol: str
    buy_sell: str
    quantity: float
    price: float
    trade_date: date
    strategy_name: Optional[str]
    created_at: str


class ProfitLossResponse(BaseModel):
    realized_pl: Optional[float] = None
    total_unrealized_pl: Optional[float] = None
    total_market_value: Optional[float] = None
    total_cost: Optional[float] = None
    total_pl: Optional[float] = None


class DailyOperationListResponse(BaseModel):
    id: int
    date: str
    sector_name: str
    sector_rank: int
    stock_code: str
    stock_name: Optional[str]
    strategy_type: str
    position_ratio: float
    stop_loss_price: float
    take_profit_price: float
    open_trigger_high_pct: float
    open_trigger_seal_ratio: float
    open_trigger_auction_amount: float
    strength_score: float
    is_executed: bool
    executed_price: Optional[float] = None
    executed_time: Optional[str] = None
    actual_return_pct: Optional[float] = None

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')}
    )


class SectorDataResponse(BaseModel):
    id: int
    date: str
    sector_code: str
    sector_name: str
    main_net_inflow_1d: float
    volume_expansion_ratio: float
    limit_up_count: int
    close: float
    ma5: float
    ma10: float
    rsi: float
    strength_score: float


class BacktestResultResponse(BaseModel):
    id: int
    strategy_name: str
    start_date: str
    end_date: str
    win_rate: float
    profit_loss_ratio: float
    max_drawdown: float
    avg_return_per_trade: float
    total_trades: int
    avg_holding_days: float
