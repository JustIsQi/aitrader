from dataclasses import dataclass, asdict, fields
from functools import reduce
from pathlib import Path
from typing import List, Dict, Any
from xxsubtype import bench

import bt
import numpy as np
import pandas as pd
import polars as pl

from alpha.dataset import AlphaDataset
from alpha.load_bar_df import load_all_data_polars
from alpha.polar_loader import PolarDataloader
from alpha.task_config import StockTask
from config import DATA_STOCK_QUOTES


class SelectTopK(bt.AlgoStack):
    def __init__(self, signal, K=1, dropN=0, sort_descending=True, all_or_none=False, filter_selected=True):
        super(SelectTopK, self).__init__(bt.algos.SetStat(signal),
                                         bt.algos.SelectN(int(K) + int(dropN), sort_descending, all_or_none,
                                                          filter_selected))
        self.dropN = dropN

    def __call__(self, target):
        #print('selectTopK运行.....')
        super(SelectTopK, self).__call__(target)

        print(target.now, target.temp['selected'])

        if self.dropN > 0:
            sel = target.temp["selected"]
            if self.dropN >= len(sel):
                target.temp['selected'] = []
            else:
                target.temp["selected"] = target.temp["selected"][self.dropN:]
            return True
        return True

from matplotlib import rcParams
from dataclasses import dataclass, field

rcParams['font.family'] = 'SimHei'

# 因子信息： name：动量 , expr:'roc(close,$P')', params=[20,], params_desc=['周期']




@dataclass
class StrategyConfig:
    name: str = '策略'
    desc: str = '策略描述'
    config_json: Dict[str, int] = field(default_factory=dict)
    author: str = ''


import importlib


from alpha.task_config import StockTask


