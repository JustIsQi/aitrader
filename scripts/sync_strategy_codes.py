#!/usr/bin/env python3
"""
从 strategies/ 目录的A股策略文件中提取股票代码
插入到当前保留的 stock_codes 表
"""
import re
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from database.db_manager import get_db


def extract_codes_from_strategies(strategy_dir: Path) -> set:
    """从所有策略文件中提取代码

    Returns:
        股票代码集合
    """
    stock_codes = set()

    # 匹配 '123456.SH' 或 "123456.SZ" 格式的代码
    pattern = r"['\"]([\d]{6}\.[A-Z]{2})['\"]"

    for py_file in strategy_dir.glob('stocks_*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            matches = re.findall(pattern, content)
            for match in matches:
                stock_codes.add(match)
        except Exception as e:
            logger.warning(f"读取 {py_file} 失败: {e}")

    return stock_codes


def sync_codes():
    """同步代码到数据库"""
    strategy_dir = Path('./strategies')

    logger.info('='*60)
    logger.info('开始同步A股策略代码')
    logger.info('='*60)

    # 1. 提取代码
    stock_codes = extract_codes_from_strategies(strategy_dir)

    logger.info(f'扫描A股策略文件: {len(list(strategy_dir.glob("stocks_*.py")))} 个')
    logger.info(f'  股票: {len(stock_codes)} 个')

    # 2. 连接数据库
    db = get_db()

    # 3. 插入股票代码
    logger.info('插入股票代码...')
    stock_inserted = 0
    for symbol in sorted(stock_codes):
        try:
            # add_stock_code 内部会检查是否存在
            db.add_stock_code(symbol)
            stock_inserted += 1
        except Exception as e:
            logger.error(f"插入 {symbol} 失败: {e}")

    # 4. 统计结果
    stock_count = len(db.get_stock_codes())

    logger.info('\n' + '='*60)
    logger.info('同步完成！')
    logger.info('='*60)
    logger.info(f'stock_codes: {stock_count} 条记录')
    logger.info('='*60)


if __name__ == '__main__':
    sync_codes()
