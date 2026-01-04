"""
Signals API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
from database.pg_manager import get_db
from web.models import SignalResponse
import numpy as np
import pandas as pd

router = APIRouter()


def clean_dataframe(df):
    """清理 DataFrame 中的 NaN 值"""
    if not df.empty:
        df = df.replace({np.nan: None})
    return df


def safe_dict_value(value):
    """安全处理字典中的 NaN 值"""
    if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
        return None
    return value


@router.get("/latest", response_model=List[SignalResponse])
async def get_latest_signals(limit: int = 10):
    """
    获取最新的交易信号

    Args:
        limit: 返回的最大信号数量 (默认: 10)

    Returns:
        最新信号列表
    """
    try:
        db = get_db()
        signals_df = db.get_latest_trader_signals(limit=limit)

        if signals_df.empty:
            return []

        # 清理 NaN 值
        signals_df = clean_dataframe(signals_df)

        # 转换DataFrame为字典列表
        signals = signals_df.to_dict('records')

        # 清理并格式化
        cleaned_signals = []
        for signal in signals:
            cleaned_record = {k: safe_dict_value(v) for k, v in signal.items()}
            # 格式化日期字段
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            cleaned_signals.append(cleaned_record)

        return cleaned_signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-date/{signal_date}", response_model=List[SignalResponse])
async def get_signals_by_date(signal_date: str):
    """
    获取指定日期的信号

    Args:
        signal_date: 日期 (YYYY-MM-DD)

    Returns:
        该日期的信号列表
    """
    try:
        db = get_db()
        signals_df = db.get_trader_signals_by_date(signal_date)

        if signals_df.empty:
            return []

        # 清理 NaN 值
        signals_df = clean_dataframe(signals_df)

        signals = signals_df.to_dict('records')

        cleaned_signals = []
        for signal in signals:
            cleaned_record = {k: safe_dict_value(v) for k, v in signal.items()}
            # 格式化日期字段
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            cleaned_signals.append(cleaned_record)

        return cleaned_signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-symbol/{symbol}", response_model=List[SignalResponse])
async def get_signals_by_symbol(symbol: str, start_date: str = None, end_date: str = None):
    """
    获取指定标的的信号

    Args:
        symbol: ETF代码
        start_date: 开始日期 YYYY-MM-DD (可选)
        end_date: 结束日期 YYYY-MM-DD (可选)

    Returns:
        该标的的信号列表
    """
    try:
        db = get_db()
        signals_df = db.get_trader_signals_by_symbol(symbol, start_date, end_date)

        if signals_df.empty:
            return []

        # 清理 NaN 值
        signals_df = clean_dataframe(signals_df)

        signals = signals_df.to_dict('records')

        cleaned_signals = []
        for signal in signals:
            cleaned_record = {k: safe_dict_value(v) for k, v in signal.items()}
            # 格式化日期字段
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            cleaned_signals.append(cleaned_record)

        return cleaned_signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/grouped")
async def get_signals_history_grouped(start_date: str = None, end_date: str = None):
    """
    获取历史信号，按日期分组

    Args:
        start_date: 开始日期 YYYY-MM-DD (可选)
        end_date: 结束日期 YYYY-MM-DD (可选)

    Returns:
        按日期分组的历史信号
    """
    try:
        db = get_db()

        # 构建查询
        query = "SELECT * FROM trader"
        conditions = []

        if start_date:
            conditions.append(f"signal_date >= '{start_date}'")
        if end_date:
            conditions.append(f"signal_date <= '{end_date}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY signal_date DESC, created_at DESC"

        # 执行查询
        signals_df = db.conn.sql(query).df()

        if signals_df.empty:
            return {"dates": []}

        # 清理 NaN 值
        signals_df = clean_dataframe(signals_df)

        # 按日期分组
        grouped = {}
        for record in signals_df.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}

            # 格式化日期字段
            signal_date = cleaned_record.get('signal_date')
            if signal_date:
                signal_date_str = signal_date.strftime('%Y-%m-%d')
                cleaned_record['signal_date'] = signal_date_str

                if 'created_at' in cleaned_record and cleaned_record['created_at']:
                    cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                if signal_date_str not in grouped:
                    grouped[signal_date_str] = []

                grouped[signal_date_str].append(cleaned_record)

        # 转换为列表并排序
        dates_list = [
            {"date": date, "signals": signals}
            for date, signals in grouped.items()
        ]
        dates_list.sort(key=lambda x: x["date"], reverse=True)

        return {"dates": dates_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
