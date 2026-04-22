import importlib
import os
from collections.abc import Mapping, Sequence
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

    benchmark: str = ''
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

# 进程级基准数据缓存: {(symbol, start, end): df}
# 避免同一进程内多次 Engine.run() 重复查询同一基准。
_BENCHMARK_CACHE: dict = {}

# 进程内宽表缓存: {(symbols, start, end, fields): df_all}
_DATAFEED_CACHE: dict[tuple, pd.DataFrame] = {}


def _normalize_cache_bound(value: str) -> str:
    return str(value).replace('-', '')


def _normalize_field_key(fields: list[str]) -> tuple[str, ...]:
    return tuple(sorted({field for field in fields if field}))


def _datafeed_cache_key(
    symbols: tuple[str, ...],
    start_date: str,
    end_date: str,
    adjust_type: str,
    fields: tuple[str, ...],
) -> tuple:
    return (
        symbols,
        _normalize_cache_bound(start_date),
        _normalize_cache_bound(end_date),
        adjust_type,
        fields,
    )


def _find_datafeed_cache(
    symbols: tuple[str, ...],
    start_date: str,
    end_date: str,
    adjust_type: str,
    fields: tuple[str, ...],
) -> tuple[pd.DataFrame | None, bool]:
    """Return cached df_all and whether it came from a superset field cache."""
    cache_key = _datafeed_cache_key(symbols, start_date, end_date, adjust_type, fields)
    cached = _DATAFEED_CACHE.get(cache_key)
    if cached is not None:
        return cached, False

    requested_fields = set(fields)
    start_norm = _normalize_cache_bound(start_date)
    end_norm = _normalize_cache_bound(end_date)
    for (
        cached_symbols,
        cached_start,
        cached_end,
        cached_adjust_type,
        cached_fields,
    ), cached_df in _DATAFEED_CACHE.items():
        if cached_symbols != symbols:
            continue
        if cached_start != start_norm or cached_end != end_norm:
            continue
        if cached_adjust_type != adjust_type:
            continue
        if requested_fields.issubset(set(cached_fields)):
            return cached_df, True

    return None, False


def _resolve_factor_workers() -> int | None:
    """Optional cap for nested factor-calculation pools.

    AITRADER_FACTOR_WORKERS is useful on large servers where multiple strategy
    processes run concurrently. Without a cap, each strategy may try to use all
    CPUs for factor calculation and oversubscribe the machine.
    """
    raw = os.getenv('AITRADER_FACTOR_WORKERS', '').strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"AITRADER_FACTOR_WORKERS={raw!r} 不是整数, 使用自动 worker 数")
        return None
    if value <= 0:
        logger.warning(f"AITRADER_FACTOR_WORKERS={raw!r} 必须 > 0, 使用自动 worker 数")
        return None
    return value


def _normalize_benchmark_symbol(value: str | None) -> str:
    return str(value or '').strip()


_POSITION_DATE_KEYS = {'date', 'datetime', 'time', 'index', 'dt'}
_POSITION_SYMBOL_KEYS = {'symbol', 'ticker', 'code', 'security', 'asset', 'name', '标的', '证券'}
_POSITION_VALUE_KEYS = {
    'value',
    'amount',
    'shares',
    'size',
    'qty',
    'quantity',
    'weight',
    'position',
    'holding',
    'exposure',
}


def _normalize_position_key(value: object) -> str:
    return str(value).strip().lower()


def _is_cash_column(col_name: object) -> bool:
    col_text = _normalize_position_key(col_name)
    return col_text in {'cash', '现金'} or 'cash' in col_text


def _pick_mapping_value(record: Mapping, key_pool: set[str]):
    for key, value in record.items():
        if _normalize_position_key(key) in key_pool and value not in (None, ''):
            return value
    return None


def _to_finite_float(value: object) -> float | None:
    if value is None or value == '':
        return None

    try:
        value = value.item()
    except Exception:
        pass

    if isinstance(value, (pd.Timestamp, datetime)):
        return None

    try:
        number = float(value)
    except Exception:
        return None

    if not np.isfinite(number):
        return None
    return number


def _coerce_position_record(item) -> dict | None:
    if item is None:
        return None

    if pd is not None and isinstance(item, pd.Series):
        return item.to_dict()

    if isinstance(item, Mapping):
        record = dict(item)
        nested_value = record.get('value')
        if set(record.keys()) <= {'date', 'datetime', 'time', 'index', 'value'} and isinstance(nested_value, Mapping):
            expanded = dict(nested_value)
            for key in ('date', 'datetime', 'time', 'index'):
                if key in record and key not in expanded:
                    expanded[key] = record[key]
            return expanded
        return record

    if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)) and len(item) >= 2:
        head, tail = item[0], item[1]
        if isinstance(tail, Mapping):
            record = dict(tail)
            record.setdefault('date', head)
            return record

    return None


