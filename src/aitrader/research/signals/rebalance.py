"""调仓日历工具。"""
from __future__ import annotations

from typing import Literal

import pandas as pd


def weekly_rebalance_dates(index: pd.DatetimeIndex, warmup_days: int = 60) -> list[pd.Timestamp]:
    out: list[pd.Timestamp] = []
    last_week: tuple[int, int] | None = None
    for i, dt in enumerate(index):
        iso = dt.isocalendar()
        wk = (int(iso.year), int(iso.week))
        if wk != last_week:
            last_week = wk
            if i >= warmup_days:
                out.append(dt)
    return out


def monthly_rebalance_dates(index: pd.DatetimeIndex, warmup_days: int = 60) -> list[pd.Timestamp]:
    out: list[pd.Timestamp] = []
    last_month: tuple[int, int] | None = None
    for i, dt in enumerate(index):
        mk = (int(dt.year), int(dt.month))
        if mk != last_month:
            last_month = mk
            if i >= warmup_days:
                out.append(dt)
    return out


def rebalance_dates_for(
    index: pd.DatetimeIndex,
    freq: Literal["W", "M"],
    warmup_days: int,
) -> list[pd.Timestamp]:
    if freq == "W":
        return weekly_rebalance_dates(index, warmup_days)
    if freq == "M":
        return monthly_rebalance_dates(index, warmup_days)
    raise ValueError(f"freq 必须为 W 或 M，实际={freq}")
