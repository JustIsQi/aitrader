"""
代码表初始化脚本
从 AkShare 获取 ETF 和 A股列表并初始化到 PostgreSQL

用法:
    python scripts/init_codes.py --all              # 初始化所有代码表
    python scripts/init_codes.py --etf              # 仅初始化ETF
    python scripts/init_codes.py --stock            # 仅初始化股票
    python scripts/init_codes.py --all --force      # 强制重新初始化
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from loguru import logger
from database.pg_manager import get_db
from datafeed.downloaders.etf_downloader import EtfDownloader
from datafeed.downloaders.stock_downloader import StockDownloader


class CodeInitializer:
    """代码表初始化器"""

    def __init__(self):
        self.db = get_db()
        self.etf_downloader = EtfDownloader()
        self.stock_downloader = StockDownloader()

    def fetch_etf_list_from_akshare(self) -> pd.DataFrame:
        """
        从 AkShare 获取 ETF 列表

        Returns:
            DataFrame: 包含 symbol 列
        """
        logger.info('正在从 AkShare 获取 ETF 列表...')

        df = self.etf_downloader.fetch_etf_list()
        if df is None or df.empty:
            logger.error('获取 ETF 列表失败')
            return pd.DataFrame()

        # 格式化代码
        df['symbol'] = df['代码'].apply(self.etf_downloader.format_etf_symbol)

        logger.info(f'成功获取 {len(df)} 个 ETF')
        return df[['symbol']]

    def fetch_stock_list_from_akshare(self) -> pd.DataFrame:
        """
        从 AkShare 获取 A股列表

        Returns:
            DataFrame: 包含 symbol 列
        """
        logger.info('正在从 AkShare 获取 A股列表...')

        df = self.stock_downloader.fetch_stock_list()
        if df is None or df.empty:
            logger.error('获取 A股列表失败')
            return pd.DataFrame()

        logger.info(f'成功获取 {len(df)} 只 A股(已过滤)')
        return df[['symbol']]

    def init_etf_codes(self, force: bool = False) -> int:
        """
        初始化 ETF 代码表

        Args:
            force: 是否强制重新初始化(清空后重新填充)

        Returns:
            初始化的代码数量
        """
        logger.info('='*60)
        logger.info('开始初始化 ETF 代码表')
        logger.info('='*60)

        # 检查现有代码数量
        existing_count = self.db.get_code_count('etf').get('etf', 0)

        if existing_count > 0 and not force:
            logger.info(f'ETF 代码表已有 {existing_count} 条记录,跳过初始化')
            logger.info('如需强制重新初始化,请使用 --force 参数')
            return existing_count

        if force and existing_count > 0:
            logger.info(f'强制模式:清空现有的 {existing_count} 条记录')
            self.db.clear_etf_codes()

        # 获取 ETF 列表
        df = self.fetch_etf_list_from_akshare()
        if df.empty:
            logger.error('未能获取 ETF 列表')
            return 0

        # 批量插入数据库
        symbols = df['symbol'].tolist()
        inserted = self.db.batch_add_etf_codes(symbols)

        logger.info(f'✓ ETF 代码表初始化完成: {inserted} 条记录')
        return inserted

    def init_stock_codes(self, force: bool = False) -> int:
        """
        初始化股票代码表

        Args:
            force: 是否强制重新初始化(清空后重新填充)

        Returns:
            初始化的代码数量
        """
        logger.info('='*60)
        logger.info('开始初始化股票代码表')
        logger.info('='*60)

        # 检查现有代码数量
        existing_count = self.db.get_code_count('stock').get('stock', 0)

        if existing_count > 0 and not force:
            logger.info(f'股票代码表已有 {existing_count} 条记录,跳过初始化')
            logger.info('如需强制重新初始化,请使用 --force 参数')
            return existing_count

        if force and existing_count > 0:
            logger.info(f'强制模式:清空现有的 {existing_count} 条记录')
            self.db.clear_stock_codes()

        # 获取股票列表
        df = self.fetch_stock_list_from_akshare()
        if df.empty:
            logger.error('未能获取股票列表')
            return 0

        # 批量插入数据库
        symbols = df['symbol'].tolist()
        inserted = self.db.batch_add_stock_codes(symbols)

        logger.info(f'✓ 股票代码表初始化完成: {inserted} 条记录')
        return inserted

    def init_all_codes(self, force: bool = False) -> dict:
        """
        初始化所有代码表

        Args:
            force: 是否强制重新初始化

        Returns:
            dict: {'etf': N, 'stock': M}
        """
        start_time = datetime.now()
        logger.info('')
        logger.info('*'*60)
        logger.info(f'代码表初始化开始 - {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('*'*60)
        logger.info('')

        results = {}

        # 初始化 ETF
        etf_count = self.init_etf_codes(force=force)
        results['etf'] = etf_count
        logger.info('')

        # 初始化股票
        stock_count = self.init_stock_codes(force=force)
        results['stock'] = stock_count
        logger.info('')

        # 输出总结
        duration = (datetime.now() - start_time).total_seconds()
        logger.info('*'*60)
        logger.info('代码表初始化完成!')
        logger.info('*'*60)
        logger.info(f'  ETF代码:  {results["etf"]} 条')
        logger.info(f'  股票代码: {results["stock"]} 条')
        logger.info(f'  总耗时:   {duration:.2f} 秒')
        logger.info('*'*60)
        logger.info('')

        return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='初始化 ETF 和 A股代码表到 PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --all                  # 初始化所有代码表
  %(prog)s --all --force          # 强制重新初始化
  %(prog)s --etf                  # 仅初始化ETF
  %(prog)s --stock                # 仅初始化股票
        """
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='初始化所有代码表 (ETF + 股票)'
    )

    parser.add_argument(
        '--etf',
        action='store_true',
        help='仅初始化 ETF 代码表'
    )

    parser.add_argument(
        '--stock',
        action='store_true',
        help='仅初始化股票代码表'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='强制重新初始化(清空现有数据)'
    )

    args = parser.parse_args()

    # 如果没有指定任何选项,默认初始化所有
    if not (args.all or args.etf or args.stock):
        args.all = True

    # 创建初始化器
    initializer = CodeInitializer()

    # 执行初始化
    if args.all:
        initializer.init_all_codes(force=args.force)
    elif args.etf:
        initializer.init_etf_codes(force=args.force)
    elif args.stock:
        initializer.init_stock_codes(force=args.force)


if __name__ == '__main__':
    main()
