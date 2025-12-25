from dataclasses import dataclass, asdict
from typing import List, Dict

import bt
import numpy as np
import pandas as pd
from bt import Algo


class SelectTopK(bt.AlgoStack):
    def __init__(self, signal, K=1, dropN=0, sort_descending=True, all_or_none=False, filter_selected=True):
        super(SelectTopK, self).__init__(bt.algos.SetStat(signal),
                                         bt.algos.SelectN(int(K) + int(dropN), sort_descending, all_or_none,
                                                          filter_selected))
        self.dropN = dropN

    def __call__(self, target):
        #print('selectTopK运行.....')
        super(SelectTopK, self).__call__(target)

        #print(target.now, target.temp['selected'])

        if self.dropN > 0:
            sel = target.temp["selected"]
            if self.dropN >= len(sel):
                target.temp['selected'] = []
            else:
                target.temp["selected"] = target.temp["selected"][self.dropN:]
            print(target.now, target.temp['selected'])
            return True
        return True

from matplotlib import rcParams
from dataclasses import dataclass, field
from datetime import datetime

rcParams['font.family'] = 'SimHei'


@dataclass
class Task:
    name: str = '策略'
    symbols: List[str] = field(default_factory=list)

    start_date: str = '20100101'
    end_date: str = datetime.now().strftime('%Y%m%d')

    benchmark: str = '510300.SH'
    select: str = 'SelectAll'

    select_buy: List[str] = field(default_factory=list)
    buy_at_least_count: int = 0
    select_sell: List[str] = field(default_factory=list)
    sell_at_least_count: int = 1

    order_by_signal: str = ''
    order_by_topK: int = 1
    order_by_dropN: int = 0
    order_by_DESC: bool = True  # 默认从大至小排序

    weight: str = 'WeighEqually'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunDaily'
    period_days: int = None


@dataclass
class StrategyConfig:
    name: str = '策略'
    desc: str = '策略描述'
    config_json: Dict[str, int] = field(default_factory=dict)
    author: str = ''


import importlib
from datafeed.csv_dataloader import CsvDataLoader
from datafeed.factor_expr import FactorExpr
class DataFeed:
    def __init__(self, task: Task):
        dfs = CsvDataLoader().read_dfs(symbols=task.symbols,start_date=task.start_date, end_date=task.end_date)

        fields = list(set(task.select_buy + task.select_sell))
        if task.order_by_signal:
            fields += [task.order_by_signal]
        names = fields
        df_all = FactorExpr().calc_formulas(dfs,fields)
        self.df_all = df_all
        #self.df_all.to_csv('df_all.csv')

    def get_factor_df(self, col):
        if col not in self.df_all.columns:
            print(f'{col}不存在')
            return None
        df_factor = self.df_all.pivot_table(values=col, index=self.df_all.index, columns='symbol')
        if col == 'close':
            df_factor = df_factor.ffill()
        return df_factor




