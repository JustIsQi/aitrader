import numpy as np
import pandas as pd

#from bak.calc_utils import calc_by_symbol


def _rolling_regression_metrics(x: np.ndarray, y: np.ndarray, window: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(x) != len(y):
        raise ValueError('x and y must have the same length')

    metrics = np.full((len(x), 3), np.nan, dtype=float)
    if window <= 1 or len(x) < window:
        return metrics

    from numpy.lib.stride_tricks import sliding_window_view

    xw = sliding_window_view(x, window)
    yw = sliding_window_view(y, window)
    valid = np.isfinite(xw).all(axis=1) & np.isfinite(yw).all(axis=1)
    if not np.any(valid):
        return metrics

    sum_x = xw.sum(axis=1)
    sum_x2 = np.square(xw).sum(axis=1)
    sum_y = yw.sum(axis=1)
    sum_y2 = np.square(yw).sum(axis=1)
    sum_xy = np.sum(xw * yw, axis=1)

    denom = window * sum_x2 - sum_x ** 2
    fit_valid = valid & (np.abs(denom) > 1e-12)
    if not np.any(fit_valid):
        return metrics

    slope = np.full(len(xw), np.nan, dtype=float)
    intercept = np.full(len(xw), np.nan, dtype=float)
    slope[fit_valid] = (window * sum_xy[fit_valid] - sum_x[fit_valid] * sum_y[fit_valid]) / denom[fit_valid]
    intercept[fit_valid] = (sum_y[fit_valid] - slope[fit_valid] * sum_x[fit_valid]) / window

    residual = yw[fit_valid] - (slope[fit_valid][:, None] * xw[fit_valid] + intercept[fit_valid][:, None])
    ss_res = np.square(residual).sum(axis=1)
    ss_tot = sum_y2[fit_valid] - (sum_y[fit_valid] ** 2) / window
    r_squared = np.where(np.abs(ss_tot) > 1e-12, 1 - ss_res / ss_tot, 0.0)
    r_squared = np.clip(r_squared, 0.0, 1.0)

    metrics_window = metrics[window - 1:]
    metrics_window[:, 0] = intercept
    metrics_window[:, 1] = slope
    metrics_window[fit_valid, 2] = r_squared
    return metrics


def _numpy_rolling_regress(x, y, window, array=False):
    """
    Use vectorized rolling linear regression.
    
    Returns intercept, slope and R^2 for each point. When array=False,
    preserves the legacy slope-only return value.
    """
    metrics = _rolling_regression_metrics(x, y, window)
    if array:
        return metrics
    return metrics[:, 1]

def _rolling_window(a: np.ndarray, window: int) -> np.ndarray:
    """
    创建滚动窗口视图

    参数:
    a: 输入数组
    window: 窗口大小

    返回:
    滚动窗口数组
    """
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)

def trend_score(close: pd.Series, period:int=25):
    """
                Vectorized trend score: annualized return times R-squared.
                """
    close_series = pd.Series(close)
    if len(close_series) < period:
        return pd.Series(np.full(len(close_series), np.nan), index=close_series.index)

    values = close_series.to_numpy(dtype=float, copy=False)
    with np.errstate(divide='ignore', invalid='ignore'):
        log_values = np.log(values)

    from numpy.lib.stride_tricks import sliding_window_view

    windows = sliding_window_view(log_values, period)
    valid = np.isfinite(windows).all(axis=1)
    result = np.full(len(values), np.nan, dtype=float)
    if not np.any(valid):
        return pd.Series(result, index=close_series.index)

    x = np.arange(period, dtype=float)
    sum_x = x.sum()
    sum_x2 = np.square(x).sum()
    denom = period * sum_x2 - sum_x ** 2
    if abs(denom) <= 1e-12:
        return pd.Series(result, index=close_series.index)

    sum_y = windows.sum(axis=1)
    sum_xy = windows @ x
    slope = np.full(len(windows), np.nan, dtype=float)
    intercept = np.full(len(windows), np.nan, dtype=float)
    slope[valid] = (period * sum_xy[valid] - sum_x * sum_y[valid]) / denom
    intercept[valid] = (sum_y[valid] - slope[valid] * sum_x) / period

    residual = windows[valid] - (slope[valid][:, None] * x + intercept[valid][:, None])
    ss_res = np.square(residual).sum(axis=1)
    ss_tot = np.square(windows[valid]).sum(axis=1) - (sum_y[valid] ** 2) / period
    r_squared = np.where(np.abs(ss_tot) > 1e-12, 1 - ss_res / ss_tot, 0.0)
    r_squared = np.clip(r_squared, 0.0, 1.0)

    annualized_return = np.exp(slope[valid] * 250) - 1
    result_indices = np.flatnonzero(valid) + period - 1
    result[result_indices] = annualized_return * r_squared

    return pd.Series(result, index=close_series.index)

