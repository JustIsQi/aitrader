"""
历史数据下载脚本
一次性下载过去N年的ETF和A股历史数据到PostgreSQL数据库

功能:
    1. 下载ETF历史数据 -> 存入 etf_history 表
    2. 下载A股历史数据 -> 存入 stock_history 表
    3. 下载基本面数据(仅PE/PB) -> 存入 stock_fundamental_daily 表
    4. 自动初始化代码表 -> etf_codes 和 stock_codes

用法:
    python scripts/download_historical_data.py                        # 下载默认5年历史数据(全部类型)
    python scripts/download_historical_data.py --years 3             # 下载近3年数据
    python scripts/download_historical_data.py -t etf stock          # 只下载ETF和股票历史数据
    python scripts/download_historical_data.py -t fundamental        # 只下载基本面快照(仅PE/PB)
    python scripts/download_historical_data.py --force               # 强制重新下载(覆盖已有数据)
    
注意:
    - 基本面数据仅下载PE(市盈率)和PB(市净率)，其他字段设为NULL
    - 支持断点续传，重新运行会自动跳过已有数据
"""     
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import List, Optional, NamedTuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from loguru import logger
from tqdm import tqdm
from database.pg_manager import get_db
from datafeed.downloaders.etf_downloader import EtfDownloader
from datafeed.downloaders.stock_downloader import StockDownloader
from datafeed.downloaders.fundamental_downloader import FundamentalDownloader
from datafeed.downloaders.rate_limiter import RateLimiter
from scripts.init_codes import CodeInitializer


class DownloadDecision(NamedTuple):
    """下载决策结果"""
    should_download: bool
    actual_start_date: Optional[str]
    reason: str


