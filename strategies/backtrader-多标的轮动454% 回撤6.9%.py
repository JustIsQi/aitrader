from core.backtrader_engine import Task, Engine


def strategy():
    t = Task()
    t.name = 'etf轮动'
    # 排序
    t.period = 'RunDaily'
    t.weight = 'WeighEqually'
    t.order_by_signal = 'trend_score(close,25)*0.25+(roc(close,5)+roc(close,10))*0.17+ma(volume,5)/ma(volume,18)'
    #t.order_by_signal = 'trend_score(close,25)*0.25+(roc(close,9)+roc(close,19))*0.17+ma(volume,5)/ma(volume,18)'
    t.select_sell = ['roc(close,20)>0.158']
    t.start_date = '20231204'
    t.end_date = '20250601'

    t.symbols = [
        '513290.SH',
        '513520.SH',
        '159509.SZ',
        '513030.SH',
        '159915.SZ',
        '563300.SH',
        '588100.SH',
        '513040.SH',
        '563000.SH',
        '159939.SZ',
        '515230.SH',
        '515980.SH',
        '159819.SZ',
        '162719.SZ',
        '518880.SH',
        '513330.SH',
        '513180.SH',
        '513130.SH',
        '159505.SZ',
        '513090.SH',
        '159792.SZ',
        '159857.SZ',
        '159887.SZ',
        '561600.SH',
        '588000.SH',
        '513500.SH',
        '512480.SH',
        '513100.SH',
        '513380.SH',
        '588110.SH',
        '515880.SH',

    ]

    t.benchmark = '510300.SH'
    return t

e = Engine()
results = e.run(strategy())
returns = results[0].analyzers.returns.get_analysis()
print(returns)
e.stats()
e.plot()