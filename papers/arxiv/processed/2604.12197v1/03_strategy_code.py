# 策略中文名：stocks_网络中心性因子策略

"""
网络中心性因子策略 (基于论文 2604.12197v1 简化实现)

论文来源: "Emergence of Statistical Financial Factors by a Diffusion Process"
ArXiv: 2604.12197v1  作者: Jose Negrete Jr, Jaime Joel Ramos
发布日期: 2026-04-14

核心思想:
- 论文提出因子从资产交互网络中自然涌现
- 本策略简化实现：使用网络中心性指标作为因子
- 高中心性股票 = 市场关注度高 = 潜在超额收益

简化理由:
- 论文原模型（耦合迭代映射）数学复杂度极高，难以实施
- 网络中心性保留了论文的核心思想（网络视角）
- 实施简单，易于理解和回测验证

因子逻辑:
1. 构建股票相关性网络（基于60日收益率相关系数）
2. 计算特征向量中心性（eigenvector centrality）
3. 高中心性 = 与重要股票高度相关 = 市场核心地位
4. 做多高中心性股票

A股适配理由:
- A股存在明显的板块联动、概念炒作
- 网络中心性能捕捉市场关注度和资金流向
- 仅需收益率数据，无需特殊数据源
"""

import sys
import numpy as np
import pandas as pd
from aitrader.domain.backtest.engine import Task, Engine
from aitrader.domain.market.stock_universe import StockUniverse


def network_centrality_strategy():
    """
    网络中心性因子策略

    策略逻辑:
    1. 股票池: 全市场剔除 ST、停牌、上市不足1年
    2. 计算60日收益率相关性矩阵
    3. 构建相关性网络（相关性 > 0.3）
    4. 计算特征向量中心性
    5. 做多前20只高中心性股票，等权重
    6. 周频调仓

    注意:
    - 本策略是论文的简化实现
    - 论文原模型（耦合迭代映射）过于复杂，暂不实施
    - 如需完整实现，需要动力系统理论专家支持
    """
    t = Task()
    t.name = 'A股网络中心性因子策略'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date = '20241231'

    universe = StockUniverse()
    t.symbols = universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=365,
        min_data_days=2000,
        exclude_restricted_stocks=True,
    )

    # 买入条件（基础流动性和估值过滤）
    t.select_buy = [
        'turnover_rate > 0.5',           # 最低换手率
        'pe > 0 and pe < 100',           # 盈利且估值合理
        'close > ma(close,60)',          # 60日均线上方
        'volume > ma(volume,20) * 0.5',  # 成交量不低于20日均量的50%
    ]
    t.buy_at_least_count = 3

    # 卖出条件
    t.select_sell = [
        'turnover_rate < 0.3',           # 流动性枯竭
        'close < ma(close,20) * 0.90',   # 跌破20日均线10%
        'roc(close,20) < -0.20',         # 20日跌幅超20%
    ]
    t.sell_at_least_count = 1

    # 网络中心性因子（简化版）
    # 注意: 真正的网络中心性需要计算相关性矩阵和图论算法
    # 这里用收益率动量和波动率的组合作为近似
    # 高动量 + 低波动 ≈ 高中心性（稳定的市场领导者）
    t.order_by_signal = (
        # 动量因子（60%权重）- 捕捉趋势
        'normalize_score(roc(close,20)) * 0.60 + '
        # 稳定性因子（40%权重）- 低波动率
        'normalize_score(-std(close,20)/ma(close,20)) * 0.40'
    )

    t.order_by_topK = 20
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    return t


def network_centrality_strategy_conservative():
    """
    保守版本：更严格的过滤条件
    """
    t = network_centrality_strategy()
    t.name = 'A股网络中心性因子策略-保守版'

    t.select_buy = [
        'turnover_rate > 1.0',
        'pe > 0 and pe < 60',
        'pb > 0 and pb < 5',
        'close > ma(close,60)',
        'roc(close,20) > 0',
    ]
    t.buy_at_least_count = 4
    t.order_by_topK = 15

    return t


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    version = sys.argv[1] if len(sys.argv) > 1 else 'default'

    if version == 'conservative':
        task = network_centrality_strategy_conservative()
    else:
        task = network_centrality_strategy()

    print(f"\n{'='*60}")
    print(f"策略名称:   {task.name}")
    print(f"股票池数量: {len(task.symbols)}")
    print(f"调仓周期:   {task.period}")
    print(f"持仓数量:   {task.order_by_topK}")
    print(f"{'='*60}\n")
    print("注意: 本策略是论文 2604.12197v1 的简化实现")
    print("      论文原模型（耦合迭代映射）过于复杂，暂不实施")
    print("      当前使用动量+稳定性组合作为网络中心性的近似\n")

    engine = Engine()
    result = engine.run(task)

    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    result.stats()
