"""
基本面因子库
提供PE、PB、ROE等基本面因子的计算和评分函数

作者: AITrader
日期: 2025-12-29
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict


# ==================== 估值因子 ====================

def pe_score(pe_series: pd.Series) -> pd.Series:
    """
    PE评分(倒数,PE越低分越高)

    Args:
        pe_series: 市盈率序列

    Returns:
        PE评分序列(越高越好)

    Example:
        >>> pe = pd.Series([10, 20, 30, 40])
        >>> scores = pe_score(pe)
        >>> # 返回: [0.1, 0.05, 0.033, 0.025]
    """
    return 1 / (pe_series.replace(0, np.nan) + 1e-6)


def pb_score(pb_series: pd.Series) -> pd.Series:
    """
    PB评分(倒数,PB越低分越高)

    Args:
        pb_series: 市净率序列

    Returns:
        PB评分序列(越高越好)

    Example:
        >>> pb = pd.Series([1, 2, 3, 4])
        >>> scores = pb_score(pb)
        >>> # 返回: [1.0, 0.5, 0.33, 0.25]
    """
    return 1 / (pb_series.replace(0, np.nan) + 1e-6)


def ps_score(ps_series: pd.Series) -> pd.Series:
    """
    PS评分(倒数,PS越低分越高)

    Args:
        ps_series: 市销率序列

    Returns:
        PS评分序列(越高越好)
    """
    return 1 / (ps_series.replace(0, np.nan) + 1e-6)


def value_score(pe: pd.Series, pb: pd.Series, ps: pd.Series,
                weights: Optional[Dict[str, float]] = None) -> pd.Series:
    """
    综合估值评分

    Args:
        pe: 市盈率序列
        pb: 市净率序列
        ps: 市销率序列
        weights: 权重字典,默认{'pe': 0.4, 'pb': 0.3, 'ps': 0.3}

    Returns:
        综合估值评分序列

    Example:
        >>> value_score(pe, pb, ps, weights={'pe': 0.5, 'pb': 0.3, 'ps': 0.2})
    """
    if weights is None:
        weights = {'pe': 0.4, 'pb': 0.3, 'ps': 0.3}

    score = (
        pe_score(pe) * weights['pe'] +
        pb_score(pb) * weights['pb'] +
        ps_score(ps) * weights['ps']
    )

    return score


# ==================== 质量因子 ====================

def roe_score(roe_series: pd.Series) -> pd.Series:
    """
    ROE评分(直接值,ROE越高分越高)

    Args:
        roe_series: 净资产收益率序列

    Returns:
        ROE评分序列

    Example:
        >>> roe = pd.Series([0.05, 0.10, 0.15, 0.20])
        >>> scores = roe_score(roe)
        >>> # 返回: [0.05, 0.10, 0.15, 0.20]
    """
    return roe_series


def roa_score(roa_series: pd.Series) -> pd.Series:
    """
    ROA评分(直接值,ROA越高分越高)

    Args:
        roa_series: 总资产收益率序列

    Returns:
        ROA评分序列
    """
    return roa_series


def profit_margin_score(margin_series: pd.Series) -> pd.Series:
    """
    利润率评分(直接值,利润率越高分越高)

    Args:
        margin_series: 利润率序列

    Returns:
        利润率评分序列
    """
    return margin_series


def operating_margin_score(margin_series: pd.Series) -> pd.Series:
    """
    营业利润率评分(直接值,营业利润率越高分越高)

    Args:
        margin_series: 营业利润率序列

    Returns:
        营业利润率评分序列
    """
    return margin_series


# ==================== 市值因子 ====================

def total_mv_filter(mv_series: pd.Series,
                   min_mv: Optional[float] = None,
                   max_mv: Optional[float] = None) -> pd.Series:
    """
    总市值过滤(单位:亿)

    Args:
        mv_series: 总市值序列
        min_mv: 最小市值
        max_mv: 最大市值

    Returns:
        布尔序列,表示是否在市值范围内

    Example:
        >>> mv = pd.Series([50, 100, 200, 500])
        >>> mask = total_mv_filter(mv, min_mv=50, max_mv=200)
        >>> # 返回: [True, True, True, False]
    """
    mask = pd.Series(True, index=mv_series.index)

    if min_mv is not None:
        mask &= (mv_series >= min_mv)

    if max_mv is not None:
        mask &= (mv_series <= max_mv)

    return mask


def circ_mv_filter(mv_series: pd.Series,
                   min_mv: Optional[float] = None,
                   max_mv: Optional[float] = None) -> pd.Series:
    """
    流通市值过滤(单位:亿)

    Args:
        mv_series: 流通市值序列
        min_mv: 最小市值
        max_mv: 最大市值

    Returns:
        布尔序列,表示是否在市值范围内
    """
    mask = pd.Series(True, index=mv_series.index)

    if min_mv is not None:
        mask &= (mv_series >= min_mv)

    if max_mv is not None:
        mask &= (mv_series <= max_mv)

    return mask


def log_market_cap(mv_series: pd.Series) -> pd.Series:
    """
    对数市值(用于标准化)

    Args:
        mv_series: 市值序列(单位:亿)

    Returns:
        对数市值序列

    Example:
        >>> mv = pd.Series([10, 100, 1000])
        >>> log_mv = log_market_cap(mv)
        >>> # 返回对数值,便于标准化处理
    """
    return np.log(mv_series.replace(0, np.nan) + 1)


def market_cap_category(mv_series: pd.Series) -> pd.Series:
    """
    市值分类

    Args:
        mv_series: 总市值序列(单位:亿)

    Returns:
        分类标签: '大盘'/'中盘'/'小盘'

    Example:
        >>> mv = pd.Series([20, 60, 200, 600])
        >>> category = market_cap_category(mv)
        >>> # 返回: ['小盘', '中盘', '大盘', '大盘']
    """
    categories = pd.Series(index=mv_series.index, dtype=object)

    categories[mv_series < 50] = '小盘'
    categories[(mv_series >= 50) & (mv_series < 200)] = '中盘'
    categories[mv_series >= 200] = '大盘'

    return categories


# ==================== 综合因子 ====================

def quality_score(pe: pd.Series, pb: pd.Series, roe: pd.Series,
                  weights: Optional[Dict[str, float]] = None) -> pd.Series:
    """
    综合质量评分

    结合PE、PB、ROE的综合评分,评估股票质量

    Args:
        pe: 市盈率序列
        pb: 市净率序列
        roe: 净资产收益率序列
        weights: 权重字典,默认{'pe': 0.3, 'pb': 0.3, 'roe': 0.4}

    Returns:
        综合质量评分序列(越高越好)

    Example:
        >>> quality_score(pe, pb, roe)
        >>> quality_score(pe, pb, roe, weights={'pe': 0.2, 'pb': 0.2, 'roe': 0.6})
    """
    if weights is None:
        weights = {'pe': 0.3, 'pb': 0.3, 'roe': 0.4}

    score = (
        pe_score(pe) * weights['pe'] +
        pb_score(pb) * weights['pb'] +
        roe * weights['roe']  # ROE直接值
    )

    return score


def fundamental_rank_score(**factors) -> pd.Series:
    """
    多因子排名评分

    对多个因子进行排名,然后综合评分

    Args:
        **factors: 因子字典,如 {'pe': pe_series, 'roe': roe_series}

    Returns:
        综合排名评分序列

    Example:
        >>> score = fundamental_rank_score(pe=pe_series, roe=roe_series, mv=mv_series)
    """
    if not factors:
        raise ValueError('至少需要一个因子')

    # 对每个因子进行排名
    ranks = {}
    for name, series in factors.items():
        # 降序排名(值越大排名越高)
        ranks[name] = series.rank(pct=True)

    # 综合排名(平均)
    total_score = pd.Series(0.0, index=factors[list(factors.keys())[0]].index)

    for rank in ranks.values():
        total_score += rank

    total_score /= len(ranks)

    return total_score


def growth_score(pe: pd.Series, pb: pd.Series, roe: pd.Series,
                 weights: Optional[Dict[str, float]] = None) -> pd.Series:
    """
    成长评分(Growth)

    适合GARP策略(Growth at Reasonable Price)

    Args:
        pe: 市盈率
        pb: 市净率
        roe: 净资产收益率
        weights: 权重字典

    Returns:
        成长评分
    """
    if weights is None:
        weights = {'pe': 0.2, 'pb': 0.2, 'roe': 0.6}

    # GARP策略更看重成长性(ROE),但同时考虑估值的合理性
    score = (
        pe_score(pe) * weights['pe'] +
        pb_score(pb) * weights['pb'] +
        roe * weights['roe']
    )

    return score


# ==================== 工具函数 ====================

def normalize_score(series: pd.Series, method: str = 'minmax') -> pd.Series:
    """
    标准化因子得分

    Args:
        series: 因子序列
        method: 标准化方法,支持'minmax'或'zscore'

    Returns:
        标准化后的序列(0-1之间)
    """
    if method == 'minmax':
        # Min-Max标准化
        min_val = series.min()
        max_val = series.max()
        if max_val - min_val == 0:
            return pd.Series(0.5, index=series.index)
        return (series - min_val) / (max_val - min_val)

    elif method == 'zscore':
        # Z-Score标准化
        mean_val = series.mean()
        std_val = series.std()
        if std_val == 0:
            return pd.Series(0.0, index=series.index)
        zscore = (series - mean_val) / std_val
        # 转换到0-1区间
        return (zscore - zscore.min()) / (zscore.max() - zscore.min())

    else:
        raise ValueError(f'不支持的标准化方法: {method}')


def winsorize(series: pd.Series, limits: float = 0.05) -> pd.Series:
    """
    去极值处理

    Args:
        series: 因子序列
        limits: 极值比例

    Returns:
        去极值后的序列
    """
    lower = series.quantile(limits)
    upper = series.quantile(1 - limits)

    return series.clip(lower=lower, upper=upper)


if __name__ == '__main__':
    # 测试代码
    print('基本面因子库测试\n')

    # 创建测试数据
    pe = pd.Series([10, 20, 30, 40, 50])
    pb = pd.Series([1, 2, 3, 4, 5])
    roe = pd.Series([0.05, 0.10, 0.15, 0.20, 0.25])
    mv = pd.Series([20, 60, 200, 600, 1000])

    print('PE评分:')
    print(pe_score(pe))

    print('\nPB评分:')
    print(pb_score(pb))

    print('\n综合质量评分:')
    print(quality_score(pe, pb, roe))

    print('\n市值分类:')
    print(market_cap_category(mv))

    print('\n市值过滤(>50且<200):')
    print(total_mv_filter(mv, min_mv=50, max_mv=200))
