from bt_engine import Task, Engine


def ranking_ETFs():
    t = Task()
    t.name = '基于ETF历史评分的轮动策略'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)'
    t.start_date = '20180101'
    #t.end_date = '20240501'

    t.symbols = [
        '518880.SH',  # 黄金ETF（大宗商品）
        '513100.SH',  # 纳指100（海外资产）
        '159915.SZ',  # 创业板100（成长股，科技股，中小盘）
        '510180.SH',  # 上证180（价值股，蓝筹股，中大盘）
    ]
    t.benchmark = '510300.SH'
    return t

res = Engine().run(ranking_ETFs())
import matplotlib.pyplot as plt
print(res.stats)
from matplotlib import rcParams

rcParams['font.family'] = 'SimHei'
#res.plot_weights()
res.prices.plot()
print(res.get_transactions())
df = (res.prices.pct_change()+1).cumprod()
print(df.iloc[-1])
plt.show()