from backtrader_engine import Task, Engine


t = Task()
t.name = '多资产轮动-趋势评分'
# 排序
t.period = 'RunDaily'
t.weight = 'WeighEqually'
# 添加风险控制

#t.order_by_signal = 'trend_score(close,27)'
t.order_by_signal = "trend_score(close,24)+roc(close,22)*0.03+ma(volume,5)/ma(volume,18)*0.1"

t.symbols = [
    '518880.SH',  # 黄金ETF
    '513100.SH',  # 纳指100
    '159915.SZ',  # 创业板
    '510300.SH',  # 沪深300
    # 新增
    # '512690.SH',  # 酒ETF - 消费轮动
    # '515000.SH',  # 科技ETF - 科技主线
    # '512880.SH',  # 券商ETF - 市场情绪
    # '510500.SH',  # 中证500 - 中盘成长
    # '159980.SZ',  # 有色ETF - 周期品
]
t.benchmark = '510300.SH'
e = Engine(path='quotes')

# t.order_by_signal = 'trend_score(close,$P)'.replace('$P', str(p))
e.run(t)
e.stats()
e.plot()

# for p in range(15,30,2):
#     e = Engine(path='quotes')
#     print('当前参数是：',p)
#     t.order_by_signal = 'trend_score(close,$P)'.replace('$P',str(p))
#     e.run(t)
#     e.stats()
#e.plot()