def _position_records(positions) -> list[dict]:
    if positions is None:
        return []

    if pd is not None and isinstance(positions, pd.DataFrame):
        return positions.to_dict('records')

    if pd is not None and isinstance(positions, pd.Series):
        return [positions.to_dict()]

    if isinstance(positions, Mapping):
        if positions and all(isinstance(value, Mapping) for value in positions.values()):
            records = []
            for key, value in positions.items():
                record = dict(value)
                if not any(k in record for k in ('date', 'datetime', 'time', 'index')):
                    record['date'] = key
                records.append(record)
            return records
        return [dict(positions)]

    if isinstance(positions, Sequence) and not isinstance(positions, (str, bytes, bytearray)):
        records = []
        for item in positions:
            record = _coerce_position_record(item)
            if record:
                records.append(record)
        return records

    return []


def _sparse_position_holding_counts(rows: list[dict]) -> list[int]:
    counts_by_date: dict[str, set[str]] = defaultdict(set)

    for idx, row in enumerate(rows):
        symbol = _pick_mapping_value(row, _POSITION_SYMBOL_KEYS)
        numeric_value = _pick_mapping_value(row, _POSITION_VALUE_KEYS)
        numeric_value = _to_finite_float(numeric_value)
        if symbol in (None, '') or numeric_value is None or abs(numeric_value) <= 1e-8:
            continue

        date_value = _pick_mapping_value(row, _POSITION_DATE_KEYS)
        date_key = str(date_value or idx)
        counts_by_date[date_key].add(str(symbol))

    return [len(symbols) for symbols in counts_by_date.values() if symbols]


def _wide_position_holding_counts(rows: list[dict]) -> list[int]:
    holding_counts = []
    meta_keys = _POSITION_DATE_KEYS | _POSITION_SYMBOL_KEYS

    for row in rows:
        count = 0
        for key, value in row.items():
            key_text = _normalize_position_key(key)
            if key_text in meta_keys or _is_cash_column(key):
                continue

            numeric_value = _to_finite_float(value)
            if numeric_value is None or abs(numeric_value) <= 1e-8:
                continue
            count += 1

        holding_counts.append(count)

    return holding_counts


def _normalize_timestamp(value) -> pd.Timestamp | None:
    if value in (None, ''):
        return None
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    return ts.tz_localize(None).normalize() if ts.tzinfo is not None else ts.normalize()


def _signal_holding_counts(signals, trading_dates) -> list[int]:
    if not isinstance(signals, Mapping) or not signals:
        return []
    if trading_dates is None:
        return []

    holdings_by_date: dict[pd.Timestamp, int] = {}
    for raw_date, items in signals.items():
        signal_date = _normalize_timestamp(raw_date)
        if signal_date is None or not isinstance(items, Sequence):
            continue

        active_symbols = set()
        for item in items:
            if not isinstance(item, Mapping):
                continue
            symbol = _pick_mapping_value(item, _POSITION_SYMBOL_KEYS)
            pos_to = _to_finite_float(item.get('pos_to'))
            if symbol in (None, '') or pos_to is None or pos_to <= 1e-8:
                continue
            active_symbols.add(str(symbol))

        holdings_by_date[signal_date] = len(active_symbols)

    if not holdings_by_date:
        return []

    normalized_dates = []
    for value in trading_dates:
        ts = _normalize_timestamp(value)
        if ts is not None:
            normalized_dates.append(ts)

    if not normalized_dates:
        return []

    holding_counts = []
    current_count = 0
    for trade_date in normalized_dates:
        if trade_date in holdings_by_date:
            current_count = holdings_by_date[trade_date]
        holding_counts.append(current_count)

    return holding_counts


def _extract_trade_dates(trades: list) -> list[str]:
    dates = []
    for trade in trades:
        for value in (
            getattr(trade, 'buy_date', ''),
            getattr(trade, 'date', ''),
            getattr(trade, 'sell_date', ''),
        ):
            if value:
                dates.append(str(value))
    return dates