class Engine:
    def __init__(self, path='quotes'):
        self.path = path

    def _get_algos(self, task: StockTask):

        bt_algos = importlib.import_module('bt.algos')

        if task.period == 'RunEveryNPeriods':
            algo_period = bt.algos.RunEveryNPeriods(n=task.period_days)
        else:
            algo_period = getattr(bt_algos, task.period)(run_on_last_date=True)

        rules,_ = task.get_filter_rules()
        factors = [self._get_factor_df(r) for r in rules]
        result = reduce(lambda x, y: x & y, factors)
        algo_select_where = bt.algos.SelectWhere(signal=result)

        # # 排序因子
        order_by = self._get_factor_df(task.get_orderby_rule_name())
        algo_order_by = SelectTopK(order_by,K=task.topK)


        algos = [bt.algos.RunWeekly(),
                 #bt.algos.PrintDate(),
                 algo_select_where,
                 algo_order_by,
                 bt.algos.WeighEqually(),
                 bt.algos.Rebalance()]
        return algos



    def _get_bkt(self, task):

        s = bt.Strategy(task.name, self._get_algos(task))

        df_close = self._get_factor_df('close')
        df_close = df_close.ffill()
        #df_close.dropna(inplace=True)
        bkt = bt.Backtest(s, df_close, name='策略', integer_positions=True,initial_capital=10000000.0 )
        return bkt

    def _load_data2(self, task:StockTask):
        from polar_loader import PolarDataloader
        from config import DATA_STOCK_QUOTES
        symbols = ['510300.SH', '159915.SZ']
        self.loader = PolarDataloader(symbols=['000001.SZ','000002.SZ'], start='20200101', names=['roc_5'],
                                 fields=['close/shift(close,5)-1'],paths=[DATA_STOCK_QUOTES.joinpath('history')])
        self.df = self.loader.df.to_pandas()


    def _load_data3(self, task: StockTask):
        from config import DATA_STOCK_QUOTES,DATA_DIR_QUOTES
        from load_bar_df import load_bar_df
        # df = load_all_data_polars(
        #     data_sources=[str(DATA_STOCK_QUOTES.joinpath('history').resolve()), str(DATA_STOCK_QUOTES.joinpath('inc').resolve())],
        #     start_date=task.start_date,
        #     end_date=task.end_date,
        #     columns=["date", "symbol", "open", "high", "low", "close", "volume",'circ_mv','real_close']
        # )

        df = load_bar_df(
            # data_sources=[str(DATA_STOCK_QUOTES.joinpath('history').resolve()),
            #               str(DATA_STOCK_QUOTES.joinpath('inc').resolve())],
            #data_sources=[str(DATA_DIR_QUOTES.resolve())],
            symbols= ['159915.SZ','510300.SH'],
            start_date=task.start_date,
            end_date=task.end_date,
            columns=['date','symbol','close']
            #columns=["date", "symbol", "open", "high", "low", "close", "volume", 'circ_mv', 'real_close']
        )

        #print(df)

        # df = load_bar_df()
        dataset = AlphaDataset()
        rules,_ = task.get_filter_rules()
        print(rules)
        for r in rules:
            dataset.add_feature(r, r)

        # rule_order_by = task.get_order_by_factor()
        # print(rule_order_by)
        # dataset.add_feature('排序因子', rule_order_by)
        dataset.prepare_data(df)
        dataset.raw_df = dataset.raw_df.drop_nans()
        self.df = dataset.raw_df.to_pandas()
        print(self.df)

    def _get_factor_df(self,factor_name):
        df_factor = self.df.pivot(values=factor_name, index='date', columns='symbol')
        #df_factor.dropna(inplace=True)
        df_factor.index = pd.to_datetime(df_factor.index)
        #print(df_factor)
        return df_factor

    def _load_data(self,task):
        from config import DATA_DIR
        df = pd.DataFrame()
        h5 = DATA_DIR.joinpath('all.h5')
        with pd.HDFStore(h5, mode='a', complib='blosc', complevel=9) as store:
            _,base_rules = task.get_filter_rules()
            print(base_rules)
            where_condition = ' and '.join(base_rules) #+ f' and index>={int(task.start_date)} and index<={int(task.end_date)}'
            df = store.get('all')
            #df = store.select('all',where_condition)
            print('长度：',len(set(df['symbol'])))
            df['date'] = pd.to_datetime(df.index)
            df['circ_mv'] /= 10000.0

        dataset = AlphaDataset()
        rules,_ = task.get_filter_rules()
        print(rules)
        for r in rules:
            dataset.add_feature(r, r)


        rule_order_by = task.get_order_by_factor()
        print(rule_order_by)
        dataset.add_feature('排序因子', rule_order_by)
        # dataset.add_feature('ts_delay_2', 'ts_delay(close,2)')

        dataset.prepare_data(pl.from_pandas(df))

        self.df = dataset.raw_df.to_pandas()
        print(self.df)

    def run(self, task: StockTask, path=Path('data')):

        self._load_data3(task)

        bkt = self._get_bkt(task)

        # from load_bar_df import load_bar_df
        from config import DATA_DIR_QUOTES

        loader = PolarDataloader([task.benchmark], task.start_date)
        # self.loader.df.to_pandas().to_csv('df.csv')



        bkts = [bkt]
        for bench in [task.benchmark]:
            data = loader.get_col_df_by_symbols([bench])
            print(data)
            #df_bench = load_bar_df(data_sources=[str(DATA_DIR_QUOTES.resolve())],symbols=[bench],columns=['close'],start_date=task.start_date, end_date=task.end_date)
            data = loader.get_col_df_by_symbols([bench])
            #df_close = data.pivot(values='close', index='date', columns='symbol')
            #df_close.dropna(how='all', inplace=True)

            s = bt.Strategy(bench, [bt.algos.RunOnce(),
                                    bt.algos.SelectAll(),
                                    bt.algos.WeighEqually(),
                                    bt.algos.Rebalance()])
            stra = bt.Backtest(s, data, name='benchmark', progress_bar=True)
            bkts.append(stra)

        print('开始回测...')
        res = bt.run(*bkts)
        # res.get_transactions()
        self.res = res
        return res





    def get_equities(self):
        quotes = (self.res.prices.pct_change() + 1).cumprod().dropna()
        quotes['date'] = quotes.index
        # quotes['date'] = quotes['date'].apply(lambda x: x.strftime('%Y%m%d'))
        quotes.index = pd.to_datetime(quotes.index).map(lambda x: x.value)
        quotes = quotes[['策略', 'benchmark']]
        dict = quotes.to_dict(orient='series')

        results = {}
        for k, s in dict.items():
            result = list(zip(s.index, s.values))
            results[k] = result
        #print(results)


