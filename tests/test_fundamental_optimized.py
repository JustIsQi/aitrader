"""
基本面数据下载优化模块测试
"""
import time
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datafeed.downloaders.rate_limiter import RateLimiter
from datafeed.downloaders.retry import retry_on_failure
from database.pg_manager import get_db
from loguru import logger


def test_rate_limiter():
    """测试限流器功能"""
    logger.info('=' * 60)
    logger.info('测试限流器')
    logger.info('=' * 60)

    limiter = RateLimiter(max_requests_per_second=10)

    start = time.time()
    for i in range(10):
        limiter.acquire()
        logger.debug(f'第 {i+1} 次请求')

    elapsed = time.time() - start

    logger.info(f'10 次请求耗时: {elapsed:.2f} 秒')
    assert 0.9 <= elapsed <= 1.2, f'期望 0.9-1.2 秒，实际 {elapsed:.2f} 秒'
    logger.info('✓ 限流器测试通过')
    logger.info('')


def test_retry_decorator():
    """测试重试装饰器"""
    logger.info('=' * 60)
    logger.info('测试重试装饰器')
    logger.info('=' * 60)

    call_count = 0

    @retry_on_failure(max_retries=3, delay=0.1)
    def failing_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("模拟失败")
        return "成功"

    result = failing_func()
    assert result == "成功", f'期望 "成功"，实际 {result}'
    assert call_count == 3, f'期望调用 3 次，实际 {call_count} 次'

    logger.info(f'函数在第 {call_count} 次尝试后成功')
    logger.info('✓ 重试装饰器测试通过')
    logger.info('')


def test_get_latest_date():
    """测试查询最新日期"""
    logger.info('=' * 60)
    logger.info('测试数据库查询方法')
    logger.info('=' * 60)

    try:
        db = get_db()
        latest = db.get_stock_latest_fundamental_date('000001.SZ')

        if latest:
            logger.info(f'000001.SZ 最新数据日期: {latest}')
        else:
            logger.info('000001.SZ 暂无基本面数据')

        assert latest is None or hasattr(latest, 'strftime'), '返回值应该是 date 对象或 None'
        logger.info('✓ 数据库查询方法测试通过')
        logger.info('')
    except Exception as e:
        logger.error(f'数据库查询测试失败: {e}')
        raise


def test_integration_small_scale():
    """小规模集成测试 - 下载少量股票验证功能"""
    logger.info('=' * 60)
    logger.info('小规模集成测试')
    logger.info('=' * 60)

    try:
        from datafeed.downloaders.fundamental_downloader import FundamentalDownloader
        import pandas as pd

        downloader = FundamentalDownloader()

        # 创建小规模测试数据（3只股票）
        test_stocks = pd.DataFrame([
            {'symbol': '000001.SZ', '代码': '000001', '名称': '平安银行'},
            {'symbol': '000002.SZ', '代码': '000002', '名称': '万科A'},
            {'symbol': '600000.SH', '代码': '600000', '名称': '浦发银行'},
        ])

        logger.info(f'测试股票: {test_stocks["名称"].tolist()}')
        logger.info('下载历史数据（近3个月）...')

        # 下载近3个月的数据
        start_time = time.time()
        downloader._download_historical_fundamental(
            stock_list=test_stocks,
            years=0.25,  # 约3个月
            batch_size=3
        )
        elapsed = time.time() - start_time

        logger.info(f'耗时: {elapsed:.2f} 秒')
        logger.info('✓ 小规模集成测试通过')
        logger.info('')

    except Exception as e:
        logger.error(f'集成测试失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        raise


def main():
    """运行所有测试"""
    logger.info('')
    logger.info('*' * 60)
    logger.info('基本面数据下载优化模块测试')
    logger.info('*' * 60)
    logger.info('')

    # 1. 测试限流器
    test_rate_limiter()

    # 2. 测试重试装饰器
    test_retry_decorator()

    # 3. 测试数据库查询
    test_get_latest_date()

    # 4. 小规模集成测试（可选，需要数据库连接）
    # 取消注释以运行
    # test_integration_small_scale()

    logger.info('=' * 60)
    logger.info('所有测试通过!')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
