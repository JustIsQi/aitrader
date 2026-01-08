#!/usr/bin/env python3
"""
补充 stock_metadata 表的 list_date 字段

使用每只股票的最早交易日期作为上市日期

作者: AITrader
日期: 2026-01-06
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.pg_manager import get_db
from database.models import StockHistory, StockMetadata
from sqlalchemy import func
from loguru import logger


def update_list_dates():
    """从 stock_history 表中获取最早日期，更新到 stock_metadata"""
    db = get_db()
    
    with db.get_session() as session:
        # 获取每只股票的最早交易日期
        subquery = session.query(
            StockHistory.symbol,
            func.min(StockHistory.date).label('earliest_date')
        ).group_by(StockHistory.symbol).subquery()
        
        # 统计
        total = 0
        updated = 0
        
        # 逐个更新
        for row in session.query(subquery).all():
            symbol = row.symbol
            earliest_date = row.earliest_date
            
            total += 1
            
            # 查找对应的 metadata 记录
            metadata = session.query(StockMetadata).filter(
                StockMetadata.symbol == symbol
            ).first()
            
            if metadata:
                metadata.list_date = earliest_date
                updated += 1
                
                if updated % 500 == 0:
                    logger.info(f'已更新 {updated}/{total} 只股票')
        
        session.commit()
        logger.success(f'✓ 更新完成: {updated}/{total} 只股票的上市日期')
        
        # 验证
        with_list_date = session.query(StockMetadata).filter(
            StockMetadata.list_date.isnot(None)
        ).count()
        logger.info(f'✓ 现有 list_date 的股票数: {with_list_date}')


if __name__ == '__main__':
    logger.info('='*60)
    logger.info('开始更新股票上市日期')
    logger.info('='*60)
    
    update_list_dates()
    
    logger.info('='*60)
    logger.info('更新完成')
    logger.info('='*60)

