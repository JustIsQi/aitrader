"""
Signals API endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime
from database.pg_manager import get_db
from web.models import SignalResponse
from loguru import logger
import numpy as np
import pandas as pd
import json

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
            from sqlalchemy import func, and_, case

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

            # 卖出信号优先显示，然后是价格<50的股票，再按rank、日期排序
            query = query.order_by(
                case(
                    (Trader.signal_type == 'sell', 0),  # 卖出信号优先级为0
                    else_=1                              # 买入信号优先级为1
                ).asc(),                                 # 按信号类型优先级升序
                case(
                    (Trader.price < 50, 0),      # 价格<50优先级为0
                    else_=1                       # 价格>=50优先级为1
                ).asc(),                          # 按价格优先级升序
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

        # Sort by date descending (newest first)
        etf_dates_list = [{"date": date, "signals": signals}
                         for date, signals in sorted(etf_grouped.items(), key=lambda x: x[0], reverse=True)]

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

        # Sort by date descending (newest first)
        weekly_dates_list = [{"date": date, "signals": signals}
                            for date, signals in sorted(weekly_grouped.items(), key=lambda x: x[0], reverse=True)]

        # 月频信号按日期分组
        monthly_grouped = {}
        for signal in ashare_monthly:
            date_key = signal['signal_date']
            if date_key not in monthly_grouped:
                monthly_grouped[date_key] = []
            monthly_grouped[date_key].append(signal)

        # Sort by date descending (newest first)
        monthly_dates_list = [{"date": date, "signals": signals}
                             for date, signals in sorted(monthly_grouped.items(), key=lambda x: x[0], reverse=True)]

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
    获取最新一天的ETF信号 (仅返回最新日期的信号)

    Returns:
        Single object with latest date and signals (not grouped by date)
        {
            "date": "2024-01-15",
            "signals": [...]
        }
    """
    try:
        db = get_db()
        with db.get_session() as session:
            # Query ETF signals using asset_type column
            from database.models.models import Trader
            from sqlalchemy import func, case

            # ETF信号：使用asset_type字段过滤，按rank排序（rank=1优先）
            # 卖出信号优先显示，然后是价格<50的ETF
            query = session.query(Trader).filter(
                Trader.asset_type == 'etf'
            ).order_by(
                case(
                    (Trader.signal_type == 'sell', 0),  # 卖出信号优先级为0
                    else_=1                              # 买入信号优先级为1
                ).asc(),                                 # 按信号类型优先级升序
                case(
                    (Trader.price < 50, 0),      # 价格<50优先级为0
                    else_=1                       # 价格>=50优先级为1
                ).asc(),                          # 按价格优先级升序
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc()
            ).limit(limit)

            signals_df = pd.read_sql(query.statement, session.bind)

        if signals_df.empty:
            return {"date": None, "signals": []}

        # Clean and process signals
        signals_df = clean_dataframe(signals_df)

        # Batch get ETF names for all symbols
        symbols = signals_df['symbol'].unique().tolist()
        etf_name_map = db.batch_get_etf_names(symbols)

        signals_list = []
        for record in signals_df.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
            if 'created_at' in cleaned_record and cleaned_record['created_at']:
                cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            # Add ETF name
            cleaned_record['zh_company_abbr'] = etf_name_map.get(record['symbol'], '')

            # 新增: 获取回测信息
            backtest_info = db.get_signal_backtest(record['id'])
            cleaned_record['backtest'] = backtest_info

            signals_list.append(cleaned_record)

        # Find the latest date and filter signals
        if signals_list:
            dates = [s['signal_date'] for s in signals_list]
            latest_date = max(dates)
            latest_signals = [s for s in signals_list if s['signal_date'] == latest_date]
        else:
            latest_date = None
            latest_signals = []

        # Return single date object (not a list)
        return {
            "date": latest_date,
            "signals": latest_signals
        }

    except Exception as e:
        logger.error(f"Error fetching ETF signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ashare/latest")
async def get_latest_ashare_signals(limit: int = 50):
    """
    获取最新一天的A股信号 (仅返回最新日期的信号)

    Returns:
        Weekly and monthly signals from latest date only
        {
            "weekly": {
                "date": "2024-01-15",
                "signals": [...]
            },
            "monthly": {
                "date": "2024-01-15",
                "signals": [...]
            }
        }
    """
    try:
        db = get_db()
        with db.get_session() as session:
            # Query A-share signals using asset_type column
            from database.models.models import Trader
            from sqlalchemy import func, case

            # A股信号：使用asset_type字段过滤，按rank排序（rank=1优先）
            # 卖出信号优先显示，然后是价格<50的股票
            query = session.query(Trader).filter(
                Trader.asset_type == 'ashare'
            ).order_by(
                case(
                    (Trader.signal_type == 'sell', 0),  # 卖出信号优先级为0
                    else_=1                              # 买入信号优先级为1
                ).asc(),                                 # 按信号类型优先级升序
                case(
                    (Trader.price < 50, 0),      # 价格<50优先级为0
                    else_=1                       # 价格>=50优先级为1
                ).asc(),                          # 按价格优先级升序
                func.coalesce(Trader.rank, 9999).asc(),
                Trader.signal_date.desc(),
                Trader.created_at.desc()
            ).limit(limit)

            signals_df = pd.read_sql(query.statement, session.bind)

        if signals_df.empty:
            return {"weekly": {"date": None, "signals": []}, "monthly": {"date": None, "signals": []}}

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

        # Find latest date for weekly and filter
        if weekly_signals:
            weekly_dates = [s['signal_date'] for s in weekly_signals]
            latest_weekly_date = max(weekly_dates)
            latest_weekly = [s for s in weekly_signals if s['signal_date'] == latest_weekly_date]
        else:
            latest_weekly_date = None
            latest_weekly = []

        # Find latest date for monthly and filter
        if monthly_signals:
            monthly_dates = [s['signal_date'] for s in monthly_signals]
            latest_monthly_date = max(monthly_dates)
            latest_monthly = [s for s in monthly_signals if s['signal_date'] == latest_monthly_date]
        else:
            latest_monthly_date = None
            latest_monthly = []

        # Return single date objects (not lists)
        return {
            "weekly": {
                "date": latest_weekly_date,
                "signals": latest_weekly
            },
            "monthly": {
                "date": latest_monthly_date,
                "signals": latest_monthly
            }
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


@router.get("/backtest/{backtest_id}")
async def get_backtest_by_id_universal(backtest_id: int):
    """
    获取回测详情通用端点(支持ETF和A股)

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
