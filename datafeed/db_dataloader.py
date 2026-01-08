from datetime import datetime

import pandas as pd
from loguru import logger

from config import DATA_DIR


class DbDataLoader:
    """数据库批量查询数据加载器（支持PostgreSQL）"""

    def __init__(self, auto_download=True):
        """
        Args:
            auto_download: 是否自动下载缺失的数据
        """
        self.auto_download = auto_download
        from database.pg_manager import get_db
        self.db = get_db()
        logger.info('DbDataLoader: 使用 PostgreSQL 作为数据源')

    def _download_to_postgres(self, symbol):
        """下载数据并直接写入 PostgreSQL"""
        try:
            from scripts.get_data import is_etf, fetch_stock_history_with_proxy, fetch_etf_history, fetch_stock_history
            from datetime import timedelta
            import time

            download_start = time.time()
            logger.info(f'🔄 [数据下载] {symbol} - 开始准备下载...')

            # 从数据库获取最新日期
            if is_etf(symbol):
                last_db_date = self.db.get_latest_date(symbol)
            else:
                last_db_date = self.db.get_stock_latest_date(symbol)

            if last_db_date:
                next_day = last_db_date + timedelta(days=1)
                start_date = next_day.strftime('%Y%m%d')
                logger.info(f'📅 [数据下载] {symbol} - 增量下载模式: 从 {start_date} 开始')
            else:
                start_date = None
                logger.info(f'📅 [数据下载] {symbol} - 全量下载模式: 获取所有历史数据')

            # 判断是 ETF 还是股票
            if is_etf(symbol):
                code = symbol.split('.')[0]
                logger.info(f'📊 [数据下载] {symbol} - 识别为ETF，开始通过代理获取数据 (可能需要30-60秒)...')
                fetch_start = time.time()
                df = fetch_stock_history_with_proxy(code, func=fetch_etf_history,
                                                     start_date=start_date, end_date=None)
                fetch_elapsed = time.time() - fetch_start
                logger.info(f'⏱️ [数据下载] {symbol} - 网络请求完成，耗时 {fetch_elapsed:.1f}秒')
            else:
                code = symbol.split('.')[0]
                logger.info(f'📊 [数据下载] {symbol} - 识别为股票，开始通过代理获取数据 (可能需要30-60秒)...')
                fetch_start = time.time()
                df = fetch_stock_history_with_proxy(code, func=fetch_stock_history,
                                                     start_date=start_date, end_date=None)
                fetch_elapsed = time.time() - fetch_start
                logger.info(f'⏱️ [数据下载] {symbol} - 网络请求完成，耗时 {fetch_elapsed:.1f}秒')

            if df is None or df.empty:
                logger.error(f'❌ [数据下载] {symbol} - 获取数据为空或失败')
                return None

            logger.info(f'✓ [数据下载] {symbol} - 成功获取 {len(df)} 条记录')

            # 转换列名为英文
            if '日期' in df.columns:
                df.rename(columns={'日期': 'date', '股票代码': 'symbol',
                                   '开盘': 'open', '收盘': 'close',
                                   '最高': 'high', '最低': 'low',
                                   '成交量': 'volume', '成交额': 'amount',
                                   '涨跌幅': 'change_pct', '涨跌额': 'change_amount',
                                   '振幅': 'amplitude', '换手率': 'turnover_rate'}, inplace=True)
                logger.debug(f'📝 [数据下载] {symbol} - 列名已转换为英文格式')

            # 添加 symbol 列
            df['symbol'] = symbol

            # 显示数据范围
            if 'date' in df.columns:
                date_range = f"{df['date'].min()} ~ {df['date'].max()}"
                logger.info(f'📅 [数据下载] {symbol} - 数据范围: {date_range}')

            # 直接写入 PostgreSQL
            logger.info(f'💾 [数据库] {symbol} - 开始写入数据库...')
            write_start = time.time()
            if is_etf(symbol):
                success = self.db.append_etf_history(df, symbol)
                table_name = 'etf_history'
            else:
                success = self.db.append_stock_history(df, symbol)
                table_name = 'stock_history'
            write_elapsed = time.time() - write_start

            if success:
                total_elapsed = time.time() - download_start
                logger.success(f'✅ [数据下载] {symbol} - 完成! 写入耗时 {write_elapsed:.2f}秒 | 总耗时 {total_elapsed:.2f}秒 | 记录数: {len(df)}')
            else:
                logger.error(f'❌ [数据库] {symbol} - 数据写入失败')

            return df if success else None

        except Exception as e:
            total_elapsed = time.time() - download_start if 'download_start' in locals() else 0
            logger.error(f'❌ [数据下载] {symbol} - 下载失败 (耗时 {total_elapsed:.2f}秒): {e}')
            import traceback
            logger.debug(f'🔍 [错误详情]\n{traceback.format_exc()}')
            return None

    def _read_postgres(self, symbol, start_date, end_date):
        """从 PostgreSQL 读取数据"""
        try:
            # 转换日期格式
            start_date_fmt = start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:]
            end_date_fmt = end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:]

            # 判断是 ETF 还是股票
            from scripts.get_data import is_etf
            if is_etf(symbol):
                df = self.db.get_etf_history(symbol, start_date=start_date_fmt, end_date=end_date_fmt)
            else:
                df = self.db.get_stock_history(symbol, start_date=start_date_fmt, end_date=end_date_fmt)

            if df.empty:
                if self.auto_download:
                    logger.info(f'PostgreSQL 中无 {symbol} 数据，开始下载...')
                    # 尝试下载数据到 PostgreSQL
                    df = self._download_to_postgres(symbol)
                    if df is not None:
                        # 统一日期格式为 YYYYMMDD（移除横杠）
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
                        df['symbol'] = symbol
                        df.dropna(inplace=True)
                        return df
                else:
                    logger.warning(f'PostgreSQL 中无 {symbol} 数据（auto_download=False，跳过下载）')
                return None

            # 转换日期格式为 YYYYMMDD
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')

            # 添加 symbol 列
            df['symbol'] = symbol

            df.dropna(inplace=True)
            return df

        except Exception as e:
            logger.error(f'从 PostgreSQL 读取 {symbol} 失败: {e}')
            return None

    def read_dfs(self, symbols: list[str], start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        """读取多个标的的数据（批量查询优化版本）"""
        # ⭐ ADD: Performance monitoring
        import time
        from concurrent.futures import ThreadPoolExecutor

        load_start = time.time()

        # 检查 symbols 是否为空
        if not symbols:
            raise ValueError("没有提供任何标的代码。请确保策略生成了有效的股票/ETF列表。")

        from scripts.get_data import is_etf

        # 转换日期格式
        start_date_fmt = start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:]
        end_date_fmt = end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:]

        # ⭐ ADD: Log request details for monitoring
        logger.info(f'DbDataLoader: 开始加载 {len(symbols)} 个标的的数据 ({start_date_fmt} ~ {end_date_fmt})')

        # 分离ETF和股票
        etf_symbols = [s for s in symbols if is_etf(s)]
        stock_symbols = [s for s in symbols if not is_etf(s)]

        dfs = {}

        # ⭐ OPTIMIZATION 1: Adaptive batch sizes based on symbol count
        # ETF batches: Keep 100 (ETFs are fewer, queries are faster)
        ETF_BATCH_SIZE = 100

        # Stock batches: Scale based on total stocks
        # - < 500 stocks: batch size = stock count (single query)
        # - 500-2000 stocks: batch size = 500
        # - > 2000 stocks: batch size = 1000
        if len(stock_symbols) < 500:
            STOCK_BATCH_SIZE = len(stock_symbols)  # Single batch
        elif len(stock_symbols) < 2000:
            STOCK_BATCH_SIZE = 500
        else:
            STOCK_BATCH_SIZE = 1000

        logger.debug(f'批量查询配置: ETF_BATCH={ETF_BATCH_SIZE}, STOCK_BATCH={STOCK_BATCH_SIZE}')

        # ⭐ OPTIMIZATION 2: Define batch loading functions
        def load_etf_batch():
            """Load all ETF batches"""
            results = {}
            if not etf_symbols:
                return results

            batch_start = time.time()
            for i in range(0, len(etf_symbols), ETF_BATCH_SIZE):
                batch = etf_symbols[i:i+ETF_BATCH_SIZE]
                try:
                    logger.debug(f'批量查询ETF: 第 {i//ETF_BATCH_SIZE + 1} 批，共 {len(batch)} 只ETF')
                    query_start = time.time()

                    # ✅ Date filtering happens in SQL (fast)
                    df_all = self.db.batch_get_etf_history(batch, start_date_fmt, end_date_fmt)

                    query_elapsed = time.time() - query_start
                    logger.debug(f'  查询耗时: {query_elapsed:.2f}秒, 返回 {len(df_all)} 行')

                    if not df_all.empty:
                        # ✅ OPTIMIZATION 3: Use groupby instead of loop for symbol filtering
                        for symbol, group in df_all.groupby('symbol'):
                            group = group.copy()
                            group['date'] = pd.to_datetime(group['date']).dt.strftime('%Y%m%d')
                            group.dropna(inplace=True)
                            results[symbol] = group
                    else:
                        logger.warning(f'批量查询ETF（第 {i//ETF_BATCH_SIZE + 1} 批）未返回数据')

                except Exception as e:
                    logger.error(f'批量查询ETF失败（第 {i//ETF_BATCH_SIZE + 1} 批）: {e}，回退到单个查询')
                    # Fallback to individual queries
                    for s in batch:
                        df = self._read_postgres(s, start_date, end_date)
                        if df is not None:
                            results[s] = df

            batch_elapsed = time.time() - batch_start
            logger.info(f'✓ ETF数据加载完成: {len(results)} 个标的, 耗时 {batch_elapsed:.2f}秒')
            return results

        def load_stock_batch():
            """Load all stock batches"""
            results = {}
            if not stock_symbols:
                return results

            batch_start = time.time()
            for i in range(0, len(stock_symbols), STOCK_BATCH_SIZE):
                batch = stock_symbols[i:i+STOCK_BATCH_SIZE]
                try:
                    logger.debug(f'批量查询股票: 第 {i//STOCK_BATCH_SIZE + 1} 批，共 {len(batch)} 只股票')
                    query_start = time.time()

                    # ✅ Date filtering happens in SQL (fast)
                    df_all = self.db.batch_get_stock_history(batch, start_date_fmt, end_date_fmt)

                    query_elapsed = time.time() - query_start
                    logger.debug(f'  查询耗时: {query_elapsed:.2f}秒, 返回 {len(df_all)} 行')

                    if not df_all.empty:
                        # ✅ OPTIMIZATION 3: Use groupby instead of loop for symbol filtering
                        for symbol, group in df_all.groupby('symbol'):
                            group = group.copy()
                            group['date'] = pd.to_datetime(group['date']).dt.strftime('%Y%m%d')
                            group.dropna(inplace=True)
                            results[symbol] = group
                    else:
                        logger.warning(f'批量查询股票（第 {i//STOCK_BATCH_SIZE + 1} 批）未返回数据')

                except Exception as e:
                    logger.error(f'批量查询股票失败（第 {i//STOCK_BATCH_SIZE + 1} 批）: {e}，回退到单个查询')
                    # Fallback to individual queries
                    for s in batch:
                        df = self._read_postgres(s, start_date, end_date)
                        if df is not None:
                            results[s] = df

            batch_elapsed = time.time() - batch_start
            logger.info(f'✓ 股票数据加载完成: {len(results)} 个标的, 耗时 {batch_elapsed:.2f}秒')
            return results

        # ⭐ OPTIMIZATION 4: Parallel processing of ETFs and stocks
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_etf = executor.submit(load_etf_batch)
            future_stock = executor.submit(load_stock_batch)

            dfs.update(future_etf.result())
            dfs.update(future_stock.result())

        if not dfs:
            missing_symbols = [s for s in symbols if s not in dfs]
            raise ValueError(f"没有可用的数据。以下标的数据缺失: {missing_symbols}。已尝试自动下载但仍失败，请检查网络连接或代理设置。")

        # ⭐ NEW: 合并基本面数据（仅股票，ETF不需要）
        if stock_symbols:
            dfs = self._merge_fundamental_data(dfs, stock_symbols)

        total_elapsed = time.time() - load_start
        logger.success(f'✓ 数据加载全部完成: {len(dfs)} 个标的, 总耗时 {total_elapsed:.2f}秒')

        return dfs

    def _merge_fundamental_data(self, dfs: dict, stock_symbols: list) -> dict:
        """
        合并基本面数据（PE、PB）到股票历史数据中

        Args:
            dfs: 股票历史数据字典 {symbol: DataFrame}
            stock_symbols: 股票代码列表

        Returns:
            合并后的数据字典
        """
        try:
            # 批量获取基本面数据
            fundamental_df = self.db.batch_get_latest_fundamental(stock_symbols)

            if fundamental_df.empty:
                logger.warning('未获取到基本面数据，PE/PB等字段将为空')
                return dfs

            logger.info(f'✓ 已获取 {len(fundamental_df)} 只股票的基本面数据 (PE/PB)')

            # 将基本面数据转为字典 {symbol: {pe: xxx, pb: xxx}}
            fund_dict = fundamental_df.set_index('symbol').to_dict('index')

            # 为每只股票的DataFrame添加基本面列
            for symbol, df in dfs.items():
                if symbol in fund_dict:
                    fund_data = fund_dict[symbol]
                    # 添加PE和PB列（所有行使用相同的最新值）
                    df['pe'] = fund_data.get('pe')
                    df['pb'] = fund_data.get('pb')
                else:
                    # 没有基本面数据的股票，设为NaN
                    df['pe'] = None
                    df['pb'] = None

            return dfs

        except Exception as e:
            logger.error(f'合并基本面数据失败: {e}')
            return dfs


# 向后兼容：保留 CsvDataLoader 别名
CsvDataLoader = DbDataLoader


if __name__ == '__main__':
    df = DbDataLoader().read_dfs(symbols=['510300.SH', '159915.SZ'])
    print(df)
