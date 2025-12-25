import numpy as np
import pandas as pd
import polars as pl

from .utility import DataProxy


def to_pd_series(feature: DataProxy) -> pd.Series:
    """Convert to pandas.Series data structure"""
    return feature.df.to_pandas().set_index(["date", "symbol"])["data"]


def to_pl_dataframe(series: pd.Series) -> pl.DataFrame:
    """Convert to polars.DataFrame data structure"""
    return pl.from_pandas(series.reset_index().rename(columns={0: "data"}))


def _linear_regression_params(y_raw: np.ndarray) -> tuple[float, float, float]:
    """复用核心逻辑：对数转换 + 回归参数计算（斜率、截距、R平方）
    返回值：(slope, intercept, r_squared)
    """
    # === 与第一个函数完全一致的计算逻辑 ===
    y = np.log(y_raw)  # 对数转换
    x = np.arange(len(y))
    n = len(x)

    if n < 2:
        return (np.nan, np.nan, 0.0)  # 窗口不足返回NaN

    sum_x = x.sum()
    sum_y = y.sum()
    sum_x2 = (x ** 2).sum()
    sum_xy = (x * y).sum()
    denominator = n * sum_x2 - sum_x ** 2

    # 处理零分母（完全无波动）
    if denominator <= 1e-9:
        return (0.0, sum_y / n, 0.0)

    # 计算斜率/截距
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    # 计算R平方
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum(y ** 2) - (sum_y ** 2) / n
    r_squared = 1 - ss_res / ss_tot if ss_tot > 1e-9 else 0.0
    r_squared = max(0.0, min(r_squared, 1.0))  # 限制在[0,1]范围

    return (slope, intercept, r_squared)


# --------- 复用后的斜率计算函数 ---------
def ts_slope2(feature: DataProxy, window: int) -> DataProxy:
    """复用核心逻辑计算年化收益率"""

    def calc_slope(s: pl.Series) -> float:
        slope, _, _ = _linear_regression_params(s.to_numpy())
        return np.exp(slope * 250) - 1 if not np.isnan(slope) else np.nan

    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        pl.col("data").rolling_map(
            lambda s: calc_slope(s),
            window_size=window
        ).over("symbol")
    )
    return DataProxy(df)


# --------- 复用后的R平方计算函数 ---------
def ts_rsquare2(feature: DataProxy, window: int) -> DataProxy:
    """复用核心逻辑计算R平方"""

    def calc_rsquare(s: pl.Series) -> float:
        _, _, r2 = _linear_regression_params(s.to_numpy())
        return r2

    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        pl.col("data").rolling_map(
            lambda s: calc_rsquare(s),
            window_size=window
        ).over("symbol")
    )
    return DataProxy(df)


# 趋势评分函数保持不变
def trend_score(feature: DataProxy, window: int) -> DataProxy:
    return ts_slope2(feature, window) * ts_rsquare2(feature, window)


def roc(feature: DataProxy, window: int) -> DataProxy:
    """计算给定窗口期的变动率（Rate of Change）"""
    df: pl.DataFrame = feature.df.select(
        pl.col("date"),
        pl.col("symbol"),
        # ROC 公式: (当前值 - N周期前值) / N周期前值
        (
            (pl.col("data") - pl.col("data").shift(window).over("symbol"))
            / pl.col("data").shift(window).over("symbol")

        ).alias("data")  # 结果命名为 data，保持结构一致
    )
    return DataProxy(df)

import numpy as np
import polars as pl

def ATR(feature_high: DataProxy, feature_low: DataProxy, feature_close: DataProxy, window: int) -> DataProxy:
    """
    Calculate ATR (Average True Range) using Polars.

    Parameters:
    feature_high (DataProxy): DataProxy containing 'date', 'symbol', and 'data' columns for high prices.
    feature_low (DataProxy): DataProxy containing 'date', 'symbol', and 'data' columns for low prices.
    feature_close (DataProxy): DataProxy containing 'date', 'symbol', and 'data' columns for close prices.
    window (int): The window size for calculating ATR.

    Returns:
    DataProxy: DataProxy containing 'date', 'symbol', and 'atr' columns.
    """
    # 合并高点、低点和收盘价数据
    merged = feature_high.df.join(feature_low.df, on=["date", "symbol"]).join(feature_close.df, on=["date", "symbol"])
    merged = merged.rename({"data": "high", "data": "low", "data": "close"})

    # 计算 True Range (TR)
    merged = merged.with_columns(
        pl.col("high").cast(pl.Float64).alias("high"),
        pl.col("low").cast(pl.Float64).alias("low"),
        pl.col("close").cast(pl.Float64).alias("close"),
    )

    # 计算 TR 的三个组成部分
    tr1 = (merged["high"] - merged["low"]).alias("tr1")
    tr2 = (merged["high"] - merged["close"].shift(1)).abs().alias("tr2")
    tr3 = (merged["low"] - merged["close"].shift(1)).abs().alias("tr3")

    # 合并 TR 的三个部分并取最大值
    merged = merged.with_columns(
        pl.concat_list([tr1, tr2, tr3]).arr.max().alias("tr")
    )

    # 使用 rolling_map 计算 ATR
    atr = merged.with_columns(
        pl.col("tr")
        .rolling_map(lambda s: s.mean(), window)
        .over("symbol")
        .alias("atr")
    )

    return DataProxy(atr.select(pl.col("date"), pl.col("symbol"), pl.col("atr")))

def RSRS(high: pl.DataFrame, low: pl.DataFrame, window: int) -> pl.DataFrame:
    """Calculate RSRS (Relative Strength Slope) indicator"""

    # 合并高点和低点数据，按日期和symbol对齐
    combined = (
        high.select(pl.col("date"), pl.col("symbol"), pl.col("data").alias("high"))
        .join(
            low.select(pl.col("date"), pl.col("symbol"), pl.col("data").alias("low")),
            on=["date", "symbol"]
        )
    )

    # 计算高点和低点的回归斜率
    rsrs = combined.with_columns(
        pl.col("high")
        .rolling_map(
            lambda s: 0.0 if len(s) < window else np.polyfit(np.arange(window), s[-window:], 1)[0],
            window,
            min_periods=window
        )
        .over("symbol")
        .alias("high_slope"),
        pl.col("low")
        .rolling_map(
            lambda s: 0.0 if len(s) < window else np.polyfit(np.arange(window), s[-window:], 1)[0],
            window,
            min_periods=window
        )
        .over("symbol")
        .alias("low_slope")
    )

    # 计算RSRS指标（高点斜率与低点斜率的比值）
    rsrs = rsrs.with_columns(
        (pl.col("high_slope") / pl.col("low_slope")).alias("rsrs")
    )

    return rsrs.select(pl.col("date"), pl.col("symbol"), pl.col("rsrs"))