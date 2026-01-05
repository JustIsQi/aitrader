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

            logger.info(f'🔄 [PostgreSQL] 开始下载 {symbol} 数据...')

            # 从数据库获取最新日期
            if is_etf(symbol):
                last_db_date = self.db.get_latest_date(symbol)
            else:
                last_db_date = self.db.get_stock_latest_date(symbol)

            if last_db_date:
                next_day = last_db_date + timedelta(days=1)
                start_date = next_day.strftime('%Y%m%d')
                logger.info(f'📅 [PostgreSQL] {symbol} 从 {start_date} 开始增量下载')
            else:
                start_date = None
                logger.info(f'📅 [PostgreSQL] {symbol} 无历史数据，全量下载')

            # 判断是 ETF 还是股票
            if is_etf(symbol):
                code = symbol.split('.')[0]
                logger.info(f'📊 [PostgreSQL] {symbol} 识别为 ETF，代码: {code}')
                df = fetch_stock_history_with_proxy(code, func=fetch_etf_history,
                                                     start_date=start_date, end_date=None)
            else:
                code = symbol.split('.')[0]
                logger.info(f'📊 [PostgreSQL] {symbol} 识别为股票，代码: {code}')
                df = fetch_stock_history_with_proxy(code, func=fetch_stock_history,
                                                     start_date=start_date, end_date=None)

            if df is None or df.empty:
                logger.error(f'❌ [PostgreSQL] 获取 {symbol} 数据为空')
                return None

            logger.info(f'✓ [PostgreSQL] {symbol} 原始数据获取成功，共 {len(df)} 条记录')

            # 转换列名为英文
            if '日期' in df.columns:
                df.rename(columns={'日期': 'date', '股票代码': 'symbol',
                                   '开盘': 'open', '收盘': 'close',
                                   '最高': 'high', '最低': 'low',
                                   '成交量': 'volume', '成交额': 'amount',
                                   '涨跌幅': 'change_pct', '涨跌额': 'change_amount',
                                   '振幅': 'amplitude', '换手率': 'turnover_rate'}, inplace=True)
                logger.debug(f'📝 [PostgreSQL] {symbol} 列名已转换为英文')

            # 添加 symbol 列
            df['symbol'] = symbol

            # 显示数据范围
            if 'date' in df.columns:
                date_range = f"{df['date'].min()} ~ {df['date'].max()}"
                logger.info(f'📅 [PostgreSQL] {symbol} 数据日期范围: {date_range}')

            # 直接写入 PostgreSQL
            logger.info(f'💾 [PostgreSQL] 正在写入 {symbol} 数据到数据库...')
            if is_etf(symbol):
                success = self.db.append_etf_history(df, symbol)
                table_name = 'etf_history'
            else:
                success = self.db.append_stock_history(df, symbol)
                table_name = 'stock_history'

            if success:
                logger.info(f'✅ [PostgreSQL] {symbol} 数据已成功写入表 {table_name}: {df.shape}')
            else:
                logger.error(f'❌ [PostgreSQL] {symbol} 数据写入失败')

            return df if success else None

        except Exception as e:
            logger.error(f'❌ [PostgreSQL] 下载 {symbol} 到数据库失败: {e}')
            import traceback
            logger.debug(f'🔍 [PostgreSQL] 错误详情:\n{traceback.format_exc()}')
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
                logger.info(f'PostgreSQL 中无 {symbol} 数据，开始下载...')
                # 尝试下载数据到 PostgreSQL
                if self.auto_download:
                    df = self._download_to_postgres(symbol)
                    if df is not None:
                        # 统一日期格式为 YYYYMMDD（移除横杠）
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y%m%d')
                        df['symbol'] = symbol
                        df.dropna(inplace=True)
                        return df
                logger.warning(f'PostgreSQL 中无 {symbol} 数据')
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
        from scripts.get_data import is_etf

        # 转换日期格式
        start_date_fmt = start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:]
        end_date_fmt = end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:]

        # 分离ETF和股票
        etf_symbols = [s for s in symbols if is_etf(s)]
        stock_symbols = [s for s in symbols if not is_etf(s)]

        dfs = {}

        # 批量查询ETF（一次查询获取所有ETF）
        if etf_symbols:
            try:
                df_all = self.db.batch_get_etf_history(etf_symbols, start_date_fmt, end_date_fmt)
                if not df_all.empty:
                    for symbol in etf_symbols:
                        df_symbol = df_all[df_all['symbol'] == symbol].copy()
                        if not df_symbol.empty:
                            df_symbol['date'] = pd.to_datetime(df_symbol['date']).dt.strftime('%Y%m%d')
                            df_symbol['symbol'] = symbol
                            df_symbol.dropna(inplace=True)
                            dfs[symbol] = df_symbol
                        else:
                            logger.warning(f'ETF {symbol} 无数据')
                else:
                    logger.warning(f'批量查询ETF未返回数据')
            except Exception as e:
                logger.error(f'批量查询ETF失败: {e}，回退到单个查询')
                # 回退到单个查询
                for s in etf_symbols:
                    df = self._read_postgres(s, start_date, end_date)
                    if df is not None:
                        dfs[s] = df

        # 批量查询股票（一次查询获取所有股票）
        if stock_symbols:
            try:
                df_all = self.db.batch_get_stock_history(stock_symbols, start_date_fmt, end_date_fmt)
                if not df_all.empty:
                    for symbol in stock_symbols:
                        df_symbol = df_all[df_all['symbol'] == symbol].copy()
                        if not df_symbol.empty:
                            df_symbol['date'] = pd.to_datetime(df_symbol['date']).dt.strftime('%Y%m%d')
                            df_symbol['symbol'] = symbol
                            df_symbol.dropna(inplace=True)
                            dfs[symbol] = df_symbol
                        else:
                            logger.warning(f'股票 {symbol} 无数据')
                else:
                    logger.warning(f'批量查询股票未返回数据')
            except Exception as e:
                logger.error(f'批量查询股票失败: {e}，回退到单个查询')
                # 回退到单个查询
                for s in stock_symbols:
                    df = self._read_postgres(s, start_date, end_date)
                    if df is not None:
                        dfs[s] = df

        if not dfs:
            missing_symbols = [s for s in symbols if s not in dfs]
            raise ValueError(f"没有可用的数据。以下标的数据缺失: {missing_symbols}。已尝试自动下载但仍失败，请检查网络连接或代理设置。")

        # 按日期过滤
        for s in list(dfs.keys()):  # 使用list()避免修改字典大小
            df = dfs[s]
            df = df[df['date'] >= start_date]
            df = df[df['date'] <= end_date]
            dfs[s] = df

        return dfs


# 向后兼容：保留 CsvDataLoader 别名
CsvDataLoader = DbDataLoader


if __name__ == '__main__':
    df = DbDataLoader().read_dfs(symbols=['510300.SH', '159915.SZ'])
    print(df)
