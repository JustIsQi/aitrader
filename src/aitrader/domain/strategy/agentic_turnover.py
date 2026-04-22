# 策略中文名：stocks_Agentic换手率因子策略

"""
A股换手率因子策略 (Agentic AI Inspired)

论文来源: "Beyond Prompting: An Autonomous Framework for Systematic Factor Investing via Agentic AI"
ArXiv: 2603.14288v2  作者: Allen Yikuan Huang, Zheqi Fan (北京大学 / 香港科技大学)
发布日期: 2026-03-15

核心发现:
- Agentic AI 自主发现的 12 个因子全部基于换手率动态
- 复合因子线性组合在美股 OOS 2021-2024 实现 Sharpe 2.75，年化收益 54.81%
- 因子主题：换手率冲击、持续性、稳定性、均值回归

A股适配理由:
- 换手率在 A 股（散户主导市场）尤为重要，直接反映散户关注度与资金流入
- 换手率动态捕捉流动性冲击和投资者注意力效应，在 A 股中信号更强
- 无需高频数据、新闻数据或 NLP 基础设施，仅用日频 OHLCV + 换手率
- 论文作者来自中国高校，具有中国市场研究背景

因子实现（对应论文 Exhibit 15 中 12 个因子的简化版）:
  F1  FlowShock          换手率冲击     (turnover - ma20) / ma20          权重 25%
  F2  TurnoverMomentum   换手率动量     ma5 / ma20                        权重 20%
  F3  SmoothedFlowShock  平滑冲击       (ma5 - ma20) / ma20               权重 20%
  F4  DefensiveMeanRev   防御均值回归   (ma20_close - close) / close      权重 15%
  F5  SustainedAttention 持续关注度     LOG(ma20_turnover + 1)            权重 20%
"""

import sys
from aitrader.domain.backtest.engine import Task, Engine
from aitrader.domain.market.stock_universe import StockUniverse


# ── 复合因子表达式 ─────────────────────────────────────────────────────────────
_COMPOSITE_SIGNAL = (
    # F1: 换手率冲击 — 当前换手率偏离 20 日均值的程度（异常关注度）
    'normalize_score((turnover_rate - ma(turnover_rate,20)) / ma(turnover_rate,20)) * 0.25 + '
    # F2: 换手率动量 — 短期(5日)与中期(20日)换手率之比（关注度加速）
    'normalize_score(ma(turnover_rate,5) / ma(turnover_rate,20)) * 0.20 + '
    # F3: 平滑换手率冲击 — 5日均与20日均之差（去噪后的流量冲击）
    'normalize_score((ma(turnover_rate,5) - ma(turnover_rate,20)) / ma(turnover_rate,20)) * 0.20 + '
    # F4: 防御性均值回归 — 价格低于20日均线（低波动下的错误定价修正）
    'normalize_score((ma(close,20) - close) / close) * 0.15 + '
    # F5: 持续关注度 — 20日均换手率的对数（防止极端值主导，捕捉持续注意力）
    'normalize_score(LOG(ma(turnover_rate,20) + 1)) * 0.20'
)


def agentic_turnover_strategy_weekly():
    """
    周频换手率因子策略

    策略逻辑:
    1. 股票池: 全市场剔除 ST、停牌、上市不足 1 年新股
    2. 买入过滤: 流动性 + 估值 + 长期趋势（满足 3/4 条件）
    3. 排序: 按复合换手率因子评分从高到低
    4. 持仓: 前 20 只，等权重
    5. 调仓: 每周
    6. 卖出: 流动性枯竭 / 跌破均线 / 强势下跌（满足任一）
    """
    t = Task()
    t.name = 'A股换手率因子策略-周频'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'   # 提前一年加载，保证60日均线在2020-01-01已可用
    t.end_date = '20241231'

    # min_data_days=2500 ≈ 2019-01-01之前约7年，确保回测从2019年开始时
    # 所有入池股票都已有足够历史（60日均线等指标可算），同时排除退市股
    universe = StockUniverse()
    t.symbols = universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=None,
        min_data_days=2500,             # 约7年历史，确保2019-01-01前已上市
        exclude_restricted_stocks=True,
        as_of_date=t.end_date,
    )

    # 买入条件（至少满足 2 个）— 宽松版以保证足够候选池
    t.select_buy = [
        'turnover_rate > 0.3',           # 最低换手率（主板大盘股均值约0.5%）
        'pe > 0 and pe < 100',           # 盈利且估值合理
        'close > ma(close,60)',          # 60 日均线上方（长期趋势向上）
        'volume > ma(volume,20) * 0.3',  # 成交量不低于 20 日均量的 30%
    ]
    t.buy_at_least_count = 2

    # 卖出条件（满足任一即卖出）
    t.select_sell = [
        'turnover_rate < 0.3',           # 换手率极低，流动性枯竭
        'close < ma(close,20) * 0.92',   # 跌破 20 日均线 8%
        'roc(close,20) < -0.15',         # 20 日跌幅超 15%
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = _COMPOSITE_SIGNAL
    t.order_by_topK = 20
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    return t


def agentic_turnover_strategy_monthly():
    """月频版本（低换手，适合资金量较大的账户）"""
    t = agentic_turnover_strategy_weekly()
    t.name = 'A股换手率因子策略-月频'
    t.period = 'RunMonthly'
    t.order_by_topK = 30
    return t


def agentic_turnover_strategy_conservative():
    """
    保守版本：加强估值过滤 + 减少持仓数量
    适合风险偏好较低的投资者
    """
    t = agentic_turnover_strategy_weekly()
    t.name = 'A股换手率因子策略-保守版'
    t.select_buy = [
        'turnover_rate > 1.5',
        'pe > 0 and pe < 60',
        'pb > 0 and pb < 5',
        'close > ma(close,60)',
        'roc(close,20) > -0.05',
    ]
    t.buy_at_least_count = 4
    t.order_by_topK = 15
    return t


# ── 入口 ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    version = sys.argv[1] if len(sys.argv) > 1 else 'weekly'

    if version == 'monthly':
        task = agentic_turnover_strategy_monthly()
    elif version == 'conservative':
        task = agentic_turnover_strategy_conservative()
    else:
        task = agentic_turnover_strategy_weekly()

    print(f"\n{'='*60}")
    print(f"策略名称:   {task.name}")
    print(f"股票池数量: {len(task.symbols)}")
    print(f"调仓周期:   {task.period}")
    print(f"持仓数量:   {task.order_by_topK}")
    print(f"{'='*60}\n")

    engine = Engine()
    result = engine.run(task)

    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    result.stats()
