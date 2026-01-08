#!/usr/bin/env python3
"""
填充股票上市日期

从 AkShare 获取每只股票的上市日期，更新到数据库 stock_metadata 表

使用方法:
    python scripts/populate_list_dates.py

作者: AITrader
日期: 2026-01-06
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import akshare as ak
from loguru import logger
from tqdm import tqdm
from database.pg_manager import get_db
from database.models import StockMetadata


def parse_list_date(date_str: Optional[str]) -> Optional[str]:
    """
    解析上市日期字符串

    Args:
        date_str: 日期字符串，格式可能是 "2020-01-01" 或 "20200101"

    Returns:
        标准格式的日期字符串 "YYYY-MM-DD" 或 None
    """
    if not date_str or date_str == '-' or date_str == '':
        return None

    try:
        # 尝试解析不同格式
        date_str = str(date_str).strip()

        # 如果已经是 YYYY-MM-DD 格式
        if '-' in date_str:
            # 验证是否为有效日期
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str

        # 如果是 YYYYMMDD 格式
        if len(date_str) == 8 and date_str.isdigit():
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            formatted = f"{year}-{month}-{day}"
            # 验证是否为有效日期
            datetime.strptime(formatted, '%Y-%m-%d')
            return formatted

        return None

    except Exception as e:
        logger.debug(f'解析日期失败: {date_str}, 错误: {e}')
        return None


def fetch_list_date_from_akshare(symbol_code: str) -> Optional[str]:
    """
    从 AkShare 获取股票的上市日期

    Args:
        symbol_code: 股票代码 (如 "000001"，不带后缀)

    Returns:
        上市日期字符串 "YYYY-MM-DD" 或 None
    """
    try:
        # 获取个股信息
        info = ak.stock_individual_info_em(symbol=symbol_code)

        if info.empty:
            return None

        # 转换为字典
        info_dict = {}
        for _, row in info.iterrows():
            key = str(row['item']).strip()
            value = row['value']
            info_dict[key] = value

        # 查找"上市日期"字段
        list_date_str = info_dict.get('上市日期')
        return parse_list_date(list_date_str)

    except Exception as e:
        logger.debug(f'获取 {symbol_code} 上市日期失败: {e}')
        return None


def extract_code_from_symbol(symbol: str) -> str:
    """
    从标准股票代码提取原始代码

    Args:
        symbol: 标准格式代码 (如 "000001.SZ")

    Returns:
        原始代码 (如 "000001")
    """
    return symbol.split('.')[0]


def populate_list_dates(batch_size: int = 100, delay: float = 0.1):
    """
    批量填充所有股票的上市日期

    Args:
        batch_size: 批量提交大小
        delay: 请求间隔（秒），避免请求过快被封禁
    """
    db = get_db()

    try:
        # 获取所有股票代码
        with db.get_session() as session:
            # 获取所有 list_date 为 NULL 的股票
            stocks = session.query(StockMetadata.symbol).filter(
                StockMetadata.list_date.is_(None)
            ).all()

            total_stocks = len(stocks)
            logger.info(f'找到 {total_stocks} 只股票需要填充上市日期')

            if total_stocks == 0:
                logger.info('所有股票的上市日期已填充，无需更新')
                return

        # 批量处理
        updated_count = 0
        failed_count = 0
        skipped_count = 0

        with tqdm(total=total_stocks, desc="填充上市日期") as pbar:
            for i in range(0, total_stocks, batch_size):
                batch = stocks[i:i + batch_size]

                for stock in batch:
                    symbol = stock[0]
                    code = extract_code_from_symbol(symbol)

                    # 获取上市日期
                    list_date = fetch_list_date_from_akshare(code)

                    if list_date:
                        # 更新数据库
                        db.update_stock_metadata(symbol, list_date=list_date)
                        updated_count += 1
                        pbar.set_postfix({
                            'updated': updated_count,
                            'failed': failed_count,
                            'skipped': skipped_count
                        })
                    else:
                        if list_date is None:
                            failed_count += 1
                        else:
                            skipped_count += 1

                    pbar.update(1)

                    # 延迟，避免请求过快
                    time.sleep(delay)

        # 输出统计
        logger.info('=' * 60)
        logger.info('上市日期填充完成')
        logger.info(f'  总数: {total_stocks}')
        logger.info(f'  成功: {updated_count}')
        logger.info(f'  失败: {failed_count}')
        logger.info(f'  跳过: {skipped_count}')
        logger.info('=' * 60)

    except Exception as e:
        logger.error(f'填充上市日期失败: {e}')
        import traceback
        traceback.print_exc()


def verify_list_dates():
    """验证上市日期填充结果"""
    db = get_db()

    try:
        with db.get_session() as session:
            total = session.query(StockMetadata).count()
            with_date = session.query(StockMetadata).filter(
                StockMetadata.list_date.isnot(None)
            ).count()
            without_date = total - with_date

            logger.info('=' * 60)
            logger.info('上市日期统计')
            logger.info(f'  总股票数: {total}')
            logger.info(f'  有上市日期: {with_date} ({with_date/total*100:.1f}%)')
            logger.info(f'  缺少日期: {without_date} ({without_date/total*100:.1f}%)')
            logger.info('=' * 60)

            # 显示一些示例
            samples = session.query(StockMetadata).filter(
                StockMetadata.list_date.isnot(None)
            ).limit(5).all()

            if samples:
                logger.info('示例数据:')
                for stock in samples:
                    logger.info(f'  {stock.symbol}: {stock.list_date}')

    except Exception as e:
        logger.error(f'验证失败: {e}')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='填充股票上市日期到数据库',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='批量提交大小 (默认: 100)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0.1,
        help='请求间隔秒数 (默认: 0.1)'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='仅验证，不填充数据'
    )

    args = parser.parse_args()

    if args.verify:
        verify_list_dates()
    else:
        populate_list_dates(batch_size=args.batch_size, delay=args.delay)
        verify_list_dates()
