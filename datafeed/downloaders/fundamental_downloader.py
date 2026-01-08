"""
A 股基本面数据下载器
从 akshare 下载基本面数据并存储到 PostgreSQL
"""
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional, List, Dict
from tqdm import tqdm
import time
from database.pg_manager import get_db
from sqlalchemy import text


class FundamentalDownloader:
    """A 股基本面数据下载器"""

    def __init__(self):
        self.db = get_db()
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0
        }

    def get_all_a_stocks(self) -> pd.DataFrame:
        """
        获取全市场 A 股列表

        Returns:
            DataFrame: 包含股票代码、名称等信息的DataFrame
        """
        try:
            logger.info('正在获取全市场 A 股列表...')
            df = ak.stock_zh_a_spot_em()

            # 格式化股票代码
            df['symbol'] = df['代码'].apply(self._format_symbol)
            df['name'] = df['名称']
            df['is_st'] = df['名称'].apply(self._check_is_st)

            logger.info(f'成功获取 {len(df)} 只 A股')
            return df[['symbol', 'name', 'is_st', '代码']]

        except Exception as e:
            logger.error(f'获取 A 股列表失败: {e}')
            return pd.DataFrame()

    def _format_symbol(self, code: str) -> str:
        """
        格式化股票代码

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

    def _check_is_st(self, name: str) -> bool:
        """
        检查是否为 ST 股票

        Args:
            name: 股票名称

        Returns:
            是否为 ST 股票
        """
        if pd.isna(name):
            return False
        name = str(name).upper()
        return 'ST' in name or 'S*' in name or '退市' in name

    def get_all_a_stocks_with_fundamentals(self) -> pd.DataFrame:
        """
        获取全市场A股列表及基本面数据(一次获取)

        Returns:
            DataFrame: 包含股票代码、名称、PE、PB、市值等
        """
        try:
            logger.info('正在从 AkShare 获取全市场A股实时行情(含基本面数据)...')
            df = ak.stock_zh_a_spot_em()
            logger.info(f'获取到 {len(df)} 只A股')

            # 过滤ST股票、退市股票、暂停上市
            df = df[~df['名称'].str.contains('ST|退市|暂停', na=False)]

            # 过滤B股(代码以200或900开头)
            df = df[~df['代码'].astype(str).str.match(r'^(200|900)')]

            # 格式化代码列
            df['symbol'] = df['代码'].apply(self._format_symbol)

            logger.info(f'过滤后剩余 {len(df)} 只A股')
            return df

        except Exception as e:
            logger.error(f'获取A股列表失败: {e}')
            return pd.DataFrame()

    def fetch_stock_fundamental(self, symbol: str, code: str) -> Optional[Dict]:
        """
        获取单只股票的基本面数据（仅PE和PB）

        Args:
            symbol: 格式化后的代码 (如 000001.SZ)
            code: 原始代码 (如 000001)

        Returns:
            包含基本面数据的字典（仅PE、PB）
        """
        try:
            # 获取实时行情数据 (仅PE、PB)
            hist_data = self._fetch_hist_data(code)
            if hist_data is None:
                return None

            # 只返回PE和PB数据
            fundamental = {
                'date': self.today,
                'symbol': symbol,
                'pe_ratio': hist_data.get('pe_ratio'),
                'pb_ratio': hist_data.get('pb_ratio'),
            }

            return fundamental

        except Exception as e:
            logger.warning(f'获取 {symbol} 基本面数据失败: {e}')
            return None

    def _fetch_hist_data(self, code: str) -> Optional[Dict]:
        """
        获取历史行情中的估值数据（仅PE和PB）

        Args:
            code: 原始代码

        Returns:
            包含 PE/PB 数据的字典
        """
        try:
            # 使用历史行情接口获取最新数据
            # 使用最近10天的数据,包含今天
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )

            if df.empty:
                return None

            # 获取最新一天的数据
            latest = df.iloc[-1]

            return {
                'pe_ratio': latest.get('市盈率-动态', None),
                'pb_ratio': latest.get('市净率', None),
            }

        except Exception as e:
            logger.debug(f'获取 {code} 历史数据失败: {e}')
            return None

    def _fetch_financial_data(self, code: str) -> Dict:
        """
        获取财务数据

        Args:
            code: 原始代码

        Returns:
            包含财务指标的字典
        """
        try:
            # 尝试获取个股信息
            info = ak.stock_individual_info_em(symbol=code)

            if not info.empty:
                # 转换为字典
                info_dict = {}
                for _, row in info.iterrows():
                    key = row['item']
                    value = row['value']
                    info_dict[key] = value

                return {
                    'roe': self._safe_float(info_dict.get('净资产收益率')),
                    'roa': self._safe_float(info_dict.get('总资产收益率')),
                    'profit_margin': self._safe_float(info_dict.get('销售净利率')),
                    'operating_margin': None,  # AkShare 中可能没有
                    'debt_ratio': self._safe_float(info_dict.get('资产负债率')),
                    'current_ratio': self._safe_float(info_dict.get('流动比率')),
                }

        except Exception as e:
            logger.debug(f'获取 {code} 财务数据失败: {e}')

        # 返回空值
        return {
            'roe': None,
            'roa': None,
            'profit_margin': None,
            'operating_margin': None,
            'debt_ratio': None,
            'current_ratio': None,
        }

    def _safe_float(self, value) -> Optional[float]:
        """
        安全转换为 float

        Args:
            value: 输入值

        Returns:
            float 值或 None
        """
        if value is None or value == '' or value == '-':
            return None

        try:
            return float(str(value).replace('%', '').replace(',', ''))
        except:
            return None

    def update_metadata(self, df: pd.DataFrame):
        """
        批量更新股票元数据

        Args:
            df: 包含股票信息的 DataFrame
        """
        try:
            logger.info('正在更新股票元数据...')

            # 准备数据
            metadata_df = pd.DataFrame({
                'symbol': df['symbol'],
                'name': df['name'],
                'sector': None,  # AkShare 暂无
                'industry': None,  # AkShare 暂无
                'list_date': None,  # 可以后续补充
                'is_st': df['is_st'],
                'is_suspend': False,
                'is_new_ipo': False
            })

            self.db.batch_upsert_stock_metadata(metadata_df)
            logger.info(f'成功更新 {len(metadata_df)} 条元数据')

        except Exception as e:
            logger.error(f'更新元数据失败: {e}')

    def update_fundamental_data(self, symbols: List[str] = None,
                               batch_size: int = 100) -> dict:
        """
        更新基本面数据（仅最新数据）

        注意：只更新最新的基本面快照数据，不下载历史数据
        原因：估值因子(PE/PB)主要用于横截面比较，最新数据即可满足需求

        Args:
            symbols: 股票代码列表，为 None 则更新全市场
            batch_size: 批量提交大小

        Returns:
            dict: 统计信息
        """
        try:
            # 使用新接口一次性获取所有股票的基本面数据
            stock_list = self.get_all_a_stocks_with_fundamentals()

            if stock_list.empty:
                logger.error('获取股票列表失败')
                return self.stats

            self.stats['total'] = len(stock_list)
            logger.info(f'开始更新 {len(stock_list)} 只股票的基本面数据...')

            # 更新元数据
            self._update_metadata_from_spot(stock_list)

            # 更新今天的实时数据
            logger.info('更新最新实时数据...')
            fundamental_list = []
            today = datetime.now().strftime('%Y-%m-%d')

            for _, row in stock_list.iterrows():
                try:
                    # 只获取PE和PB数据
                    fundamental = {
                        'date': today,
                        'symbol': row['symbol'],
                        'pe_ratio': self._safe_float(row.get('市盈率-动态')),
                        'pb_ratio': self._safe_float(row.get('市净率')),
                    }

                    fundamental_list.append(fundamental)
                    self.stats['success'] += 1

                    # 批量提交
                    if len(fundamental_list) >= batch_size:
                        self._batch_insert(fundamental_list)
                        fundamental_list = []

                except Exception as e:
                    symbol = row.get('symbol', 'unknown')
                    logger.warning(f'处理 {symbol} 失败: {e}')
                    self.stats['failed'] += 1

            # 提交剩余数据
            if fundamental_list:
                self._batch_insert(fundamental_list)

            # 打印统计
            logger.info(f'基本面数据更新完成:')
            logger.info(f'  总计: {self.stats["total"]}')
            logger.info(f'  成功: {self.stats["success"]}')
            logger.info(f'  失败: {self.stats["failed"]}')

            return self.stats

        except Exception as e:
            logger.error(f'更新基本面数据失败: {e}')
            return self.stats

    def _update_metadata_from_spot(self, df: pd.DataFrame):
        """
        从实时行情数据更新股票元数据

        Args:
            df: 实时行情DataFrame
        """
        try:
            logger.info('正在更新股票元数据...')

            # 准备数据
            metadata_df = pd.DataFrame({
                'symbol': df['symbol'],
                'name': df['名称'],
                'sector': None,  # AkShare 暂无
                'industry': None,  # AkShare 暂无
                'list_date': None,  # 可以后续补充
                'is_st': df['名称'].apply(self._check_is_st),
                'is_suspend': False,
                'is_new_ipo': False
            })

            self.db.batch_upsert_stock_metadata(metadata_df)
            logger.info(f'成功更新 {len(metadata_df)} 条元数据')

        except Exception as e:
            logger.error(f'更新元数据失败: {e}')

    # 注意：已移除 _download_historical_fundamental 方法
    # 原因：AkShare 的 stock_zh_a_hist 接口不返回历史 PE/PB 数据
    # 估值因子(PE/PB)主要用于横截面比较，使用最新数据即可满足需求
    # 如需历史基本面数据，建议使用 Tushare 等付费数据源

    def _batch_insert_all(self, df_list: list):
        """
        批量插入多只股票的数据（使用 ON CONFLICT DO NOTHING）

        Args:
            df_list: DataFrame 列表
        """
        if not df_list:
            return

        try:
            # 合并所有 DataFrame
            combined_df = pd.concat(df_list, ignore_index=True)
            self.db.batch_insert_fundamental_if_not_exists(combined_df)
        except Exception as e:
            logger.error(f'批量插入数据失败: {e}')

    def _batch_insert(self, fundamental_list: List[Dict]):
        """
        批量插入基本面数据（仅PE和PB）

        Args:
            fundamental_list: 基本面数据列表
        """
        try:
            df = pd.DataFrame(fundamental_list)

            # 添加其他必需字段，设为None（因为只下载PE和PB）
            required_columns = [
                'ps_ratio', 'roe', 'roa', 'profit_margin', 'operating_margin',
                'debt_ratio', 'current_ratio', 'total_mv', 'circ_mv'
            ]
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None

            # 确保数值列是正确的数据类型
            numeric_columns = [
                'pe_ratio', 'pb_ratio', 'ps_ratio', 'roe', 'roa',
                'profit_margin', 'operating_margin', 'debt_ratio', 'current_ratio',
                'total_mv', 'circ_mv'
            ]

            for col in numeric_columns:
                if col in df.columns:
                    # 转换为数值类型,无法转换的变为NaN
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            self.db.batch_upsert_fundamental(df)
            logger.debug(f'批量插入 {len(df)} 条基本面数据（仅PE和PB有效）')
        except Exception as e:
            logger.error(f'批量插入失败: {e}')


if __name__ == '__main__':
    # 示例用法
    downloader = FundamentalDownloader()

    # 选项1: 仅更新最新数据
    print("=" * 60)
    print("选项1: 仅更新最新基本面数据")
    print("=" * 60)
    stats = downloader.update_fundamental_data(download_history=False)
    print(stats)
    print()

    # 选项2: 更新最新数据 + 下载历史数据(首次运行)
    # print("=" * 60)
    # print("选项2: 下载近5年的历史基本面数据")
    # print("=" * 60)
    # stats = downloader.update_fundamental_data(download_history=True, history_years=5)
    # print(stats)
