from fastapi import APIRouter, HTTPException
from typing import List

from aitrader.interfaces.api.dependencies import get_short_term_service
from aitrader.interfaces.api.schemas import BacktestResultResponse, DailyOperationListResponse, SectorDataResponse

router = APIRouter(prefix='/short-term', tags=['short-term'])


@router.get('/daily-operation-list/latest', response_model=List[DailyOperationListResponse])
async def get_latest_daily_operation_list(limit: int = 50):
    try:
        return get_short_term_service().latest_daily_operation_list(limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/daily-operation-list/by-date/{date}', response_model=List[DailyOperationListResponse])
async def get_daily_operation_list_by_date(date: str):
    try:
        return get_short_term_service().daily_operation_list_by_date(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='日期格式错误,请使用 YYYY-MM-DD 格式') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/sectors/latest', response_model=List[SectorDataResponse])
async def get_latest_sectors(limit: int = 10):
    try:
        return get_short_term_service().latest_sectors(limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/sectors/by-date/{date}', response_model=List[SectorDataResponse])
async def get_sectors_by_date(date: str):
    try:
        return get_short_term_service().sectors_by_date(date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='日期格式错误') from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/backtest/latest', response_model=List[BacktestResultResponse])
async def get_latest_backtests(limit: int = 10):
    try:
        return get_short_term_service().latest_backtests(limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/backtest/{backtest_id}')
async def get_backtest_result(backtest_id: int):
    backtest = get_short_term_service().backtest_by_id(backtest_id)
    if not backtest:
        raise HTTPException(status_code=404, detail='回测不存在')
    return backtest


@router.get('/summary')
async def get_summary():
    try:
        return get_short_term_service().summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
