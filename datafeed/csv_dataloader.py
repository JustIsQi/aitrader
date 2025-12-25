from datetime import datetime

import pandas as pd
from loguru import logger

from config import DATA_DIR


class CsvDataLoader:
    def __init__(self, auto_download=True):
        """
        Args:
            auto_download: 是否自动下载缺失的数据
        """
        self.auto_download = auto_download

    def _read_csv(self, symbol, path='akshare_data'):
        # 支持 akshare_data 格式: 代码_history.csv
        csv = DATA_DIR.joinpath(path).joinpath('{}_history.csv'.format(symbol))
        if not csv.exists():
            if self.auto_download:
                logger.warning(f'{csv.resolve()} 不存在，尝试自动下载...')
                from get_data import download_symbol_data
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

    def read_dfs(self, symbols: list[str], path='akshare_data', start_date='20100101', end_date=datetime.now().strftime('%Y%m%d')):
        dfs = {}

        for s in symbols:
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
            raise ValueError(f"没有可用的数据文件。以下股票数据缺失: {missing_symbols}。已尝试自动下载但仍失败，请检查网络连接或代理设置。")

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