from aitrader.infrastructure.config.settings import get_settings


def get_static_dir():
    return get_settings().static_dir


def get_templates_dir():
    return get_settings().templates_dir
