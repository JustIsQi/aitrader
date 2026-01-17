# 策略中文名：创业板择时策略

from core.bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '创业板动量'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['roc(close,20)>0.08']
    t.select_sell = ['roc(close,20)<0']


    t.symbols = [
        '159915.SZ'
        ]
    t.benchmark = '159915.SZ'
    return t


res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
res.prices.plot()
plt.show()
