#!/usr/bin/env python3
"""
从 strategy/ 目录的所有策略文件中提取 ETF 和股票代码
插入到 DuckDB 的 etf_codes 和 stock_codes 表
"""
import re
import duckdb
from pathlib import Path
from loguru import logger


def is_etf(symbol: str) -> bool:
    """判断是否为 ETF 代码

    ETF 代码特征:
    - 上海 51xxxx, 56xxxx, 58xxxx (科创板ETF)
    - 深圳 159xxx
    """
    code = symbol.split('.')[0]
    return code.startswith('51') or code.startswith('56') or code.startswith('58') or code.startswith('159')


def extract_codes_from_strategies(strategy_dir: Path) -> tuple:
    """从所有策略文件中提取代码

    Returns:
        (all_codes, etf_codes, stock_codes) 三个集合的元组
    """
    all_codes = set()
    etf_codes = set()
    stock_codes = set()

    # 匹配 '123456.SH' 或 "123456.SZ" 格式的代码
    pattern = r"['\"]([\d]{6}\.[A-Z]{2})['\"]"

    for py_file in strategy_dir.glob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            matches = re.findall(pattern, content)
            for match in matches:
                all_codes.add(match)
                if is_etf(match):
                    etf_codes.add(match)
                else:
                    stock_codes.add(match)
        except Exception as e:
            logger.warning(f"读取 {py_file} 失败: {e}")

    return all_codes, etf_codes, stock_codes


def sync_codes():
    """同步代码到数据库"""
    strategy_dir = Path('./strategies')
    db_path = '/data/home/yy/data/duckdb/trading.db'

    logger.info('='*60)
    logger.info('开始同步策略代码到 DuckDB')
    logger.info('='*60)

    # 1. 提取代码
    all_codes, etf_codes, stock_codes = extract_codes_from_strategies(strategy_dir)

    logger.info(f'扫描策略文件: {len(list(strategy_dir.glob("*.py")))} 个')
    logger.info(f'提取唯一代码: {len(all_codes)} 个')
    logger.info(f'  ETF: {len(etf_codes)} 个')
    logger.info(f'  股票: {len(stock_codes)} 个')

    # 2. 连接数据库
    conn = duckdb.connect(db_path)

    # 获取当前最大的 ID 值
    max_etf_id = conn.sql("SELECT COALESCE(MAX(id), 0) as max_id FROM etf_codes").df()['max_id'][0]
    max_stock_id = conn.sql("SELECT COALESCE(MAX(id), 0) as max_id FROM stock_codes").df()['max_id'][0]

    # 3. 插入 ETF 代码
    logger.info('\n插入 ETF 代码...')
    etf_inserted = 0
    etf_skipped = 0
    current_etf_id = max_etf_id + 1

    for symbol in sorted(etf_codes):
        # 检查是否已存在
        exists = conn.sql(f"SELECT COUNT(*) as cnt FROM etf_codes WHERE symbol = '{symbol}'").df()['cnt'][0]
        if exists > 0:
            etf_skipped += 1
            continue

        try:
            conn.sql(f"INSERT INTO etf_codes (id, symbol) VALUES ({current_etf_id}, '{symbol}')")
            etf_inserted += 1
            current_etf_id += 1
        except Exception as e:
            logger.error(f"插入 {symbol} 失败: {e}")

    # 4. 插入股票代码
    logger.info('插入股票代码...')
    stock_inserted = 0
    stock_skipped = 0
    current_stock_id = max_stock_id + 1

    for symbol in sorted(stock_codes):
        # 检查是否已存在
        exists = conn.sql(f"SELECT COUNT(*) as cnt FROM stock_codes WHERE symbol = '{symbol}'").df()['cnt'][0]
        if exists > 0:
            stock_skipped += 1
            continue

        try:
            conn.sql(f"INSERT INTO stock_codes (id, symbol) VALUES ({current_stock_id}, '{symbol}')")
            stock_inserted += 1
            current_stock_id += 1
        except Exception as e:
            logger.error(f"插入 {symbol} 失败: {e}")

    # 5. 统计结果
    etf_count = conn.sql("SELECT COUNT(*) as cnt FROM etf_codes").df()['cnt'][0]
    stock_count = conn.sql("SELECT COUNT(*) as cnt FROM stock_codes").df()['cnt'][0]

    logger.info('\n' + '='*60)
    logger.info('同步完成！')
    logger.info('='*60)
    logger.info(f'etf_codes: {etf_count} 条记录')
    logger.info(f'stock_codes: {stock_count} 条记录')
    logger.info('='*60)

    conn.close()


if __name__ == '__main__':
    sync_codes()
