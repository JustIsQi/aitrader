from datetime import datetime

import pandas as pd
from loguru import logger

from config import DATA_DIR

# 是否启用 DuckDB 作为数据源
ENABLE_DUCKDB = True
DUCKDB_PATH = '/data/home/yy/data/duckdb/trading.db'


class CsvDataLoader:
    def __init__(self, auto_download=True, use_duckdb=None):
        """
        Args:
            auto_download: 是否自动下载缺失的数据
            use_duckdb: 是否使用 DuckDB 作为数据源（None 表示根据全局配置）
        """
        self.auto_download = auto_download
        # 确定是否使用 DuckDB
        if use_duckdb is None:
            self.use_duckdb = ENABLE_DUCKDB
        else:
            self.use_duckdb = use_duckdb

        # 如果启用 DuckDB，初始化数据库连接
        self.db = None
        if self.use_duckdb:
            try:
                from database.db_manager import get_db
                self.db = get_db(DUCKDB_PATH)
                logger.info('CsvDataLoader: 使用 DuckDB 作为数据源')
            except Exception as e:
                logger.warning(f'DuckDB 初始化失败，回退到 CSV 模式: {e}')
                self.use_duckdb = False

    def _download_to_duckdb(self, symbol):
        """下载数据并直接写入DuckDB，不保存CSV文件"""
        try:
            from scripts.get_data import is_etf, fetch_stock_history_with_proxy, fetch_etf_history, fetch_stock_history
            import akshare as ak

            logger.info(f'🔄 [DuckDB] 开始下载 {symbol} 数据...')

            # 判断是ETF还是股票
            if is_etf(symbol):
                code = symbol.split('.')[0]
                logger.info(f'📊 [DuckDB] {symbol} 识别为 ETF，代码: {code}')
                df = fetch_stock_history_with_proxy(code, func=fetch_etf_history)
            else:
                code = symbol.split('.')[0]
                logger.info(f'📊 [DuckDB] {symbol} 识别为股票，代码: {code}')
                df = fetch_stock_history_with_proxy(code, func=fetch_stock_history)

            if df is None or df.empty:
                logger.error(f'❌ [DuckDB] 获取 {symbol} 数据为空')
                return None

            logger.info(f'✓ [DuckDB] {symbol} 原始数据获取成功，共 {len(df)} 条记录')

            # 转换列名为英文
            if '日期' in df.columns:
                df.rename(columns={'日期': 'date', '股票代码': 'symbol',
                                   '开盘': 'open', '收盘': 'close',
                                   '最高': 'high', '最低': 'low',
                                   '成交量': 'volume', '成交额': 'amount',
                                   '涨跌幅': 'change_pct', '涨跌额': 'change_amount',
                                   '振幅': 'amplitude', '换手率': 'turnover_rate'}, inplace=True)
                logger.debug(f'📝 [DuckDB] {symbol} 列名已转换为英文')

            # 添加 symbol 列
            df['symbol'] = symbol

            # 显示数据范围
            if 'date' in df.columns:
                date_range = f"{df['date'].min()} ~ {df['date'].max()}"
                logger.info(f'📅 [DuckDB] {symbol} 数据日期范围: {date_range}')

            # 直接写入 DuckDB
            logger.info(f'💾 [DuckDB] 正在写入 {symbol} 数据到数据库...')
            if is_etf(symbol):
                success = self.db.insert_etf_history(df, symbol)
                table_name = 'etf_history'
            else:
                success = self.db.insert_stock_history(df, symbol)
                table_name = 'stock_history'

            if success:
                logger.info(f'✅ [DuckDB] {symbol} 数据已成功写入表 {table_name}: {df.shape}')
            else:
                logger.error(f'❌ [DuckDB] {symbol} 数据写入失败')

            return df if success else None

        except Exception as e:
            logger.error(f'❌ [DuckDB] 下载 {symbol} 到数据库失败: {e}')
            import traceback
            logger.debug(f'🔍 [DuckDB] 错误详情:\n{traceback.format_exc()}')
            return None

    def _read_csv(self, symbol, path='akshare_data'):
        # 支持 akshare_data 格式: 代码_history.csv
        csv = DATA_DIR.joinpath(path).joinpath('{}_history.csv'.format(symbol))
        if not csv.exists():
            if self.auto_download:
                # 如果启用了 DuckDB，直接写入数据库，不保存 CSV
                if self.use_duckdb and self.db:
                    logger.warning(f'{csv.resolve()} 不存在，尝试自动下载到 DuckDB...')
                    df = self._download_to_duckdb(symbol)
                    if df is not None:
                        # 统一日期格式为 YYYYMMDD（移除横杠）
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
                        df['symbol'] = symbol
                        df.dropna(inplace=True)
                        return df
                    else:
                        logger.error(f'下载 {symbol} 数据失败')
                        return None
                else:
                    # 原有逻辑：下载到 CSV
                    logger.warning(f'{csv.resolve()} 不存在，尝试自动下载...')
                    from scripts.get_data import download_symbol_data
                    success = download_symbol_data(symbol)
                    if not success:
                        logger.error(f'下载 {symbol} 数据失败')
                        return None
                    # 下载成功后重新读取
                    if not csv.exists():
                        logger.error(f'下载后文件仍不存在: {csv.resolve()}')
                        return None
            else:
                logger.warning('{}不存在'.format(csv.resolve()))
                return None

        df = pd.read_csv(csv.resolve(), index_col=None)

        # akshare 格式使用中文列名"日期"，转换为"date"
        if '日期' in df.columns:
            df.rename(columns={'日期': 'date', '股票代码': 'symbol',
                               '开盘': 'open', '收盘': 'close',
                               '最高': 'high', '最低': 'low',
                               '成交量': 'volume', '成交额': 'amount'}, inplace=True)
        else:
            # 原有格式处理
            df['date'] = df['date'].apply(lambda x: str(x))

        # 统一日期格式为 YYYYMMDD（移除横杠）
        df['date'] = df['date'].astype(str).str.replace('-', '')

        df['symbol'] = symbol
        df.dropna(inplace=True)
        return df

    def _read_duckdb(self, symbol, start_date, end_date):
        """从 DuckDB 读取数据"""
        try:
            if not self.db:
                raise Exception("DuckDB 未初始化")

            # 转换日期格式
            start_date_fmt = start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:]
            end_date_fmt = end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:]

            # 判断是ETF还是股票
            from scripts.get_data import is_etf
            if is_etf(symbol):
                df = self.db.get_etf_history(symbol, start_date=start_date_fmt, end_date=end_date_fmt)
            else:
                df = self.db.get_stock_history(symbol, start_date=start_date_fmt, end_date=end_date_fmt)

            if df.empty:
                logger.info(f'DuckDB 中无 {symbol} 数据，开始下载...')
                # 尝试下载数据到 DuckDB
                if self.auto_download:
                    df = self._download_to_duckdb(symbol)
                    if df is not None:
                        # 统一日期格式为 YYYYMMDD（移除横杠）
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
                        df['symbol'] = symbol
                        df.dropna(inplace=True)
                        return df
                logger.warning(f'DuckDB 中无 {symbol} 数据')
                return None

            # 转换日期格式为 YYYYMMDD
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')

            # 添加 symbol 列
            df['symbol'] = symbol

            df.dropna(inplace=True)
            return df

        except Exception as e:
            logger.error(f'从 DuckDB 读取 {symbol} 失败: {e}')
            return None

    def read_dfs(self, symbols: list[str], path='akshare_data', start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        dfs = {}

        for s in symbols:
            # 使用 DuckDB 模式
            if self.use_duckdb:
                df = self._read_duckdb(s, start_date, end_date)
                if df is not None:
                    dfs[s] = df
                    continue
                # DuckDB 读取失败（包括下载失败）
                logger.error(f'无法获取 {s} 的数据，已尝试自动下载但失败')
                continue

            # 使用 CSV 模式（非 DuckDB）
            df = self._read_csv(s, path=path)
            if df is None:
                logger.warning(f'数据文件 {s} 不存在，跳过')
                continue

            # akshare 数据已经是升序，无需排序
            # df.sort_values(by='date', ascending=True, inplace=True)

            if df['date'].iloc[0] > start_date:
                start_date = df['date'].iloc[0]
            df = df[df['date'] >= start_date]
            df = df[df['date'] <= end_date]

            dfs[s] = df

        if not dfs:
            missing_symbols = [s for s in symbols if s not in dfs]
            raise ValueError(f"没有可用的数据。以下标的数据缺失: {missing_symbols}。已尝试自动下载但仍失败，请检查网络连接或代理设置。")

        print('开始日期', start_date)

        for s in dfs.keys():
            df = dfs[s]
            df = df[df['date'] >= start_date]
            df = df[df['date'] <= end_date]

            dfs[s] = df
        return dfs

    def read_df(self, symbols: list[str], start_date='20100101', end_date=datetime.now().strftime('%Y%m%d'),
                path='akshare_data'):
        dfs = []
        for s in symbols:
            df = self._read_csv(s, path=path)
            if df is not None:
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        df = pd.concat(dfs, axis=0)
        # akshare 数据已经是升序，无需排序
        # df.sort_values(by='date', ascending=True, inplace=True)
        df = df[df['date'] >= start_date]
        df = df[df['date'] <= end_date]

        return df

if __name__ == '__main__':
    df = CsvDataLoader().read_df(symbols=['510300.SH','159915.SZ'])
    print(df)