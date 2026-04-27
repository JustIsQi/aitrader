"""把日序列切到 train / holdout 窗口。"""
from __future__ import annotations

import pandas as pd


def split_by_window(
    series: pd.Series | pd.DataFrame,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
) -> pd.Series | pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if isinstance(series, (pd.Series, pd.DataFrame)):
        mask = (series.index >= start_ts) & (series.index <= end_ts)
        return series.loc[mask]
    raise TypeError("仅支持 pandas Series / DataFrame")
