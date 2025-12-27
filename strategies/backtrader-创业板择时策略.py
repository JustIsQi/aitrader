from core.backtrader_engine import Task, Engine


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


e = Engine(path='quotes')
e.run(ranking_ETFs())
e.stats()
e.plot()

