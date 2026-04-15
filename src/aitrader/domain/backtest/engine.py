import importlib
from dataclasses import dataclass, asdict
from typing import List, Dict

import backtrader as bt
import numpy as np
import pandas as pd
from aitrader.infrastructure.config.logging import logger

from aitrader.domain.backtest.strategy_template import StrategyTemplate
from aitrader.domain.backtest.algos import *
from aitrader.domain.backtest.result import BacktestResult



from matplotlib import rcParams
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

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

    weight: str = 'WeightEqually'
    weight_fixed: Dict[str, int] = field(default_factory=dict)
    period: str = 'RunDaily'
    period_days: int = None

    # A股模式参数
    ashare_mode: bool = False          # 是否启用A股模式
    ashare_commission: str = 'v2'      # A股手续费方案 ('v1', 'v2', 'zero', 'fixed')

    # 复权类型参数
    adjust_type: str = 'hfq'           # 复权类型: 'qfq'前复权, 'hfq'后复权 (默认后复权保持向后兼容)


@dataclass
class StrategyConfig:
    name: str = '策略'
    desc: str = '策略描述'
    config_json: Dict[str, int] = field(default_factory=dict)
    author: str = ''


class AlgoStrategy(StrategyTemplate):
    """
    算法策略类

    支持通过algo_list传递算法链进行策略执行
    """

    # params = (('ashare_mode', False),)  # A股模式参数(继承自StrategyTemplate)

    def __init__(self, algo_list, ashare_mode=False, **kwargs):
        """
        初始化算法策略

        Args:
            algo_list: 算法列表
            ashare_mode: 是否启用A股模式
            **kwargs: 其他策略参数
        """
        super(AlgoStrategy, self).__init__()
        self.algos = algo_list

        # 设置A股模式参数
        if ashare_mode:
            self.p.ashare_mode = ashare_mode
            # 传递其他A股相关参数
            for key, value in kwargs.items():
                if hasattr(self.p, key):
                    setattr(self.p, key, value)

    def prenext(self):
        pass

    def next(self):
        #print(f"next - 当前日期: {self.datetime.date(0)}")
        self.temp = {}

        for algo in self.algos:
            if algo(self) is False:  # 如果algo返回False,直接不运行
                return



from aitrader.infrastructure.market_data.loaders import DbDataLoader
from aitrader.infrastructure.market_data.factor_expr import FactorExpr
import time

class DataFeed:
    def __init__(self, task: Task):
        datafeed_start = time.time()
        logger.info(f"  [{task.name}] DataFeed: 开始加载数据 (标的数: {len(task.symbols)})...")
        logger.debug(f"  [{task.name}] DataFeed: 日期范围 {task.start_date} ~ {task.end_date}")

        dfs = DbDataLoader(auto_download=False).read_dfs(symbols=task.symbols,start_date=task.start_date, end_date=task.end_date)
        logger.info(f"  [{task.name}] DataFeed: 原始数据加载完成, 耗时 {time.time() - datafeed_start:.2f}秒")

        fields = list(set(task.select_buy + task.select_sell))
        if task.order_by_signal:
            fields += [task.order_by_signal]
        names = fields

        logger.debug(f"  [{task.name}] DataFeed: 计算技术指标: {', '.join(fields)}")
        calc_start = time.time()
        df_all = FactorExpr().calc_formulas(dfs,fields)
        logger.info(f"  [{task.name}] DataFeed: 技术指标计算完成, 耗时 {time.time() - calc_start:.2f}秒, 数据量: {len(df_all)}行")
        self.df_all = df_all

        total_elapsed = time.time() - datafeed_start
        logger.info(f"  [{task.name}] DataFeed: 数据准备总完成, 总耗时 {total_elapsed:.2f}秒")


    def get_factor_df(self, col):
        if col not in self.df_all.columns:
            logger.warning(f'Column {col} not found in computed factors')
            return None
        df_factor = self.df_all.pivot_table(values=col, index=self.df_all.index, columns='symbol')
        if col == 'close':
            df_factor = df_factor.ffill()
        return df_factor


