"""
Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class TradingRecord(BaseModel):
    """交易记录模型"""
    symbol: str = Field(..., description="ETF代码")
    buy_sell: str = Field(..., description="buy 或 sell")
    quantity: float = Field(..., gt=0, description="数量")
    price: float = Field(..., gt=0, description="单价")
    trade_date: date = Field(..., description="交易日期")
    strategy_name: Optional[str] = Field(None, description="策略名称")


class SignalResponse(BaseModel):
    """信号响应模型"""
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
    """持仓响应模型"""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: Optional[float]
    market_value: Optional[float]
    updated_at: str


class TransactionResponse(BaseModel):
    """交易记录响应模型"""
    id: int
    symbol: str
    buy_sell: str
    quantity: float
    price: float
    trade_date: date
    strategy_name: Optional[str]
    created_at: str


class ProfitLossResponse(BaseModel):
    """盈亏响应模型"""
    realized_pl: Optional[float] = None
    total_unrealized_pl: Optional[float] = None
    total_market_value: Optional[float] = None
    total_cost: Optional[float] = None
    total_pl: Optional[float] = None
