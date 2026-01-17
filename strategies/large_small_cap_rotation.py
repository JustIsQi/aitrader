# 策略中文名：大小盘轮动策略

from core.bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '大小盘轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['roc(close,20)>0.02']
    t.select_sell = ['roc(close,20)<-0.02']
    t.order_by_signal = 'roc(close,20)'


    t.symbols = [
        '159915.SZ',
        '510300.SH'
        ]
    t.benchmark = '510300.SH'
    return t


res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
(res.prices.pct_change()+1).cumprod().plot()
plt.show()
