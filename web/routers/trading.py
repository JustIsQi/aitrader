"""
Trading API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import date
from pathlib import Path
from database.pg_manager import get_db
from web.models import TradingRecord, TransactionResponse, PositionResponse
import numpy as np
import pandas as pd

router = APIRouter()

# 策略目录
STRATEGY_DIR = Path(__file__).parent.parent.parent / "strategies"


def clean_dataframe(df):
    """清理 DataFrame 中的 NaN 值"""
    if not df.empty:
        df = df.replace({np.nan: None})
    return df


def safe_dict_value(value):
    """安全处理字典中的 NaN 值"""
    if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
        return None
    # 将 NumPy 类型转换为 Python 原生类型
    if hasattr(value, 'item'):  # NumPy scalar types
        return value.item()
    return value


@router.post("/record", response_model=dict)
async def add_trading_record(record: TradingRecord):
    """
    添加新的交易记录

    此操作会:
    1. 将交易记录插入transactions表
    2. 更新positions表

    Args:
        record: 交易记录详情

    Returns:
        成功消息
    """
    try:
        db = get_db()

        # 插入交易记录
        db.insert_transaction(
            symbol=record.symbol,
            buy_sell=record.buy_sell,
            quantity=record.quantity,
            price=record.price,
            trade_date=record.trade_date.strftime('%Y-%m-%d'),
            strategy_name=record.strategy_name
        )

        # 更新持仓
        # 获取当前持仓（如果存在）
        positions = db.get_positions()
        current_position = None

        if not positions.empty:
            position_rows = positions[positions['symbol'] == record.symbol]
            if not position_rows.empty:
                current_position = position_rows.iloc[0]

        if record.buy_sell == 'buy':
            # 买入：更新或创建持仓
            if current_position is not None:
                # 计算新的平均成本
                total_quantity = float(current_position['quantity'] + record.quantity)
                total_cost = (float(current_position['avg_cost']) * float(current_position['quantity']) +
                            float(record.price) * float(record.quantity))
                new_avg_cost = total_cost / total_quantity

                db.update_position(
                    symbol=record.symbol,
                    quantity=total_quantity,
                    avg_cost=float(new_avg_cost),
                    current_price=float(record.price)
                )
            else:
                # 创建新持仓
                db.update_position(
                    symbol=record.symbol,
                    quantity=float(record.quantity),
                    avg_cost=float(record.price),
                    current_price=float(record.price)
                )
        else:  # sell
            # 卖出：更新持仓
            if current_position is not None:
                new_quantity = float(current_position['quantity'] - record.quantity)

                if new_quantity > 0:
                    # 部分卖出，保留持仓
                    db.update_position(
                        symbol=record.symbol,
                        quantity=new_quantity,
                        avg_cost=float(current_position['avg_cost']),
                        current_price=float(record.price)
                    )
                else:
                    # 全部卖出，移除持仓（设为0）
                    db.update_position(
                        symbol=record.symbol,
                        quantity=0.0,
                        avg_cost=float(current_position['avg_cost']),
                        current_price=float(record.price)
                    )

        return {
            "status": "success",
            "message": f"交易记录已添加: {record.buy_sell} {record.quantity}股 {record.symbol} @ {record.price}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(symbol: str = None, start_date: str = None,
                           end_date: str = None, limit: int = 100):
    """
    获取交易记录

    Args:
        symbol: 过滤ETF代码 (可选)
        start_date: 开始日期 YYYY-MM-DD (可选)
        end_date: 结束日期 YYYY-MM-DD (可选)
        limit: 最大记录数 (默认: 100)

    Returns:
        交易记录列表
    """
    try:
        db = get_db()
        transactions_df = db.get_transactions(symbol, start_date, end_date)

        if transactions_df.empty:
            return []

        # 清理 NaN 值
        transactions_df = clean_dataframe(transactions_df)

        # 应用限制
        transactions_df = transactions_df.head(limit)

        transactions = transactions_df.to_dict('records')

        cleaned_transactions = []
        for t in transactions:
            cleaned_record = {k: safe_dict_value(v) for k, v in t.items()}
            # 格式化日期
            if 'trade_date' in cleaned_record and cleaned_record['trade_date']:
                cleaned_record['trade_date'] = cleaned_record['trade_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            cleaned_transactions.append(cleaned_record)

        return cleaned_transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions():
    """
    获取当前持仓

    Returns:
        当前持仓列表
    """
    try:
        db = get_db()
        positions_df = db.get_positions()

        if positions_df.empty:
            return []

        # 清理 NaN 值
        positions_df = clean_dataframe(positions_df)

        positions = positions_df.to_dict('records')

        cleaned_positions = []
        for p in positions:
            cleaned_record = {k: safe_dict_value(v) for k, v in p.items()}
            # 格式化日期
            if 'updated_at' in cleaned_record and cleaned_record['updated_at']:
                cleaned_record['updated_at'] = cleaned_record['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            cleaned_positions.append(cleaned_record)

        return cleaned_positions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies", response_model=List[str])
async def get_strategies():
    """
    获取可用策略列表

    Returns:
        策略名称列表
    """
    try:
        if not STRATEGY_DIR.exists():
            return []

        # 获取所有 .py 策略文件名（去掉扩展名）
        strategies = []
        for py_file in STRATEGY_DIR.glob("*.py"):
            # 跳过缓存文件和隐藏文件
            if "__pycache__" in str(py_file) or py_file.name.startswith("."):
                continue
            strategies.append(py_file.stem)

        return sorted(strategies)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalculate-positions", response_model=dict)
async def recalculate_positions():
    """
    重新计算所有持仓

    从 transactions 表读取所有交易记录，重新计算 positions 表。
    适用于手动修改了 transactions 表后同步持仓数据。

    Returns:
        dict: {
            'status': 'success',
            'message': str,
            'updated_count': int,
            'deleted_count': int,
            'details': List[dict]
        }
    """
    try:
        db = get_db()
        result = db.recalculate_positions()

        return {
            'status': 'success',
            'message': f'重新计算完成: 更新 {result["updated_count"]} 个持仓, 删除 {result["deleted_count"]} 个',
            'updated_count': result['updated_count'],
            'deleted_count': result['deleted_count'],
            'details': result['details']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/codes")
async def get_trading_codes(search: str = None, limit: int = 100):
    """
    获取 ETF 和股票代码列表（支持搜索）

    Args:
        search: 搜索关键词（可选）
        limit: 最大返回数量（默认100）

    Returns:
        List[str]: 代码列表
    """
    try:
        db = get_db()
        codes = db.search_codes(search=search, limit=limit)
        return codes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
