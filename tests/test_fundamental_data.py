"""
基本面数据系统单元测试
测试数据库操作、因子计算等功能

作者: AITrader
日期: 2025-12-29
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from database.pg_manager import get_db
from datafeed.factor_fundamental import (
    pe_score, pb_score, ps_score,
    roe_score, roa_score, profit_margin_score,
    total_mv_filter, market_cap_category,
    quality_score, value_score, fundamental_rank_score
)


class TestDatabaseOperations(unittest.TestCase):
    """测试数据库操作"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.db = get_db(':memory:')  # 使用内存数据库测试

    def test_stock_metadata_crud(self):
        """测试股票元数据CRUD操作"""
        # 插入元数据
        self.db.upsert_stock_metadata(
            symbol='000001.SZ',
            name='平安银行',
            sector='金融',
            industry='银行',
            list_date='1991-04-03',
            is_st=False
        )

        # 查询元数据
        metadata = self.db.get_stock_metadata('000001.SZ')
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['name'], '平安银行')
        self.assertEqual(metadata['sector'], '金融')
        self.assertFalse(metadata['is_st'])

    def test_fundamental_daily_crud(self):
        """测试基本面数据CRUD操作"""
        # 插入基本面数据
        self.db.upsert_fundamental_daily(
            symbol='000001.SZ',
            date='2025-12-29',
            pe_ratio=5.2,
            pb_ratio=0.8,
            roe=0.12,
            total_mv=250.5
        )

        # 查询基本面数据
        fundamental = self.db.get_latest_fundamental('000001.SZ')
        self.assertIsNotNone(fundamental)
        self.assertEqual(fundamental['pe_ratio'], 5.2)
        self.assertEqual(fundamental['pb_ratio'], 0.8)
        self.assertEqual(fundamental['roe'], 0.12)

    def test_factor_cache(self):
        """测试因子缓存"""
        # 缓存因子
        self.db.cache_factor('000001.SZ', '2025-12-29', 'quality_score', 0.75)

        # 获取缓存
        cached = self.db.get_cached_factor('000001.SZ', '2025-12-29', 'quality_score')
        self.assertEqual(cached, 0.75)


class TestFundamentalFactors(unittest.TestCase):
    """测试基本面因子计算"""

    def test_pe_score(self):
        """测试PE评分"""
        pe = pd.Series([10, 20, 30, 40, 50])
        scores = pe_score(pe)

        # PE越低分数越高
        self.assertTrue(scores.iloc[0] > scores.iloc[4])

    def test_pb_score(self):
        """测试PB评分"""
        pb = pd.Series([1, 2, 3, 4, 5])
        scores = pb_score(pb)

        # PB越低分数越高
        self.assertTrue(scores.iloc[0] > scores.iloc[4])

    def test_roe_score(self):
        """测试ROE评分"""
        roe = pd.Series([0.05, 0.10, 0.15, 0.20, 0.25])
        scores = roe_score(roe)

        # ROE越高分数越高
        self.assertTrue(scores.iloc[4] > scores.iloc[0])

    def test_total_mv_filter(self):
        """测试市值过滤"""
        mv = pd.Series([20, 60, 200, 600])
        mask = total_mv_filter(mv, min_mv=50, max_mv=200)

        # 只有60和200符合条件
        self.assertEqual(mask.sum(), 2)

    def test_market_cap_category(self):
        """测试市值分类"""
        mv = pd.Series([20, 60, 200, 600])
        category = market_cap_category(mv)

        self.assertEqual(category.iloc[0], '小盘')
        self.assertEqual(category.iloc[1], '中盘')
        self.assertEqual(category.iloc[2], '大盘')
        self.assertEqual(category.iloc[3], '大盘')

    def test_quality_score(self):
        """测试综合质量评分"""
        pe = pd.Series([10, 20, 30])
        pb = pd.Series([1, 2, 3])
        roe = pd.Series([0.10, 0.15, 0.20])

        scores = quality_score(pe, pb, roe)

        # 分数应该在0-1之间
        self.assertTrue((scores >= 0).all())
        self.assertTrue((scores <= 1).all())

    def test_value_score(self):
        """测试价值评分"""
        pe = pd.Series([10, 20, 30])
        pb = pd.Series([1, 2, 3])
        ps = pd.Series([2, 4, 6])

        scores = value_score(pe, pb, ps)

        # 分数应该在0-1之间
        self.assertTrue((scores >= 0).all())

    def test_fundamental_rank_score(self):
        """测试多因子排名评分"""
        pe = pd.Series([10, 20, 30])
        roe = pd.Series([0.10, 0.15, 0.20])

        scores = fundamental_rank_score(pe=pe, roe=roe)

        # 分数应该在0-1之间
        self.assertTrue((scores >= 0).all())
        self.assertTrue((scores <= 1).all())


class TestIntegration(unittest.TestCase):
    """集成测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.db = get_db(':memory:')

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 插入元数据
        self.db.upsert_stock_metadata(
            symbol='600000.SH',
            name='浦发银行',
            is_st=False
        )

        # 2. 插入基本面数据
        self.db.upsert_fundamental_daily(
            symbol='600000.SH',
            date='2025-12-29',
            pe_ratio=5.5,
            pb_ratio=0.7,
            roe=0.13,
            total_mv=200.0
        )

        # 3. 读取数据
        metadata = self.db.get_stock_metadata('600000.SH')
        fundamental = self.db.get_latest_fundamental('600000.SH')

        # 4. 计算因子
        pe_score_val = pe_score(pd.Series([fundamental['pe_ratio']])).iloc[0]
        quality_score_val = quality_score(
            pd.Series([fundamental['pe_ratio']]),
            pd.Series([fundamental['pb_ratio']]),
            pd.Series([fundamental['roe']])
        ).iloc[0]

        # 验证
        self.assertIsNotNone(metadata)
        self.assertIsNotNone(fundamental)
        self.assertGreater(pe_score_val, 0)
        self.assertGreater(quality_score_val, 0)


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("基本面数据系统单元测试")
    print("=" * 60)
    print()

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseOperations))
    suite.addTests(loader.loadTestsFromTestCase(TestFundamentalFactors))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    print(f"测试完成: {result.testsRun}个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
