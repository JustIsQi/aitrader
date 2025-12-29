"""
全球资产动量轮动策略
基于趋势评分、多周期动量和成交量的复合指标进行资产轮动
"""
from core.backtrader_engine import Task, Engine


def global_asset_momentum_rotation():
    """
    全球资产动量轮动策略

    排序规则: 趋势评分(25)×0.2 + 动量(5) + 动量(10)×1.5 + 交易量均线(5)/交易量均线(19)
    卖出规则: 动量(20) > 0.16
    """
    t = Task()
    t.name = '全球资产动量轮动'

    # 策略配置
    t.period = 'RunDaily'  # 每天运行
    t.weight = 'WeighEqually'  # 等权重配置

    # 基准选择：沪深300
    t.benchmark = '510300.SH'

    # 基金列表（15只）
    t.symbols = [
        '513290.SH',  # 汇添富纳斯达克生物科技ETF (QDII)
        '513520.SH',  # 华夏野村日经225ETF (QDII)
        '159509.SZ',  # 景顺长城纳斯达克科技ETF(QDII)
        '513030.SH',  # 华安德国(DAX)ETF (QDII)
        '159915.SZ',  # 易方达创业板ETF
        '512100.SH',  # 南方中证1000ETF
        '563300.SH',  # 中证2000
        '588100.SH',  # 嘉实上证科创板新一代信息技术ETF
        '563000.SH',  # 易方达MSCI中国A50互联互通ETF (QDII)
        '159819.SZ',  # 易方达中证人工智能主题ETF
        '518880.SH',  # 华安黄金易(ETF)
        '513330.SH',  # 华夏恒生互联网科技业ETF(QDII)
        '513100.SH',  # 国泰纳斯达克100(QDII-ETF)
        '588000.SH',  # 华夏上证科创板50成份ETF
        '515880.SH',  # 国泰中证全指通信设备ETF
    ]

    # 排序规则: 趋势评分(25)×0.2 + 动量(5) + 动量(10)×1.5 + 交易量均线(5)/交易量均线(19)
    # 使用 roc(close, N) 表示动量，ma(volume, N) 表示成交量均线
    t.order_by_signal = 'trend_score(close,25)*0.2 + roc(close,5) + roc(close,10)*1.5 + ma(volume,5)/ma(volume,19)'

    # 卖出规则: 动量(20) > 0.16
    t.select_sell = ['roc(close,20) > 0.16']

    # 最高持仓数量
    t.order_by_topK = 1

    # 卖出规则至少满足: 1
    t.sell_at_least_count = 1

    # 排序剔除前N个: 0
    t.order_by_dropN = 0

    # 默认降序排列
    t.order_by_DESC = True

    # 回测开始日期
    t.start_date = '20200101'

    return t


if __name__ == '__main__':
    # 运行策略
    res = Engine(path='quotes').run(global_asset_momentum_rotation())

    # 显示统计结果
    res.stats()

    # 绘制净值曲线
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    rcParams['font.family'] = 'SimHei'
    rcParams['axes.unicode_minus'] = False
    res.plot()
    plt.show()
