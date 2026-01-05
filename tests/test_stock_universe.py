"""
测试股票池管理器

验证股票池筛选功能的正确性
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from core.stock_universe import StockUniverse


def test_get_all_stocks():
    """测试获取所有可交易股票"""
    logger.info('\n' + '='*60)
    logger.info('测试1: 获取所有可交易股票')
    logger.info('='*60)

    universe = StockUniverse()

    # 测试1.1: 获取所有股票（包括ST）
    logger.info('\n1.1 获取所有股票（包括ST）')
    stocks_with_st = universe.get_all_stocks(exclude_st=False)
    logger.info(f'  股票数量: {len(stocks_with_st)}')
    logger.info(f'  前5只: {stocks_with_st[:5]}')

    # 测试1.2: 排除ST股票
    logger.info('\n1.2 排除ST股票')
    stocks_without_st = universe.get_all_stocks(exclude_st=True)
    logger.info(f'  股票数量: {len(stocks_without_st)}')
    logger.info(f'  前5只: {stocks_without_st[:5]}')

    # 测试1.3: 排除ST和停牌
    logger.info('\n1.3 排除ST和停牌股票')
    stocks_filtered = universe.get_all_stocks(
        exclude_st=True,
        exclude_suspend=True
    )
    logger.info(f'  股票数量: {len(stocks_filtered)}')
    logger.info(f'  前5只: {stocks_filtered[:5]}')

    logger.info('✅ 测试通过')
    return True


def test_filter_by_market_cap():
    """测试市值筛选"""
    logger.info('\n' + '='*60)
    logger.info('测试2: 市值筛选')
    logger.info('='*60)

    universe = StockUniverse()

    # 先获取基础股票列表
    all_stocks = universe.get_all_stocks()
    logger.info(f'\n基础股票: {len(all_stocks)} 只')

    # 测试2.1: 大盘股（市值>100亿）
    logger.info('\n2.1 筛选大盘股（市值>100亿）')
    large_caps = universe.filter_by_market_cap(all_stocks, min_mv=100)
    logger.info(f'  大盘股: {len(large_caps)} 只')
    logger.info(f'  前5只: {large_caps[:5]}')

    # 测试2.2: 中盘股（50-200亿）
    logger.info('\n2.2 筛选中盘股（50-200亿）')
    mid_caps = universe.filter_by_market_cap(all_stocks, min_mv=50, max_mv=200)
    logger.info(f'  中盘股: {len(mid_caps)} 只')
    logger.info(f'  前5只: {mid_caps[:5]}')

    # 测试2.3: 小盘股（<50亿）
    logger.info('\n2.3 筛选小盘股（<50亿）')
    small_caps = universe.filter_by_market_cap(all_stocks, max_mv=50)
    logger.info(f'  小盘股: {len(small_caps)} 只')
    logger.info(f'  前5只: {small_caps[:5]}')

    logger.info('✅ 测试通过')
    return True


def test_filter_by_fundamental():
    """测试基本面筛选"""
    logger.info('\n' + '='*60)
    logger.info('测试3: 基本面筛选')
    logger.info('='*60)

    universe = StockUniverse()

    # 先获取基础股票列表
    all_stocks = universe.get_all_stocks()
    logger.info(f'\n基础股票: {len(all_stocks)} 只')

    # 测试3.1: 低PE筛选（PE<20）
    logger.info('\n3.1 筛选低PE股票（PE<20）')
    low_pe = universe.filter_by_fundamental(all_stocks, max_pe=20)
    logger.info(f'  低PE股票: {len(low_pe)} 只')
    logger.info(f'  前5只: {low_pe[:5]}')

    # 测试3.2: 高ROE筛选（ROE>0.10）
    logger.info('\n3.2 筛选高ROE股票（ROE>10%）')
    high_roe = universe.filter_by_fundamental(all_stocks, min_roe=0.10)
    logger.info(f'  高ROE股票: {len(high_roe)} 只')
    logger.info(f'  前5只: {high_roe[:5]}')

    # 测试3.3: 综合筛选（低PE + 高ROE）
    logger.info('\n3.3 综合筛选（PE<30 且 ROE>0.08）')
    quality = universe.filter_by_fundamental(
        all_stocks,
        max_pe=30,
        min_roe=0.08
    )
    logger.info(f'  质量股票: {len(quality)} 只')
    logger.info(f'  前5只: {quality[:5]}')

    logger.info('✅ 测试通过')
    return True


def test_filter_by_industry():
    """测试行业筛选"""
    logger.info('\n' + '='*60)
    logger.info('测试4: 行业筛选')
    logger.info('='*60)

    universe = StockUniverse()

    # 先获取基础股票列表
    all_stocks = universe.get_all_stocks()
    logger.info(f'\n基础股票: {len(all_stocks)} 只')

    # 测试4.1: 金融行业
    logger.info('\n4.1 筛选金融行业')
    financial = universe.filter_by_industry(all_stocks, sectors=['金融'])
    logger.info(f'  金融股: {len(financial)} 只')
    logger.info(f'  前5只: {financial[:5]}')

    # 测试4.2: 多个行业
    logger.info('\n4.2 筛选多个行业')
    multi_industry = universe.filter_by_industry(
        all_stocks,
        industries=['银行', '证券']
    )
    logger.info(f'  银行+证券: {len(multi_industry)} 只')
    logger.info(f'  前5只: {multi_industry[:5]}')

    logger.info('✅ 测试通过')
    return True


def test_get_stock_pool():
    """测试综合筛选"""
    logger.info('\n' + '='*60)
    logger.info('测试5: 综合筛选')
    logger.info('='*60)

    universe = StockUniverse()

    # 测试5.1: 大盘优质股
    logger.info('\n5.1 筛选大盘优质股')
    pool1 = universe.get_stock_pool(filters={
        'min_market_cap': 100,
        'max_pe': 30,
        'min_roe': 0.10,
        'exclude_st': True
    })
    logger.info(f'  股票池: {len(pool1)} 只')
    logger.info(f'  前5只: {pool1[:5]}')

    # 测试5.2: 价值股
    logger.info('\n5.2 筛选价值股（低估值）')
    pool2 = universe.get_stock_pool(filters={
        'min_market_cap': 50,
        'max_pe': 15,
        'max_pb': 2,
        'exclude_st': True
    })
    logger.info(f'  股票池: {len(pool2)} 只')
    logger.info(f'  前5只: {pool2[:5]}')

    # 测试5.3: 成长股
    logger.info('\n5.3 筛选成长股（高ROE）')
    pool3 = universe.get_stock_pool(filters={
        'min_market_cap': 50,
        'min_roe': 0.15,
        'exclude_st': True
    })
    logger.info(f'  股票池: {len(pool3)} 只')
    logger.info(f'  前5只: {pool3[:5]}')

    logger.info('✅ 测试通过')
    return True


def test_get_universe_stats():
    """测试统计信息"""
    logger.info('\n' + '='*60)
    logger.info('测试6: 统计信息')
    logger.info('='*60)

    universe = StockUniverse()

    # 获取一个股票池
    stocks = universe.get_stock_pool(filters={
        'min_market_cap': 100
    })

    if not stocks:
        logger.warning('没有找到符合条件的股票，跳过统计测试')
        return True

    logger.info(f'\n股票池: {len(stocks)} 只')

    # 只统计前100只，避免太慢
    stats = universe.get_universe_stats(stocks[:100])

    logger.info('\n统计信息:')
    logger.info(f'  总数: {stats.get("total_count", 0)}')
    logger.info(f'  板块分布: {stats.get("sectors", {})}')
    logger.info(f'  行业分布: {stats.get("industries", {})}')
    logger.info(f'  市值: {stats.get("market_cap", {})}')
    logger.info(f'  基本面: {stats.get("fundamental", {})}')

    logger.info('✅ 测试通过')
    return True


def test_usage_in_strategy():
    """测试在策略中使用"""
    logger.info('\n' + '='*60)
    logger.info('测试7: 策略使用示例')
    logger.info('='*60)

    logger.info('\n模拟策略使用场景:')

    logger.info('\n场景1: 价值选股策略')
    universe = StockUniverse()
    t_symbols = universe.get_stock_pool(filters={
        'min_market_cap': 50,
        'max_pe': 20,
        'min_roe': 0.12,
        'exclude_st': True
    })
    logger.info(f'  策略股票池: {len(t_symbols)} 只')
    logger.info(f'  示例: {t_symbols[:5]}')

    logger.info('\n场景2: 大盘蓝筹策略')
    blue_chips = universe.get_stock_pool(filters={
        'min_market_cap': 200,
        'sectors': ['金融'],
        'exclude_st': True
    })
    logger.info(f'  蓝筹股票池: {len(blue_chips)} 只')
    logger.info(f'  示例: {blue_chips[:5]}')

    logger.info('✅ 测试通过')
    return True


def run_all_tests():
    """运行所有测试"""
    logger.info('\n')
    logger.info('╔' + '═'*58 + '╗')
    logger.info('║' + ' '*15 + '股票池管理器测试' + ' '*31 + '║')
    logger.info('╚' + '═'*58 + '╝')

    tests = [
        ('获取所有可交易股票', test_get_all_stocks),
        ('市值筛选', test_filter_by_market_cap),
        ('基本面筛选', test_filter_by_fundamental),
        ('行业筛选', test_filter_by_industry),
        ('综合筛选', test_get_stock_pool),
        ('统计信息', test_get_universe_stats),
        ('策略使用', test_usage_in_strategy),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            logger.error(f'❌ {name} 测试失败: {e}')

    # 总结
    logger.info('\n' + '='*60)
    logger.info('测试总结')
    logger.info('='*60)
    logger.info(f'通过: {passed}/{len(tests)}')
    logger.info(f'失败: {failed}/{len(tests)}')

    if failed == 0:
        logger.info('\n🎉 所有测试通过!')
    else:
        logger.info(f'\n⚠️  有 {failed} 个测试失败')

    logger.info('='*60 + '\n')

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
