"""
A股股票数据下载器
从 akshare 下载 A股历史数据并存储到 PostgreSQL
"""
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional
from database.pg_manager import get_db


class StockDownloader:
    """A 股股票数据下载器"""

    def __init__(self):
        self.db = get_db()

    def _format_symbol(self, code: str) -> str:
        """
        格式化股票代码,添加市场后缀

        Args:
            code: 原始代码 (如 000001)

        Returns:
            格式化后的代码 (如 000001.SZ)
        """
        code = str(code).zfill(6)

        if code.startswith('6'):
            return f'{code}.SH'  # 上海
        elif code.startswith('0') or code.startswith('3'):
            return f'{code}.SZ'  # 深圳
        elif code.startswith('8') or code.startswith('4'):
            return f'{code}.BJ'  # 北京
        else:
            return code

    def fetch_stock_history(self, symbol: str, start_date: str = None,
                           end_date: str = None, adjust: str = "hfq") -> Optional[pd.DataFrame]:
        """
        从 AkShare 获取股票历史数据

        Args:
            symbol: 股票代码 (例如: '000001')
            start_date: 开始日期 (YYYYMMDD 格式)
            end_date: 结束日期 (YYYYMMDD 格式)
            adjust: 复权类型 ('qfq'前复权, 'hfq'后复权, ''不复权)

        Returns:
            DataFrame: 历史数据
        """
        try:
            result = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                adjust=adjust,
                start_date=start_date,
                end_date=end_date
            )
            return result
        except Exception as e:
            logger.error(f'获取股票 {symbol} 数据失败: {e}')
            return None

    def update_stock_data(self, symbol: str) -> bool:
        """
        更新单个股票数据（增量下载）

        Args:
            symbol: 股票代码 (例如: '000001.SZ')

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            # 从数据库获取最新日期
            latest_date = self.db.get_stock_latest_date(symbol)

            # 使用今天的日期,akshare会自动判断交易日
            from datetime import timedelta
            end_date = datetime.now().strftime('%Y%m%d')

            if latest_date:
                # 增量更新
                next_day = latest_date + timedelta(days=1)
                start_date = next_day.strftime('%Y%m%d')
                logger.info(f'增量更新 {symbol}，从 {start_date} 开始')
            else:
                # 首次下载,从2020年开始
                start_date = '20200101'
                logger.info(f'首次下载 {symbol}，从 {start_date} 开始')

            # 获取数据
            code = symbol.split('.')[0]
            df = self.fetch_stock_history(code, start_date, end_date)

            if df is None or df.empty:
                logger.info(f'{symbol} 无新数据')
                return True

            # 转换列名为英文
            df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate'
            }, inplace=True)

            # 追加到数据库
            success = self.db.append_stock_history(df, symbol)

            if success:
                logger.info(f'成功更新 {symbol}，新增 {len(df)} 条数据')

            return success

        except Exception as e:
            logger.error(f'更新股票 {symbol} 失败: {e}')
            return False

    def update_stock_data_qfq(self, symbol: str) -> bool:
        """
        更新单个股票前复权数据（增量下载）

        Args:
            symbol: 股票代码 (例如: '000001.SZ')

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            # 从数据库获取最新日期
            latest_date = self.db.get_stock_qfq_latest_date(symbol)

            # 使用今天的日期,akshare会自动判断交易日
            from datetime import timedelta
            end_date = datetime.now().strftime('%Y%m%d')

            if latest_date:
                # 增量更新
                next_day = latest_date + timedelta(days=1)
                start_date = next_day.strftime('%Y%m%d')
                logger.info(f'增量更新前复权数据 {symbol}，从 {start_date} 开始')
            else:
                # 首次下载,从2020年开始
                start_date = '20200101'
                logger.info(f'首次下载前复权数据 {symbol}，从 {start_date} 开始')

            # 获取前复权数据
            code = symbol.split('.')[0]
            df = self.fetch_stock_history(code, start_date, end_date, adjust="qfq")

            if df is None or df.empty:
                logger.info(f'{symbol} 无新前复权数据')
                return True

            # 转换列名为英文
            df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change_amount',
                '换手率': 'turnover_rate'
            }, inplace=True)

            # 追加到前复权数据表
            success = self.db.append_stock_history_qfq(df, symbol)

            if success:
                logger.info(f'成功更新 {symbol} 前复权数据，新增 {len(df)} 条数据')

            return success

        except Exception as e:
            logger.error(f'更新股票前复权数据 {symbol} 失败: {e}')
            return False

    def update_all_stock_data(self) -> dict:
        """
        更新所有股票数据

        Returns:
            dict: 统计信息
        """
        symbols = self.db.get_stock_codes()

        stats = {
            'total': len(symbols),
            'success': 0,
            'failed': 0
        }

        logger.info(f'开始更新 {len(symbols)} 只股票')

        for i, symbol in enumerate(symbols, 1):
            if i % 100 == 0:
                logger.info(f'进度: {i}/{len(symbols)}')

            if self.update_stock_data(symbol):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        logger.info(f'股票更新完成: 成功 {stats["success"]}, 失败 {stats["failed"]}')

        return stats

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取所有 A 股股票列表(过滤ST、退市、B股等)

        Returns:
            DataFrame: 股票列表(已过滤)
        """
        try:
            df = ak.stock_zh_a_spot_em()
            logger.info(f'原始获取到 {len(df)} 只 A股')

            # 过滤ST股票、退市股票、暂停上市
            df = df[~df['名称'].str.contains('ST|退市|暂停', na=False)]

            # 过滤B股(代码以200或900开头)
            df = df[~df['代码'].astype(str).str.match(r'^(200|900)')]

            # 格式化代码列
            df['symbol'] = df['代码'].apply(self._format_symbol)

            logger.info(f'过滤后剩余 {len(df)} 只A股')
            return df
        except Exception as e:
            logger.error(f'获取股票列表失败: {e}')
            return None


if __name__ == '__main__':
    # 示例用法
    downloader = StockDownloader()
    stats = downloader.update_all_stock_data()
    print(stats)
