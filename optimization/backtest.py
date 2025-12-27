from config import DATA_DIR_QUOTES
from deap_factor.utils import stringify_for_sympy
from bt_engine import DataFeed,Task
import bt
from bt_algos_extend import SelectTopK

task = Task()
task.symbols = ['510300.SH','159915.SZ','513500.SH','518880.SH']


def backtester(evaluate, inds):


    names, features = [], []
    for i, expr in enumerate(inds):
        #names.append(f'GP_{i:04d}')
        features.append(stringify_for_sympy(expr))



    bkts = []
    features = list(set(features))
    for expr in features:
        print(f'回测{expr}')
        task.order_by_signal = expr
        datafeed = DataFeed(task)
        signal = datafeed.get_factor_df(expr)
        #print(signal)
        for K in [1]:
            s = bt.Strategy('{}'.format(expr), [
                bt.algos.RunWeekly(),
                bt.algos.SelectAll(),
                SelectTopK(signal, K),
                bt.algos.WeighEqually(),
                bt.algos.Rebalance()])
            bkts.append(s)

    stras = [bt.Backtest(s, datafeed.get_factor_df('close')) for s in bkts]
    res = bt.run(*stras)
    stats = res.stats
    # print(stats.loc['cagr'])

    results = []
    for expr in features:
            results.append((stats.loc['cagr'][expr],))
            # results.append((stats.loc['cagr'][name], stats.loc['calmar'][name]))
    print(results)
    return results