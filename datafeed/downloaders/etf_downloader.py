"""
ETF 数据下载器
从 akshare 下载 ETF 历史数据并存储到 PostgreSQL
"""
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional
from database.pg_manager import get_db


class EtfDownloader:
    """ETF 数据下载器"""

    def __init__(self):
        self.db = get_db()

    def fetch_etf_list(self) -> Optional[dict]:
        """
        从 AkShare 获取 ETF 列表

        Returns:
            dict: {formatted_symbol: name} 字典，例如 {'510300.SH': '沪深300ETF'}
        """
        try:
            # 使用AkShare接口获取ETF列表
            df = ak.fund_etf_spot_em()
            logger.info(f'获取到 {len(df)} 个ETF')

            # 构建格式化的代码到名称的映射
            name_map = {}
            for _, row in df.iterrows():
                code = str(row['代码']).zfill(6)
                formatted_symbol = self.format_etf_symbol(code)
                name = row['名称']
                name_map[formatted_symbol] = name

            logger.info(f'成功映射 {len(name_map)} 个ETF名称')
            return name_map
        except Exception as e:
            logger.error(f'获取ETF列表失败: {e}')
            return None

    def update_etf_names(self) -> bool:
        """
        从 AkShare 获取 ETF 列表并更新名称到数据库

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            name_map = self.fetch_etf_list()
            if not name_map:
                logger.error('获取ETF名称失败')
                return False

            # 更新到数据库
            updated = self.db.upsert_etf_names(name_map)
            logger.info(f'成功更新 {updated} 个ETF名称')
            return True
        except Exception as e:
            logger.error(f'更新ETF名称失败: {e}')
            return False

    def format_etf_symbol(self, code: str) -> str:
        """
        格式化ETF代码，添加市场后缀

        Args:
            code: 原始代码 (如 '510300')

        Returns:
            格式化后的代码 (如 '510300.SH')
        """
        code = str(code).zfill(6)

        # 上海ETF: 51xxxx, 56xxxx, 58xxxx
        if code.startswith(('51', '56', '58')):
            return f'{code}.SH'
        # 深圳ETF: 159xxx
        elif code.startswith('159'):
            return f'{code}.SZ'
        # 双创50等ETF: 52xxxx, 53xxxx (上海跨市场ETF)
        elif code.startswith(('52', '53')):
            return f'{code}.SH'
        else:
            logger.warning(f'未知ETF代码格式: {code},使用.SH后缀')
            return f'{code}.SH'

    def fetch_etf_history(self, symbol: str, start_date: str = None,
                         end_date: str = None, adjust: str = "hfq") -> Optional[pd.DataFrame]:
        """
        从 AkShare 获取 ETF 历史数据

        Args:
            symbol: ETF 代码 (例如: '510300')
            start_date: 开始日期 (YYYYMMDD 格式)
            end_date: 结束日期 (YYYYMMDD 格式)
            adjust: 复权类型 ('qfq'前复权, 'hfq'后复权, ''不复权)

        Returns:
            DataFrame: 历史数据
        """
        try:
            result = ak.fund_etf_hist_em(
                symbol=symbol,
                period="daily",
                adjust=adjust,
                start_date=start_date,
                end_date=end_date
            )
            return result
        except Exception as e:
            logger.error(f'获取 ETF {symbol} 数据失败: {e}')
            return None

    def update_etf_data(self, symbol: str, etf_name: str = None) -> bool:
        """
        更新单个 ETF 数据（增量下载）

        Args:
            symbol: ETF 代码 (例如: '510300.SH')
            etf_name: ETF 名称 (可选)

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            # 如果没有提供名称，从数据库获取
            if etf_name is None:
                etf_name = self.db.get_etf_name(symbol)

            # 从数据库获取最新日期
            latest_date = self.db.get_latest_date(symbol)

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
            df = self.fetch_etf_history(code, start_date, end_date)

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

            # 追加到数据库（包含名称）
            success = self.db.append_etf_history(df, symbol, name=etf_name)

            if success:
                logger.info(f'成功更新 {symbol}，新增 {len(df)} 条数据')

            return success

        except Exception as e:
            logger.error(f'更新 ETF {symbol} 失败: {e}')
            return False

    def update_etf_data_qfq(self, symbol: str, etf_name: str = None) -> bool:
        """
        更新单个 ETF 前复权数据（增量下载）

        Args:
            symbol: ETF 代码 (例如: '510300.SH')
            etf_name: ETF 名称 (可选)

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            # 如果没有提供名称，从数据库获取
            if etf_name is None:
                etf_name = self.db.get_etf_name(symbol)

            # 从数据库获取最新日期
            latest_date = self.db.get_etf_qfq_latest_date(symbol)

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
            df = self.fetch_etf_history(code, start_date, end_date, adjust="qfq")

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

            # 追加到前复权数据表（包含名称）
            success = self.db.append_etf_history_qfq(df, symbol, name=etf_name)

            if success:
                logger.info(f'成功更新 {symbol} 前复权数据，新增 {len(df)} 条数据')

            return success

        except Exception as e:
            logger.error(f'更新 ETF 前复权数据 {symbol} 失败: {e}')
            return False

    def update_all_etf_data(self) -> dict:
        """
        更新所有 ETF 数据

        Returns:
            dict: 统计信息
        """
        # 首先更新ETF名称
        logger.info('开始更新ETF名称...')
        self.update_etf_names()

        # 获取所有ETF及其名称
        name_map = self.db.get_all_etf_names()
        symbols = list(name_map.keys())

        stats = {
            'total': len(symbols),
            'success': 0,
            'failed': 0
        }

        logger.info(f'开始更新 {len(symbols)} 个 ETF')

        for symbol in symbols:
            etf_name = name_map.get(symbol)
            if self.update_etf_data(symbol, etf_name=etf_name):
                stats['success'] += 1
            else:
                stats['failed'] += 1

        logger.info(f'ETF 更新完成: 成功 {stats["success"]}, 失败 {stats["failed"]}')

        return stats


if __name__ == '__main__':
    # 示例用法
    downloader = EtfDownloader()
    stats = downloader.update_all_etf_data()
    print(stats)
