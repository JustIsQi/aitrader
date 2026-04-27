from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from aitrader.shared.utils.paths import project_root


@dataclass(frozen=True)
class Settings:
    project_root: Path
    logs_dir: Path
    database_url: str
    mysql_host: str | None
    mysql_port: int
    mysql_user: str | None
    mysql_password: str | None
    mysql_database: str | None
    log_level: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    root = project_root()
    load_dotenv(root / '.env')
    return Settings(
        project_root=root,
        logs_dir=root / 'logs',
        database_url=os.getenv('DATABASE_URL', 'sqlite:///aitrader.db'),
        mysql_host=os.getenv('MYSQL_HOST'),
        mysql_port=int(os.getenv('MYSQL_PORT', '3306')),
        mysql_user=os.getenv('MYSQL_USER'),
        mysql_password=os.getenv('MYSQL_PASSWORD'),
        mysql_database=os.getenv('MYSQL_DATABASE'),
        log_level=os.getenv('AITRADER_LOG_LEVEL', 'INFO'),
    )
