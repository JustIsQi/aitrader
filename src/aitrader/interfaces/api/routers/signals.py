from fastapi import APIRouter, HTTPException
from typing import List

from aitrader.interfaces.api.dependencies import get_signals_service
from aitrader.interfaces.api.schemas import SignalResponse

router = APIRouter()


@router.get('/latest', response_model=List[SignalResponse])
async def get_latest_signals(limit: int = 10):
    try:
        return get_signals_service().latest(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/by-date/{signal_date}', response_model=List[SignalResponse])
async def get_signals_by_date(signal_date: str):
    try:
        return get_signals_service().by_date(signal_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/by-symbol/{symbol}', response_model=List[SignalResponse])
async def get_signals_by_symbol(symbol: str, start_date: str = None, end_date: str = None):
    try:
        return get_signals_service().by_symbol(symbol, start_date, end_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/history/grouped')
async def get_signals_history_grouped(start_date: str = None, end_date: str = None):
    try:
        return get_signals_service().grouped_history(start_date=start_date, end_date=end_date)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/ashare/latest')
async def get_latest_ashare_signals(limit: int = 50):
    try:
        return get_signals_service().latest_ashare(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/ashare/backtest/{backtest_id}')
async def get_backtest_detail(backtest_id: int):
    backtest = get_signals_service().backtest_detail(backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail='Backtest not found')
    return backtest


@router.get('/backtest/{backtest_id}')
async def get_backtest_by_id_universal(backtest_id: int):
    backtest = get_signals_service().backtest_detail(backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail='Backtest not found')
    return backtest
