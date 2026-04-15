from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def project_root() -> Path:
    configured = os.getenv('AITRADER_PROJECT_ROOT')
    if configured:
        return Path(configured).expanduser().resolve()

    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / 'README.md').exists() and (candidate / 'requirements.txt').exists():
            return candidate
    return current.parents[5]
