"""Compatibility shim"""
import sys; from pathlib import Path as _P
_src = str(_P(__file__).resolve().parent.parent / "src")
if _src not in sys.path: sys.path.insert(0, _src)
from aitrader.domain.strategy.multi_factor import *  # noqa
