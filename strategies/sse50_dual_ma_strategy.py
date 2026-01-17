# 策略中文名：上证50双均线策略

from core.bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '创业板布林带'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['ma(close,20)>ma(close,120)']
    t.select_sell = ['ma(close,20)<ma(close,120)']


    t.symbols = [
        '510050.SH'
        ]
    t.benchmark = '510050.SH'
    return t


res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
res.prices.plot()
plt.show()
