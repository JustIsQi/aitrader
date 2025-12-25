

from backtrader_strategy import RotationStrategyTemplate
from backtrader_inds import TrendScore
from backtrader_engine import Engine
from collections import defaultdict

class StrategyTrendScore(RotationStrategyTemplate):
    params = dict(
        period=20,  # 动量周期
        # upper=8,
        # lower=0,
    )

    def __init__(self):
        super().__init__()
        self.inds = defaultdict(dict)
        print(f"策略初始化，period参数: {self.p.period}")
        for data in self.datas:
            self.inds['sorter'][data] = TrendScore(data.close, period=self.p.period)

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()


    #for p in range(21,29,1):
    for p in [26,]:
        e = Engine()
        symbols = [
            '518880.SH',  # 黄金ETF（大宗商品）
            '513100.SH',  # 纳指100（海外资产）
            '159915.SZ',  # 创业板
            '510180.SH',  # 上证180（价值股，蓝筹股，中大盘）
            #'510030.SH',  # 沪深300
        ]
        e.run_strategy(StrategyTrendScore,symbols,period=p)
        e.stats()
        e.plot()
    #e.opt(StrategyTrendScore,symbols,period=range(1, 50, 5),)