def _compute_backtest_diagnostics(
    trades: list,
    positions,
    signals=None,
    trading_dates=None,
) -> dict:
    diagnostics = {
        'trade_count': len(trades),
        'first_trade_date': '',
        'invested_days_pct': 0.0,
        'avg_holdings': 0.0,
    }

    trade_dates = sorted(_extract_trade_dates(trades))
    if trade_dates:
        diagnostics['first_trade_date'] = trade_dates[0]

    holding_counts = _signal_holding_counts(signals, trading_dates)
    if not holding_counts:
        rows = _position_records(positions)
        if not rows:
            return diagnostics

        sparse_rows = sum(
            1
            for row in rows
            if _pick_mapping_value(row, _POSITION_SYMBOL_KEYS) not in (None, '')
            and any(_normalize_position_key(key) in _POSITION_VALUE_KEYS for key in row.keys())
        )
        if sparse_rows and sparse_rows >= len(rows) / 2:
            holding_counts = _sparse_position_holding_counts(rows)
        else:
            holding_counts = _wide_position_holding_counts(rows)

    if not holding_counts:
        return diagnostics

    invested_counts = [count for count in holding_counts if count > 0]
    diagnostics['invested_days_pct'] = float(len(invested_counts) / len(holding_counts))
    if invested_counts:
        diagnostics['avg_holdings'] = float(sum(invested_counts) / len(invested_counts))

    return diagnostics


