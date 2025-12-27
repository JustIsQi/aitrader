from core.bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '优质资产动量轮动'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['roc(close,20)>0.02']
    t.select_sell = ['roc(close,20)<-0.02']
    t.order_by_signal = 'roc(close,20)'
    t.start_date = '20150101'
    t.order_by_topK = 7


    t.symbols = [
        '511220.SH',  # 城投债
        '512010.SH',  # 医药
        '518880.SH',  # 黄金
        '163415.SZ',# 兴全商业
        '159928.SZ', # 消费
        '161903.SZ',  # 万家优选
        '513100.SH', #纳指
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
