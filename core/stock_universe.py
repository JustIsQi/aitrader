"""
股票池管理器

提供股票池动态筛选功能，支持多种筛选条件：
- 基础过滤：ST、停牌、退市等
- 市值筛选：最小/最大市值
- 基本面筛选：PE、PB、ROE等
- 行业筛选：板块、行业
- 流动性筛选：成交额

作者: AITrader
日期: 2026-01-05
"""

import pandas as pd
import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Callable, TypeVar
from loguru import logger
from sqlalchemy.exc import OperationalError, DBAPIError

from database.pg_manager import get_db
from database.models import StockMetadata, StockFundamentalDaily

T = TypeVar('T')


def retry_on_db_error(func: Callable[..., T], max_retries: int = 3, delay: float = 1.0) -> T:
    """
    数据库操作重试装饰器
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        
    Returns:
        函数执行结果
    """
    for attempt in range(max_retries):
        try:
            return func()
        except (OperationalError, DBAPIError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"数据库操作失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                time.sleep(delay * (attempt + 1))  # 指数退避
                continue
            else:
                logger.error(f"数据库操作失败，已达最大重试次数: {e}")
                raise
        except Exception as e:
            logger.error(f"非数据库错误: {e}")
            raise
    
    raise RuntimeError("重试逻辑异常")


class StockUniverse:
    """
    股票池管理器

    功能：
    1. 动态筛选股票池
    2. 统计分析
    3. 历史快照（可选）
    """

    def __init__(self, db=None):
        """
        初始化股票池管理器

        Args:
            db: 数据库管理器实例，为None则自动创建
        """
        self.db = db if db else get_db()
        logger.debug('股票池管理器初始化完成')

    def get_all_stocks(self, exclude_st=True, exclude_suspend=True,
                      exclude_new_ipo_days=None, min_data_days=180) -> List[str]:
        """
        获取所有可交易股票（基于实际交易数据）

        Args:
            exclude_st: 是否排除ST股票（需要元数据支持）
            exclude_suspend: 是否排除停牌股票（需要元数据支持）
            exclude_new_ipo_days: **已废弃**，保留参数仅为兼容性
            min_data_days: 最小数据天数，默认180天（半年）

        Returns:
            股票代码列表
        """
        def _query_stocks():
            from database.models import StockHistory
            from sqlalchemy import distinct

            # 计算截止日期
            cutoff_date = datetime.now().date() - timedelta(days=min_data_days)

            with self.db.get_session() as session:
                # 从 stock_history 表查询有足够数据的股票
                query = session.query(
                    distinct(StockHistory.symbol)
                ).filter(
                    StockHistory.date >= cutoff_date
                )

                # 如果需要排除ST/停牌股票，且元数据有标记，则进行过滤
                if exclude_st or exclude_suspend:
                    # 子查询：获取可交易股票的元数据
                    metadata_query = session.query(StockMetadata.symbol)

                    if exclude_st:
                        metadata_query = metadata_query.filter(StockMetadata.is_st == False)

                    if exclude_suspend:
                        metadata_query = metadata_query.filter(StockMetadata.is_suspend == False)

                    # 只保留既满足数据要求，又满足元数据要求的股票
                    valid_symbols = [row[0] for row in metadata_query.all()]
                    if valid_symbols:
                        query = query.filter(StockHistory.symbol.in_(valid_symbols))

                symbols = [row[0] for row in query.all()]
                logger.info(f'获取可交易股票: {len(symbols)} 只 '
                           f'(最近{min_data_days}天有数据)')
                return symbols

        try:
            return retry_on_db_error(_query_stocks, max_retries=3, delay=1.0)
        except Exception as e:
            logger.error(f'获取股票列表失败: {e}')
            return []

    def filter_by_market_cap(self, symbols: List[str],
                            min_mv: Optional[float] = None,
                            max_mv: Optional[float] = None) -> List[str]:
        """
        按市值筛选股票

        Args:
            symbols: 原始股票列表
            min_mv: 最小市值（亿元）
            max_mv: 最大市值（亿元）

        Returns:
            筛选后的股票代码列表
        """
        if not symbols:
            return []

        try:
            with self.db.get_session() as session:
                # 获取最新基本面数据
                subquery = session.query(
                    StockFundamentalDaily.symbol,
                    StockFundamentalDaily.total_mv
                ).filter(
                    StockFundamentalDaily.symbol.in_(symbols)
                ).distinct(
                    StockFundamentalDaily.symbol
                ).subquery()

                query = session.query(subquery.c.symbol)

                # 应用市值过滤
                if min_mv is not None:
                    query = query.filter(subquery.c.total_mv >= min_mv)

                if max_mv is not None:
                    query = query.filter(subquery.c.total_mv <= max_mv)

                filtered = [row[0] for row in query.all()]
                logger.debug(f'市值筛选: {len(symbols)} -> {len(filtered)}')
                return filtered

        except Exception as e:
            logger.error(f'市值筛选失败: {e}')
            return []

    def filter_by_fundamental(self, symbols: List[str],
                             min_pe: Optional[float] = None,
                             max_pe: Optional[float] = None,
                             min_pb: Optional[float] = None,
                             max_pb: Optional[float] = None,
                             min_roe: Optional[float] = None,
                             max_roe: Optional[float] = None,
                             min_roa: Optional[float] = None) -> List[str]:
        """
        按基本面指标筛选股票

        Args:
            symbols: 原始股票列表
            min_pe: 最小市盈率
            max_pe: 最大市盈率
            min_pb: 最小市净率
            max_pb: 最大市净率
            min_roe: 最小ROE
            max_roe: 最大ROE
            min_roa: 最小ROA

        Returns:
            筛选后的股票代码列表
        """
        if not symbols:
            return []

        try:
            with self.db.get_session() as session:
                # 获取最新基本面数据
                subquery = session.query(
                    StockFundamentalDaily
                ).filter(
                    StockFundamentalDaily.symbol.in_(symbols)
                ).distinct(
                    StockFundamentalDaily.symbol
                ).subquery()

                query = session.query(subquery.c.symbol)

                # 应用基本面过滤
                if min_pe is not None:
                    query = query.filter(subquery.c.pe_ratio >= min_pe)
                if max_pe is not None:
                    query = query.filter(subquery.c.pe_ratio <= max_pe)

                if min_pb is not None:
                    query = query.filter(subquery.c.pb_ratio >= min_pb)
                if max_pb is not None:
                    query = query.filter(subquery.c.pb_ratio <= max_pb)

                if min_roe is not None:
                    query = query.filter(subquery.c.roe >= min_roe)
                if max_roe is not None:
                    query = query.filter(subquery.c.roe <= max_roe)

                if min_roa is not None:
                    query = query.filter(subquery.c.roa >= min_roa)

                filtered = [row[0] for row in query.all()]
                logger.debug(f'基本面筛选: {len(symbols)} -> {len(filtered)}')
                return filtered

        except Exception as e:
            logger.error(f'基本面筛选失败: {e}')
            return []

    def filter_by_industry(self, symbols: List[str],
                          industries: Optional[List[str]] = None,
                          sectors: Optional[List[str]] = None) -> List[str]:
        """
        按行业筛选股票

        Args:
            symbols: 原始股票列表
            industries: 行业列表
            sectors: 板块列表

        Returns:
            筛选后的股票代码列表
        """
        if not symbols:
            return []

        if not industries and not sectors:
            return symbols

        try:
            with self.db.get_session() as session:
                query = session.query(StockMetadata.symbol).filter(
                    StockMetadata.symbol.in_(symbols)
                )

                # 行业筛选
                if industries:
                    query = query.filter(StockMetadata.industry.in_(industries))

                # 板块筛选
                if sectors:
                    query = query.filter(StockMetadata.sector.in_(sectors))

                filtered = [row[0] for row in query.all()]
                logger.debug(f'行业筛选: {len(symbols)} -> {len(filtered)}')
                return filtered

        except Exception as e:
            logger.error(f'行业筛选失败: {e}')
            return []

    def filter_by_liquidity(self, symbols: List[str],
                           min_amount: Optional[float] = None) -> List[str]:
        """
        按流动性筛选（基于成交额）

        Args:
            symbols: 原始股票列表
            min_amount: 最小日成交额（万元）

        Returns:
            筛选后的股票代码列表
        """
        if not symbols or min_amount is None:
            return symbols

        try:
            with self.db.get_session() as session:
                # 从历史数据获取最新成交额
                # 这里简化处理，实际应使用最新交易日的成交额
                logger.warning('流动性筛选功能需要最新成交额数据，当前返回原列表')
                return symbols

        except Exception as e:
            logger.error(f'流动性筛选失败: {e}')
            return []

    def get_stock_pool(self, date: Optional[date] = None,
                      filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        综合筛选股票池

        Args:
            date: 筛选日期（None表示最新）
            filters: 筛选条件字典
                - min_market_cap: 最小市值(亿)
                - max_market_cap: 最大市值(亿)
                - exclude_st: 排除ST股票 (默认True)
                - exclude_suspend: 排除停牌股票 (默认True)
                - exclude_new_ipo: 排除新上市天数
                - industries: 行业列表
                - sectors: 板块列表
                - min_liquidity: 最小成交额(万元)
                - min_pe, max_pe: 市盈率范围
                - min_pb, max_pb: 市净率范围
                - min_roe, max_roe: ROE范围
                - min_roa: 最小ROA

        Returns:
            符合条件的股票代码列表
        """
        if filters is None:
            filters = {}

        logger.info(f'开始筛选股票池，日期: {date or "最新"}')

        # 1. 获取基础股票列表
        symbols = self.get_all_stocks(
            exclude_st=filters.get('exclude_st', True),
            exclude_suspend=filters.get('exclude_suspend', True),
            exclude_new_ipo_days=filters.get('exclude_new_ipo')
        )

        if not symbols:
            logger.warning('基础股票列表为空')
            return []

        # 2. 按市值筛选
        min_mv = filters.get('min_market_cap')
        max_mv = filters.get('max_market_cap')
        if min_mv is not None or max_mv is not None:
            symbols = self.filter_by_market_cap(symbols, min_mv, max_mv)

        if not symbols:
            logger.warning('市值筛选后无股票')
            return []

        # 3. 按基本面筛选
        fundamental_filters = {
            'min_pe': filters.get('min_pe'),
            'max_pe': filters.get('max_pe'),
            'min_pb': filters.get('min_pb'),
            'max_pb': filters.get('max_pb'),
            'min_roe': filters.get('min_roe'),
            'max_roe': filters.get('max_roe'),
            'min_roa': filters.get('min_roa')
        }
        if any(v is not None for v in fundamental_filters.values()):
            symbols = self.filter_by_fundamental(symbols, **fundamental_filters)

        if not symbols:
            logger.warning('基本面筛选后无股票')
            return []

        # 4. 按行业筛选
        industries = filters.get('industries')
        sectors = filters.get('sectors')
        if industries or sectors:
            symbols = self.filter_by_industry(symbols, industries, sectors)

        if not symbols:
            logger.warning('行业筛选后无股票')
            return []

        # 5. 按流动性筛选
        min_liquidity = filters.get('min_liquidity')
        if min_liquidity is not None:
            symbols = self.filter_by_liquidity(symbols, min_liquidity)

        logger.info(f'筛选完成，最终股票池: {len(symbols)} 只')
        return symbols

    def get_universe_stats(self, symbols: List[str]) -> Dict[str, Any]:
        """
        获取股票池统计信息

        Args:
            symbols: 股票代码列表

        Returns:
            统计信息字典
        """
        if not symbols:
            return {}

        try:
            with self.db.get_session() as session:
                # 获取元数据统计
                metadata = session.query(StockMetadata).filter(
                    StockMetadata.symbol.in_(symbols)
                ).all()

                # 获取基本面统计
                fundamental = session.query(StockFundamentalDaily).filter(
                    StockFundamentalDaily.symbol.in_(symbols)
                ).all()

                # 统计
                stats = {
                    'total_count': len(symbols),
                    'sectors': {},
                    'industries': {},
                    'market_cap': {
                        'total': 0,
                        'avg': 0,
                        'median': 0
                    },
                    'fundamental': {
                        'avg_pe': 0,
                        'avg_pb': 0,
                        'avg_roe': 0
                    }
                }

                # 板块统计
                for stock in metadata:
                    sector = stock.sector or '未知'
                    stats['sectors'][sector] = stats['sectors'].get(sector, 0) + 1

                # 行业统计
                for stock in metadata:
                    industry = stock.industry or '未知'
                    stats['industries'][industry] = stats['industries'].get(industry, 0) + 1

                # 市值统计
                mvs = [f.total_mv for f in fundamental if f.total_mv]
                if mvs:
                    stats['market_cap']['total'] = sum(mvs)
                    stats['market_cap']['avg'] = sum(mvs) / len(mvs)
                    stats['market_cap']['median'] = sorted(mvs)[len(mvs) // 2]

                # 基本面统计
                pes = [f.pe_ratio for f in fundamental if f.pe_ratio]
                pbs = [f.pb_ratio for f in fundamental if f.pb_ratio]
                roes = [f.roe for f in fundamental if f.roe]

                if pes:
                    stats['fundamental']['avg_pe'] = sum(pes) / len(pes)
                if pbs:
                    stats['fundamental']['avg_pb'] = sum(pbs) / len(pbs)
                if roes:
                    stats['fundamental']['avg_roe'] = sum(roes) / len(roes)

                return stats

        except Exception as e:
            logger.error(f'获取统计信息失败: {e}')
            return {}


if __name__ == '__main__':
    """测试代码"""
    from loguru import logger

    logger.info('股票池管理器测试')

    universe = StockUniverse()

    # 测试1: 获取所有可交易股票
    logger.info('\n=== 测试1: 获取所有可交易股票 ===')
    all_stocks = universe.get_all_stocks()
    logger.info(f'可交易股票: {len(all_stocks)} 只')
    logger.info(f'前10只: {all_stocks[:10]}')

    # 测试2: 市值筛选
    logger.info('\n=== 测试2: 大盘股筛选（市值>100亿）===')
    large_caps = universe.get_stock_pool(filters={
        'min_market_cap': 100
    })
    logger.info(f'大盘股: {len(large_caps)} 只')
    logger.info(f'前10只: {large_caps[:10]}')

    # 测试3: 质量筛选
    logger.info('\n=== 测试3: 质量筛选 ===')
    quality_stocks = universe.get_stock_pool(filters={
        'min_market_cap': 50,
        'max_pe': 30,
        'min_roe': 0.10
    })
    logger.info(f'质量股票: {len(quality_stocks)} 只')

    # 测试4: 统计信息
    if large_caps:
        logger.info('\n=== 测试4: 统计信息 ===')
        stats = universe.get_universe_stats(large_caps[:100])  # 只统计前100只
        logger.info(f'统计: {stats}')
