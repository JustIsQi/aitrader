"""
A股策略示例

演示如何在策略中启用A股交易约束:
1. T+1结算规则
2. 涨跌停限制
3. 手数限制(100股/手)
4. A股真实手续费
"""

from core.backtrader_engine import Task, Engine


def example_etf_strategy():
    """示例: ETF策略(非A股模式)"""
    t = Task()
    t.name = 'ETF轮动策略'
    t.symbols = ['510300.SH', '510500.SH', '159915.SZ']
    t.start_date = '20200101'
    t.end_date = '20231231'

    # 简单动量选股
    t.select_buy = ['roc(close,20) > 0.02']
    t.buy_at_least_count = 1
    t.select_sell = ['roc(close,20) < 0']

    # 按动量排序,选top1
    t.order_by_signal = 'roc(close,20)'
    t.order_by_topK = 1

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    # ETF模式(默认)
    t.ashare_mode = False

    e = Engine()
    e.run(t)
    e.stats()
    # e.plot()


def example_ashare_stock_strategy():
    """示例: A股股票策略(启用A股约束)"""
    t = Task()
    t.name = 'A股动量选股策略'
    t.symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH']
    t.start_date = '20200101'
    t.end_date = '20231231'

    # 买入条件: 强动量 + 放量
    t.select_buy = [
        'roc(close,20) > 0.05',      # 20日涨幅>5%
        'volume > ma(volume,20)'     # 成交量放大
    ]
    t.buy_at_least_count = 2  # 必须满足2个条件

    # 卖出条件: 动量转负
    t.select_sell = ['roc(close,20) < 0']
    t.sell_at_least_count = 1

    # 按动量排序,选top2
    t.order_by_signal = 'roc(close,20)'
    t.order_by_topK = 2
    t.order_by_DESC = True

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    # ========== 启用A股模式 ==========
    t.ashare_mode = True              # 启用A股交易约束
    t.ashare_commission = 'v2'        # 使用V2手续费方案(2023年后)

    e = Engine()
    e.run(t)
    e.stats()
    # e.plot()


def example_ashare_multi_factor_strategy():
    """示例: A股多因子选股策略"""
    t = Task()
    t.name = 'A股多因子智能选股'
    t.symbols = [
        '000001.SZ', '000002.SZ', '000063.SZ', '600000.SH',
        '600036.SH', '600519.SH', '600887.SH', '601318.SH'
    ]
    t.start_date = '20200101'
    t.end_date = '20231231'

    # 多因子买入条件
    t.select_buy = [
        'roc(close,20) > 0.03',        # 正动量
        'close > ma(close,60)',        # 长期趋势向上
        'volume > ma(volume,20)*1.2'   # 放量确认
    ]
    t.buy_at_least_count = 2

    # 卖出条件
    t.select_sell = [
        'roc(close,20) < -0.05',       # 动量转负
        'close < ma(close,20)*0.95'    # 跌破均线
    ]
    t.sell_at_least_count = 1

    # 综合评分排序
    t.order_by_signal = 'roc(close,20)*0.6 + trend_score(close,25)*0.4'
    t.order_by_topK = 3

    t.period = 'RunWeekly'
    t.weight = 'WeightEqually'

    # ========== 启用A股模式 ==========
    t.ashare_mode = True
    t.ashare_commission = 'v2'

    e = Engine()
    e.run(t)
    e.stats()
    # e.plot()


if __name__ == '__main__':
    import sys

    print("="*60)
    print("A股策略示例")
    print("="*60)

    if len(sys.argv) > 1:
        strategy_type = sys.argv[1]

        if strategy_type == 'etf':
            print("\n运行ETF策略...")
            example_etf_strategy()

        elif strategy_type == 'ashare_momentum':
            print("\n运行A股动量策略...")
            example_ashare_stock_strategy()

        elif strategy_type == 'ashare_multifactor':
            print("\n运行A股多因子策略...")
            example_ashare_multi_factor_strategy()

        else:
            print(f"\n未知策略类型: {strategy_type}")
            print("可用选项: etf, ashare_momentum, ashare_multifactor")
    else:
        print("\n请指定策略类型:")
        print("  python ashare_strategy_example.py etf")
        print("  python ashare_strategy_example.py ashare_momentum")
        print("  python ashare_strategy_example.py ashare_multifactor")
