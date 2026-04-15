import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aitrader.interfaces.api.main import create_app


def test_create_app_registers_core_routes():
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/" in paths
    assert "/health" in paths
    assert "/api/signals/latest" in paths
    assert "/api/trading/positions" in paths
    assert "/api/short-term/summary" in paths
