"""
短线交易信号API端点

提供每日操作清单、强势板块、回测结果等查询接口
作者: AITrader
日期: 2026-01-21
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from database.db_manager import get_db
from loguru import logger
import pandas as pd
import numpy as np


def model_to_dict(model):
    """将SQLAlchemy模型对象转换为字典"""
    if model is None:
        return None

    result = {}
    for column in model.__table__.columns:
        key = column.name
        value = getattr(model, key)

        # 处理日期时间类型
        if isinstance(value, datetime):
            result[key] = value
        elif value is None or (isinstance(value, float) and (pd.isna(value) or np.isnan(value))):
            result[key] = None
        else:
            result[key] = value

    return result


router = APIRouter(
    prefix="/short-term",
    tags=["short-term"]
)


# ==================== Pydantic Models ====================

class DailyOperationListResponse(BaseModel):
    """每日操作清单响应模型"""
    id: int
    date: str
    sector_name: str
    sector_rank: int
    stock_code: str
    stock_name: Optional[str]
    strategy_type: str  # 'chase' or 'dip'
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

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%d %H:%M:%S')
        }


class SectorDataResponse(BaseModel):
    """板块数据响应模型"""
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
    """回测结果响应模型"""
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


# ==================== Utility Functions ====================

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清理 DataFrame 中的 NaN 值"""
    if not df.empty:
        df = df.replace({np.nan: None})
    return df


def safe_dict_value(value: Any) -> Any:
    """安全处理字典中的 NaN 值"""
    if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
        return None
    return value


# ==================== API Endpoints ====================

@router.get("/daily-operation-list/latest", response_model=List[DailyOperationListResponse])
async def get_latest_daily_operation_list(limit: int = 50):
    """
    获取最新的每日操作清单

    Args:
        limit: 返回的最大数量 (默认: 50)

    Returns:
        最新每日操作清单
    """
    try:
        db = get_db()

        with db.get_session() as session:
            from database.models.models import DailyOperationList

            # 获取最新日期
            latest_date = session.query(
                DailyOperationList.date
            ).order_by(
                DailyOperationList.date.desc()
            ).first()

            if not latest_date:
                return []

            # 获取该日期的操作清单
            query = session.query(DailyOperationList).filter(
                DailyOperationList.date == latest_date[0]
            ).order_by(
                DailyOperationList.sector_rank,
                DailyOperationList.strength_score.desc()
            ).limit(limit)

            operations = []
            for op in query.all():
                op_dict = model_to_dict(op)
                # 格式化日期
                if 'date' in op_dict and op_dict['date']:
                    op_dict['date'] = op_dict['date'].strftime('%Y-%m-%d')
                if 'executed_time' in op_dict and op_dict['executed_time']:
                    op_dict['executed_time'] = op_dict['executed_time'].strftime('%Y-%m-%d %H:%M:%S')

                # 处理position_ratio为百分比
                if 'position_ratio' in op_dict and op_dict['position_ratio']:
                    op_dict['position_ratio'] = round(op_dict['position_ratio'] * 100, 2)

                operations.append(op_dict)

            logger.info(f"返回 {len(operations)} 条每日操作清单")
            return operations

    except Exception as e:
        logger.error(f"获取每日操作清单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-operation-list/by-date/{date}", response_model=List[DailyOperationListResponse])
async def get_daily_operation_list_by_date(date: str):
    """
    获取指定日期的每日操作清单

    Args:
        date: 日期 (YYYY-MM-DD)

    Returns:
        该日期的操作清单
    """
    try:
        db = get_db()

        # 转换日期格式
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()

        with db.get_session() as session:
            from database.models.models import DailyOperationList

            query = session.query(DailyOperationList).filter(
                DailyOperationList.date == date_obj
            ).order_by(
                DailyOperationList.sector_rank,
                DailyOperationList.strength_score.desc()
            )

            operations = []
            for op in query.all():
                op_dict = model_to_dict(op)
                # 格式化日期
                if 'date' in op_dict and op_dict['date']:
                    op_dict['date'] = op_dict['date'].strftime('%Y-%m-%d')
                if 'executed_time' in op_dict and op_dict['executed_time']:
                    op_dict['executed_time'] = op_dict['executed_time'].strftime('%Y-%m-%d %H:%M:%S')

                # 处理position_ratio为百分比
                if 'position_ratio' in op_dict and op_dict['position_ratio']:
                    op_dict['position_ratio'] = round(op_dict['position_ratio'] * 100, 2)

                operations.append(op_dict)

            return operations

    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误,请使用 YYYY-MM-DD 格式")
    except Exception as e:
        logger.error(f"获取每日操作清单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/latest", response_model=List[SectorDataResponse])