import requests, json

def dict_to_task(data: Dict[str, Any]) -> StockTask:
    """将字典安全转换为 Task 实例"""
    # 获取 Task 类的字段集合
    valid_fields = {f.name for f in fields(StockTask)}

    # 过滤非法字段并进行类型检查
    filtered_data = {}
    for key, value in data.items():
        if key not in valid_fields:
            continue

        # 获取字段类型信息
        #field_type = Task.__annotations__.get(key)

        # # 简单类型校验（可选）
        # if field_type and not isinstance(value, field_type):
        #     try:
        #         # 尝试类型转换（如 str -> List）
        #         value = field_type(value)
        #     except (TypeError, ValueError):
        #         raise ValueError(
        #             f"字段 '{key}' 类型不匹配，预期 {field_type}，实际 {type(value)}"
        #         )

        filtered_data[key] = value

    return StockTask(**filtered_data)

if __name__ == '__main__':
    from task_config import SortRule, Rule
    task = StockTask()
    task.period = 'RunEveryNPeriods'
    task.topK=10
    task.period_days=5
    #task.end_date = '20230911'
    # task.filters_rules.append(Rule(
    #     factor_name='收盘价',
    #     params=[],
    #     op='小于',
    #     value=10
    # ))

    task.filters_rules.append(Rule(
        factor_name='流通市值',
        params=[],
        op='大于',
        value=120000
    ))

    # task.filters_rules.append(Rule(
    #     factor_name='流通市值',
    #     params=[],
    #     op='小于',
    #     value=1000
    # ))

    task.orderby_rules.append(SortRule(
        factor_name='流通市值',
        params=[],
        desc=False,
        weight=1.0
    ))

    from load_bar_df import load_bar_df

    df = load_all_data_polars(
        data_sources=[str(DATA_STOCK_QUOTES.joinpath('history').resolve()), str(DATA_STOCK_QUOTES.joinpath('inc').resolve())],
        start_date=task.start_date,
        end_date=task.end_date,
        columns=["date", "symbol", "open", "high", "low", "close", "volume",'circ_mv','real_close']
    )
    print(df)
    dataset = AlphaDataset()
    rules, _ = task.get_filter_rules()
    print(rules)
    for r in rules:
        dataset.add_feature(r, r)
    dataset.add_feature('排序因子',task.get_order_by_factor())
    dataset.prepare_data(df)
    df = dataset.raw_df.to_pandas()
    #df = df.to_pandas()
    data = df.pivot(values='close', index='date', columns='symbol')
    data = data.ffill()
    condition = df.pivot(values='circ_mv>120000', index='date', columns='symbol')
    orderby = df.pivot(values='排序因子', index='date', columns='symbol')
    print(data)
    s = bt.Strategy('test', [bt.algos.RunWeekly(),
                             bt.algos.SelectWhere(condition),
                            #bt.algos.SelectAll(),
                             SelectTopK(orderby,K=1,dropN=0),
                            bt.algos.WeighEqually(),
                            bt.algos.Rebalance()])
    stra = bt.Backtest(s, data, name='benchmark', progress_bar=True)
    res = bt.run(stra)
    print(res.stats)
    res.plot()
    import matplotlib.pyplot as plt
    plt.show()


    # df = load_bar_df(
    #     # data_sources=[str(DATA_STOCK_QUOTES.joinpath('history').resolve()),
    #     #               str(DATA_STOCK_QUOTES.joinpath('inc').resolve())],
    #     # data_sources=[str(DATA_DIR_QUOTES.resolve())],
    #     symbols=['159915.SZ', '510300.SH'],
    #     start_date=task.start_date,
    #     end_date=task.end_date,
    #     columns=['date', 'symbol', 'close']
    #     # columns=["date", "symbol", "open", "high", "low", "close", "volume", 'circ_mv', 'real_close']
    # )

    # print(df)






