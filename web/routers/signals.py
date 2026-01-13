"""
Signals API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List
from database.pg_manager import get_db
from web.models import SignalResponse
from loguru import logger
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
    获取历史信号，按日期分组，并按ETF/A股分类

    Args:
        start_date: 开始日期 YYYY-MM-DD (可选)
        end_date: 结束日期 YYYY-MM-DD (可选)

    Returns:
        按ETF和A股分类，再按日期分组的历史信号
        {
            "etf": {"dates": [...]},
            "ashare": {"weekly": {"dates": [...]}, "monthly": {"dates": [...]}}
        }
    """
    try:
        db = get_db()
        with db.get_session() as session:
            from database.models.models import Trader
            from sqlalchemy import func, and_

            # 构建查询条件
            conditions = []
            if start_date:
                conditions.append(Trader.signal_date >= start_date)
            if end_date:
                conditions.append(Trader.signal_date <= end_date)

            # 查询所有信号
            if conditions:
                query = session.query(Trader).filter(and_(*conditions))
            else:
                query = session.query(Trader)

            query = query.order_by(
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc()
            )

            signals_df = pd.read_sql(query.statement, session.bind)

        if signals_df.empty:
            return {
                "etf": {"dates": []},
                "ashare": {"weekly": {"dates": []}, "monthly": {"dates": []}}
            }

        # 清理 NaN 值
        signals_df = clean_dataframe(signals_df)

        # 批量获取公司简称
        symbols = signals_df['symbol'].unique().tolist()
        company_abbr_map = db.batch_get_company_abbr(symbols)

        # 按asset_type分组
        etf_signals = []
        ashare_signals = []

        for record in signals_df.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}

            # 格式化日期字段
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # 添加公司简称
            cleaned_record['zh_company_abbr'] = company_abbr_map.get(record['symbol'], '')

            # 按类型分组
            asset_type = cleaned_record.get('asset_type', '')
            if asset_type == 'etf':
                etf_signals.append(cleaned_record)
            elif asset_type == 'ashare':
                ashare_signals.append(cleaned_record)

        # ETF信号按日期分组
        etf_grouped = {}
        for signal in etf_signals:
            date_key = signal['signal_date']
            if date_key not in etf_grouped:
                etf_grouped[date_key] = []
            etf_grouped[date_key].append(signal)

        etf_dates_list = [{"date": date, "signals": signals}
                         for date, signals in etf_grouped.items()]

        # A股信号按周频/月频分组，再按日期分组
        ashare_weekly = []
        ashare_monthly = []

        for signal in ashare_signals:
            strategies = signal.get('strategies', '')
            if '周频' in strategies:
                ashare_weekly.append(signal)
            elif '月频' in strategies:
                ashare_monthly.append(signal)
            else:
                # 默认归为周频
                ashare_weekly.append(signal)

        # 周频信号按日期分组
        weekly_grouped = {}
        for signal in ashare_weekly:
            date_key = signal['signal_date']
            if date_key not in weekly_grouped:
                weekly_grouped[date_key] = []
            weekly_grouped[date_key].append(signal)

        weekly_dates_list = [{"date": date, "signals": signals}
                            for date, signals in weekly_grouped.items()]

        # 月频信号按日期分组
        monthly_grouped = {}
        for signal in ashare_monthly:
            date_key = signal['signal_date']
            if date_key not in monthly_grouped:
                monthly_grouped[date_key] = []
            monthly_grouped[date_key].append(signal)

        monthly_dates_list = [{"date": date, "signals": signals}
                             for date, signals in monthly_grouped.items()]

        return {
            "etf": {"dates": etf_dates_list},
            "ashare": {
                "weekly": {"dates": weekly_dates_list},
                "monthly": {"dates": monthly_dates_list}
            }
        }

    except Exception as e:
        logger.error(f"Error fetching historical signals grouped: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/latest")
