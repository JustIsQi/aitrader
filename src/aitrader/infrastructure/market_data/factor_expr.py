from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from math import ceil
import os

import numpy as np
import pandas as pd

from aitrader.infrastructure.market_data import factor_extends
from aitrader.infrastructure.market_data import factor_fundamental
from aitrader.infrastructure.market_data import factor_qlib
from aitrader.infrastructure.market_data import mytt


def _build_context() -> dict:
    context = {}

    for module in (factor_extends, mytt, factor_qlib, factor_fundamental):
        for method_name in dir(module):
            if method_name.startswith('_'):
                continue
            method = getattr(module, method_name)
            context[method_name] = method
            context[method_name.upper()] = method

    math_funcs = {
        'LOG': np.log,
        'EXP': np.exp,
        'SQRT': np.sqrt,
        'ABS': np.abs,
        'SIN': np.sin,
        'COS': np.cos,
        'TAN': np.tan,
        'POWER': np.power,
        'SIGN': np.sign,
        'MAX': np.maximum,
        'MIN': np.minimum,
        'MEAN': np.mean,
        'STD': np.std,
    }
    context.update(math_funcs)
    context['np'] = np
    context['pd'] = pd
    return context


def _fork_context():
    try:
        return multiprocessing.get_context('fork')
    except ValueError:
        return None


class FactorExpr:
    def __init__(self):
        self.base_context = _build_context()

    def _build_symbol_context(self, df: pd.DataFrame) -> dict:
        context = self.base_context.copy()
        for col in df.columns:
            if col != 'symbol' and pd.api.types.is_numeric_dtype(df[col]):
                context[col.upper()] = df[col].copy()
        return context

    def _prepare_symbol_df(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        if 'date' in data.columns:
            data = data.set_index('date')
        data.index = pd.to_datetime(data.index)
        data.sort_index(ascending=True, inplace=True)
        data = data[~data.index.duplicated(keep='first')]
        return data

    def calc_formula(self, df: pd.DataFrame, expr: str, context: dict | None = None):
        try:
            if context is None:
                context = self._build_symbol_context(df)

            expr_upper = expr.upper()
            if ' AND ' in expr_upper or ' OR ' in expr_upper:
                expr_upper = expr_upper.replace(' AND ', ') & (')
                expr_upper = expr_upper.replace(' OR ', ') | (')
                expr_upper = '(' + expr_upper + ')'

            result = eval(expr_upper, context)

            if isinstance(result, tuple):
                results = []
                for i, value in enumerate(result):
                    series = pd.Series(value)
                    series.name = f'{expr}_{i}'
                    series.index = df.index
                    results.append(series)
                return results

            series = pd.Series(result)
            series.name = expr
            series.index = df.index
            return series

        except Exception as exc:
            print(f'Formula execution error: {exc}')
            return None

    def _calc_single_symbol(self, df: pd.DataFrame, expr_list: list[str]) -> pd.DataFrame:
        data = self._prepare_symbol_df(df)
        context = self._build_symbol_context(data)
        datas = []

        for expr in expr_list:
            if expr in data.columns:
                continue

            result = self.calc_formula(data, expr, context=context)
            if isinstance(result, list):
                datas.extend(result)
            elif result is not None:
                datas.append(result)

        datas.append(data)
        df_all = pd.concat(datas, axis=1)
        df_all = df_all[~df_all.index.duplicated(keep='first')]
        return df_all

    def _resolve_worker_count(self, total_symbols: int, max_workers: int | None = None) -> int:
        if total_symbols <= 1:
            return 1

        if max_workers is not None:
            return max(1, min(max_workers, total_symbols))

        cpu_count = os.cpu_count() or 1
        try:
            import psutil

            available_gb = psutil.virtual_memory().available / (1024**3)
            memory_limited = max(1, int(available_gb // 2.0))
            return max(1, min(cpu_count, total_symbols, memory_limited))
        except Exception:
            return max(1, min(cpu_count, total_symbols))

    def _calc_formulas_sequential(self, dfs: dict, expr_list: list[str]) -> pd.DataFrame:
        all_datas = []
        for _, df in dfs.items():
            symbol_df = self._calc_single_symbol(df, expr_list)
            if not symbol_df.empty:
                all_datas.append(symbol_df)

        if not all_datas:
            return pd.DataFrame()

        result = pd.concat(all_datas)
        result.sort_index(ascending=True, inplace=True)
        return result

    def _calc_formulas_parallel(
        self,
        dfs: dict,
        expr_list: list[str],
        max_workers: int | None = None,
    ) -> pd.DataFrame:
        symbol_items = list(dfs.items())
        worker_count = self._resolve_worker_count(len(symbol_items), max_workers=max_workers)
        if worker_count <= 1:
            return self._calc_formulas_sequential(dfs, expr_list)

        chunk_size = max(1, ceil(len(symbol_items) / worker_count))
        chunks = [symbol_items[i:i + chunk_size] for i in range(0, len(symbol_items), chunk_size)]

        results = []
        executor_kwargs = {'max_workers': worker_count}
        mp_context = _fork_context()
        if mp_context is not None:
            executor_kwargs['mp_context'] = mp_context

        with ProcessPoolExecutor(**executor_kwargs) as executor:
            futures = [
                executor.submit(_calc_formulas_chunk, chunk, expr_list)
                for chunk in chunks
            ]
            for future in as_completed(futures):
                chunk_result = future.result()
                if chunk_result is not None and not chunk_result.empty:
                    results.append(chunk_result)

        if not results:
            return pd.DataFrame()

        result = pd.concat(results)
        result.sort_index(ascending=True, inplace=True)
        return result

    def calc_formulas(
        self,
        dfs: dict,
        expr_list: list[str],
        parallel: bool = False,
        max_workers: int | None = None,
    ):
        if not dfs:
            raise ValueError('没有可用的数据文件。请确保数据文件存在，或使用 fetch_stock_history_with_proxy 先下载数据。')

        if parallel and len(dfs) > 1:
            return self._calc_formulas_parallel(dfs, expr_list, max_workers=max_workers)
        return self._calc_formulas_sequential(dfs, expr_list)


def _calc_formulas_chunk(symbol_items, expr_list):
    factor_calc = FactorExpr()
    results = []

    for _, df in symbol_items:
        symbol_df = factor_calc._calc_single_symbol(df, expr_list)
        if not symbol_df.empty:
            results.append(symbol_df)

    if not results:
        return pd.DataFrame()

    chunk_result = pd.concat(results)
    chunk_result.sort_index(ascending=True, inplace=True)
    return chunk_result


if __name__ == '__main__':
    from aitrader.infrastructure.market_data.loaders import DbDataLoader

    dfs = DbDataLoader().read_dfs(symbols=['510300.SH', '159915.SZ'])
    expr = ['MACD(close,12,26,9)', 'SAR(high,low)']
    result = FactorExpr().calc_formulas(dfs, expr, parallel=True)
    print('这是计算结果', result)
