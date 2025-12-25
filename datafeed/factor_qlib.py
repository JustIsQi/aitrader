import numpy as np
import pandas as pd

import numpy as np
import pandas as pd


# def sign(se: pd.Series):
#     return np.sign(se)
#
#
# def signed_power(se: pd.Series, a:int):
#     return np.where(se < 0, -np.abs(se) ** a, np.abs(se) ** a)
#
# def log(se: pd.Series):
#     return np.log(se)
#
#
# def abs(se:pd.Series):
#     return np.abs(se)
#
#
# def scale(x:pd.Series, a:int=1):
#     """
#     Scales the array x such that the sum of the absolute values equals a.
#
#     Parameters:
#     x (array-like): The input array to be scaled.
#     a (float, optional): The target sum of absolute values. Default is 1.
#
#     Returns:
#     numpy.ndarray: The scaled array.
#     """
#     import numpy as np
#     x = np.array(x)  # 确保输入是numpy数组
#     sum_abs_x = np.sum(np.abs(x))  # 计算x的绝对值之和
#     if sum_abs_x == 0:
#         raise ValueError("The sum of absolute values of x is zero, cannot scale by a non-zero value.")
#     scale_factor = a / sum_abs_x  # 计算缩放因子
#
#     return pd.Series(x * scale_factor,index=x.index)  # 应用缩放因子
#
# def decay_linear(series:pd.Series, window:int):
#     """
#     对输入的时间序列进行线性衰减。
#
#     :param series: 输入的时间序列。
#     :param window: 衰减的窗口大小。
#     :return: 衰减后的序列。
#     """
#     weights = np.arange(1, window + 1)
#     decay = np.convolve(series, weights, 'valid') / np.sum(weights)
#     decay = pd.Series(decay,index=series.index)
#     return decay
#
#
# def delay(se: pd.Series, periods:int=5):
#     return se.shift(periods=periods)



def delta(se: pd.Series, periods:int=20):
    se_result = se - se.shift(periods=periods)
    return se_result


def ts_min(se: pd.Series, periods:int=5):
    return se.rolling(window=periods).min()


def ts_max(se: pd.Series, periods:int=5):
    return se.rolling(window=periods).max()



def ts_argmin(se: pd.Series, periods:int=5):
    return se.rolling(periods, min_periods=2).apply(lambda x: x.argmin())


def ts_argmax(se: pd.Series, periods:int=5):
    return se.rolling(periods, min_periods=2).apply(lambda x: x.argmax())


def stddev(se:pd.Series, periods:int=5):
    return se.rolling(window=periods).std()


def ts_rank(se: pd.Series, periods:int=9):
    ret = se.rolling(window=periods).rank(pct=True)
    return ret


def sum(se: pd.Series, N:int):
    ret = se.rolling(N).sum()
    ret.name = 'sum_{}'.format(N)
    return ret


def shift(se: pd.Series, N:int):
    return se.shift(N)


def roc(se: pd.Series, N:int):
    return se / shift(se, N) - 1


# def product(se: pd.Series, d:int):
#     return se.rolling(window=d).apply(np.product)


# def zscore(se: pd.Series, N:int):
#     def _zscore(x):
#
#         try:
#             x.dropna(inplace=True)
#             #print('sub', x)
#             value = (x[-1] - x.mean()) / x.std()
#             if value:
#                 return value
#         except:
#             return -1
#
#     ret = se.rolling(window=N).apply(lambda x: _zscore(x))
#     return ret
