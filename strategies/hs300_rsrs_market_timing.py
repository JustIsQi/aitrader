# 策略中文名：沪深300ETF的RSRS择时

from core.bt_engine import Task, Engine


def strategy():
    t = Task()
    t.name = '沪深300ETF的RSRS择时'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.select_buy = ['RSRS(high,low,18)>1.0']
    t.select_sell = ['RSRS(high,low,18)<0.8']
    t.start_date = '20100101'
    t.end_date = '20171231'

    t.symbols = [
        '159915.SZ',  # 标普500
    ]

    t.benchmark = '510300.SH'
    return t

# 交易成本fn(quantity, price)
commissions = lambda q, p: max(5, abs(q*p) * 0.00003)
res = Engine().run(strategy(),commissions)
import matplotlib.pyplot as plt
print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
#res.plot_weights()
res.prices.plot()
print(res.get_transactions())
df = (res.prices.pct_change()+1).cumprod()
plt.show()