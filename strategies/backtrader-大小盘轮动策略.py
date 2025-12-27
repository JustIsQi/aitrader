from core.backtrader_engine import Task, Engine


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


e = Engine(path='quotes')
e.run(ranking_ETFs())
e.stats()
e.plot()