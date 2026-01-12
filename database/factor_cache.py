"""
因子缓存优化器
批量计算并缓存因子表达式,避免重复计算
"""
import pandas as pd
from typing import List, Dict
from datafeed.db_dataloader import DbDataLoader
from datafeed.factor_expr import FactorExpr


class FactorCache:
    """因子缓存类"""

    def __init__(self, symbols: List[str], start_date: str, end_date: str, adjust_type='qfq'):
        """
        初始化因子缓存

        Args:
            symbols: 标的列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            adjust_type: 复权类型 ('qfq'前复权, 'hfq'后复权，默认前复权)
        """
        self.symbols = list(set(symbols))  # 去重
        self.start_date = start_date
        self.end_date = end_date
        self.adjust_type = adjust_type
        self.factor_cache: Dict[str, pd.DataFrame] = {}
        self.df_all = None

    def calculate_factors(self, factor_expressions: List[str]) -> Dict[str, pd.DataFrame]:
        """
        批量计算所有因子表达式

        Args:
            factor_expressions: 因子表达式列表

        Returns:
            因子字典 {expression: DataFrame}
        """
        import io
        import sys
        from loguru import logger

        # 去重并添加必需的 close 字段
        unique_exprs = list(set(factor_expressions))
        if 'close' not in unique_exprs:
            unique_exprs.append('close')

        # 临时禁用详细日志和调试输出
        logger.disable("datafeed.db_dataloader")

        # 捕获标准输出,抑制因子计算的调试信息
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # 加载数据
            loader = DbDataLoader(adjust_type=self.adjust_type)
            dfs = loader.read_dfs(
                symbols=self.symbols,
                start_date=self.start_date,
                end_date=self.end_date
            )

            if not dfs:
                print("  ⚠️  没有加载到任何数据", file=old_stdout)
                return {}

            # 批量计算所有因子
            factor_calc = FactorExpr()
            self.df_all = factor_calc.calc_formulas(dfs, unique_exprs)

        except Exception as e:
            print(f"  ⚠️  数据处理失败: {e}", file=old_stdout)
            return {}
        finally:
            # 恢复标准输出
            sys.stdout = old_stdout
            logger.enable("datafeed.db_dataloader")

        # 缓存每个因子 (pivot 为 date × symbol 格式)
        for expr in unique_exprs:
            try:
                df_factor = self.df_all.pivot_table(
                    values=expr,
                    index=self.df_all.index,
                    columns='symbol'
                )

                # close 价格需要前向填充
                if expr == 'close':
                    df_factor = df_factor.ffill()

                self.factor_cache[expr] = df_factor
            except Exception as e:
                print(f"  ⚠️  因子 {expr} 处理失败: {e}")

        print(f"  ✓ 因子缓存完成: {len(self.factor_cache)} 个因子")

        return self.factor_cache

    def get_factor(self, expression: str) -> pd.DataFrame:
        """
        获取缓存的因子数据

        Args:
            expression: 因子表达式

        Returns:
            因子 DataFrame (index=date, columns=symbols)
        """
        return self.factor_cache.get(expression)

    def get_latest_value(self, expression: str, symbol: str) -> float:
        """
        获取某个标的的最新因子值

        Args:
            expression: 因子表达式
            symbol: 标的代码

        Returns:
            最新因子值,如果不存在返回 None
        """
        df = self.get_factor(expression)
        if df is None or df.empty or symbol not in df.columns:
            return None

        return df.iloc[-1][symbol]

    def has_factor(self, expression: str) -> bool:
        """
        检查因子是否已缓存

        Args:
            expression: 因子表达式

        Returns:
            是否存在
        """
        return expression in self.factor_cache

    def get_all_symbols(self) -> List[str]:
        """
        获取所有标的代码

        Returns:
            标的代码列表
        """
        return self.symbols

    def get_latest_date(self) -> str:
        """
        获取最新数据的日期

        Returns:
            最新日期字符串
        """
        if self.df_all is None or self.df_all.empty:
            return None

        latest = self.df_all.index.max()
        return latest.strftime('%Y-%m-%d')


if __name__ == '__main__':
    # 测试因子缓存
    cache = FactorCache(
        symbols=['510300.SH', '513100.SH', '159915.SZ'],
        start_date='20240101',
        end_date='20241231'
    )

    factors = [
        'close',
        'roc(close,5)',
        'roc(close,10)',
        'ma(close,20)',
        'trend_score(close,25)'
    ]

    cache.calculate_factors(factors)

    # 测试获取因子
    print("\n测试获取因子:")
    df_close = cache.get_factor('close')
    if df_close is not None:
        print(f"close 形状: {df_close.shape}")
        print(f"510300.SH 最新价格: {df_close.iloc[-1]['510300.SH']:.3f}")

    df_roc = cache.get_factor('roc(close,5)')
    if df_roc is not None:
        print(f"roc(close,5) 形状: {df_roc.shape}")
        print(f"513100.SH 最新 ROC: {df_roc.iloc[-1]['513100.SH']:.4f}")