def _bbands(series: pd.Series, N: int = 20, K: float = 2) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算布林带
    :param price_series: 价格序列（一般为收盘价）
    :param N: 移动平均窗口大小（默认20）
    :param K: 标准差乘数（默认2）
    :return: (上轨, 中轨, 下轨)
    """
    # 计算中轨（N期移动平均）
    mid_band = series.rolling(N).mean()

    # 计算N期标准差
    std_dev = series.rolling(N).std()

    # 计算上轨和下轨
    upper_band = mid_band + K * std_dev
    lower_band = mid_band - K * std_dev

    return upper_band, mid_band, lower_band

def BBANDS_UP(series: pd.Series, N: int = 20, K: float = 2):
    up,mid,bottom = _bbands(series, N, K)
    return up

def BBANDS_DOWN(series: pd.Series, N: int = 20, K: float = 2):
    up, mid, bottom = _bbands(series, N, K)
    return bottom

def MA(series: pd.Series, N: int) -> pd.Series:
    return series.rolling(N).mean()

def RSRS(high: pd.Series, low: pd.Series, N: int = 18) -> pd.Series:
    coefs = _numpy_rolling_regress(
        low.values,
        high.values,
        window=N,
        array=True
    )

    beta = coefs[:, 1]
    return pd.Series(beta, index=high.index)

def RSRS_ZSCORE(high:pd.Series,low:pd.Series,N:int=18,M:int=600):
    # 计算RSRS斜率
    coefs = _numpy_rolling_regress(
        low.values,
        high.values,
        window=N,
        array=True
    )
    beta = coefs[:, 1]  # 斜率系数

    if len(beta) < M:
        return pd.Series(np.full(len(high), np.nan), index=high.index)

    beta_rollwindow = _rolling_window(beta, M)
    beta_mean = np.nanmean(beta_rollwindow, axis=1)
    beta_std = np.nanstd(beta_rollwindow, axis=1)

    zscore = (beta[M - 1:] - beta_mean) / beta_std

    len_to_pad = len(high) - len(zscore)
    pad = np.full(len(high), np.nan, dtype=float)
    pad[len_to_pad:] = zscore
    return pd.Series(pad, index=high.index)

def RSRS_ZSCORE_RIGHT(high,low,N=18,M=600):
    # 计算RSRS斜率、截距和R²
    coefs = _numpy_rolling_regress(
        low.values,
        high.values,
        window=N,
        array=True
    )

    beta = coefs[:, 1]  # 斜率系数
    r_squared = coefs[:, 2]  # R²值

    if len(beta) < M:
        return pd.Series(np.full(len(high), np.nan), index=high.index)

    beta_rollwindow = _rolling_window(beta, M)
    beta_mean = np.nanmean(beta_rollwindow, axis=1)
    beta_std = np.nanstd(beta_rollwindow, axis=1)

    zscore = (beta[M - 1:] - beta_mean) / beta_std
    r_squared_window = r_squared[M - 1:]
    right_zscore = zscore * r_squared_window

    len_to_pad = len(high) - len(right_zscore)
    pad = np.full(len(high), np.nan, dtype=float)
    pad[len_to_pad:] = right_zscore
    return pd.Series(pad, index=high.index)
