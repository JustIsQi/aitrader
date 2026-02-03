"""
填充股票板块信息到数据库

从 akshare 获取行业板块成分股，更新到 StockMetadata 表的 sector 字段

作者: AITrader
日期: 2026-01-21
"""

import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import akshare as ak
from database.pg_manager import get_db
from database.models.models import StockMetadata
from tqdm import tqdm


def fill_stock_sectors():
    """填充股票板块信息"""
    logger.info("开始填充股票板块信息...")

    db = get_db()

    # 1. 获取所有行业板块列表
    logger.info("正在获取行业板块列表...")
    try:
        sectors_df = ak.stock_board_industry_name_em()
        sector_names = sectors_df['板块名称'].tolist()
        logger.info(f"✓ 获取到 {len(sector_names)} 个行业板块")
    except Exception as e:
        logger.error(f"获取板块列表失败: {e}")
        return

    # 2. 遍历每个板块，获取成分股
    stock_to_sector = {}  # {股票代码: 板块名称}

    logger.info("正在获取各板块成分股...")
    for sector_name in tqdm(sector_names, desc="获取板块成分股"):
        try:
            # 获取板块成分股
            df = ak.stock_board_industry_cons_em(symbol=sector_name)

            if df.empty:
                continue

            # 提取股票代码
            stock_codes = df['代码'].tolist()

            # 建立映射
            for code in stock_codes:
                # 如果一只股票属于多个板块，保留第一个
                if code not in stock_to_sector:
                    stock_to_sector[code] = sector_name

        except Exception as e:
            logger.warning(f"获取板块 {sector_name} 成分股失败: {e}")
            continue

    logger.info(f"✓ 共获取到 {len(stock_to_sector)} 只股票的板块信息")

    # 3. 更新数据库
    logger.info("正在更新数据库...")
    updated_count = 0
    failed_count = 0

    with db.get_session() as session:
        # 获取所有股票
        all_stocks = session.query(StockMetadata).all()

        for stock in tqdm(all_stocks, desc="更新数据库"):
            # 提取股票代码（可能带后缀）
            code = stock.symbol

            # 尝试匹配
            sector = stock_to_sector.get(code)

            if sector:
                stock.sector = sector
                updated_count += 1
            else:
                # 尝试不带后缀的代码
                code_without_suffix = code.split('.')[0]
                sector = stock_to_sector.get(code_without_suffix)
                if sector:
                    stock.sector = sector
                    updated_count += 1
                else:
                    failed_count += 1

        # 提交更改
        session.commit()

    logger.info(f"✓ 更新完成: 成功 {updated_count} 只, 失败 {failed_count} 只")

    # 4. 验证结果
    logger.info("正在验证结果...")
    with db.get_session() as session:
        total = session.query(StockMetadata).count()
        with_sector = session.query(StockMetadata).filter(
            StockMetadata.sector.isnot(None)
        ).count()

        # 各板块股票数量
        sector_counts = session.query(
            StockMetadata.sector,
            func.count(StockMetadata.symbol)
        ).filter(
            StockMetadata.sector.isnot(None)
        ).group_by(StockMetadata.sector).order_by(
            func.count(StockMetadata.symbol).desc()
        ).all()

        logger.info(f"总股票数: {total}")
        logger.info(f"有板块信息的股票数: {with_sector} ({with_sector/total*100:.1f}%)")

        logger.info(f"\n各板块股票数量 (前10个):")
        for sector, count in sector_counts[:10]:
            logger.info(f"  {sector}: {count} 只")

    logger.info("✓ 填充完成!")


if __name__ == '__main__':
    from sqlalchemy import func

    # 配置日志
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=''),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>\n"
    )

    fill_stock_sectors()