@dataclass
class DownloadStats:
    """下载统计信息"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    etf_stats: dict = field(default_factory=lambda: {
        'total': 0, 'downloaded': 0, 'skipped': 0,
        'failed': 0, 'records_added': 0, 'duration': 0
    })
    stock_stats: dict = field(default_factory=lambda: {
        'total': 0, 'downloaded': 0, 'skipped': 0,
        'failed': 0, 'records_added': 0, 'duration': 0
    })
    fundamental_stats: dict = field(default_factory=lambda: {
        'total': 0, 'success': 0, 'failed': 0, 'duration': 0
    })


class HistoricalDataDownloader:
    """历史数据下载器 - 负责下载过去N年的数据"""

    def __init__(self, max_workers: int = 5):
        self.db = get_db()
        self.etf_downloader = EtfDownloader()
        self.stock_downloader = StockDownloader()
        self.fundamental_downloader = FundamentalDownloader()
        self.stats = DownloadStats()
        self.failed_symbols = {'etf': [], 'stock': []}
        self.max_workers = max_workers  # 并发线程数
        self.rate_limiter = RateLimiter(max_requests_per_second=5)  # API限流器

    def check_and_init_codes(self, force_refresh: bool = False) -> bool:
        """
        检查并自动初始化代码表

        Args:
            force_refresh: 是否强制刷新代码表（清空并重新下载）

        Returns:
            bool: 是否执行了初始化
        """
        logger.info('[阶段0] 检查代码表状态...')

        code_count = self.db.get_code_count()
        etf_empty = code_count.get('etf', 0) == 0
        stock_empty = code_count.get('stock', 0) == 0

        logger.info(f'  etf_codes:   {code_count.get("etf", 0)} 条')
        logger.info(f'  stock_codes: {code_count.get("stock", 0)} 条')

        if force_refresh or etf_empty or stock_empty:
            if force_refresh:
                logger.info('')
                logger.info('🔄 强制刷新代码表...')
                logger.info('')
            else:
                logger.warning('')
                logger.warning('⚠️  代码表为空,开始自动初始化...')
                logger.warning('')

            initializer = CodeInitializer()
            initializer.init_all_codes(force=force_refresh)

            logger.info('')
            logger.info('✓ 代码表初始化完成')
            logger.info('')
            return True

        logger.info('✓ 代码表状态正常')
        logger.info('')
        return False

    def calculate_date_range(self, years: int) -> tuple[str, str]:
        """
        计算下载日期范围

        Args:
            years: 历史年数

        Returns:
            (start_date, end_date) in YYYYMMDD format
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)

        # 对齐到1月1日，使数据更整洁
        start_date = start_date.replace(month=1, day=1)

        start_date_str = start_date.strftime('%Y%m%d')
        end_date_str = end_date.strftime('%Y%m%d')

        logger.info(f'目标日期范围: {start_date.strftime("%Y-%m-%d")} 至 {end_date.strftime("%Y-%m-%d")} ({years}年)')

        return start_date_str, end_date_str

    def _should_download(self, symbol: str, latest_date: Optional[datetime],
                        target_start: str, force: bool) -> DownloadDecision:
        """
        判断是否需要下载数据

        Args:
            symbol: 股票/ETF代码
            latest_date: 数据库中最新的日期 (可能是 datetime.date 或 datetime.datetime)
            target_start: 目标起始日期 (YYYYMMDD)
            force: 是否强制重新下载

        Returns:
            DownloadDecision
        """
        target_start_dt = datetime.strptime(target_start, '%Y%m%d')

        if force:
            return DownloadDecision(
                should_download=True,
                actual_start_date=target_start,
                reason="强制重新下载"
            )

        if latest_date is None:
            return DownloadDecision(
                should_download=True,
                actual_start_date=target_start,
                reason="首次下载"
            )

        # 确保 latest_date 是 datetime.datetime 类型
        if isinstance(latest_date, datetime):
            latest_date_dt = latest_date
        else:
            # 如果是 datetime.date，转换为 datetime.datetime
            latest_date_dt = datetime.combine(latest_date, datetime.min.time())

        if latest_date_dt < target_start_dt:
            return DownloadDecision(
                should_download=True,
                actual_start_date=target_start,
                reason=f"数据不足 (最新: {latest_date_dt.strftime('%Y-%m-%d')})"
            )

        # 检查是否需要增量更新
        today = datetime.now()
        if latest_date_dt < today:
            next_day = latest_date_dt + timedelta(days=1)
            return DownloadDecision(
                should_download=True,
                actual_start_date=next_day.strftime('%Y%m%d'),
                reason=f"增量更新 (从 {latest_date_dt.strftime('%Y-%m-%d')})"
            )

        return DownloadDecision(
            should_download=False,
            actual_start_date=None,
            reason="数据已是最新"
        )

    def _download_single_batch(self, symbols_batch: List[str], start_date: str, end_date: str,
                              is_etf_batch: bool = False) -> dict:
        """
        下载一批股票/ETF数据（带限流和错误处理）

        Args:
            symbols_batch: 一批股票/ETF代码
            start_date: 开始日期
            end_date: 结束日期
            is_etf_batch: 是否为ETF批次（默认False，表示股票批次）

        Returns:
            dict: 批次统计信息
        """
        batch_data = []
        failed_symbols = []

        for symbol in symbols_batch:
            try:
                # 使用限流器控制API请求速率
                self.rate_limiter.acquire()

                code = symbol.split('.')[0]

                # 根据批次类型选择下载器
                if is_etf_batch:
                    df = self.etf_downloader.fetch_etf_history(code, start_date, end_date)
                else:
                    df = self.stock_downloader.fetch_stock_history(code, start_date, end_date)

                if df is not None and not df.empty:
                    # 转换列名
                    df.rename(columns={
                        '日期': 'date', '开盘': 'open', '收盘': 'close',
                        '最高': 'high', '最低': 'low', '成交量': 'volume',
                        '成交额': 'amount', '振幅': 'amplitude', '涨跌幅': 'change_pct',
                        '涨跌额': 'change_amount', '换手率': 'turnover_rate'
                    }, inplace=True)
                    df['symbol'] = symbol
                    batch_data.append(df)
                else:
                    failed_symbols.append(symbol)

            except Exception as e:
                logger.debug(f'{symbol} 下载失败: {e}')
                failed_symbols.append(symbol)

        # 批量插入数据库
        records_added = 0
        if batch_data:
            try:
                combined_df = pd.concat(batch_data, ignore_index=True)

                # 根据批次类型选择批量插入方法
                if is_etf_batch:
                    records_added = self.db.batch_append_etf_history(combined_df)
                else:
                    records_added = self.db.batch_append_stock_history(combined_df)

            except Exception as e:
                logger.error(f'批量插入失败: {e}')
                failed_symbols.extend([s for df in batch_data for s in df['symbol'].unique()])

        return {
            'total': len(symbols_batch),
            'success': len(batch_data),
            'failed': len(failed_symbols),
            'failed_symbols': failed_symbols,
            'records_added': records_added
        }

    def download_etf_history_optimized(self, start_date: str, end_date: str,
                                       force: bool = False) -> dict:
        """
        优化的ETF历史数据下载（智能批量模式）

        三阶段策略:
        1. 批量检查完整性 - 单次查询所有ETF
        2. 分批处理 - 将需要下载的ETF分成批次
        3. 并发下载 + 批量插入 - 使用线程池并发处理批次

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制重新下载

        Returns:
            dict: 统计信息
        """
        logger.info('='*60)
        logger.info('[阶段1] 下载ETF历史数据 (智能批量模式)')
        logger.info('='*60)
        logger.info('')

        start = time.time()
        symbols = self.db.get_etf_codes()

        if not symbols:
            logger.warning('没有找到 ETF 代码,跳过 ETF 下载')
            return {'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0, 'records_added': 0, 'duration': 0}

        # Phase 1: 批量检查完整性
        logger.info(f'[Phase 1] 检查 {len(symbols)} 个ETF的数据完整性...')
        completeness = self.db.get_etf_completeness_info(symbols, start_date)

        needs_download = [s for s, info in completeness.items()
                         if info['needs_download'] or force]
        already_complete = len(symbols) - len(needs_download)

        logger.info(f'  已完整: {already_complete} 个 (跳过)')
        logger.info(f'  需下载: {len(needs_download)} 个')
        logger.info('')

        if not needs_download:
            return {
                'total': len(symbols),
                'downloaded': 0,
                'skipped': len(symbols),
                'failed': 0,
                'records_added': 0,
                'duration': 0
            }

        # Phase 2: 分批处理
        BATCH_SIZE = 50
        symbol_batches = [needs_download[i:i+BATCH_SIZE]
                         for i in range(0, len(needs_download), BATCH_SIZE)]

        logger.info(f'[Phase 2] 处理 {len(symbol_batches)} 个批次 (每批{BATCH_SIZE}个)...')
        logger.info(f'并发数: {self.max_workers} 个线程')
        logger.info('')

        stats = {
            'total': len(symbols),
            'downloaded': 0,
            'skipped': already_complete,
            'failed': 0,
            'records_added': 0
        }

        # Phase 3: 并发下载批次
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_single_batch, batch, start_date, end_date, is_etf_batch=True): batch
                for batch in symbol_batches
            }

            with tqdm(total=len(symbol_batches), desc="ETF批量下载", unit="批") as pbar:
                for future in as_completed(futures):
                    try:
                        batch_stats = future.result()
                        stats['downloaded'] += batch_stats['success']
                        stats['failed'] += batch_stats['failed']
                        stats['records_added'] += batch_stats['records_added']
                        self.failed_symbols['etf'].extend(batch_stats['failed_symbols'])

                        pbar.set_postfix({
                            '下载': stats['downloaded'],
                            '失败': stats['failed']
                        })

                    except Exception as e:
                        logger.error(f'批次处理失败: {e}')
                        stats['failed'] += len(futures[future])

                    pbar.update(1)

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ ETF 下载完成!')
        logger.info(f'  总数: {stats["total"]}')
        logger.info(f'  已下载: {stats["downloaded"]}')
        logger.info(f'  跳过: {stats["skipped"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  新增记录: {stats["records_added"]:,}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info(f'  平均速度: {len(symbols)/duration:.2f} 个/秒')
        logger.info('')

        return stats

    def download_stock_history_optimized(self, start_date: str, end_date: str,
                                        force: bool = False) -> dict:
        """
        优化的A股历史数据下载（智能批量模式）

        三阶段策略:
        1. 批量检查完整性 - 单次查询所有股票
        2. 分批处理 - 将需要下载的股票分成批次
        3. 并发下载 + 批量插入 - 使用线程池并发处理批次

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制重新下载

        Returns:
            dict: 统计信息
        """
        logger.info('='*60)
        logger.info('[阶段2] 下载A股历史数据 (智能批量模式)')
        logger.info('='*60)
        logger.info('')

        start = time.time()
        symbols = self.db.get_stock_codes()

        if not symbols:
            logger.warning('没有找到股票代码,跳过股票下载')
            return {'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0, 'records_added': 0, 'duration': 0}

        # Phase 1: 批量检查完整性
        logger.info(f'[Phase 1] 检查 {len(symbols)} 只股票的数据完整性...')
        completeness = self.db.get_stock_completeness_info(symbols, start_date)

        needs_download = [s for s, info in completeness.items()
                         if info['needs_download'] or force]
        already_complete = len(symbols) - len(needs_download)

        logger.info(f'  已完整: {already_complete} 只 (跳过)')
        logger.info(f'  需下载: {len(needs_download)} 只')
        logger.info('')

        if not needs_download:
            return {
                'total': len(symbols),
                'downloaded': 0,
                'skipped': len(symbols),
                'failed': 0,
                'records_added': 0,
                'duration': 0
            }

        # Phase 2: 分批处理
        BATCH_SIZE = 50
        symbol_batches = [needs_download[i:i+BATCH_SIZE]
                         for i in range(0, len(needs_download), BATCH_SIZE)]

        logger.info(f'[Phase 2] 处理 {len(symbol_batches)} 个批次 (每批{BATCH_SIZE}只)...')
        logger.info(f'并发数: {self.max_workers} 个线程')
        logger.info('')

        stats = {
            'total': len(symbols),
            'downloaded': 0,
            'skipped': already_complete,
            'failed': 0,
            'records_added': 0
        }

        # Phase 3: 并发下载批次
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._download_single_batch, batch, start_date, end_date): batch
                for batch in symbol_batches
            }

            with tqdm(total=len(symbol_batches), desc="股票批量下载", unit="批") as pbar:
                for future in as_completed(futures):
                    try:
                        batch_stats = future.result()
                        stats['downloaded'] += batch_stats['success']
                        stats['failed'] += batch_stats['failed']
                        stats['records_added'] += batch_stats['records_added']
                        self.failed_symbols['stock'].extend(batch_stats['failed_symbols'])

                        pbar.set_postfix({
                            '下载': stats['downloaded'],
                            '失败': stats['failed']
                        })

                    except Exception as e:
                        logger.error(f'批次处理失败: {e}')
                        stats['failed'] += len(futures[future])

                    pbar.update(1)

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ 股票下载完成!')
        logger.info(f'  总数: {stats["total"]}')
        logger.info(f'  已下载: {stats["downloaded"]}')
        logger.info(f'  跳过: {stats["skipped"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  新增记录: {stats["records_added"]:,}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info(f'  平均速度: {len(symbols)/duration:.2f} 只/秒')
        logger.info('')

        return stats

    def _download_single_etf(self, symbol: str, start_date: str, end_date: str,
                             force: bool) -> dict:
        """
        下载单个ETF数据（用于并发调用）

        Args:
            symbol: ETF代码
            start_date: 目标起始日期
            end_date: 结束日期
            force: 是否强制重新下载

        Returns:
            dict: {'symbol': str, 'success': bool, 'skipped': bool, 'records': int, 'error': str}
        """
        try:
            # 检查最新日期
            latest_date = self.db.get_latest_date(symbol)

            # 决策是否需要下载
            decision = self._should_download(symbol, latest_date, start_date, force)

            if not decision.should_download:
                return {'symbol': symbol, 'success': False, 'skipped': True,
                       'records': 0, 'error': '', 'reason': decision.reason}

            # 下载数据
            code = symbol.split('.')[0]
            df = self.etf_downloader.fetch_etf_history(code, decision.actual_start_date, end_date)

            if df is None or df.empty:
                return {'symbol': symbol, 'success': False, 'skipped': True,
                       'records': 0, 'error': '无数据', 'reason': '无数据'}

            # 转换列名
            df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '成交额': 'amount', '振幅': 'amplitude', '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount', '换手率': 'turnover_rate'
            }, inplace=True)

            # 存入数据库
            success = self.db.append_etf_history(df, symbol)

            if success:
                return {'symbol': symbol, 'success': True, 'skipped': False,
                       'records': len(df), 'error': '', 'reason': decision.reason}
            else:
                return {'symbol': symbol, 'success': False, 'skipped': False,
                       'records': 0, 'error': '数据库插入失败', 'reason': decision.reason}

        except Exception as e:
            return {'symbol': symbol, 'success': False, 'skipped': False,
                   'records': 0, 'error': str(e), 'reason': '异常'}

    def download_etf_history(self, start_date: str, end_date: str,
                            force: bool = False) -> dict:
        """
        并发下载ETF历史数据

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制重新下载

        Returns:
            dict: 统计信息
        """
        logger.info('='*60)
        logger.info('[阶段1] 下载ETF历史数据 (并发模式)')
        logger.info('='*60)
        logger.info('')

        start = time.time()
        symbols = self.db.get_etf_codes()

        if not symbols:
            logger.warning('没有找到 ETF 代码,跳过 ETF 下载')
            return {'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0, 'records_added': 0, 'duration': 0}

        stats = {
            'total': len(symbols),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'records_added': 0
        }

        logger.info(f'待检查: {len(symbols)} 个 ETF')
        logger.info(f'并发数: {self.max_workers} 个线程')
        logger.info('')

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self._download_single_etf, symbol, start_date, end_date, force): symbol
                for symbol in symbols
            }

            # 使用tqdm显示进度
            with tqdm(total=len(symbols), desc="ETF下载", unit="个") as pbar:
                for future in as_completed(futures):
                    symbol = futures[future]
                    try:
                        result = future.result()

                        if result['skipped']:
                            stats['skipped'] += 1
                        elif result['success']:
                            stats['downloaded'] += 1
                            stats['records_added'] += result['records']
                        else:
                            stats['failed'] += 1
                            self.failed_symbols['etf'].append(symbol)
                            if result.get('error'):
                                logger.debug(f'{symbol} 失败: {result["error"]}')

                        pbar.set_postfix({
                            '下载': stats['downloaded'],
                            '跳过': stats['skipped'],
                            '失败': stats['failed']
                        })

                    except Exception as e:
                        logger.error(f'处理 {symbol} 时发生异常: {e}')
                        stats['failed'] += 1
                        self.failed_symbols['etf'].append(symbol)

                    pbar.update(1)

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ ETF 下载完成!')
        logger.info(f'  总数: {stats["total"]}')
        logger.info(f'  已下载: {stats["downloaded"]}')
        logger.info(f'  跳过: {stats["skipped"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  新增记录: {stats["records_added"]:,}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info(f'  平均速度: {len(symbols)/duration:.2f} 个/秒')
        logger.info('')

        return stats

    def _download_single_stock(self, symbol: str, start_date: str, end_date: str,
                              force: bool) -> dict:
        """
        下载单个股票数据（用于并发调用）

        Args:
            symbol: 股票代码
            start_date: 目标起始日期
            end_date: 结束日期
            force: 是否强制重新下载

        Returns:
            dict: {'symbol': str, 'success': bool, 'skipped': bool, 'records': int, 'error': str}
        """
        try:
            # 检查最新日期
            latest_date = self.db.get_stock_latest_date(symbol)

            # 决策是否需要下载
            decision = self._should_download(symbol, latest_date, start_date, force)

            if not decision.should_download:
                return {'symbol': symbol, 'success': False, 'skipped': True,
                       'records': 0, 'error': '', 'reason': decision.reason}

            # 下载数据
            code = symbol.split('.')[0]
            df = self.stock_downloader.fetch_stock_history(code, decision.actual_start_date, end_date)

            if df is None or df.empty:
                return {'symbol': symbol, 'success': False, 'skipped': True,
                       'records': 0, 'error': '无数据', 'reason': '无数据'}

            # 转换列名
            df.rename(columns={
                '日期': 'date', '开盘': 'open', '收盘': 'close',
                '最高': 'high', '最低': 'low', '成交量': 'volume',
                '成交额': 'amount', '振幅': 'amplitude', '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount', '换手率': 'turnover_rate'
            }, inplace=True)

            # 存入数据库
            success = self.db.append_stock_history(df, symbol)

            if success:
                return {'symbol': symbol, 'success': True, 'skipped': False,
                       'records': len(df), 'error': '', 'reason': decision.reason}
            else:
                return {'symbol': symbol, 'success': False, 'skipped': False,
                       'records': 0, 'error': '数据库插入失败', 'reason': decision.reason}

        except Exception as e:
            return {'symbol': symbol, 'success': False, 'skipped': False,
                   'records': 0, 'error': str(e), 'reason': '异常'}

    def download_stock_history(self, start_date: str, end_date: str,
                              force: bool = False) -> dict:
        """
        并发下载A股历史数据

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            force: 是否强制重新下载

        Returns:
            dict: 统计信息
        """
        logger.info('='*60)
        logger.info('[阶段2] 下载A股历史数据 (并发模式)')
        logger.info('='*60)
        logger.info('')

        start = time.time()
        symbols = self.db.get_stock_codes()

        if not symbols:
            logger.warning('没有找到股票代码,跳过股票下载')
            return {'total': 0, 'downloaded': 0, 'skipped': 0, 'failed': 0, 'records_added': 0, 'duration': 0}

        stats = {
            'total': len(symbols),
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'records_added': 0
        }

        logger.info(f'待检查: {len(symbols)} 只股票')
        logger.info(f'并发数: {self.max_workers} 个线程')
        logger.info('')

        # 使用线程池并发下载
        completed_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self._download_single_stock, symbol, start_date, end_date, force): symbol
                for symbol in symbols
            }

            # 使用tqdm显示进度
            with tqdm(total=len(symbols), desc="股票下载", unit="只") as pbar:
                for future in as_completed(futures):
                    symbol = futures[future]
                    completed_count += 1
                    try:
                        result = future.result()

                        if result['skipped']:
                            stats['skipped'] += 1
                        elif result['success']:
                            stats['downloaded'] += 1
                            stats['records_added'] += result['records']
                        else:
                            stats['failed'] += 1
                            self.failed_symbols['stock'].append(symbol)
                            if result.get('error'):
                                logger.debug(f'{symbol} 失败: {result["error"]}')

                        # 每100只股票更新一次日志
                        if completed_count % 100 == 0:
                            logger.info(f'进度: {completed_count}/{len(symbols)}')

                        pbar.set_postfix({
                            '下载': stats['downloaded'],
                            '跳过': stats['skipped'],
                            '失败': stats['failed']
                        })

                    except Exception as e:
                        logger.error(f'处理 {symbol} 时发生异常: {e}')
                        stats['failed'] += 1
                        self.failed_symbols['stock'].append(symbol)

                    pbar.update(1)

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ 股票下载完成!')
        logger.info(f'  总数: {stats["total"]}')
        logger.info(f'  已下载: {stats["downloaded"]}')
        logger.info(f'  跳过: {stats["skipped"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  新增记录: {stats["records_added"]:,}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info(f'  平均速度: {len(symbols)/duration:.2f} 只/秒')
        logger.info('')

        return stats

    def download_fundamental_snapshot(self) -> dict:
        """
        下载基本面数据快照（仅最新数据，仅PE和PB）

        Returns:
            dict: 统计信息
        """
        logger.info('='*60)
        logger.info('[阶段3] 下载基本面数据快照 (仅PE/PB)')
        logger.info('='*60)
        logger.info('')
        logger.info('注意: 仅下载最新基本面快照，且只包含PE(市盈率)和PB(市净率)')
        logger.info('      其他财务指标(ROE/ROA/市值等)不下载，数据库中设为NULL')
        logger.info('      估值因子(PE/PB)主要用于横截面比较，最新数据即可满足需求')
        logger.info('')

        start = time.time()

        # 获取股票代码列表
        symbols = self.db.get_stock_codes()

        if not symbols:
            logger.warning('没有找到股票代码,跳过基本面下载')
            return {'total': 0, 'success': 0, 'failed': 0, 'duration': 0}

        logger.info(f'待更新: {len(symbols)} 只股票')
        logger.info('')

        # 直接调用现有的基本面下载器
        stats = self.fundamental_downloader.update_fundamental_data(symbols=symbols)

        duration = time.time() - start
        stats['duration'] = duration
        stats['total'] = len(symbols)

        logger.info('')
        logger.info('✓ 基本面下载完成!')
        logger.info(f'  总数: {stats["total"]}')
        logger.info(f'  成功: {stats["success"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info('')

        return stats

    def download_historical_data(self, years: int = 5,
                                data_types: List[str] = None,
                                force: bool = False,
                                refresh_codes: bool = True) -> dict:
        """
        下载历史数据的主入口

        Args:
            years: 历史年数 (默认5年)
            data_types: 数据类型列表，可选: 'etf', 'stock', 'fundamental', 'all'
            force: 是否强制重新下载已有数据
            refresh_codes: 是否刷新代码表 (默认: True)

        Returns:
            dict: 总体统计信息
        """
        start_time = datetime.now()
        logger.info('')
        logger.info('*'*60)
        logger.info(f'历史数据下载流程启动 - {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('*'*60)
        logger.info('')

        # 阶段0: 检查代码表
        self.check_and_init_codes(force_refresh=refresh_codes)

        # 计算日期范围
        start_date, end_date = self.calculate_date_range(years)
        logger.info('')

        # 规范化data_types
        if data_types is None or 'all' in data_types:
            data_types = ['etf', 'stock', 'fundamental']

        # 执行各阶段（使用优化的批量下载方法）
        if 'etf' in data_types:
            stats = self.download_etf_history_optimized(start_date, end_date, force)
            self.stats.etf_stats = stats

        if 'stock' in data_types:
            time.sleep(2)  # 稍作停顿
            stats = self.download_stock_history_optimized(start_date, end_date, force)
            self.stats.stock_stats = stats

        if 'fundamental' in data_types:
            time.sleep(2)  # 稍作停顿
            stats = self.download_fundamental_snapshot()
            self.stats.fundamental_stats = stats

        # 打印总结
        self.stats.end_time = datetime.now()
        self._print_summary()
        self._save_failed_symbols()

        return {
            'etf': self.stats.etf_stats,
            'stock': self.stats.stock_stats,
            'fundamental': self.stats.fundamental_stats
        }

    def _print_summary(self):
        """打印下载总结"""
        total_duration = (self.stats.end_time - self.stats.start_time).total_seconds()

        logger.info('')
        logger.info('*'*60)
        logger.info('历史数据下载总结')
        logger.info('*'*60)

        # ETF统计
        if self.stats.etf_stats['total'] > 0:
            stats = self.stats.etf_stats
            logger.info('[ETF数据]')
            logger.info(f'  总数: {stats["total"]}')
            logger.info(f'  已下载: {stats["downloaded"]},  跳过: {stats["skipped"]},  失败: {stats["failed"]}')
            logger.info(f'  新增记录: {stats["records_added"]:,}')
            logger.info(f'  耗时: {stats["duration"]:.2f} 秒 ({stats["duration"]/60:.1f} 分钟)')
            logger.info('')

        # 股票统计
        if self.stats.stock_stats['total'] > 0:
            stats = self.stats.stock_stats
            logger.info('[股票数据]')
            logger.info(f'  总数: {stats["total"]}')
            logger.info(f'  已下载: {stats["downloaded"]},  跳过: {stats["skipped"]},  失败: {stats["failed"]}')
            logger.info(f'  新增记录: {stats["records_added"]:,}')
            logger.info(f'  耗时: {stats["duration"]:.2f} 秒 ({stats["duration"]/60:.1f} 分钟)')
            logger.info('')

        # 基本面统计
        if self.stats.fundamental_stats['total'] > 0:
            stats = self.stats.fundamental_stats
            logger.info('[基本面数据]')
            logger.info(f'  总数: {stats["total"]}')
            logger.info(f'  成功: {stats["success"]},  失败: {stats["failed"]}')
            logger.info(f'  耗时: {stats["duration"]:.2f} 秒 ({stats["duration"]/60:.1f} 分钟)')
            logger.info('')

        logger.info(f'总耗时: {total_duration:.2f} 秒 ({total_duration/60:.1f} 分钟)')
        logger.info('*'*60)
        logger.info('')

    def _save_failed_symbols(self):
        """保存失败的代码列表"""
        if self.failed_symbols['etf'] or self.failed_symbols['stock']:
            failed_file = project_root / 'logs' / f'failed_symbols_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

            # 确保logs目录存在
            failed_file.parent.mkdir(parents=True, exist_ok=True)

            with open(failed_file, 'w') as f:
                if self.failed_symbols['etf']:
                    f.write('# 失败的ETF\n')
                    f.write('\n'.join(self.failed_symbols['etf']))
                    f.write('\n\n')

                if self.failed_symbols['stock']:
                    f.write('# 失败的股票\n')
                    f.write('\n'.join(self.failed_symbols['stock']))

            logger.info(f'失败代码已保存到: {failed_file}')
            logger.info('可以重新运行脚本以重试失败的代码')
            logger.info('')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='下载历史数据到PostgreSQL (支持并发下载)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                          # 下载默认5年历史数据(全部类型)
  %(prog)s --years 3                               # 下载近3年数据
  %(prog)s --data-types etf stock                  # 只下载ETF和股票历史数据
  %(prog)s --data-types fundamental                # 只下载基本面快照
  %(prog)s --force                                 # 强制重新下载已有数据
  %(prog)s --workers 10                            # 使用10个并发线程
  %(prog)s --years 10 --data-types all --force     # 强制重新下载近10年所有数据

注意:
  - ETF和股票数据分别存入 etf_history 和 stock_history 表
  - 代码清单分别存入 etf_codes 和 stock_codes 表
  - 基本面数据只下载最新快照，且仅包含PE(市盈率)和PB(市净率)
  - 脚本支持断点续传，重新运行会自动跳过已有数据
  - 使用 --force 可强制重新下载所有数据
  - 默认使用5个并发线程，可根据网络情况调整
        """
    )

    parser.add_argument(
        '--years', '-y',
        type=int,
        default=5,
        help='历史数据年数 (默认: 5)'
    )

    parser.add_argument(
        '--data-types', '-t',
        nargs='+',
        choices=['etf', 'stock', 'fundamental', 'all'],
        default=['all'],
        help='数据类型 (默认: all)'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制重新下载已有数据'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=5,
        help='并发下载数量 (默认: 5, 建议3-10)'
    )

    parser.add_argument(
        '--refresh-codes',
        action='store_true',
        default=True,
        help='下载前刷新代码表 (默认: True)'
    )

    parser.add_argument(
        '--no-refresh-codes',
        action='store_true',
        help='不刷新代码表（使用现有代码表）'
    )

    args = parser.parse_args()

    # 确定是否刷新代码表
    refresh_codes = args.refresh_codes and not args.no_refresh_codes

    # 创建下载器
    downloader = HistoricalDataDownloader(max_workers=args.workers)

    # 执行下载
    try:
        downloader.download_historical_data(
            years=args.years,
            data_types=args.data_types,
            force=args.force,
            refresh_codes=refresh_codes
        )
    except KeyboardInterrupt:
        logger.warning('')
        logger.warning('下载被用户中断')
        logger.warning('可以重新运行脚本继续下载(会自动跳过已有数据)')
        logger.warning('')
    except Exception as e:
        logger.error(f'下载过程发生错误: {e}')
        raise


if __name__ == '__main__':
    main()