class Engine:
    def __init__(self, path='quotes'):
        self.path = path


    def _parse_rules(self, task: Task):

        def _rules(rules, at_least):
            if not rules or len(rules) == 0:
                return None

            all = None
            for r in rules:
                if r == '':
                    continue

                df_r = self.datafeed.get_factor_df(r)
                if df_r is not None:
                    df_r = df_r.replace({True: 1, False: 0})
                    df_r = df_r.astype('Int64')

                    #print(df_r)
                    #df_r = df_r.astype(int)
                #else:
                    #print(r)
                if all is None:
                    all = df_r
                else:
                    all += df_r
            return all >= at_least

        buy_at_least_count = task.buy_at_least_count
        if buy_at_least_count <= 0:
            buy_at_least_count = len(task.select_buy)

        all_buy = _rules(task.select_buy, at_least=buy_at_least_count)
        all_sell = _rules(task.select_sell, task.sell_at_least_count)  # 卖出 求或，满足一个即卖出

        if all_sell is not None:
            all_sell = all_sell.fillna(True)
        if all_buy is not None:
            all_buy = all_buy.fillna(False)
        return all_buy, all_sell

    def _get_algos(self, task: Task):

        bt_algos = importlib.import_module('bt.algos')

        if task.period == 'RunEveryNPeriods':
            algo_period = bt.algos.RunEveryNPeriods(n=task.period_days, run_on_last_date=True)
        else:
            algo_period = getattr(bt_algos, task.period)(run_on_last_date=True)

        algo_select_where = None
        # 信号规则
        signal_buy, signal_sell = self._parse_rules(task)
        if signal_buy is not None or signal_sell is not None:  # 至少一个不为None
            df_close = self.datafeed.get_factor_df('close')
            if signal_buy is None:
                select_signal = np.ones(df_close.shape)  # 注意这里是全1，没有select_buy就是全选
                select_signal = pd.DataFrame(select_signal, columns=df_close.columns, index=df_close.index)
            else:
                select_signal = np.where(signal_buy, 1, np.nan)  # 有select_buy的话，就是买入，否则选置Nan表示 hold状态不变
            if signal_sell is not None:
                select_signal = np.where(signal_sell, 0, select_signal)  # select_sell置为0，就是清仓或不选
            select_signal = pd.DataFrame(select_signal, index=df_close.index, columns=df_close.columns)
            select_signal.ffill(inplace=True)  # 这一句非常关键，ffill就是前向填充，保持持仓状态不变。即不符合buy，也不符合sell，保持不变。
            select_signal.fillna(0, inplace=True)
            algo_select_where = bt.algos.SelectWhere(signal=select_signal)

        # 排序因子
        algo_order_by = None
        if task.order_by_signal:
            signal_order_by = self.datafeed.get_factor_df(col=task.order_by_signal)
            algo_order_by = SelectTopK(signal=signal_order_by, K=task.order_by_topK, dropN=task.order_by_dropN,
                                       sort_descending=task.order_by_DESC)

        algos = []
        algos.append(algo_period)

        if algo_select_where:
            algos.append(algo_select_where)
        else:
            algos.append(bt.algos.SelectAll())

        if algo_order_by:
            algos.append(algo_order_by)

        if task.weight == 'WeighERC':
            algos.insert(0, bt.algos.RunAfterDays(days=256))
            algo_weight = getattr(bt_algos, task.weight)()
        elif task.weight == 'WeighSpecified':
            #print(task.weight_fixed)
            algo_weight = bt.algos.WeighSpecified(**task.weight_fixed)


        else:
            if task.weight == 'WeighInVol':
                task.weight = 'WeighInvVol'
            algo_weight = getattr(bt_algos, task.weight)()

        algos.append(algo_weight)
        algos.append(bt.algos.Rebalance())
        #print(algos)
        return algos


    def _get_bkt(self, task):
        if type(task) is str:
            return task


        s = bt.Strategy(task.name, self._get_algos(task))

        df_close = self.datafeed.get_factor_df('close')
        bkt = bt.Backtest(s, df_close, name='策略', integer_positions=True, commissions=self.commissions )
        return bkt

    def run(self, task: Task, commissions=None):
        self.commissions = commissions
        self.datafeed = DataFeed(task)

        bkt = self._get_bkt(task)

        bkts = [bkt]
        for bench in [task.benchmark]:
            df = CsvDataLoader().read_df([bench])
            df.set_index('date',inplace=True)
            df.index = pd.to_datetime(df.index)
            data = df.pivot_table(values='close', index=df.index, columns='symbol')
            #data =self.loader.get_col_df_by_symbols([bench])
            #data = CSVDataloader.get([bench], path=self.path)
            s = bt.Strategy(bench, [bt.algos.RunOnce(),
                                    bt.algos.SelectAll(),
                                    bt.algos.WeighEqually(),
                                    bt.algos.Rebalance()])
            stra = bt.Backtest(s, data, name='benchmark', progress_bar=True,commissions=commissions)
            bkts.append(stra)

        res = bt.run(*bkts)
        # res.get_transactions()
        self.res = res
        print(res.get_transactions())
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

if __name__ == '__main__':
    t = Task()
    t.name = '全球大类资产-修正斜率轮动'
    etfs = [
        '510300.SH',  # 沪深300ETF
        '159915.SZ',  # 创业板
        '518880.SH',  # 黄金ETF
        '513100.SH',  # 纳指ETF
        '159985.SZ',  # 豆柏ETF
        '511880.SH',  # 银华日利ETF
    ]

    t.symbols = etfs

    #t.select_sell = ["roc(close,21)>0.17"]
    t.order_by_signal =  "roc(close,22)"

    e = Engine()
    res = e.run(t)
    print(res.stats)
    res.get_transactions().to_csv('bt_orders.csv')
    # print(res.get_security_weights().iloc[-1].to_dict())
    # print(res.get_weights())
    import matplotlib.pyplot as plt
    res.plot()
    plt.show()
