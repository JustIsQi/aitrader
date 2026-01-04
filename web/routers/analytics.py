"""
Analytics API endpoints
"""
from fastapi import APIRouter, HTTPException
from database.pg_manager import get_db
from web.models import ProfitLossResponse
import numpy as np
import pandas as pd

router = APIRouter()


def clean_dataframe(df):
    """清理 DataFrame 中的 NaN 值"""
    if not df.empty:
        df = df.replace({np.nan: None})
    return df


@router.get("/profit-loss", response_model=ProfitLossResponse)
async def get_profit_loss():
    """
    获取盈亏统计

    Returns:
        包含已实现和未实现盈亏的指标
    """
    try:
        db = get_db()
        pl_data = db.calculate_profit_loss()

        total_pl = pl_data['realized_pl'] + pl_data['total_unrealized_pl']

        return ProfitLossResponse(
            realized_pl=safe_float(pl_data['realized_pl']),
            total_unrealized_pl=safe_float(pl_data['total_unrealized_pl']),
            total_market_value=safe_float(pl_data['total_market_value']),
            total_cost=safe_float(pl_data['total_cost']),
            total_pl=safe_float(total_pl)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def safe_float(value):
    """安全转换浮点数，将 NaN 转为 None"""
    if pd.isna(value) or np.isnan(value):
        return None
    return float(value)


@router.get("/performance")
async def get_performance_metrics():
    """
    获取详细绩效指标

    Returns:
        绩效统计数据
    """
    try:
        db = get_db()
        positions = db.get_positions()

        if positions.empty:
            return {
                "total_positions": 0,
                "total_market_value": 0,
                "total_cost": 0,
                "best_performer": None,
                "worst_performer": None,
                "avg_return_pct": 0
            }

        # 清理 NaN 值
        positions = clean_dataframe(positions)

        # 计算收益率
        positions['return_pct'] = ((positions['current_price'] - positions['avg_cost']) /
                                   positions['avg_cost'] * 100)
        positions['return_amount'] = ((positions['current_price'] - positions['avg_cost']) *
                                      positions['quantity'])

        # 清理计算结果中的 NaN
        positions['return_pct'] = positions['return_pct'].replace({np.nan: None})
        positions['return_amount'] = positions['return_amount'].replace({np.nan: None})

        # 找出表现最好和最差的
        best_idx = positions['return_pct'].idxmax()
        worst_idx = positions['return_pct'].idxmin()

        total_cost = (positions['avg_cost'] * positions['quantity']).sum()
        total_return = positions['return_amount'].sum()

        return {
            "total_positions": len(positions),
            "total_market_value": safe_float(positions['market_value'].sum()),
            "total_cost": safe_float(total_cost),
            "total_return": safe_float(total_return),
            "total_return_pct": safe_float(total_return / total_cost * 100 if total_cost > 0 else 0),
            "best_performer": {
                "symbol": positions.loc[best_idx, 'symbol'],
                "return_pct": safe_float(positions.loc[best_idx, 'return_pct'])
            },
            "worst_performer": {
                "symbol": positions.loc[worst_idx, 'symbol'],
                "return_pct": safe_float(positions.loc[worst_idx, 'return_pct'])
            },
            "avg_return_pct": safe_float(positions['return_pct'].mean())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
