from bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '创业板布林带'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['close>bbands_up(close,20,2)']
    t.select_sell = ['close<bbands_down(close,20,2)']


    t.symbols = [
        '159915.SZ'
        ]
    t.benchmark = '159915.SZ'
    return t

commissions = lambda q, p: max(5, abs(q*p) * 0.0003)
res = Engine(path='quotes').run(ranking_ETFs(),commissions)
#res = Engine(path='quotes').run(ranking_ETFs())
import matplotlib.pyplot as plt

print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
# res.plot_weights()
res.prices.plot()
plt.show()
