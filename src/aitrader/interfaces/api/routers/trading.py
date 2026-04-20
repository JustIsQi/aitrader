from fastapi import APIRouter, HTTPException
from typing import List

from aitrader.interfaces.api.dependencies import get_trading_service
from aitrader.interfaces.api.schemas import PositionResponse, TradingRecord, TransactionResponse

router = APIRouter()


@router.post('/record', response_model=dict)
async def add_trading_record(record: TradingRecord):
    try:
        return get_trading_service().add_record(record)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/transactions', response_model=List[TransactionResponse])
async def get_transactions(symbol: str = None, start_date: str = None, end_date: str = None, limit: int = 100):
    try:
        return get_trading_service().transactions(symbol, start_date, end_date, limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/positions', response_model=List[PositionResponse])
async def get_positions():
    try:
        return get_trading_service().positions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/strategies', response_model=List[str])
async def get_strategies():
    try:
        return get_trading_service().strategies()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/recalculate-positions', response_model=dict)
async def recalculate_positions():
    try:
        return get_trading_service().recalculate_positions()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/codes')
async def get_trading_codes(search: str = None, limit: int = 100):
    try:
        return get_trading_service().codes(search, limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