class Engine:
    def __init__(self, path='quotes'):
        self.path = path
        self._init_engine()


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

        from core import backtrader_algos

        if task.period == 'RunEveryNPeriods':
            algo_period = bt.algos.RunEveryNPeriods(n=task.period_days, run_on_last_date=True)
        else:
            algo_period = getattr(backtrader_algos,task.period)()

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
            algo_select_where = SelectWhere(signal=select_signal)

        # 排序因子
        algo_order_by = None
        if task.order_by_signal:
            signal_order_by = self.datafeed.get_factor_df(col=task.order_by_signal)
            algo_order_by = SelectTopK(signal=signal_order_by, K=task.order_by_topK, drop_top_n=task.order_by_dropN,
                                       b_ascending=task.order_by_DESC==False)

        algos = []
        algos.append(algo_period)

        if algo_select_where:
            algos.append(algo_select_where)
        else:
            algos.append(SelectAll())

        if algo_order_by:
            algos.append(algo_order_by)


        algo_weight = WeightEqually()
        if task.weight == 'WeightFix':
            algo_weight =  WeightFix(weights_dict=task.weight_fixed)

        algos.append(algo_weight)

        force_update=False
        if task.weight == 'WeightFix':
            force_update = True
        algos.append(ReBalance(force_update))
        return algos


    def _init_engine(self):
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(1000000.0)  # 设置初始资金
        # cerebro.broker.setcommission(0.0005)
        # 添加PyFolio分析器
        cerebro.addanalyzer(bt.analyzers.PyFolio, _name='_PyFolio')

        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        cerebro.broker.set_coc(True)  # 设置Cheat-On-Close，确保在收盘时执行订单
        self.cerebro = cerebro

    def _prepare_run(self, symbols, start_date, end_date, commissions=0.0):
        dfs = DbDataLoader(auto_download=False).read_dfs(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )
        self.cerebro.broker.setcommission(commissions)
        if not dfs:
            logger.warning("未加载到任何回测数据")
            return start_date, end_date

        requested_start = pd.to_datetime(start_date)
        requested_end = pd.to_datetime(end_date)
        cleaned_dfs = {}
        effective_start = requested_start

        for s, data in dfs.items():
            if data.empty or 'date' not in data.columns:
                continue
            data = data.copy()
            data['openinterest'] = 0
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
            data.sort_index(ascending=True, inplace=True)
            if not data.empty:
                effective_start = max(effective_start, data.index.min())
            cleaned_dfs[s] = data

        for s, data in cleaned_dfs.items():
            clipped = data[
                (data.index >= effective_start) &
                (data.index <= requested_end)
            ]
            if clipped.empty:
                continue

            bt_data = bt.feeds.PandasData(
                dataname=clipped,
                fromdate=effective_start,
                todate=requested_end,
                timeframe=bt.TimeFrame.Days,
                name=s,
            )
            self.cerebro.adddata(bt_data)

        return effective_start.strftime('%Y%m%d'), requested_end.strftime('%Y%m%d')


    def run_strategy(self, strategy, symbols,start_date='20101001', end_date=datetime.now().strftime('%Y%m%d'),*args,**kwargs):
        self._init_engine()
        self._prepare_run(symbols,start_date, end_date)
        self.cerebro.addstrategy(strategy,*args,**kwargs)
        self.results = self.cerebro.run()
        portfolio_stats = self.results[0].analyzers.getbyname('_PyFolio')
        returns, positions, transactions, _ = portfolio_stats.get_pf_items()
        returns.index = returns.index.tz_convert(None)

        #equity = (1 + returns).cumprod()
        self.perf = (1 + returns).cumprod().calc_stats()
        self.hist_trades = [trade.to_dict() for trade in BacktestResult.normalize_trade_records(self.results[0].trade_list)]
        self.backtest_result = BacktestResult.from_common_inputs(
            statistics=self.perf.stats,
            equity_curve=self.perf.prices[['策略']] if hasattr(self.perf, 'prices') else (1 + returns).cumprod(),
            trades=self.hist_trades,
            positions=positions,
            raw={'start_date': start_date, 'end_date': end_date},
        )
        return self.backtest_result


    def run(self, task: Task, commissions=0.0):
        """
        运行策略回测

        Args:
            task: 策略任务配置
            commissions: 佣金费率(仅非A股模式时使用)

        Returns:
            回测结果
        """
        import time
        run_start = time.time()
        self._init_engine()
        effective_end_date = task.end_date or datetime.now().strftime('%Y%m%d')
        effective_start_date = task.start_date

        logger.debug(f"  [{task.name}] Engine.run(): 初始化回测引擎...")

        # 准备数据
        effective_start_date, effective_end_date = self._prepare_run(
            task.symbols, effective_start_date, effective_end_date, 0.0
        )

        # A股模式: 覆盖手续费方案
        if task.ashare_mode:
            from aitrader.domain.backtest.ashare_commission import setup_ashare_commission
            setup_ashare_commission(self.cerebro, scheme_version=task.ashare_commission)
            logger.debug(f"  [{task.name}] A股模式已启用, 手续费方案: {task.ashare_commission}")
        else:
            # 默认模式: 使用传统佣金设置
            self.cerebro.broker.setcommission(commissions)

        # DataFeed初始化(包含数据加载和指标计算)
        self.datafeed = DataFeed(task)

        # 添加策略,传递A股模式参数
        logger.debug(f"  [{task.name}] 添加策略算法...")
        self.cerebro.addstrategy(
            AlgoStrategy,
            algo_list=self._get_algos(task),
            ashare_mode=task.ashare_mode
        )

        # 运行回测
        logger.info(f"  [{task.name}] 开始执行Backtrader回测...")
        backtest_start = time.time()
        self.results = self.cerebro.run()
        backtest_elapsed = time.time() - backtest_start
        logger.info(f"  [{task.name}] Backtrader回测完成, 耗时 {backtest_elapsed:.2f}秒")

        timereturn = self.results[0].analyzers.timereturn.get_analysis()
        returns_series = pd.Series(timereturn, dtype=float)

        portfolio_stats = self.results[0].analyzers.getbyname('_PyFolio')
        returns, self.positions, self.transactions, _ = portfolio_stats.get_pf_items()
        #print('returns', returns)

        returns.index = returns.index.tz_convert(None)
        returns.name = '策略'

        equity = pd.DataFrame((1 + returns).cumprod())
        import ffn
        datas = [equity]
        benchmark_curve = pd.DataFrame()
        for bench in [task.benchmark]:
            dfs = DbDataLoader().read_dfs([bench],start_date=task.start_date, end_date=task.end_date)
            df = dfs.get(bench, pd.DataFrame())
            if df.empty:
                logger.warning(f"基准 {bench} 数据为空，跳过")
                continue
            df.set_index('date',inplace=True)
            df.index = pd.to_datetime(df.index)
            data = df.pivot_table(values='close', index=df.index, columns='symbol')
            data.columns = ['benchmark']
            datas.append(data)
            benchmark_curve = data.copy()


        all_returns = pd.concat(datas, axis=1).pct_change()
        all_returns.dropna(inplace=True)

        self.perf = (1 + all_returns).cumprod().calc_stats()
        normalized_trades = BacktestResult.normalize_trade_records(self.results[0].trade_list)
        self.hist_trades = [trade.to_dict() for trade in reversed(normalized_trades)]
        self.signals = self.results[0].signals
        self.weights = self.results[0].weights
        self.backtest_result = BacktestResult.from_common_inputs(
            statistics=self.perf.stats,
            equity_curve=self.perf.prices[['策略']] if hasattr(self.perf, 'prices') else equity,
            benchmark_curve=self.perf.prices[['benchmark']] if hasattr(self.perf, 'prices') and 'benchmark' in getattr(self.perf, 'prices').columns else benchmark_curve,
            trades=self.hist_trades,
            positions=self.positions,
            signals=self.signals,
            weights=self.weights,
            analyzers={
                'timereturn': returns_series.to_dict(),
                'returns': self.results[0].analyzers.returns.get_analysis(),
                'drawdown': self.results[0].analyzers.drawdown.get_analysis(),
                'sharpe': self.results[0].analyzers.sharpe.get_analysis(),
            },
            raw={
                'strategy_name': task.name,
                'start_date': effective_start_date,
                'end_date': effective_end_date,
            }
        )
        return self.backtest_result

    def opt(self, strategy,symbols,start_date='20101001', end_date=datetime.now().strftime('%Y%m%d'),*args,**kwargs):
        self._prepare_run(symbols, start_date, end_date)
        self.cerebro.optstrategy(
            strategy,
            period=[5,10,15,20,25,30]
        )

        # 打印结果
        def get_my_analyzer(result):
            analyzer = {}
            # 返回参数
            analyzer['period'] = result.params.period
            #analyzer['period2'] = result.params.lower

            pyfolio = result.analyzers.getbyname('_PyFolio')
            returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
            #print(positions, transactions)
            import empyrical as em
            analyzer['年化收益率'] = em.annual_return(returns)
            return analyzer

        self.results = self.cerebro.run(stdstats=False)
        ret = []
        for i in self.results:
            #print(i)
            ret.append(get_my_analyzer(i[0]))

        df = pd.DataFrame(ret)
        #print(df)



    def stats(self):

        print(self.perf.display())

    def plot(self):
        self.perf.plot()
        import matplotlib.pyplot as plt
        # 设置字体为 SimHei（黑体）
        plt.rcParams['font.sans-serif'] = ['SimHei']
        # 解决坐标轴负号显示问题
        plt.rcParams['axes.unicode_minus'] = False
        plt.show()


