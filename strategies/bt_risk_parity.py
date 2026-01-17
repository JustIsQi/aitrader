# 策略中文名：backtrader_风险平价

from core.backtrader_engine import Task


def ranking_ETFs():
    t = Task()
    t.name = '风险平价策略'
    t.start_date = '20190512'
    # 排序
    t.period = 'RunQuarterly'
    t.weight = 'WeightFix'
    t.weight_fixed = {
        '159928.SZ':0.03,
        '510050.SH':0.06,
        '512010.SH':0.08,
        '513100.SH': 0.05,
        '518880.SH': 0.1,
        '511220.SH':0.32,
        '511010.SH':0.26,
        '161716.SZ':0.1
    }
    t.select = 'SelectAll'

    t.symbols = list(t.weight_fixed.keys())
    t.benchmark = '510300.SH'
    return t


# 仅在直接运行时执行引擎
if __name__ == '__main__':
    from core.backtrader_engine import Engine
    e = Engine(path='quotes')
    e.run(ranking_ETFs())
    e.stats()
    e.plot()