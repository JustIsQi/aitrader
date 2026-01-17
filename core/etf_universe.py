"""
ETF池管理器 - ETF Universe Manager

提供ETF池动态筛选功能,支持多种筛选条件:
- 基础过滤:数据可用性
- 流动性筛选:成交额、换手率
- 类似StockUniverse,但针对ETF特性优化

作者: AITrader
日期: 2026-01-16
"""

import pandas as pd
import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from loguru import logger
from sqlalchemy.exc import OperationalError, DBAPIError

from database.pg_manager import get_db


class EtfUniverse:
    """
    ETF池管理器

    功能:
    1. 动态筛选ETF池
    2. 流动性分析
    3. 数据质量检查

    与StockUniverse的区别:
    - 不需要ST/停牌筛选(ETF无这些属性)
    - 专注于流动性筛选
    - 使用etf_history表数据
    """

    def __init__(self, db=None):
        """
        初始化ETF池管理器

        Args:
            db: 数据库管理器实例,为None则自动创建
        """
        self.db = db if db else get_db()
        logger.debug('ETF池管理器初始化完成')

    def get_all_etfs(self, min_data_days: int = 180) -> List[str]:
        """
        从etf_history表获取有足够数据的ETF

        Args:
            min_data_days: 最小历史数据天数,默认180天(半年)

        Returns:
            ETF代码列表
        """
        try:
            from database.models import EtfHistory

            with self.db.get_session() as session:
                # 从etf_history表查询有足够数据的ETF
                # 统计每个ETF的总交易天数(使用所有历史数据)
                from sqlalchemy import func

                # 统计每个ETF的总数据天数
                subquery = session.query(
                    EtfHistory.symbol,
                    func.count(EtfHistory.date).label('total_days')
                ).group_by(
                    EtfHistory.symbol
                ).having(
                    func.count(EtfHistory.date) >= min_data_days  # 至少有min_data_days天数据
                )

                # 获取符合条件的ETF代码
                results = subquery.all()
                symbols = [r[0] for r in results]

                logger.info(f'获取有{min_data_days}天以上数据的ETF: {len(symbols)}只')
                return symbols

        except Exception as e:
            logger.error(f'获取ETF列表失败: {e}')
            return []

    def filter_by_liquidity(self,
                           symbols: List[str],
                           min_avg_amount: float = 5000,
                           days: int = 20) -> List[str]:
        """
        按成交额筛选ETF

        Args:
            symbols: 初始ETF列表
            min_avg_amount: 最小日均成交额(万元),默认5000万
            days: 统计天数,默认20天

        Returns:
            筛选后的ETF列表
        """
        if not symbols:
            return []

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载ETF数据")
                return symbols

            # 计算每个ETF的平均成交额
            qualified = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty or 'amount' not in df.columns:
                    continue

                # 计算平均成交额(万元)
                recent_amount = df['amount'].tail(days)
                avg_amount = recent_amount.mean()

                # 筛选
                if pd.notna(avg_amount) and avg_amount >= min_avg_amount:
                    qualified.append(symbol)

            logger.debug(f'成交额筛选(>={min_avg_amount}万): {len(symbols)} -> {len(qualified)}')
            return qualified

        except Exception as e:
            logger.error(f'成交额筛选失败: {e}')
            return symbols

    def filter_by_turnover_rate(self,
                               symbols: List[str],
                               min_turnover: float = 1.0,
                               days: int = 20) -> List[str]:
        """
        按换手率筛选ETF

        Args:
            symbols: 初始ETF列表
            min_turnover: 最小平均换手率(%),默认1.0%
            days: 统计天数,默认20天

        Returns:
            筛选后的ETF列表
        """
        if not symbols:
            return []

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载ETF数据")
                return symbols

            # 计算每个ETF的平均换手率
            qualified = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty or 'turnover_rate' not in df.columns:
                    continue

                # 计算平均换手率
                recent_turnover = df['turnover_rate'].tail(days)
                avg_turnover = recent_turnover.mean()

                # 筛选
                if pd.notna(avg_turnover) and avg_turnover >= min_turnover:
                    qualified.append(symbol)

            logger.debug(f'换手率筛选(>={min_turnover}%): {len(symbols)} -> {len(qualified)}')
            return qualified

        except Exception as e:
            logger.error(f'换手率筛选失败: {e}')
            return symbols

    def get_etf_pool(self,
                    min_data_days: int = 180,
                    min_avg_amount: float = 5000,
                    min_turnover: float = 1.0,
                    liquidity_days: int = 20) -> List[str]:
        """
        综合获取ETF池(链式筛选)

        Args:
            min_data_days: 最小历史数据天数
            min_avg_amount: 最小日均成交额(万元)
            min_turnover: 最小平均换手率(%)
            liquidity_days: 流动性统计天数

        Returns:
            筛选后的ETF列表
        """
        import time
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"ETF池筛选开始")

        # 获取所有有足够数据的ETF
        symbols = self.get_all_etfs(min_data_days=min_data_days)
        logger.info(f"✓ 数据可用性: {len(symbols)} 只ETF")

        if not symbols:
            logger.warning("没有符合数据要求的ETF")
            return []

        # 按成交额筛选
        if min_avg_amount > 0:
            symbols = self.filter_by_liquidity(
                symbols=symbols,
                min_avg_amount=min_avg_amount,
                days=liquidity_days
            )
            logger.info(f"✓ 成交额筛选: {len(symbols)} 只ETF")

        # 按换手率筛选
        if min_turnover > 0:
            symbols = self.filter_by_turnover_rate(
                symbols=symbols,
                min_turnover=min_turnover,
                days=liquidity_days
            )
            logger.info(f"✓ 换手率筛选: {len(symbols)} 只ETF")

        elapsed = time.time() - start_time
        logger.success(f"✓ 筛选完成! 最终: {len(symbols)} 只ETF, 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return symbols


if __name__ == '__main__':
    """测试代码"""
    logger.info('ETF池管理器测试')

    # 测试: 获取ETF池
    universe = EtfUniverse()
    etf_pool = universe.get_etf_pool(
        min_data_days=180,
        min_avg_amount=5000,
        min_turnover=1.0,
        liquidity_days=20
    )

    logger.info(f"筛选结果: {len(etf_pool)} 只ETF")
    if len(etf_pool) > 0:
        logger.info(f"前10只: {etf_pool[:10]}")
