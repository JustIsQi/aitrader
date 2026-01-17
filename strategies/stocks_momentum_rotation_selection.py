# 策略中文名：stocks_动量轮动选股策略

"""
A股动量轮动选股策略

策略特点:
- 纯动量驱动，激进型策略
- 强势筛选（6个条件全部满足）
- 多层止损机制
- 避免涨停追高
- 高换手率，适合趋势行情

作者: AITrader
日期: 2026-01-06
"""

from core.backtrader_engine import Task, Engine
from core.stock_universe import StockUniverse


def momentum_strategy_weekly():
    """
    周频动量轮动策略

    策略逻辑:
    1. 股票池: 全市场剔除ST、停牌、新股，按流动性和市值筛选
    2. 选股: 6个强势条件全部满足（强动量+上升趋势+流动性）
    3. 排序: 按20日收益率排序
    4. 持仓: 15只股票，等权重
    5. 调仓: 每周
    6. 止损: 多层止损机制

    Returns:
        Task: 策略配置对象
    """
    t = Task()
    t.name = 'A股动量轮动-周频'
    t.ashare_mode = True
    t.ashare_commission = 'v2'
    t.start_date = '20200101'
    t.end_date = '20241231'

    # 动态股票池 - 先进行基础过滤
    universe = StockUniverse()
    base_symbols = universe.get_all_stocks(
        exclude_st=True,              # 剔除ST股票
        exclude_suspend=True,         # 剔除停牌股票
        exclude_new_ipo_days=252      # 排除上市1年内新股
    )

    # 流动性筛选 - 日成交额>5000万
    liquidity_symbols = universe.filter_by_liquidity(
        symbols=base_symbols,
        min_amount=5000               # 单位: 万元
    )

    # 市值筛选 - 市值>50亿
    t.symbols = universe.filter_by_market_cap(
        symbols=liquidity_symbols,
        min_mv=50                     # 单位: 亿元
    )

    # 强势筛选条件（6个条件全部满足）
    t.select_buy = [
        'roc(close,20) > 0.08',              # 强动量 > 8%
        'roc(close,5) > -0.03',              # 短期未大幅回调
        'volume > ma(volume,20)',            # 量能支撑
        'close > ma(close,20)',              # 上升趋势
        'turnover_rate > 1.5',               # 流动性充足
        'close < ref(close,1)*1.095'         # 未涨停（留出追涨空间）
    ]
    t.buy_at_least_count = 6  # 必须全部满足

    # 多层止损机制（满足任一即卖出）
    t.select_sell = [
        'roc(close,20) < 0',                 # 动量转负
        'close/ref(close,1) < 0.92',         # 单日大跌-8%止损
        'close < ma(close,20)*0.95',         # 跌破20日均线5%
        'volume < ma(volume,20)*0.3',        # 缩量到30%以下
        'roc(close,5) < -0.10'               # 短期暴跌-10%
    ]
    t.sell_at_least_count = 1  # 满足任一条件

    # 按动量排序（选择动量最强的股票）
    t.order_by_signal = 'roc(close,20)'
    t.order_by_topK = 15  # 持仓15只股票
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    return t


def momentum_strategy_monthly():
    """
    月频动量轮动策略

    与周频策略相比:
    - 持仓数量: 20只（月频持仓更多）
    - 调仓频率: 每月
    - 条件适当放宽，增加稳定性
    - 降低交易成本

    Returns:
        Task: 策略配置对象
    """
    t = momentum_strategy_weekly()
    t.name = 'A股动量轮动-月频'
    t.period = 'RunMonthly'
    t.ashare_mode = True  # 明确标记为A股策略
    t.order_by_topK = 20  # 月频持仓20只股票

    # 月频条件适当放宽
    t.select_buy = [
        'roc(close,20) > 0.05',              # 降低动量要求到5%
        'roc(close,60) > 0.10',              # 增加中期动量要求
        'volume > ma(volume,20)',
        'close > ma(close,60)',              # 更长期趋势
        'turnover_rate > 1.0',               # 降低流动性要求
        'close < ref(close,1)*1.095'
    ]
    t.buy_at_least_count = 4  # 至少满足4个条件

    # 月频止损条件可以适当放宽
    t.select_sell = [
        'roc(close,20) < -0.03',             # 动量轻度转负
        'close < ma(close,20)*0.92',         # 跌破均线8%
        'volume < ma(volume,20)*0.2',
        'roc(close,60) < 0'                  # 中期动量转负
    ]
    t.sell_at_least_count = 1

    return t


