from fastapi import APIRouter, HTTPException

from aitrader.interfaces.api.dependencies import get_analytics_service
from aitrader.interfaces.api.schemas import ProfitLossResponse

router = APIRouter()


@router.get('/profit-loss', response_model=ProfitLossResponse)
async def get_profit_loss():
    try:
        return get_analytics_service().profit_loss()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/performance')
async def get_performance_metrics():
    try:
        return get_analytics_service().performance()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/historical-pl')
async def get_historical_pl():
    try:
        return get_analytics_service().historical_pl()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