async def get_latest_sectors(limit: int = 10):
    """
    获取最新的强势板块

    Args:
        limit: 返回的最大数量 (默认: 10)

    Returns:
        最新强势板块列表
    """
    try:
        db = get_db()

        with db.get_session() as session:
            from database.models.models import SectorData

            # 获取最新日期
            latest_date = session.query(
                SectorData.date
            ).order_by(
                SectorData.date.desc()
            ).first()

            if not latest_date:
                return []

            # 获取该日期的板块数据
            query = session.query(SectorData).filter(
                SectorData.date == latest_date[0]
            ).order_by(
                SectorData.strength_score.desc()
            ).limit(limit)

            sectors = []
            for sector in query.all():
                sector_dict = model_to_dict(sector)
                # 格式化日期
                if 'date' in sector_dict and sector_dict['date']:
                    sector_dict['date'] = sector_dict['date'].strftime('%Y-%m-%d')

                sectors.append(sector_dict)

            logger.info(f"返回 {len(sectors)} 个强势板块")
            return sectors

    except Exception as e:
        logger.error(f"获取强势板块失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/by-date/{date}", response_model=List[SectorDataResponse])
async def get_sectors_by_date(date: str):
    """
    获取指定日期的强势板块

    Args:
        date: 日期 (YYYY-MM-DD)

    Returns:
        该日期的板块列表
    """
    try:
        db = get_db()

        date_obj = datetime.strptime(date, '%Y-%m-%d').date()

        with db.get_session() as session:
            from database.models.models import SectorData

            query = session.query(SectorData).filter(
                SectorData.date == date_obj
            ).order_by(
                SectorData.strength_score.desc()
            )

            sectors = []
            for sector in query.all():
                sector_dict = model_to_dict(sector)
                if 'date' in sector_dict and sector_dict['date']:
                    sector_dict['date'] = sector_dict['date'].strftime('%Y-%m-%d')

                sectors.append(sector_dict)

            return sectors

    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")
    except Exception as e:
        logger.error(f"获取板块数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/latest", response_model=List[BacktestResultResponse])
async def get_latest_backtests(limit: int = 10):
    """
    获取最新的回测结果

    Args:
        limit: 返回的最大数量 (默认: 10)

    Returns:
        最新回测结果列表
    """
    try:
        db = get_db()

        with db.get_session() as session:
            from database.models.models import ShortTermBacktest

            query = session.query(ShortTermBacktest).order_by(
                ShortTermBacktest.created_at.desc()
            ).limit(limit)

            backtests = []
            for bt in query.all():
                bt_dict = model_to_dict(bt)
                # 格式化日期
                if 'start_date' in bt_dict and bt_dict['start_date']:
                    bt_dict['start_date'] = bt_dict['start_date'].strftime('%Y-%m-%d')
                if 'end_date' in bt_dict and bt_dict['end_date']:
                    bt_dict['end_date'] = bt_dict['end_date'].strftime('%Y-%m-%d')
                if 'created_at' in bt_dict and bt_dict['created_at']:
                    bt_dict['created_at'] = bt_dict['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                backtests.append(bt_dict)

            return backtests

    except Exception as e:
        logger.error(f"获取回测结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/{backtest_id}")
async def get_backtest_result(backtest_id: int):
    """
    获取指定回测的详细信息

    Args:
        backtest_id: 回测ID

    Returns:
        回测详细信息
    """
    try:
        db = get_db()

        with db.get_session() as session:
            from database.models.models import ShortTermBacktest

            backtest = session.query(ShortTermBacktest).filter(
                ShortTermBacktest.id == backtest_id
            ).first()

            if not backtest:
                raise HTTPException(status_code=404, detail="回测不存在")

            result = model_to_dict(backtest)

            # 格式化日期
            if 'start_date' in result and result['start_date']:
                result['start_date'] = result['start_date'].strftime('%Y-%m-%d')
            if 'end_date' in result and result['end_date']:
                result['end_date'] = result['end_date'].strftime('%Y-%m-%d')
            if 'created_at' in result and result['created_at']:
                result['created_at'] = result['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_summary():
    """
    获取短线交易系统概览

    Returns:
        系统概览信息
    """
    try:
        db = get_db()

        with db.get_session() as session:
            from database.models.models import DailyOperationList, SectorData, ShortTermBacktest

            # 最新每日操作清单
            latest_operation = session.query(
                DailyOperationList.date
            ).order_by(
                DailyOperationList.date.desc()
            ).first()

            latest_operation_count = 0
            if latest_operation:
                latest_operation_count = session.query(
                    DailyOperationList
                ).filter(
                    DailyOperationList.date == latest_operation[0]
                ).count()

            # 最新板块数据
            latest_sector = session.query(
                SectorData.date
            ).order_by(
                SectorData.date.desc()
            ).first()

            latest_sector_count = 0
            if latest_sector:
                latest_sector_count = session.query(
                    SectorData
                ).filter(
                    SectorData.date == latest_sector[0]
                ).count()

            # 回测统计
            total_backtests = session.query(
                ShortTermBacktest
            ).count()

            return {
                "latest_operation_date": latest_operation[0].strftime('%Y-%m-%d') if latest_operation else None,
                "latest_operation_count": latest_operation_count,
                "latest_sector_date": latest_sector[0].strftime('%Y-%m-%d') if latest_sector else None,
                "latest_sector_count": latest_sector_count,
                "total_backtests": total_backtests,
                "system_status": "running"
            }

    except Exception as e:
        logger.error(f"获取系统概览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == '__main__':
    """测试API"""
    import uvicorn

    logger.info("启动短线交易信号API服务器...")
    uvicorn.run(
        router,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
