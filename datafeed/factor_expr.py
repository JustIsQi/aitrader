
from datafeed import mytt
from datafeed import factor_extends
from datafeed import factor_qlib

import numpy as np
import pandas as pd

class FactorExpr:
    def __init__(self):


        context = {}
        for method_name in dir(factor_extends):
            if not method_name.startswith('_'):
                method = getattr(factor_extends, method_name)
                context[method_name] = method
                context[method_name.upper()] = method

        for method_name in dir(mytt):
            if not method_name.startswith('_'):
                method = getattr(mytt, method_name)
                context[method_name] = method
                context[method_name.upper()] = method

        for method_name in dir(factor_qlib):
            if not method_name.startswith('_'):
                method = getattr(factor_qlib, method_name)
                context[method_name] = method
                context[method_name.upper()] = method

        # Add math functions to context
        math_funcs = {
            'LOG': np.log, 'EXP': np.exp, 'SQRT': np.sqrt, 'ABS': np.abs,
            'SIN': np.sin, 'COS': np.cos, 'TAN': np.tan, 'POWER': np.power,
            'SIGN': np.sign, 'MAX': np.maximum, 'MIN': np.minimum,
            'MEAN': np.mean, 'STD': np.std
        }
        context.update(math_funcs)

        # Add numpy and pandas to context
        context['np'] = np
        context['pd'] = pd

        self.context = context
        #self.update_base_factors()

    def update_base_factors(self, df: pd.DataFrame):
        for c in ['open', 'high', 'low', 'close', 'volume']:
            data = df[c]
            self.context[c.upper()] = data


    def calc_formula(self, df: pd.DataFrame, expr: str):
        try:
            #print(f'表达式:{expr}')
            context = self.context
            self.update_base_factors(df)

            result = eval(expr.upper(), context)


            if isinstance(result, tuple):
                results = []
                for i,r in enumerate(list(result)):
                    r = pd.Series(r)
                    r.name = f"{expr}_{str(i)}"
                    r.index = df.index
                    results.append(r)
                return results

            else:
                result =  pd.Series(result)
            #result = result[~result.index.duplicated(keep='first')]
                result.name = expr
                result.index = df.index
            return result

        except Exception as e:
            print(f"Formula execution error: {str(e)}")
            # print("Functions available in context:")
            # for key in sorted(context.keys()):
            #     if callable(context[key]):
            #         print(f"- {key}")


    def calc_formulas(self, dfs: dict, expr_list:list[str]):
        if not dfs:
            raise ValueError("没有可用的数据文件。请确保数据文件存在，或使用 fetch_stock_history_with_proxy 先下载数据。")

        all_datas = []
        for s, df in dfs.items():
            if 'date' in df.columns:
                df.set_index('date', inplace=True)
                df.index = pd.to_datetime(df.index)
                df.sort_index(ascending=True, inplace=True)
            datas = []
            for expr in expr_list:
                if expr in list(df.columns):
                    print(f'已存在{expr}，跳过')
                    continue

                result = self.calc_formula(df, expr)
                if isinstance(result,list):
                    datas.extend(result)
                else:
                    datas.append(result)
            df = df[~df.index.duplicated(keep='first')]  # 保留第一个
            datas.append(df) #把原始数据合成进去

            df_all = pd.concat(datas, axis=1)
            df_all = df_all[~df_all.index.duplicated(keep='first')]  # 保留第一个
            all_datas.append(df_all)

        all_datas = pd.concat(all_datas)
        all_datas.sort_index(ascending=True, inplace=True)
        return all_datas



if __name__ == '__main__':
    from datafeed.csv_dataloader import CsvDataLoader
    dfs = CsvDataLoader().read_dfs(symbols=['510300.SH', '159915.SZ'])

    expr = ['MACD(close,12,26,9)','SAR(high,low)']  # ['RSRS(high,low,18)','RSRS_right_zscore(high,low,18,600)']
    all = FactorExpr().calc_formulas(dfs,expr)



    print('这是计算结果',all)

    # from alpha.dataset.utility import DataProxy
    # from alpha.dataset.ts_function import (  # noqa
    #     ts_delay,
    #     ts_min, ts_max,
    #     ts_argmax, ts_argmin,
    #     ts_rank, ts_sum,
    #     ts_mean, ts_std,
    #     ts_slope, ts_quantile,
    #     ts_rsquare, ts_resi,
    #     ts_corr,
    #     ts_less, ts_greater,
    #     ts_log, ts_abs
    # )
    # import polars as pl
    # from alpha.dataset.ts_function import ts_delay as shift  # noqa
    # from alpha.dataset.expr_extends import trend_score, roc, RSRS  # noqa
    # from alpha.dataset.ts_function import ts_mean as ma  # noqa
    # from alpha.dataset.ts_function import ts_slope as slope  # noqa
    # df_polors = pl.from_pandas(df)
    # close = DataProxy(df_polors[["date", "symbol", 'close']])
    #
    # other: DataProxy = eval(expr, {}, locals())
    #
    # print(other.df)

    # result = FactorBuilder(df).calc_formulas(['RSRS_zscore(high,low,18,600)','trend_score(close,25)','RSRS(high,low,18)','roc100(close,20)','roc(close,20)'])
    # print(type(result),result)
    #
    # df_close = result.pivot_table(values='close', index=result.index, columns='symbol')
    # print(df_close)
    #
    # df_close = result.pivot_table(values='RSRS(high,low,18)', index=result.index, columns='symbol')
    # print(df_close)
    # import matplotlib.pyplot as plt
    #
    #
    # #
    # df_close = result.pivot_table(values='RSRS_right_zscore(high,low,18,600)', index=result.index, columns='symbol')
    # print(df_close)
    # df_close.plot()
    # plt.show()