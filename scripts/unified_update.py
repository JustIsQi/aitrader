"""
统一数据更新脚本
按顺序更新: ETF数据 → 基本面数据 → 股票交易数据

用法:
    python scripts/unified_update.py                    # 完整更新
    python scripts/unified_update.py --stage etf        # 仅更新ETF
    python scripts/unified_update.py --stage fundamental # 仅更新基本面
    python scripts/unified_update.py --stage stock      # 仅更新股票
    python scripts/unified_update.py --skip-code-check  # 跳过代码检查
"""
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from database.pg_manager import get_db
from datafeed.downloaders.etf_downloader import EtfDownloader
from datafeed.downloaders.stock_downloader import StockDownloader
from datafeed.downloaders.fundamental_downloader import FundamentalDownloader


class UnifiedUpdater:
    """统一数据更新器"""

    def __init__(self):
        self.db = get_db()
        self.etf_downloader = EtfDownloader()
        self.stock_downloader = StockDownloader()
        self.fundamental_downloader = FundamentalDownloader()

        self.stats = {
            'start_time': datetime.now(),
            'stages': {
                'etf': {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0},
                'fundamental': {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0},
                'stock': {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0}
            }
        }

    def check_and_init_codes(self) -> bool:
        """
        检查并自动初始化代码表

        Returns:
            是否执行了初始化
        """
        logger.info('[阶段0] 检查代码表状态...')

        code_count = self.db.get_code_count()
        etf_empty = code_count.get('etf', 0) == 0
        stock_empty = code_count.get('stock', 0) == 0

        logger.info(f'  etf_codes:   {code_count.get("etf", 0)} 条')
        logger.info(f'  stock_codes: {code_count.get("stock", 0)} 条')

        if etf_empty or stock_empty:
            logger.warning('')
            logger.warning('⚠️  代码表为空,开始自动初始化...')
            logger.warning('')

            from scripts.init_codes import CodeInitializer
            initializer = CodeInitializer()

            if etf_empty:
                initializer.init_etf_codes(force=False)

            if stock_empty:
                initializer.init_stock_codes(force=False)

            logger.info('')
            logger.info('✓ 代码表初始化完成')
            logger.info('')
            return True

        logger.info('✓ 代码表状态正常')
        logger.info('')
        return False

    def update_etf_stage(self) -> dict:
        """
        阶段1: 更新 ETF 数据

        Returns:
            统计信息
        """
        logger.info('='*60)
        logger.info('[阶段1] 更新 ETF 历史数据')
        logger.info('='*60)
        logger.info('')

        start = time.time()

        # 获取 ETF 代码列表
        symbols = self.db.get_etf_codes()

        if not symbols:
            logger.warning('没有找到 ETF 代码,跳过 ETF 更新')
            return {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0}

        logger.info(f'待更新: {len(symbols)} 个 ETF')
        logger.info('')

        # 更新所有 ETF
        stats = self.etf_downloader.update_all_etf_data()

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ ETF 更新完成!')
        logger.info(f'  成功: {stats["success"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info('')

        return stats

    def update_fundamental_stage(self) -> dict:
        """
        阶段2: 更新基本面数据（仅最新数据）

        注意：只更新最新的基本面快照数据，不下载历史数据
        估值因子(PE/PB)主要用于横截面比较，最新数据即可满足需求

        Returns:
            统计信息
        """
        logger.info('='*60)
        logger.info('[阶段2] 更新基本面数据')
        logger.info('='*60)
        logger.info('')

        start = time.time()

        # 获取股票代码列表
        symbols = self.db.get_stock_codes()

        if not symbols:
            logger.warning('没有找到股票代码,跳过基本面更新')
            return {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0}

        logger.info(f'待更新: {len(symbols)} 只股票')
        logger.info('')

        # 更新基本面数据
        stats = self.fundamental_downloader.update_fundamental_data(
            symbols=symbols
        )

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ 基本面更新完成!')
        logger.info(f'  成功: {stats["success"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info('')

        return stats

    def update_stock_stage(self) -> dict:
        """
        阶段3: 更新股票交易数据

        Returns:
            统计信息
        """
        logger.info('='*60)
        logger.info('[阶段3] 更新股票交易数据')
        logger.info('='*60)
        logger.info('')

        start = time.time()

        # 获取股票代码列表
        symbols = self.db.get_stock_codes()

        if not symbols:
            logger.warning('没有找到股票代码,跳过股票更新')
            return {'success': 0, 'failed': 0, 'skipped': 0, 'duration': 0}

        logger.info(f'待更新: {len(symbols)} 只股票')
        logger.info('')

        # 更新所有股票
        stats = self.stock_downloader.update_all_stock_data()

        duration = time.time() - start
        stats['duration'] = duration

        logger.info('')
        logger.info('✓ 股票交易数据更新完成!')
        logger.info(f'  成功: {stats["success"]}')
        logger.info(f'  失败: {stats["failed"]}')
        logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
        logger.info('')

        return stats

    def unified_data_update(self, stages: Optional[List[str]] = None,
                           skip_code_check: bool = False) -> dict:
        """
        统一数据更新流程

        Args:
            stages: 要执行的阶段列表,如 ['etf', 'fundamental', 'stock']
                    为 None 则执行所有阶段
            skip_code_check: 是否跳过代码表检查

        Returns:
            总体统计信息
        """
        start_time = datetime.now()
        logger.info('')
        logger.info('*'*60)
        logger.info(f'统一数据更新流程启动 - {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('*'*60)
        logger.info('')

        # 阶段0: 检查代码表
        if not skip_code_check:
            self.check_and_init_codes()
        else:
            logger.info('[阶段0] 跳过代码表检查')

        # 确定要执行的阶段
        if stages is None:
            stages = ['etf', 'fundamental', 'stock']

        # 执行各阶段
        if 'etf' in stages:
            stats = self.update_etf_stage()
            self.stats['stages']['etf'] = stats

        if 'fundamental' in stages:
            time.sleep(2)  # 稍作停顿
            stats = self.update_fundamental_stage()
            self.stats['stages']['fundamental'] = stats

        if 'stock' in stages:
            time.sleep(2)  # 稍作停顿
            stats = self.update_stock_stage()
            self.stats['stages']['stock'] = stats

        # 输出总结
        total_duration = (datetime.now() - start_time).total_seconds()
        self._print_summary(total_duration)

        return self.stats

    def _print_summary(self, total_duration: float):
        """打印更新总结"""
        logger.info('')
        logger.info('*'*60)
        logger.info('更新完成统计')
        logger.info('*'*60)

        for stage, stats in self.stats['stages'].items():
            if stats.get('success', 0) > 0 or stats.get('failed', 0) > 0:
                stage_name = {
                    'etf': 'ETF',
                    'fundamental': '基本面',
                    'stock': '股票'
                }.get(stage, stage)

                duration = stats.get('duration', 0)
                logger.info(f'[{stage_name}]')
                logger.info(f'  成功: {stats["success"]},  失败: {stats["failed"]}')
                logger.info(f'  耗时: {duration:.2f} 秒 ({duration/60:.1f} 分钟)')
                logger.info('')

        logger.info(f'总耗时: {total_duration:.2f} 秒 ({total_duration/60:.1f} 分钟)')
        logger.info('*'*60)
        logger.info('')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='统一数据更新脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                          # 完整更新(所有阶段)
  %(prog)s --stage etf                              # 仅更新ETF
  %(prog)s --stage fundamental                      # 仅更新基本面(最新数据)
  %(prog)s --stage stock                            # 仅更新股票
  %(prog)s --stage etf --stage stock                # 更新ETF和股票,跳过基本面
  %(prog)s --skip-code-check                        # 跳过代码表检查

注意: 基本面数据只更新最新快照,不下载历史数据
      估值因子(PE/PB)主要用于横截面比较,最新数据即可满足需求
        """
    )

    parser.add_argument(
        '--stage',
        action='append',
        choices=['etf', 'fundamental', 'stock'],
        help='指定要执行的阶段(可多次使用)'
    )

    parser.add_argument(
        '--skip-code-check',
        action='store_true',
        help='跳过代码表检查'
    )

    args = parser.parse_args()

    # 创建更新器
    updater = UnifiedUpdater()

    # 执行更新
    stages = args.stage if args.stage else None
    updater.unified_data_update(
        stages=stages,
        skip_code_check=args.skip_code_check
    )


if __name__ == '__main__':
    main()
