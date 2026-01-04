"""
PostgreSQL 数据库初始化脚本
创建所有必要的表结构
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models.base import Base, engine
from database.models import *
from loguru import logger


def init_database():
    """初始化 PostgreSQL 数据库"""
    try:
        logger.info('开始初始化 PostgreSQL 数据库...')

        # 创建所有表
        Base.metadata.create_all(bind=engine)

        logger.info('PostgreSQL 数据库初始化成功！')
        logger.info('已创建以下表:')
        for table_name in Base.metadata.tables.keys():
            logger.info(f'  - {table_name}')

        return True

    except Exception as e:
        logger.error(f'数据库初始化失败: {e}')
        return False


def drop_all_tables():
    """删除所有表 (慎用!)"""
    try:
        logger.warning('正在删除所有数据库表...')
        Base.metadata.drop_all(bind=engine)
        logger.info('所有表已删除')
        return True
    except Exception as e:
        logger.error(f'删除表失败: {e}')
        return False


def reset_database():
    """重置数据库 (删除所有表并重新创建)"""
    try:
        logger.warning('正在重置数据库...')
        drop_all_tables()
        init_database()
        logger.info('数据库重置完成')
        return True
    except Exception as e:
        logger.error(f'重置数据库失败: {e}')
        return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'init':
            init_database()
        elif command == 'drop':
            drop_all_tables()
        elif command == 'reset':
            reset_database()
        else:
            print('Usage: python init_postgres_db.py [init|drop|reset]')
            print('  init  - 创建所有表')
            print('  drop  - 删除所有表')
            print('  reset - 重置数据库 (删除并重新创建)')
    else:
        # 默认执行初始化
        init_database()
