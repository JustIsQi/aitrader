import numpy as np
import pandas as pd

#from bak.calc_utils import calc_by_symbol


def _numpy_rolling_regress(x, y, window, array=False):
    """
    使用numpy进行滚动线性回归计算

    参数:
    x: 自变量序列
    y: 因变量序列
    window: 窗口大小
    array: 是否返回数组格式

    返回:
    回归系数数组
    """
    # 确保x和y长度相同
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")

    # 初始化结果数组
    coefs = np.full((len(x), 2), np.nan)  # 截距和斜率

    # 逐个窗口计算回归系数
    for i in range(window - 1, len(x)):
        x_window = x[i - window + 1:i + 1]
        y_window = y[i - window + 1:i + 1]

        # 检查窗口内是否有NaN值
        if np.any(np.isnan(x_window)) or np.any(np.isnan(y_window)):
            continue

        # 计算回归系数
        A = np.vstack([x_window, np.ones(len(x_window))]).T
        try:
            slope, intercept = np.linalg.lstsq(A, y_window, rcond=None)[0]
            coefs[i, 0] = intercept
            coefs[i, 1] = slope
        except:
            # 处理线性代数计算错误
            continue

    if array:
        return coefs
    else:
        return coefs[:, 1]  # 默认返回斜率

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
                向量化计算趋势评分：年化收益率 × R平方
                修改为与第二个实现相同的计算逻辑
                :param close: 收盘价序列（np.array或pd.Series）
                :param period: 计算窗口长度，默认25天
                :return: 趋势评分数组，长度与输入相同，前period-1位为NaN
                """
    if len(close) < period:
        return np.full_like(close, np.nan)

    # 创建结果数组
    result = np.full(len(close), np.nan)

    # 对每个窗口进行计算
    for i in range(period - 1, len(close)):
        window = close[i - period + 1:i + 1]

        # 使用与第二个实现相同的回归计算逻辑
        y_raw = window.values
        y = np.log(y_raw)  # 对数转换
        x = np.arange(len(y))
        n = len(x)

        if n < 2:
            result[i] = 0.0
            continue

        sum_x = x.sum()
        sum_y = y.sum()
        sum_x2 = (x ** 2).sum()
        sum_xy = (x * y).sum()
        denominator = n * sum_x2 - sum_x ** 2

        # 处理零分母（完全无波动）
        if abs(denominator) <= 1e-9:
            result[i] = 0.0
            continue

        # 计算斜率/截距
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        # 计算R平方
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum(y ** 2) - (sum_y ** 2) / n
        r_squared = 1 - ss_res / ss_tot if abs(ss_tot) > 1e-9 else 0.0
        r_squared = max(0.0, min(r_squared, 1.0))  # 限制在[0,1]范围

        # 年化收益率
        annualized_return = np.exp(slope * 250) - 1

        # 综合评分
        result[i] = annualized_return * r_squared

    return pd.Series(result, index=close.index)

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

    # 提取斜率系数
    beta = coefs[:, 1]
    print(beta)

    # 将结果保存回DataFrame
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

    # 计算滚动窗口的均值和标准差
    if len(beta) >= M:
        beta_rollwindow = _rolling_window(beta, M)
        beta_mean = np.nanmean(beta_rollwindow, axis=1)
        beta_std = np.nanstd(beta_rollwindow, axis=1)

        # 计算Z-score
        zscore = (beta[M - 1:] - beta_mean) / beta_std

        # 将结果填充到与原始序列相同长度
        len_to_pad = len(high) - len(zscore)
        pad = [np.nan for _ in range(len_to_pad)]
        pad.extend(zscore)

    return pd.Series(pad,index=high.index)


def RSRS_ZSCORE_RIGHT(high,low,N=18,M=600):
    # 计算RSRS斜率、截距和R²
    coefs = _numpy_rolling_regress(
        low.values,
        high.values,
        window=N,
        array=True
    )

    # 提取斜率系数和R²值
    beta = coefs[:, 0]  # 斜率系数
    r_squared = coefs[:, 1]  # R²值

    # 计算滚动窗口的均值和标准差
    if len(beta) >= M:
        beta_rollwindow = _rolling_window(beta, M)
        beta_mean = np.nanmean(beta_rollwindow, axis=1)
        beta_std = np.nanstd(beta_rollwindow, axis=1)

        # 计算标准Z-score
        zscore = (beta[M - 1:] - beta_mean) / beta_std

        # 获取对应的R²值
        r_squared_window = r_squared[M - 1:]

        # 计算右偏标准分: 将负值设为0，正值乘以R²
        right_zscore = zscore * r_squared_window  # np.where(zscore < 0, 0, zscore * r_squared_window)

        # 将结果填充到与原始序列相同长度
        len_to_pad = len(high) - len(right_zscore)
        pad = [np.nan for _ in range(len_to_pad)]
        pad.extend(right_zscore)

    return pd.Series(pad,index=high.index)