#!/usr/bin/env python3
"""
回填ETF名称到历史数据表
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from database.pg_manager import get_db
from database.models import EtfCode
from sqlalchemy import text


def backfill_etf_names():
    """回填ETF名称到历史数据表"""
    db = get_db()

    # 获取所有ETF及其名称
    with db.get_session() as session:
        etf_names = session.query(EtfCode.symbol, EtfCode.name).filter(
            EtfCode.name.isnot(None)
        ).all()
        name_map = {symbol: name for symbol, name in etf_names}

    logger.info(f'找到 {len(name_map)} 个有名称的ETF')

    if not name_map:
        logger.warning('没有找到任何ETF名称，请先运行数据下载器更新名称')
        return

    # 更新 etf_history
    logger.info('开始更新 etf_history 表...')
    updated_count = 0
    with db.get_session() as session:
        for symbol, name in name_map.items():
            result = session.execute(text("""
                UPDATE etf_history
                SET name = :name
                WHERE symbol = :symbol AND (name IS NULL OR name = '')
            """), {'name': name, 'symbol': symbol})
            updated_count += result.rowcount

    logger.info(f'已更新 etf_history 表: {updated_count} 条记录')

    # 更新 etf_history_qfq
    logger.info('开始更新 etf_history_qfq 表...')
    updated_count_qfq = 0
    with db.get_session() as session:
        for symbol, name in name_map.items():
            result = session.execute(text("""
                UPDATE etf_history_qfq
                SET name = :name
                WHERE symbol = :symbol AND (name IS NULL OR name = '')
            """), {'name': name, 'symbol': symbol})
            updated_count_qfq += result.rowcount

    logger.info(f'已更新 etf_history_qfq 表: {updated_count_qfq} 条记录')
    logger.info('回填完成!')


if __name__ == '__main__':
    try:
        backfill_etf_names()
    except Exception as e:
        logger.exception(f"回填失败: {e}")
        sys.exit(1)
