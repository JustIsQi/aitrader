# 策略中文名：年化收益评分的轮动策略-超级轮动

from core.backtrader_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)*0.27+roc(close,13)*0.75+roc(close,8)*0.18+roc(high,5)*0.6+ma(volume,5)/ma(volume,20)'
    #t.start_date = '20180101'
    t.select_buy =  [
    "roc(close,5)<0.055",
    "roc(close,10)<0.01",
    "roc(close,3)>-0.015"
  ]
    t.buy_at_least_count = 2
    t.sell_at_least_count = 1
    t.select_sell = [
        "roc(close,10)>0.185",
        "roc(close,20)>0.16",
        "roc(close,1)<-0.165",
        "roc(close,2)<-0.04",
        "roc(close,3)<-0.08",
        "ma(volume,5)/ma(volume,120)<0.45",
        "slope(low,25)/ma(low,25)*44+roc(close,13)*0.6+roc(high,8)*0.3+roc(high,5)*0.9+ma(volume,5)/ma(volume,20)<-1"
    ]
    #t.end_date = '20240501'

    t.symbols = [
        "563300.SH",
    "159509.SZ",
    "518880.SH",
    "513100.SH",
    "513520.SH",
    "588000.SH",
    "513330.SH",
    "512100.SH",
    "162719.SZ",
    "513030.SH",
    "513380.SH",
    "513290.SH",
    "159560.SZ",
    "588100.SH",
    "513040.SH",
    "561600.SH",
    "515880.SH",
    "513090.SH",
    "159819.SZ",
    "515790.SH",
    "515030.SH",
    "159752.SZ",
    "159761.SZ",
    "512480.SH",
    "560800.SH",
    "513500.SH"
    ]
    t.benchmark = '510300.SH'
    return t

e = Engine()#import matplotlib.pyplot as plt

from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
#res.plot_weights()
#res.prices.plot()


e = Engine(path='quotes')

# t.order_by_signal = 'trend_score(close,$P)'.replace('$P', str(p))
e.run(ranking_ETFs())
e.stats()
e.plot()