class DataFeed:
    def __init__(self, task: Task, preloaded_dfs: dict | None = None):
        datafeed_start = time.time()
        self._factor_df_cache: dict[str, pd.DataFrame] = {}

        loader_adjust_type = 'qfq'
        cache_symbols = tuple(sorted((preloaded_dfs or {}).keys() or task.symbols))
        fields = list(
            _normalize_field_key(
                task.select_buy + task.select_sell + ([task.order_by_signal] if task.order_by_signal else [])
            )
        )
        fields_key = tuple(fields)
        cache_key = _datafeed_cache_key(
            cache_symbols,
            task.start_date,
            task.end_date,
            loader_adjust_type,
            fields_key,
        )

        cached_df_all, is_superset_cache = _find_datafeed_cache(
            cache_symbols,
            task.start_date,
            task.end_date,
            loader_adjust_type,
            fields_key,
        )
        if cached_df_all is not None:
            cache_kind = "宽表超集缓存" if is_superset_cache else "宽表缓存"
            logger.info(f"  [{task.name}] DataFeed: 命中{cache_kind} (标的数: {len(cache_symbols)}, 因子数: {len(fields)})")
            self.df_all = cached_df_all
            total_elapsed = time.time() - datafeed_start
            logger.info(f"  [{task.name}] DataFeed: 数据准备总完成, 总耗时 {total_elapsed:.2f}秒")
            return

        if preloaded_dfs is not None:
            logger.info(f"  [{task.name}] DataFeed: 复用已加载数据 (标的数: {len(preloaded_dfs)})")
            dfs = preloaded_dfs
        else:
            logger.info(f"  [{task.name}] DataFeed: 开始加载数据 (标的数: {len(task.symbols)})...")
            logger.debug(f"  [{task.name}] DataFeed: 日期范围 {task.start_date} ~ {task.end_date}")
            dfs = DbDataLoader(auto_download=False, adjust_type=loader_adjust_type).read_dfs(
                symbols=task.symbols,
                start_date=task.start_date,
                end_date=task.end_date,
                copy_result=False,
            )
            logger.info(f"  [{task.name}] DataFeed: 原始数据加载完成, 耗时 {time.time() - datafeed_start:.2f}秒")

        if fields:
            logger.debug(f"  [{task.name}] DataFeed: 计算技术指标: {', '.join(fields)}")
        else:
            logger.debug(f"  [{task.name}] DataFeed: 无额外因子表达式，仅使用原始行情字段")

        calc_start = time.time()
        factor_workers = _resolve_factor_workers()
        if factor_workers is not None:
            logger.info(f"  [{task.name}] DataFeed: 因子计算 worker 上限={factor_workers}")
        df_all = FactorExpr().calc_formulas(
            dfs,
            fields,
            parallel=True,
            max_workers=factor_workers,
        )
        logger.info(f"  [{task.name}] DataFeed: 技术指标计算完成, 耗时 {time.time() - calc_start:.2f}秒, 数据量: {len(df_all)}行")
        self.df_all = df_all
        _DATAFEED_CACHE[cache_key] = df_all

        total_elapsed = time.time() - datafeed_start
        logger.info(f"  [{task.name}] DataFeed: 数据准备总完成, 总耗时 {total_elapsed:.2f}秒")


    def get_factor_df(self, col):
        cached = self._factor_df_cache.get(col)
        if cached is not None:
            return cached

        if col not in self.df_all.columns:
            logger.warning(f'Column {col} not found in computed factors')
            return None

        index_name = self.df_all.index.name or 'index'
        factor_frame = self.df_all.reset_index()
        try:
            df_factor = factor_frame.pivot(index=index_name, columns='symbol', values=col)
        except ValueError:
            df_factor = factor_frame.pivot_table(
                values=col,
                index=index_name,
                columns='symbol',
                aggfunc='first',
            )

        if col == 'close':
            df_factor = df_factor.ffill()

        self._factor_df_cache[col] = df_factor
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
                    df_r = df_r.astype('boolean').astype('Int64')

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

        from aitrader.domain.backtest import algos as backtrader_algos

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
        load_start = time.time()
        dfs = DbDataLoader(auto_download=False).read_dfs(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            copy_result=False,
        )
        logger.info(f"  _prepare_run: MySQL 加载完成 {len(dfs)} 标的, 耗时 {time.time() - load_start:.2f}秒")
        self.cerebro.broker.setcommission(commissions)
        if not dfs:
            logger.warning("未加载到任何回测数据")
            self._raw_dfs = {}
            return start_date, end_date

        # 缓存原始 dfs (date 仍是 YYYYMMDD 列), 供后续 DataFeed 复用,
        # 避免 Engine.run() 中再次发 MySQL 查询。
        self._raw_dfs = dfs

        requested_start = pd.to_datetime(start_date)
        requested_end = pd.to_datetime(end_date)
        cleaned_dfs = {}

        for s, data in dfs.items():
            if data.empty or 'date' not in data.columns:
                continue
            data = data.copy()
            data['openinterest'] = 0
            data['date'] = pd.to_datetime(data['date'])
            data.set_index('date', inplace=True)
            data.sort_index(ascending=True, inplace=True)
            cleaned_dfs[s] = data

        # effective_start = requested_start，不再取所有标的最晚首日，
        # 各标的数据从 requested_start 开始截取，数据不足的标的自然只有部分数据。
        effective_start = requested_start

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

        # DataFeed初始化(复用 _prepare_run 中已加载的数据, 避免再发一次 MySQL 查询)
        self.datafeed = DataFeed(task, preloaded_dfs=getattr(self, '_raw_dfs', None))

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
        benchmark_symbol = _normalize_benchmark_symbol(task.benchmark)
        if not benchmark_symbol:
            logger.info(f"  [{task.name}] 未设置基准，跳过基准对比")

        for bench in ([benchmark_symbol] if benchmark_symbol else []):
            cache_key = (bench, task.start_date, task.end_date)
            cached = _BENCHMARK_CACHE.get(cache_key)
            if cached is not None:
                logger.debug(f"  [{task.name}] 基准 {bench} 命中缓存")
                data = cached.copy()
            else:
                try:
                    dfs = DbDataLoader().read_dfs(
                        symbols=[bench],
                        start_date=task.start_date,
                        end_date=task.end_date,
                        copy_result=False,
                    )
                except (ValueError, Exception) as e:
                    logger.warning(f"基准 {bench} 数据加载失败，跳过基准对比: {e}")
                    continue
                df = dfs.get(bench, pd.DataFrame()).copy()
                if df.empty:
                    logger.warning(f"基准 {bench} 数据为空，跳过")
                    continue
                df.set_index('date', inplace=True)
                df.index = pd.to_datetime(df.index)
                data = df.pivot_table(values='close', index=df.index, columns='symbol')
                data.columns = ['benchmark']
                _BENCHMARK_CACHE[cache_key] = data.copy()
            datas.append(data)
            benchmark_curve = data.copy()


        all_returns = pd.concat(datas, axis=1).pct_change()
        all_returns.dropna(inplace=True)

        self.perf = (1 + all_returns).cumprod().calc_stats()
        normalized_trades = BacktestResult.normalize_trade_records(self.results[0].trade_list)
        self.hist_trades = [trade.to_dict() for trade in reversed(normalized_trades)]
        self.signals = self.results[0].signals
        self.weights = self.results[0].weights
        diagnostics = _compute_backtest_diagnostics(
            normalized_trades,
            self.positions,
            signals=self.signals,
            trading_dates=returns.index,
        )
        logger.info(
            f"  [{task.name}] 交易诊断: trades={diagnostics['trade_count']}, "
            f"first_trade={diagnostics['first_trade_date'] or 'NA'}, "
            f"invested_days_pct={diagnostics['invested_days_pct']:.2%}, "
            f"avg_holdings={diagnostics['avg_holdings']:.1f}"
        )
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
                'diagnostics': diagnostics,
            },
            raw={
                'strategy_name': task.name,
                'start_date': effective_start_date,
                'end_date': effective_end_date,
                'diagnostics': diagnostics,
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