async def get_latest_etf_signals(limit: int = 50):
    """
    获取最新的ETF信号（单独获取）

    Returns:
        ETF signals grouped by date
    """
    try:
        db = get_db()
        with db.get_session() as session:
            # Query ETF signals using asset_type column
            from database.models.models import Trader
            from sqlalchemy import func

            # ETF信号：使用asset_type字段过滤，按rank排序（rank=1优先）
            query = session.query(Trader).filter(
                Trader.asset_type == 'etf'
            ).order_by(
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc()
            ).limit(limit)

            signals_df = pd.read_sql(query.statement, session.bind)

        if signals_df.empty:
            return {"dates": []}

        # Clean and group by date
        signals_df = clean_dataframe(signals_df)

        # Batch get company abbreviations for all symbols
        symbols = signals_df['symbol'].unique().tolist()
        company_abbr_map = db.batch_get_company_abbr(symbols)

        signals_list = []
        for record in signals_df.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # Add company abbreviation
            cleaned_record['zh_company_abbr'] = company_abbr_map.get(record['symbol'], '')

            signals_list.append(cleaned_record)

        # Group by date
        grouped = {}
        for signal in signals_list:
            date_key = signal['signal_date']
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(signal)

        dates_list = [{"date": date, "signals": signals}
                      for date, signals in grouped.items()]

        return {"dates": dates_list}

    except Exception as e:
        logger.error(f"Error fetching ETF signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ashare/latest")
async def get_latest_ashare_signals(limit: int = 50):
    """
    获取最新的A股信号（单独获取），按周频和月频分组

    Returns:
        A-share signals split into weekly and monthly groups, each grouped by date
    """
    try:
        db = get_db()
        with db.get_session() as session:
            # Query A-share signals using asset_type column
            from database.models.models import Trader
            from sqlalchemy import func

            # A股信号：使用asset_type字段过滤，按rank排序（rank=1优先）
            query = session.query(Trader).filter(
                Trader.asset_type == 'ashare'
            ).order_by(
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc()
            ).limit(limit)

            signals_df = pd.read_sql(query.statement, session.bind)

        if signals_df.empty:
            return {"weekly": [], "monthly": []}

        signals_df = clean_dataframe(signals_df)

        # Batch get company abbreviations for all symbols
        symbols = signals_df['symbol'].unique().tolist()
        company_abbr_map = db.batch_get_company_abbr(symbols)

        # Enrich with backtest information and split by frequency
        weekly_signals = []
        monthly_signals = []

        for record in signals_df.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}

            # Format dates
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # Add company abbreviation
            cleaned_record['zh_company_abbr'] = company_abbr_map.get(record['symbol'], '')

            # Get associated backtest
            backtest_info = db.get_signal_backtest(record['id'])
            cleaned_record['backtest'] = backtest_info

            # Split by strategy frequency (周频/月频)
            strategies = cleaned_record.get('strategies', '')
            if '周频' in strategies:
                weekly_signals.append(cleaned_record)
            elif '月频' in strategies:
                monthly_signals.append(cleaned_record)
            else:
                # Fallback: if no frequency indicator, treat as weekly
                weekly_signals.append(cleaned_record)

        # Group weekly signals by date
        weekly_grouped = {}
        for signal in weekly_signals:
            date_key = signal['signal_date']
            if date_key not in weekly_grouped:
                weekly_grouped[date_key] = []
            weekly_grouped[date_key].append(signal)

        weekly_dates_list = [{"date": date, "signals": signals}
                             for date, signals in weekly_grouped.items()]

        # Group monthly signals by date
        monthly_grouped = {}
        for signal in monthly_signals:
            date_key = signal['signal_date']
            if date_key not in monthly_grouped:
                monthly_grouped[date_key] = []
            monthly_grouped[date_key].append(signal)

        monthly_dates_list = [{"date": date, "signals": signals}
                              for date, signals in monthly_grouped.items()]

        return {
            "weekly": weekly_dates_list,
            "monthly": monthly_dates_list
        }

    except Exception as e:
        logger.error(f"Error fetching A-share signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ashare/backtest/{backtest_id}")
async def get_backtest_detail(backtest_id: int):
    """
    获取回测详情

    Returns:
        Complete backtest report with equity curve and trades
    """
    try:
        db = get_db()
        backtest = db.get_backtest_by_id(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        return backtest

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching backtest detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
