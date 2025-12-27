"""
原生backtrader轮动策略 - 基于趋势评分
使用多个资产进行轮动交易
"""
from core.backtrader_engine import Task


def strategy_trend_score():
    """基于趋势评分的多资产轮动策略"""
    t = Task()
    t.name = '原生轮动策略'
    t.start_date = '20190101'

    # 定义交易标的
    t.symbols = [
        '518880.SH',  # 黄金ETF（大宗商品）
        '513100.SH',  # 纳指100（海外资产）
        '159915.SZ',  # 创业板
        '510180.SH',  # 上证180（价值股，蓝筹股，中大盘）
    ]
    t.benchmark = '510300.SH'

    # 买入条件：收盘价高于20日均线（上升趋势）
    t.select_buy = [
        'close > MA(close, 20)',
    ]
    t.buy_at_least_count = 1

    # 卖出条件：收盘价低于20日均线（下降趋势）
    t.select_sell = [
        'close < MA(close, 20)',
    ]
    t.sell_at_least_count = 1

    # 按收盘价排序（降序）
    t.order_by_signal = 'close'
    t.order_by_topK = 1  # 只持有评分最高的1个
    t.order_by_DESC = True

    # 权重：等权重
    t.weight = 'WeightEqually'

    # 调仓周期：每日运行
    t.period = 'RunDaily'

    return t


# 仅在直接运行时执行回测
if __name__ == '__main__':
    from core.backtrader_engine import Engine

    e = Engine()
    e.run(strategy_trend_score())
    e.stats()
    e.plot()