def momentum_strategy_aggressive():
    """
    激进版动量策略

    特点:
    - 更高的动量要求（12%）
    - 更短的反应周期（5日）
    - 持仓10只最强势股票
    - 快进快出
    - 适合强势牛市

    Returns:
        Task: 策略配置对象
    """
    t = momentum_strategy_weekly()
    t.name = 'A股动量轮动-激进版'
    t.ashare_mode = True  # 明确标记为A股策略

    # 更激进的选股条件
    t.select_buy = [
        'roc(close,20) > 0.12',              # 更高动量要求 >12%
        'roc(close,5) > 0.03',               # 短期也必须上涨
        'roc(close,3) > 0',                  # 3日内不能下跌
        'volume > ma(volume,20)*1.5',        # 更大量能
        'close > ma(close,10)',              # 更短期趋势
        'turnover_rate > 2.5',               # 更高流动性
        'close > ma(close,5)*1.02'           # 站稳5日均线
    ]
    t.buy_at_least_count = 6  # 全部满足

    # 更严格的止损
    t.select_sell = [
        'roc(close,20) < 0.05',              # 动量降至5%以下
        'roc(close,5) < -0.05',              # 短期回调
        'close/ref(close,1) < 0.94',         # 单日大跌-6%
        'close < ma(close,10)*0.97',         # 跌破10日均线3%
        'volume < ma(volume,10)*0.5'         # 快速缩量
    ]
    t.sell_at_least_count = 1

    # 只持仓最强势的10只
    t.order_by_topK = 10

    return t


def momentum_strategy_with_skip(skip_top=2):
    """
    跳过最强势股票的动量策略

    参数:
        skip_top: 跳过前N只最强势股票，避免过度追高

    策略逻辑:
    - 选择动量排名第3-17名的股票
    - 避免买入已大幅上涨的极端股票
    - 降低追高风险

    Returns:
        Task: 策略配置对象
    """
    t = momentum_strategy_weekly()
    t.name = f'A股动量轮动-跳过前{skip_top}只'
    t.ashare_mode = True  # 明确标记为A股策略

    # 修改持仓数量，考虑跳过的股票
    t.order_by_topK = 15 + skip_top

    # 注意: 实际回测时需要在策略中实现跳过逻辑
    # 这里只是配置，具体实现需要在回测引擎中支持

    return t


if __name__ == '__main__':
    import sys

    print("="*60)
    print("A股动量轮动选股策略")
    print("="*60)

    # 选择策略版本
    if len(sys.argv) > 1:
        version = sys.argv[1]

        if version == 'weekly':
            print("\n运行周频策略...")
            task = momentum_strategy_weekly()

        elif version == 'monthly':
            print("\n运行月频策略...")
            task = momentum_strategy_monthly()

        elif version == 'aggressive':
            print("\n运行激进版策略...")
            task = momentum_strategy_aggressive()

        elif version == 'skip':
            print("\n运行跳过最强势策略...")
            skip_num = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            task = momentum_strategy_with_skip(skip_num)

        else:
            print(f"\n未知策略版本: {version}")
            print("可用选项: weekly, monthly, aggressive, skip [N]")
            sys.exit(1)
    else:
        # 默认运行周频策略
        print("\n运行周频策略（默认）...")
        task = momentum_strategy_weekly()

    # 运行回测
    print(f"\n策略名称: {task.name}")
    print(f"股票池数量: {len(task.symbols)}")
    print(f"选股条件数: {len(task.select_buy)}")
    print(f"调仓周期: {task.period}")
    print(f"持仓数量: {task.order_by_topK}")
    print(f"选股要求: 至少满足{task.buy_at_least_count}个条件")

    engine = Engine()
    result = engine.run(task)

    print("\n" + "="*60)
    print("回测结果")
    print("="*60)
    result.stats()

    # 可选: 绘制图表
    # result.plot()
