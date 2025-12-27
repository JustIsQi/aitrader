from core.bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '多标的动量轮动'
    # 排序
    t.period = 'RunWeekly'
    t.weight = 'WeighEqually'
    #t.select_buy = ['roc(close,20)>0.02']
    #t.select_sell = ['roc(close,20)<-0.02']
    t.order_by_signal = 'roc(close,20)'
    t.start_date = '20200101'


    t.symbols = [
        '518880.SH',  # 黄金ETF（大宗商品）
        '513100.SH',  # 纳指100（海外资产）
        '513130.SH',  # 恒生科技（海外资产）
        '515100.SH',# 红利ETF（红利产品）
        '159985.SZ', #大宗豆粕ETF
        '511010.SH',  # 国债ETF（国债产品）
        '511090.SH',  # 30年国债ETF（国债产品）
        '159915.SZ',  # 创业板100（成长股）
        '512100.SH',  # 中证1000ETF（成长股）
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
