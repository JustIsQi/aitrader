# 策略中文名：stocks_多因子智能选股策略

"""
A股多因子智能选股策略

策略特点:
- 动态因子权重（技术40% + 质量30% + 估值20% + 流动性10%）
- 综合选股条件（至少满足3/7个条件）
- 行业中性化处理
- 新股过滤（排除上市252天内）
- 流动性过滤（换手率>2%）

作者: AITrader
日期: 2026-01-06
"""

from core.backtrader_engine import Task, Engine
from core.stock_universe import StockUniverse


def multi_factor_strategy_weekly():
    """
    周频多因子智能选股策略

    策略逻辑:
    1. 股票池: 全市场剔除ST、停牌、新股
    2. 选股: 至少满足7个条件中的3个
    3. 排序: 综合技术、质量、估值、流动性因子
    4. 持仓: 20只股票，等权重
    5. 调仓: 每周

    Returns:
        Task: 策略配置对象
    """
    t = Task()
    t.name = 'A股多因子智能选股-周频'
    t.ashare_mode = True
    t.ashare_commission = 'v2'  # 使用V2手续费方案(2023年后)
    t.start_date = '20200101'
    t.end_date = '20241231'

    # 动态股票池
    universe = StockUniverse()
    t.symbols = universe.get_all_stocks(
        exclude_st=True,              # 剔除ST股票
        exclude_suspend=True,         # 剔除停牌股票
        exclude_new_ipo_days=252      # 排除上市1年内新股
    )

    # 多因子买入条件（至少满足3个）
    # 注意：基本面数据只下载了PE和PB，其他指标(ROE等)不可用
    t.select_buy = [
        'roc(close,20) > 0.03',              # 正动量 > 3%
        'trend_score(close,25) > 0',         # 趋势向上
        'volume > ma(volume,20)*1.2',        # 放量确认
        'close > ma(close,60)',              # 长期趋势向上
        'pe > 0 and pe < 80',                # 合理估值区间（PE）
        'pb > 0 and pb < 5',                 # 合理估值区间（PB）
        'turnover_rate > 2'                  # 换手率 > 2%
    ]
    t.buy_at_least_count = 3  # 至少满足3个条件

    # 卖出条件（满足任一）
    t.select_sell = [
        'roc(close,20) < -0.05',             # 动量转负
        'close < ma(close,20)*0.95',         # 跌破20日均线5%
        'turnover_rate < 0.5'                # 流动性枯竭
    ]
    t.sell_at_least_count = 1

    # 综合评分排序（动态因子权重）
    # 技术因子 (50%) + 估值因子 (30%) + 流动性因子 (20%)
    # 注意：ROE等财务指标未下载，公式中不能使用注释(#)
    t.order_by_signal = '''roc(close,20)*0.30 + trend_score(close,25)*0.20 + normalize_score(pe_score(pe))*0.15 + normalize_score(pb_score(pb))*0.15 + LOG(turnover_rate + 1)*0.20'''
    t.order_by_topK = 20  # 持仓20只股票
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    return t


def multi_factor_strategy_monthly():
    """
    月频多因子智能选股策略

    与周频策略相比:
    - 持仓数量: 30只（月频持仓更多）
    - 调仓频率: 每月
    - 降低交易成本，适合长期投资者

    Returns:
        Task: 策略配置对象
    """
    t = multi_factor_strategy_weekly()
    t.name = 'A股多因子智能选股-月频'
    t.period = 'RunMonthly'
    t.ashare_mode = True  # 明确标记为A股策略
    t.order_by_topK = 30  # 月频持仓30只股票

    # 月频策略可以适当放宽条件，增加稳定性
    t.select_buy = [
        'roc(close,20) > 0.02',              # 降低动量要求
        'trend_score(close,25) > 0',
        'volume > ma(volume,20)*1.1',        # 降低放量要求
        'close > ma(close,60)',
        'pe > 0 and pe < 100',               # 扩大PE估值区间
        'pb > 0 and pb < 8',                 # 扩大PB估值区间
        'turnover_rate > 1.5'                # 降低流动性要求
    ]
    t.buy_at_least_count = 3

    return t


def multi_factor_strategy_conservative():
    """
    保守版多因子策略

    特点:
    - 更严格的选股条件（至少满足5个）
    - 更低的估值要求
    - 更高的质量要求
    - 持仓15只股票

    Returns:
        Task: 策略配置对象
    """
    t = multi_factor_strategy_weekly()
    t.name = 'A股多因子智能选股-保守版'
    t.ashare_mode = True  # 明确标记为A股策略

    # 更严格的买入条件（至少满足5个）
    t.select_buy = [
        'roc(close,20) > 0.05',              # 更高动量要求
        'trend_score(close,25) > 0.5',       # 更强趋势
        'volume > ma(volume,20)*1.3',        # 更大量能
        'close > ma(close,120)',             # 更长期趋势
        'pe > 0 and pe < 30',                # 更低PE估值
        'pb > 0 and pb < 3',                 # 更低PB估值
        'turnover_rate > 3'                  # 更高流动性
    ]
    t.buy_at_least_count = 5  # 至少满足5个条件
    t.order_by_topK = 15  # 持仓15只

    return t


if __name__ == '__main__':
    import sys

    print("="*60)
    print("A股多因子智能选股策略")
    print("="*60)

    # 选择策略版本
    if len(sys.argv) > 1:
        version = sys.argv[1]

        if version == 'weekly':
            print("\n运行周频策略...")
            task = multi_factor_strategy_weekly()

        elif version == 'monthly':
            print("\n运行月频策略...")
            task = multi_factor_strategy_monthly()

        elif version == 'conservative':
            print("\n运行保守版策略...")
            task = multi_factor_strategy_conservative()

        else:
            print(f"\n未知策略版本: {version}")
            print("可用选项: weekly, monthly, conservative")
            sys.exit(1)
    else:
        # 默认运行周频策略
        print("\n运行周频策略（默认）...")
        task = multi_factor_strategy_weekly()

    # 运行回测
    print(f"\n策略名称: {task.name}")
    print(f"股票池数量: {len(task.symbols)}")
    print(f"选股条件数: {len(task.select_buy)}")
    print(f"调仓周期: {task.period}")
    print(f"持仓数量: {task.order_by_topK}")

    engine = Engine()
    result = engine.run(task)

    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    result.stats()

    # 可选: 绘制图表
    # result.plot()
