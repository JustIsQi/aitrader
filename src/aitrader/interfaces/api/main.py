from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from aitrader.infrastructure.config.logging import logger, setup_logging
from aitrader.infrastructure.config.settings import get_settings
from aitrader.interfaces.api.dependencies import get_dashboard_service
from aitrader.interfaces.api.routers import analytics, short_term_signals, signals, trading
from aitrader.interfaces.web.assets import get_static_dir, get_templates_dir

settings = get_settings()
setup_logging('web.log')
templates = Jinja2Templates(directory=str(get_templates_dir()))


def create_app() -> FastAPI:
    app = FastAPI(
        title='AITrader Web Interface',
        description='Web interface for A-share trading signals and portfolio management',
        version='1.0.0',
    )
    app.mount('/static', StaticFiles(directory=str(get_static_dir())), name='static')
    app.include_router(signals.router, prefix='/api/signals', tags=['signals'])
    app.include_router(trading.router, prefix='/api/trading', tags=['trading'])
    app.include_router(analytics.router, prefix='/api/analytics', tags=['analytics'])
    app.include_router(short_term_signals.router, prefix='/api', tags=['short-term'])

    @app.get('/', response_class=HTMLResponse)
    async def dashboard(request: Request):
        context = get_dashboard_service().dashboard_context()
        return templates.TemplateResponse('index.html', {'request': request, **context})

    @app.get('/signals', response_class=HTMLResponse)
    async def signals_page(request: Request):
        context = get_dashboard_service().signal_page_context()
        return templates.TemplateResponse('index.html', {'request': request, **context})

    @app.get('/history', response_class=HTMLResponse)
    async def history_page(request: Request):
        return templates.TemplateResponse('history.html', {'request': request})

    @app.get('/health')
    async def health_check():
        return {'status': 'healthy', 'database': 'connected'}

    return app


app = create_app()


def main():
    import uvicorn
    logger.info('启动 AITrader Web 应用...')
    uvicorn.run(app, host=settings.web_host, port=settings.web_port)


if __name__ == '__main__':
    main()
