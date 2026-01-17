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
    主仪表板页面 - 分别显示ETF和A股信号
    """
    # 获取当前持仓
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
            positions_dict[symbol] = position_data
            positions_dict[f"{symbol}.SH"] = position_data
            positions_dict[f"{symbol}.SZ"] = position_data

    # Get ETF signals separately
    from web.routers.signals import get_latest_etf_signals
    etf_result = await get_latest_etf_signals(limit=50)
    etf_date = etf_result.get("date")
    etf_signals = etf_result.get("signals", [])

    # Enrich ETF signals with position data
    for signal in etf_signals:
        symbol = signal.get('symbol')
        if symbol and symbol in positions_dict:
            signal['position'] = positions_dict[symbol]

    # Get A-share signals with backtests (split by weekly/monthly)
    from web.routers.signals import get_latest_ashare_signals
    ashare_result = await get_latest_ashare_signals(limit=50)
    ashare_weekly = ashare_result.get("weekly", {})
    ashare_monthly = ashare_result.get("monthly", {})

    # Enrich A-share weekly signals with position data
    for signal in ashare_weekly.get("signals", []):
        symbol = signal.get('symbol')
        if symbol and symbol in positions_dict:
            signal['position'] = positions_dict[symbol]

    # Enrich A-share monthly signals with position data
    for signal in ashare_monthly.get("signals", []):
        symbol = signal.get('symbol')
        if symbol and symbol in positions_dict:
            signal['position'] = positions_dict[symbol]

    # Get recent transactions
    transactions = db.get_transactions()[:20]
    positions, transactions = clean_dataframes(positions, transactions)

    # Convert to list
    positions_list = []
    if not positions.empty:
        # Fetch ETF names and stock company abbreviations
        symbols = positions['symbol'].tolist()
        etf_name_map = db.batch_get_etf_names(symbols) if symbols else {}
        stock_name_map = db.batch_get_company_abbr(symbols) if symbols else {}

        for record in positions.to_dict('records'):
            cleaned_record = {k: safe_dict_value(v) for k, v in record.items()}
            symbol = record['symbol']
            # Add ETF name or stock company abbreviation
            cleaned_record['etf_name'] = etf_name_map.get(symbol, '')
            cleaned_record['stock_name'] = stock_name_map.get(symbol, '')
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
            "etf_date": etf_date,
            "etf_signals": etf_signals,
            "ashare_weekly_date": ashare_weekly.get("date"),
            "ashare_weekly_signals": ashare_weekly.get("signals", []),
            "ashare_monthly_date": ashare_monthly.get("date"),
            "ashare_monthly_signals": ashare_monthly.get("signals", []),
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
