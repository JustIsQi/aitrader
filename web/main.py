"""
FastAPI Web Application for AITrader
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from loguru import logger
import numpy as np

from database.pg_manager import get_db
from web.routers import signals, trading, analytics
import pandas as pd


def clean_dataframes(*dfs):
    """清理 DataFrame 中的 NaN 值，转换为 None"""
    cleaned = []
    for df in dfs:
        if not df.empty:
            # 将 NaN 替换为 None
            df = df.replace({np.nan: None})
        cleaned.append(df)
    return cleaned if len(cleaned) > 1 else cleaned[0]


def safe_dict_value(value):
    """安全处理字典中的 NaN 值"""
    if isinstance(value, float) and (pd.isna(value) or np.isnan(value)):
        return None
    return value

# 初始化FastAPI应用
app = FastAPI(
    title="AITrader Web Interface",
    description="Web interface for ETF trading signals and portfolio management",
    version="1.0.0"
)

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 设置模板
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 包含路由
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

# 初始化数据库
db = get_db()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    主仪表板页面
    """
    # 获取当前持仓（移到前面，以便在信号处理中使用）
    positions = db.get_positions()

    # 构建持仓查找字典
    positions_dict = {}
    if not positions.empty:
        for record in positions.to_dict('records'):
            symbol = record['symbol']
            quantity = record['quantity']
            avg_cost = record['avg_cost']
            current_price = record.get('current_price', avg_cost)

            # 计算浮动盈亏
            unrealized_pl = (current_price - avg_cost) * quantity
            unrealized_pl_pct = ((current_price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0

            position_data = {
                'quantity': quantity,
                'avg_cost': avg_cost,
                'current_price': current_price,
                'market_value': record.get('market_value'),
                'unrealized_pl': unrealized_pl,
                'unrealized_pl_pct': unrealized_pl_pct,
                'updated_at': record.get('updated_at')
            }

            # 存储多个格式的symbol以支持匹配
            # 原始格式 (如: 518880)
            positions_dict[symbol] = position_data
            # 带.SH后缀的格式 (如: 518880.SH)
            positions_dict[f"{symbol}.SH"] = position_data
            # 带.SZ后缀的格式 (如: 518880.SZ)
            positions_dict[f"{symbol}.SZ"] = position_data

    # 获取最近5个交易日的信号，按日期分组
    # 首先获取所有信号的日期
    from database.models import Trader
    from sqlalchemy import distinct

    with db.get_session() as session:
        query = session.query(distinct(Trader.signal_date)).order_by(
            Trader.signal_date.desc()
        ).limit(5)
        dates_df = pd.read_sql(query.statement, session.bind)

    grouped_signals = {}
    if not dates_df.empty:
        # 获取每个日期的信号
        for date_record in dates_df.to_dict('records'):
            date_str = date_record['signal_date']
            if isinstance(date_str, str):
                date_obj = pd.to_datetime(date_str)
            else:
                date_obj = date_str

            date_key = date_obj.strftime('%Y-%m-%d')

            # 获取该日期的信号
            with db.get_session() as session:
                query = session.query(Trader).filter(
                    Trader.signal_date == date_key
                ).order_by(Trader.signal_type, Trader.symbol)
                daily_signals_df = pd.read_sql(query.statement, session.bind)

            if not daily_signals_df.empty:
                daily_signals_df = clean_dataframes(daily_signals_df)

                signals_list = []
                for record in daily_signals_df.to_dict('records'):
                    cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
                    # 格式化日期
                    if 'signal_date' in cleaned_record and cleaned_record['signal_date']:
                        if hasattr(cleaned_record['signal_date'], 'strftime'):
                            cleaned_record['signal_date'] = cleaned_record['signal_date'].strftime('%Y-%m-%d')
                    if 'created_at' in cleaned_record and cleaned_record['created_at']:
                        if hasattr(cleaned_record['created_at'], 'strftime'):
                            cleaned_record['created_at'] = cleaned_record['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                    # 关联持仓信息
                    symbol = cleaned_record.get('symbol')
                    if symbol and symbol in positions_dict:
                        cleaned_record['position'] = positions_dict[symbol]

                    signals_list.append(cleaned_record)

                grouped_signals[date_key] = signals_list

    # 获取最近交易记录
    transactions = db.get_transactions()[:20]

    # 清理 NaN 值
    positions, transactions = clean_dataframes(positions, transactions)

    # 转换为字典并清理剩余 NaN
    positions_list = []
    if not positions.empty:
        for record in positions.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            positions_list.append(cleaned_record)

    transactions_list = []
    if not transactions.empty:
        for record in transactions.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            transactions_list.append(cleaned_record)

    # 将分组信号转换为按日期排序的列表
    signals_by_date = [
        {"date": date, "signals": signals}
        for date, signals in grouped_signals.items()
    ]
    signals_by_date.sort(key=lambda x: x["date"], reverse=True)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "signals_by_date": signals_by_date,
            "positions": positions_list,
            "transactions": transactions_list
        }
    )


@app.get("/signals", response_class=HTMLResponse)
async def signals_page(request: Request):
    """
    信号页面
    """
    # 获取最新信号（更多条）
    latest_signals = db.get_latest_trader_signals(limit=50)

    # 清理 NaN 值
    latest_signals = clean_dataframes(latest_signals)

    # 转换为字典并清理剩余 NaN
    signals_list = []
    if not latest_signals.empty:
        for record in latest_signals.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            signals_list.append(cleaned_record)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "latest_signals": signals_list,
            "positions": [],
            "transactions": []
        }
    )


@app.get("/trading", response_class=HTMLResponse)
async def trading_page(request: Request):
    """
    交易页面
    """
    # 获取当前持仓
    positions = db.get_positions()

    # 获取最近交易记录
    transactions = db.get_transactions()[:50]  # 获取前50条

    # 清理 NaN 值
    positions, transactions = clean_dataframes(positions, transactions)

    # 转换为字典并清理剩余 NaN
    positions_list = []
    if not positions.empty:
        for record in positions.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            positions_list.append(cleaned_record)

    transactions_list = []
    if not transactions.empty:
        for record in transactions.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            transactions_list.append(cleaned_record)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "latest_signals": [],
            "positions": positions_list,
            "transactions": transactions_list
        }
    )


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """
    历史信号页面 - 按日期分组展示
    """
    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
        }
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "database": "connected"}


if __name__ == "__main__":
    import uvicorn
    logger.info("启动AITrader Web应用...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
