from functools import lru_cache


@lru_cache(maxsize=1)
def get_signals_service():
    from aitrader.app.services.web_services import SignalsService

    return SignalsService()


@lru_cache(maxsize=1)
def get_trading_service():
    from aitrader.app.services.web_services import TradingService

    return TradingService()


@lru_cache(maxsize=1)
def get_analytics_service():
    from aitrader.app.services.web_services import AnalyticsService

    return AnalyticsService()


@lru_cache(maxsize=1)
def get_short_term_service():
    from aitrader.app.services.web_services import ShortTermService

    return ShortTermService()


@lru_cache(maxsize=1)
def get_dashboard_service():
    from aitrader.app.services.web_services import DashboardService

    return DashboardService()
