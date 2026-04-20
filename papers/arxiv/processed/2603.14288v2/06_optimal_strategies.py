# 策略中文名: A股最优策略候选(4 选 1 / 组合)
"""
A 股最优策略候选合集 (修复 03_strategy_code.py 的 5 个根因后的可用版本)

核心设计准则 — 避开本仓库框架 5 个坑:
  1. order_by_signal 必须用"原始值"或"逐股 60d 滚动 z-score", 不能用全样本 normalize_score
     (因为 factor_expr 是 per-stock 调用, normalize_score 会做 per-stock min-max → 横截面不可比)
  2. buy_at_least_count 必须等于条件数 (全部满足), 而不是部分满足
  3. min_data_days 用 250-500 (1-2 年), 而不是 2500, 避免幸存者偏差
  4. exclude_restricted_stocks 按需 (微盘股/反转可放开 300/688)
  5. 多个独立维度的因子, 避免 F2/F3 那种相关性 1.0 的重复计权

候选策略:
  microcap        — 微盘股周频轮动        (total_mv 升序, top 20-50)
  reversal        — 20 日反转 × 流动性     (roc(close,20) 升序 + 换手率过滤)
  turnover_fixed  — 修复版换手率因子      (用 60d 滚动 z-score 替换 normalize_score)
  pb_value        — PB 低估值月频         (1/pb 横截面排序, 仓库无 ROE 字段, 仅用 PB)

所有策略都遵循 A 股交易制度:
  - ashare_mode=True, ashare_commission='v2' (包含印花税+佣金)
  - 周频/月频调仓, 避免 T+1 问题
  - 排除 ST + 长期停牌

性能提示:
  全 A 股 universe (5000+只) 回测 6 年极耗时 (30-60 min / 策略);
  已通过 exclude_restricted_stocks / min_data_days 控制股票池在 2000-3500 只。
  若仍太慢, 可用 AITRADER_FAST=1 跑 2023-2024 2 年快速验证。
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_SRC = Path(__file__).resolve().parents[4] / 'src'
if _REPO_SRC.is_dir() and str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from aitrader.domain.backtest.engine import Task, Engine
from aitrader.domain.market.stock_universe import StockUniverse


# ── 共享: 通用 universe 构造 ─────────────────────────────────────────────────
def _build_universe(include_chinext: bool = True, min_data_days: int = 500) -> list[str]:
    """
    构造干净的 A 股股票池:
      - 排除 ST
      - include_chinext 控制是否放入创业板/科创板
      - min_data_days=500 (≈ 2 年) 平衡"排除极新股"和"避免幸存者偏差"
    """
    universe = StockUniverse()
    return universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=False,
        exclude_new_ipo_days=180,
        min_data_days=min_data_days,
        exclude_restricted_stocks=not include_chinext,
    )


# ============================================================================
# 策略 1: 微盘股周频轮动  (A 股最有效的"傻瓜"alpha 之一)
# ============================================================================
def microcap_weekly() -> Task:
    """
    微盘股策略:
      - 排序: total_mv 升序 (取最小)  ← 这是横截面真信号, 不走 normalize_score
      - 过滤: 价格 > 1 元 (避退市股); 换手率 > 1% (有流动性)
      - 持仓: 30 只, 等权重, 周频
      - 已知风险: 2024.2 微盘股流动性危机, 单月回撤可达 -25%
    """
    t = Task()
    t.name = '微盘股-周频-Top30'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date = '20241231'
    # 仅用主板 (排除创业板/科创板), 减少股票池到 ~3400 只, 且主板才有真正微盘
    t.symbols = _build_universe(include_chinext=False, min_data_days=500)

    t.select_buy = [
        'close > 1.0',
        'turnover_rate > 1.0',
        'volume > ma(volume, 20) * 0.3',
    ]
    t.buy_at_least_count = len(t.select_buy)

    t.select_sell = [
        'turnover_rate < 0.3',
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = 'total_mv'
    t.order_by_topK = 30
    t.order_by_DESC = False

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'
    return t


def microcap_monthly() -> Task:
    """微盘股月频版 (低换手, 实盘更友好)"""
    t = microcap_weekly()
    t.name = '微盘股-月频-Top50'
    t.period = 'RunMonthly'
    t.order_by_topK = 50
    return t


# ============================================================================
# 策略 2: 20 日反转 × 流动性过滤
# ============================================================================
def reversal_weekly() -> Task:
    """
    A 股短期反转因子:
      - 排序: roc(close, 20) 升序 (买跌得最多的)  ← A 股散户过度反应, 短期均值回归
      - 过滤: 流动性 + 排除跌停 (无法买入) + 排除微盘垃圾
      - 持仓: 20 只, 等权重, 周频
    """
    t = Task()
    t.name = '20日反转-周频-Top20'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date = '20241231'
    t.symbols = _build_universe(include_chinext=False, min_data_days=500)

    t.select_buy = [
        'close > 2.0',
        'total_mv > 2000000000',
        'turnover_rate > 1.5',
        'roc(close, 20) < -0.05',
        'roc(close, 1) > -0.095',
    ]
    t.buy_at_least_count = len(t.select_buy)

    t.select_sell = [
        'roc(close, 5) > 0.10',
        'roc(close, 20) < -0.30',
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = 'roc(close, 20)'
    t.order_by_topK = 20
    t.order_by_DESC = False
    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'
    return t


# ============================================================================
# 策略 3: 修复版换手率因子 (论文原意复刻, 不再用 normalize_score)
# ============================================================================
_TURNOVER_ZSCORE_60 = (
    '(turnover_rate - ma(turnover_rate, 60)) / (stddev(turnover_rate, 60) + 1e-9)'
)
_PRICE_TREND_ZSCORE_60 = (
    '(close - ma(close, 60)) / (stddev(close, 60) + 1e-9)'
)
_FIXED_COMPOSITE = f'({_TURNOVER_ZSCORE_60}) * 0.7 + ({_PRICE_TREND_ZSCORE_60}) * 0.3'


def turnover_fixed_weekly() -> Task:
    """
    修复版换手率因子:
      - 排序: 60d 滚动 z-score (换手率 70% + 价格趋势 30%) 降序
      - 不再用 normalize_score (per-stock min-max 不可比)
      - 不再用 F2 (与 F3 重复), 不再用 F4 (与买入过滤反向)
      - 买入条件全部满足
    """
    t = Task()
    t.name = '修复版换手率因子-周频-Top20'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date = '20241231'
    t.symbols = _build_universe(include_chinext=False, min_data_days=500)

    t.select_buy = [
        'close > 2.0',
        'total_mv > 1000000000',
        'turnover_rate > 1.0',
        'close > ma(close, 60)',
        'roc(close, 5) > -0.05',
    ]
    t.buy_at_least_count = len(t.select_buy)

    t.select_sell = [
        'close < ma(close, 20) * 0.92',
        'roc(close, 20) < -0.15',
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = _FIXED_COMPOSITE
    t.order_by_topK = 20
    t.order_by_DESC = True
    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'
    return t


# ============================================================================
# 策略 4: PB 低估值 (低风险, 大容量, 但仓库缺 ROE 只能用 PB)
# ============================================================================
def pb_value_monthly() -> Task:
    """
    PB 低估值策略:
      - 排序: pb 升序 (越低越好)
      - 过滤: 排除 PB 异常股 + 微盘 + 流动性差
      - 持仓: 30 只, 等权重, 月频
    """
    t = Task()
    t.name = 'PB低估值-月频-Top30'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20190101'
    t.end_date = '20241231'
    t.symbols = _build_universe(include_chinext=False, min_data_days=500)

    t.select_buy = [
        'pb > 0.3 and pb < 10',
        'total_mv > 5000000000',
        'turnover_rate > 0.5',
        'close > 3.0',
    ]
    t.buy_at_least_count = len(t.select_buy)

    t.select_sell = [
        'pb > 15',
        'roc(close, 60) < -0.20',
    ]
    t.sell_at_least_count = 1

    t.order_by_signal = 'pb'
    t.order_by_topK = 30
    t.order_by_DESC = False
    t.period = 'RunMonthly'
    t.weight = 'WeightEqually'
    return t


# ── 入口 ──────────────────────────────────────────────────────────────────────
STRATEGY_REGISTRY = {
    'microcap':        microcap_weekly,
    'microcap_m':      microcap_monthly,
    'reversal':        reversal_weekly,
    'turnover_fixed':  turnover_fixed_weekly,
    'pb_value':        pb_value_monthly,
}


def main(name: str) -> None:
    if name not in STRATEGY_REGISTRY:
        print(f'未知策略: {name}\n可选: {list(STRATEGY_REGISTRY.keys())}')
        sys.exit(1)

    task = STRATEGY_REGISTRY[name]()
    print(f"\n{'='*60}")
    print(f'策略: {task.name}')
    print(f'股票池: {len(task.symbols)} 只')
    print(f'调仓: {task.period}, 持仓: {task.order_by_topK}, 排序: {task.order_by_signal} ({"DESC" if task.order_by_DESC else "ASC"})')
    print(f"{'='*60}\n")

    result = Engine().run(task)
    print('\n' + '=' * 60)
    print('回测结果')
    print('=' * 60)
    result.stats()


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'microcap')
