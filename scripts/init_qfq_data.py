"""
前复权数据初始化脚本
批量下载所有股票/ETF的前复权数据并存储到数据库
"""
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import argparse
import time
from loguru import logger
from database.pg_manager import get_db
from datafeed.downloaders.stock_downloader import StockDownloader
from datafeed.downloaders.etf_downloader import EtfDownloader


def init_stock_qfq_data(symbols=None, limit=None):
    """
    初始化股票前复权数据

    Args:
        symbols: 指定股票列表，None表示全部股票
        limit: 限制下载数量（用于测试）
    """
    db = get_db()
    downloader = StockDownloader()

    # 获取股票列表
    if symbols is None:
        symbols = db.get_stock_codes()
        logger.info(f'获取到 {len(symbols)} 只股票')

    if limit:
        symbols = symbols[:limit]
        logger.info(f'限制下载数量为 {len(symbols)} 只')

    stats = {
        'total': len(symbols),
        'success': 0,
        'failed': 0,
        'skipped': 0
    }

    logger.info(f'开始下载前复权数据，共 {len(symbols)} 只股票')

    for i, symbol in enumerate(symbols, 1):
        try:
            if i % 10 == 0:
                logger.info(f'进度: {i}/{len(symbols)} - 成功: {stats["success"]}, 失败: {stats["failed"]}, 跳过: {stats["skipped"]}')

            # 下载前复权数据
            result = downloader.update_stock_data_qfq(symbol)

            if result:
                stats['success'] += 1
            else:
                stats['failed'] += 1

            # 避免请求过快
            time.sleep(0.5)

        except Exception as e:
            logger.error(f'处理股票 {symbol} 时出错: {e}')
            stats['failed'] += 1
            continue

    logger.success(f'股票前复权数据初始化完成!')
    logger.info(f'总计: {stats["total"]}, 成功: {stats["success"]}, 失败: {stats["failed"]}, 跳过: {stats["skipped"]}')

    return stats


def init_etf_qfq_data(symbols=None, limit=None):
    """
    初始化ETF前复权数据

    Args:
        symbols: 指定ETF列表，None表示全部ETF
        limit: 限制下载数量（用于测试）
    """
    db = get_db()
    downloader = EtfDownloader()

    # 获取ETF列表
    if symbols is None:
        symbols = db.get_etf_codes()
        logger.info(f'获取到 {len(symbols)} 只ETF')

    if limit:
        symbols = symbols[:limit]
        logger.info(f'限制下载数量为 {len(symbols)} 只')

    stats = {
        'total': len(symbols),
        'success': 0,
        'failed': 0,
        'skipped': 0
    }

    logger.info(f'开始下载ETF前复权数据，共 {len(symbols)} 只ETF')

    for i, symbol in enumerate(symbols, 1):
        try:
            if i % 10 == 0:
                logger.info(f'进度: {i}/{len(symbols)} - 成功: {stats["success"]}, 失败: {stats["failed"]}, 跳过: {stats["skipped"]}')

            # 下载前复权数据
            result = downloader.update_etf_data_qfq(symbol)

            if result:
                stats['success'] += 1
            else:
                stats['failed'] += 1

            # 避免请求过快
            time.sleep(0.5)

        except Exception as e:
            logger.error(f'处理ETF {symbol} 时出错: {e}')
            stats['failed'] += 1
            continue

    logger.success(f'ETF前复权数据初始化完成!')
    logger.info(f'总计: {stats["total"]}, 成功: {stats["success"]}, 失败: {stats["failed"]}, 跳过: {stats["skipped"]}')

    return stats


def main():
    parser = argparse.ArgumentParser(description='初始化前复权数据')
    parser.add_argument('--type', choices=['stock', 'etf', 'all'], default='stock',
                       help='数据类型: stock(股票), etf(ETF), all(全部)')
    parser.add_argument('--limit', type=int, default=None,
                       help='限制下载数量（用于测试）')
    parser.add_argument('--symbols', nargs='+', default=None,
                       help='指定股票/ETF代码列表')

    args = parser.parse_args()

    logger.info('========================================')
    logger.info('前复权数据初始化脚本')
    logger.info('========================================')

    if args.type in ['stock', 'all']:
        logger.info('\n开始初始化股票前复权数据...')
        init_stock_qfq_data(symbols=args.symbols, limit=args.limit)

    if args.type in ['etf', 'all']:
        logger.info('\n开始初始化ETF前复权数据...')
        init_etf_qfq_data(symbols=args.symbols, limit=args.limit)

    logger.info('\n========================================')
    logger.info('所有任务完成!')
    logger.info('========================================')


if __name__ == '__main__':
    main()
