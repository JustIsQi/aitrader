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
from aitrader.infrastructure.config.logging import logger
from sqlalchemy.exc import OperationalError, DBAPIError

from aitrader.infrastructure.db.db_manager import get_db
from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader

# Process-local caches for repeated strategy construction in the same process.
_GET_ALL_STOCKS_CACHE: dict[tuple, List[str]] = {}
_MARKET_CAP_CACHE: dict[tuple, List[str]] = {}
_FUNDAMENTAL_SNAPSHOT_CACHE: dict[tuple, pd.DataFrame] = {}
_METADATA_SNAPSHOT_CACHE: dict[tuple, pd.DataFrame] = {}

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
        self.wind_reader = MySQLAshareReader()
        logger.debug('股票池管理器初始化完成')

    def _normalize_as_of_date(self, value: object | None) -> str:
        if value is None:
            return datetime.now().strftime('%Y%m%d')

        try:
            ts = pd.to_datetime(value)
        except Exception as exc:
            raise ValueError(f'无效的 as_of_date: {value!r}') from exc

        if pd.isna(ts):
            raise ValueError(f'无效的 as_of_date: {value!r}')
        return ts.strftime('%Y%m%d')

    def _format_log_date(self, value: str) -> str:
        value = str(value).replace('-', '')
        if len(value) == 8:
            return f'{value[:4]}-{value[4:6]}-{value[6:]}'
        return value

    def get_latest_fundamental_snapshot(
        self,
        symbols: List[str],
        as_of_date: object | None = None,
    ) -> pd.DataFrame:
        """直接从 Wind 读取最新衍生指标快照，市值单位统一为亿元。"""
        if not symbols:
            return pd.DataFrame()

        as_of_date_norm = self._normalize_as_of_date(as_of_date)
        unique_symbols = tuple(sorted({symbol for symbol in symbols if symbol}))
        cache_key = (unique_symbols, as_of_date_norm)
        cached = _FUNDAMENTAL_SNAPSHOT_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()

        df = self.wind_reader.read_latest_derivative_indicators(
            symbols=list(unique_symbols),
            end_date=as_of_date_norm,
        )
        _FUNDAMENTAL_SNAPSHOT_CACHE[cache_key] = df
        return df.copy()

    def get_stock_metadata_snapshot(
        self,
        symbols: Optional[List[str]] = None,
        as_of_date: object | None = None,
    ) -> pd.DataFrame:
        """直接从 Wind 读取股票元数据快照。"""
        as_of_date_norm = self._normalize_as_of_date(as_of_date)
        unique_symbols = tuple(sorted({symbol for symbol in (symbols or []) if symbol}))
        cache_key = (unique_symbols, as_of_date_norm)
        cached = _METADATA_SNAPSHOT_CACHE.get(cache_key)
        if cached is not None:
            return cached.copy()

        df = self.wind_reader.read_stock_metadata(
            symbols=list(unique_symbols) if unique_symbols else None,
            as_of_date=as_of_date_norm,
        )
        _METADATA_SNAPSHOT_CACHE[cache_key] = df
        return df.copy()

    def get_all_stocks(self, exclude_st=True, exclude_suspend=True,
                      exclude_new_ipo_days=None, min_data_days=180,
                      exclude_restricted_stocks=True, as_of_date: object | None = None) -> List[str]:
        """
        从 Wind MySQL 数据库获取所有可交易股票。

        直接查询 Wind 原始表，不依赖本地 ORM 模型：
          - ASHAREEODPRICES            : 获取有近期数据的股票
          - ASHAREST                   : 过滤 ST 股票（失败则跳过）
          - ASHARETRADINGSUSPENSION    : 过滤停牌股票（失败则跳过）
          - ASHAREDESCRIPTION          : 过滤新股（失败则跳过）
        """
        as_of_date_norm = self._normalize_as_of_date(as_of_date)
        as_of_dt = datetime.strptime(as_of_date_norm, '%Y%m%d')
        cutoff_date = (as_of_dt - timedelta(days=min_data_days)).strftime('%Y%m%d')
        today = as_of_date_norm
        recent_date = (as_of_dt - timedelta(days=30)).strftime('%Y%m%d')
        cache_key = (
            exclude_st,
            exclude_suspend,
            exclude_new_ipo_days,
            min_data_days,
            exclude_restricted_stocks,
            cutoff_date,
            recent_date,
            today,
        )
        cached = _GET_ALL_STOCKS_CACHE.get(cache_key)
        if cached is not None:
            logger.debug('get_all_stocks 缓存命中')
            return list(cached)

        from aitrader.infrastructure.market_data.mysql_reader import MySQLAshareReader

        reader = MySQLAshareReader()
        conn = None
        try:
            conn = reader.connect()
            with conn.cursor() as cursor:

                # 1. 获取有足够历史数据的股票
                # 要求: (a) 在 cutoff_date 之前就已有数据（保证历史指标可算）
                #        (b) 近30天仍在交易（排除已退市股票）
                cursor.execute(
                    "SELECT S_INFO_WINDCODE FROM ASHAREEODPRICES "
                    "GROUP BY S_INFO_WINDCODE "
                    "HAVING MIN(TRADE_DT) <= %s AND MAX(TRADE_DT) >= %s "
                    "ORDER BY S_INFO_WINDCODE",
                    [cutoff_date, recent_date],
                )
                symbols = {row['S_INFO_WINDCODE'] for row in cursor.fetchall()}
                logger.info(
                    f'Wind ASHAREEODPRICES 股票总数(有足够历史, 截止 {self._format_log_date(as_of_date_norm)}): '
                    f'{len(symbols)}'
                )

                # 2. 过滤 ST 股票
                if exclude_st:
                    try:
                        cursor.execute(
                            "SELECT DISTINCT S_INFO_WINDCODE FROM ASHAREST "
                            "WHERE ENTRY_DT <= %s AND (REMOVE_DT IS NULL OR REMOVE_DT > %s)",
                            [today, today],
                        )
                        st_set = {row['S_INFO_WINDCODE'] for row in cursor.fetchall()}
                        before = len(symbols)
                        symbols -= st_set
                        logger.info(f'ST 过滤: {before} -> {len(symbols)} (排除 {len(st_set)} 只)')
                    except Exception as e:
                        logger.warning(f'ST 过滤失败，跳过: {e}')

                # 3. 过滤停牌股票
                if exclude_suspend:
                    try:
                        cursor.execute(
                            "SELECT DISTINCT S_INFO_WINDCODE FROM ASHARETRADINGSUSPENSION "
                            "WHERE S_DQ_SUSPENDDATE <= %s "
                            "AND (S_DQ_RESUMPDATE IS NULL OR S_DQ_RESUMPDATE > %s)",
                            [today, today],
                        )
                        suspended = {row['S_INFO_WINDCODE'] for row in cursor.fetchall()}
                        before = len(symbols)
                        symbols -= suspended
                        logger.info(f'停牌过滤: {before} -> {len(symbols)} (排除 {len(suspended)} 只)')
                    except Exception as e:
                        logger.warning(f'停牌过滤失败，跳过: {e}')

                # 4. 过滤新股（上市不足 N 天）
                if exclude_new_ipo_days:
                    try:
                        ipo_cutoff = (as_of_dt - timedelta(days=exclude_new_ipo_days)).strftime('%Y%m%d')
                        cursor.execute(
                            "SELECT DISTINCT S_INFO_WINDCODE FROM ASHAREDESCRIPTION "
                            "WHERE S_INFO_LISTDATE > %s",
                            [ipo_cutoff],
                        )
                        new_ipos = {row['S_INFO_WINDCODE'] for row in cursor.fetchall()}
                        before = len(symbols)
                        symbols -= new_ipos
                        logger.info(f'新股过滤 (上市<{exclude_new_ipo_days}天): '
                                    f'{before} -> {len(symbols)} (排除 {len(new_ipos)} 只)')
                    except Exception as e:
                        logger.warning(f'新股过滤失败，跳过: {e}')

                # 5. 过滤限制交易板块（科创板 688、创业板 300、北交所 .BJ）
                if exclude_restricted_stocks:
                    before = len(symbols)
                    symbols = {
                        s for s in symbols
                        if not (s.startswith('688') or s.startswith('300') or '.BJ' in s)
                    }
                    logger.info(f'限制板块过滤: {before} -> {len(symbols)}')

            result = sorted(symbols)
            logger.info(f'最终股票池: {len(result)} 只')
            _GET_ALL_STOCKS_CACHE[cache_key] = result
            return list(result)
        finally:
            if conn:
                conn.close()

    def filter_by_market_cap(self, symbols: List[str],
                            min_mv: Optional[float] = None,
                            max_mv: Optional[float] = None,
                            as_of_date: object | None = None) -> List[str]:
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

        as_of_date_norm = self._normalize_as_of_date(as_of_date)
        cache_key = (tuple(sorted(symbols)), min_mv, max_mv, as_of_date_norm)
        cached = _MARKET_CAP_CACHE.get(cache_key)
        if cached is not None:
            logger.debug('filter_by_market_cap 缓存命中')
            return list(cached)

        try:
            snapshot = self.get_latest_fundamental_snapshot(symbols, as_of_date=as_of_date_norm)
            if snapshot.empty:
                logger.warning('市值筛选失败: Wind 衍生指标快照为空')
                return []

            mask = pd.Series(True, index=snapshot.index)
            if min_mv is not None:
                mask &= snapshot["total_mv"] >= float(min_mv)
            if max_mv is not None:
                mask &= snapshot["total_mv"] <= float(max_mv)

            filtered = snapshot.loc[mask, "symbol"].astype(str).tolist()
            logger.debug(f'市值筛选: {len(symbols)} -> {len(filtered)}')
            _MARKET_CAP_CACHE[cache_key] = filtered
            return list(filtered)

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
                             min_roa: Optional[float] = None,
                             as_of_date: object | None = None) -> List[str]:
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
            snapshot = self.get_latest_fundamental_snapshot(symbols, as_of_date=as_of_date)
            if snapshot.empty:
                logger.warning('基本面筛选失败: Wind 衍生指标快照为空')
                return []

            mask = pd.Series(True, index=snapshot.index)
            if min_pe is not None:
                mask &= snapshot["pe_ratio"] >= float(min_pe)
            if max_pe is not None:
                mask &= snapshot["pe_ratio"] <= float(max_pe)
            if min_pb is not None:
                mask &= snapshot["pb_ratio"] >= float(min_pb)
            if max_pb is not None:
                mask &= snapshot["pb_ratio"] <= float(max_pb)

            if any(value is not None for value in (min_roe, max_roe, min_roa)):
                logger.warning('Wind 直读快照当前不包含 ROE/ROA，已忽略对应过滤条件')

            filtered = snapshot.loc[mask, "symbol"].astype(str).tolist()
            logger.debug(f'基本面筛选: {len(symbols)} -> {len(filtered)}')
            return filtered

        except Exception as e:
            logger.error(f'基本面筛选失败: {e}')
            return []

    def filter_by_industry(self, symbols: List[str],
                          industries: Optional[List[str]] = None,
                          sectors: Optional[List[str]] = None,
                          as_of_date: object | None = None) -> List[str]:
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
            metadata = self.get_stock_metadata_snapshot(symbols, as_of_date=as_of_date)
            if metadata.empty:
                logger.warning('行业筛选失败: Wind 元数据快照为空')
                return []

            mask = pd.Series(True, index=metadata.index)
            if industries:
                industry_mask = pd.Series(False, index=metadata.index)
                for column in ("industry", "sw_level2", "sw_ind_name"):
                    if column in metadata.columns:
                        industry_mask |= metadata[column].isin(industries)
                mask &= industry_mask

            if sectors:
                sector_mask = pd.Series(False, index=metadata.index)
                for column in ("sector", "list_board_name"):
                    if column in metadata.columns:
                        sector_mask |= metadata[column].isin(sectors)
                mask &= sector_mask

            filtered = metadata.loc[mask, "symbol"].astype(str).tolist()
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
            exclude_new_ipo_days=filters.get('exclude_new_ipo'),
            as_of_date=date,
        )

        if not symbols:
            logger.warning('基础股票列表为空')
            return []

        # 2. 按市值筛选
        min_mv = filters.get('min_market_cap')
        max_mv = filters.get('max_market_cap')
        if min_mv is not None or max_mv is not None:
            symbols = self.filter_by_market_cap(symbols, min_mv, max_mv, as_of_date=date)

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
            symbols = self.filter_by_fundamental(symbols, as_of_date=date, **fundamental_filters)

        if not symbols:
            logger.warning('基本面筛选后无股票')
            return []

        # 4. 按行业筛选
        industries = filters.get('industries')
        sectors = filters.get('sectors')
        if industries or sectors:
            symbols = self.filter_by_industry(symbols, industries, sectors, as_of_date=date)

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
            metadata = self.get_stock_metadata_snapshot(symbols)
            fundamental = self.get_latest_fundamental_snapshot(symbols)

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
            for _, stock in metadata.iterrows():
                sector = stock.get('sector') or '未知'
                stats['sectors'][sector] = stats['sectors'].get(sector, 0) + 1

            # 行业统计
            for _, stock in metadata.iterrows():
                industry = stock.get('industry') or stock.get('sw_ind_name') or '未知'
                stats['industries'][industry] = stats['industries'].get(industry, 0) + 1

            # 市值统计
            mvs = pd.to_numeric(fundamental.get('total_mv'), errors='coerce').dropna().tolist() if not fundamental.empty else []
            if mvs:
                stats['market_cap']['total'] = sum(mvs)
                stats['market_cap']['avg'] = sum(mvs) / len(mvs)
                stats['market_cap']['median'] = sorted(mvs)[len(mvs) // 2]

            # 基本面统计
            pes = pd.to_numeric(fundamental.get('pe_ratio'), errors='coerce').dropna().tolist() if not fundamental.empty else []
            pbs = pd.to_numeric(fundamental.get('pb_ratio'), errors='coerce').dropna().tolist() if not fundamental.empty else []

            if pes:
                stats['fundamental']['avg_pe'] = sum(pes) / len(pes)
            if pbs:
                stats['fundamental']['avg_pb'] = sum(pbs) / len(pbs)

            return stats

        except Exception as e:
            logger.error(f'获取统计信息失败: {e}')
            return {}


if __name__ == '__main__':
    """测试代码"""
    from aitrader.infrastructure.config.logging import logger

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
