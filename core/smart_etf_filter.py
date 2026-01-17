"""
智能ETF筛选模块 - Smart ETF Filter

功能:
1. 多层级ETF筛选 (基础 → 流动性 → 数量限制)
2. 高性能预筛选,大幅减少计算量
3. 可配置的筛选条件
4. 与ETF信号生成器无缝集成

作者: AITrader
日期: 2026-01-16
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.etf_universe import EtfUniverse
from database.pg_manager import get_db


@dataclass
class EtfFilterConfig:
    """ETF筛选配置"""
    # 流动性筛选
    min_avg_amount: float = 5000  # 最小日均成交额(万元)
    min_turnover_rate: float = 1.5  # 最小换手率(%)
    liquidity_days: int = 20  # 流动性统计天数

    # 数据质量
    min_data_days: int = 180  # 最小历史数据天数

    # 目标数量
    target_count: int = 100  # 目标ETF数量


class SmartETFFilter:
    """
    智能ETF筛选器

    核心功能:
    1. 多层级筛选: 基础 → 流动性 → 数量限制
    2. 性能优化: 快速过滤,减少后续计算量
    3. 灵活配置: 支持不同策略使用不同筛选条件
    """

    def __init__(self, config: EtfFilterConfig = None, db=None):
        """
        初始化智能ETF筛选器

        Args:
            config: 筛选配置
            db: 数据库连接
        """
        self.config = config or EtfFilterConfig()
        self.db = db if db else get_db()
        self.universe = EtfUniverse(db=self.db)

    def filter_etfs(self,
                   initial_symbols: List[str] = None) -> List[str]:
        """
        执行多层级筛选

        Args:
            initial_symbols: 初始ETF列表 (如策略指定的ETF池,为None则使用全部)

        Returns:
            筛选后的ETF代码列表
        """
        import time
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"智能ETF筛选开始 - 初始ETF数: {len(initial_symbols) if initial_symbols else '全市场'}")
        logger.info("=" * 60)

        # 第0层: 基础过滤 (数据可用性)
        symbols = self._layer0_base_filter(initial_symbols)
        logger.info(f"✓ 第0层(基础过滤): {len(symbols)} 只ETF")

        if not symbols:
            logger.warning("基础过滤后无ETF")
            return []

        # 第1层: 流动性筛选
        symbols = self._layer1_liquidity_filter(symbols)
        logger.info(f"✓ 第1层(流动性筛选): {len(symbols)} 只ETF")

        if not symbols:
            logger.warning("流动性筛选后无ETF")
            return []

        # 最终限制数量
        if len(symbols) > self.config.target_count:
            symbols = self._limit_by_amount(symbols)
            logger.info(f"✓ 最终限制: {len(symbols)} 只ETF (目标{self.config.target_count}只)")
        else:
            logger.info(f"✓ 筛选完成: {len(symbols)} 只ETF (无需限制)")

        elapsed = time.time() - start_time
        logger.success(f"✓ 筛选完成! 最终: {len(symbols)} 只ETF, 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return symbols

    def _layer0_base_filter(self, initial_symbols: List[str]) -> List[str]:
        """
        第0层: 基础过滤

        过滤条件:
        - 数据充足 (至少min_data_days天历史数据)
        """
        # 如果提供了初始ETF列表,需要验证数据可用性
        if initial_symbols:
            # 验证这些ETF是否有足够数据
            all_etfs = self.universe.get_all_etfs(min_data_days=self.config.min_data_days)
            # 取交集: 初始列表 ∩ 有足够数据的ETF
            base_symbols = list(set(initial_symbols) & set(all_etfs))
            logger.debug(f"基础过滤(数据可用性): {len(initial_symbols)} -> {len(base_symbols)}")
            return base_symbols
        else:
            # 使用全市场ETF
            base_symbols = self.universe.get_all_etfs(
                min_data_days=self.config.min_data_days
            )
            return base_symbols

    def _layer1_liquidity_filter(self, symbols: List[str]) -> List[str]:
        """
        第1层: 流动性筛选

        指标:
        - 成交额 (amount)
        - 换手率 (turnover_rate)
        """
        if not self.config.min_avg_amount and not self.config.min_turnover_rate:
            return symbols

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=self.config.liquidity_days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载流动性数据")
                return symbols

            # 计算流动性指标
            qualified = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty:
                    continue

                passed = True

                # 检查换手率
                if self.config.min_turnover_rate and 'turnover_rate' in df.columns:
                    recent_turnover = df['turnover_rate'].tail(self.config.liquidity_days)
                    if recent_turnover.mean() < self.config.min_turnover_rate:
                        passed = False

                # 检查成交额
                if self.config.min_avg_amount and 'amount' in df.columns:
                    recent_amount = df['amount'].tail(self.config.liquidity_days)
                    if recent_amount.mean() < self.config.min_avg_amount:
                        passed = False

                if passed:
                    qualified.append(symbol)

            logger.debug(f"流动性筛选: {len(symbols)} -> {len(qualified)}")
            return qualified

        except Exception as e:
            logger.error(f"流动性筛选失败: {e}")
            return symbols

    def _limit_by_amount(self, symbols: List[str]) -> List[str]:
        """
        按成交额限制数量

        策略: 按成交额排序,选择前N只
        """
        try:
            from datafeed.db_dataloader import DbDataLoader

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=self.config.liquidity_days)).strftime('%Y%m%d')

            # 批量获取历史数据
            loader = DbDataLoader(auto_download=False)
            dfs = loader.read_dfs(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date
            )

            if not dfs:
                logger.warning("未能加载成交额数据,返回前{self.config.target_count}只")
                return symbols[:self.config.target_count]

            # 计算每个ETF的平均成交额并排序
            etf_amounts = []
            for symbol in symbols:
                if symbol not in dfs:
                    continue

                df = dfs[symbol]
                if df.empty or 'amount' not in df.columns:
                    continue

                # 计算平均成交额
                recent_amount = df['amount'].tail(self.config.liquidity_days)
                avg_amount = recent_amount.mean()

                if pd.notna(avg_amount):
                    etf_amounts.append((symbol, avg_amount))

            # 按成交额降序排序
            etf_amounts.sort(key=lambda x: x[1], reverse=True)

            # 取前N只
            result = [item[0] for item in etf_amounts[:self.config.target_count]]

            logger.debug(f"按成交额限制数量: {len(symbols)} -> {len(result)} (前{self.config.target_count}只)")
            return result

        except Exception as e:
            logger.error(f"数量限制失败: {e}")
            return symbols[:self.config.target_count]


# 预定义配置模板
class EtfFilterPresets:
    """预设ETF筛选配置"""

    @staticmethod
    def conservative() -> EtfFilterConfig:
        """保守型: 高流动性大ETF"""
        return EtfFilterConfig(
            min_avg_amount=10000,  # 1亿成交额
            min_turnover_rate=2.0,
            min_data_days=252,  # 1年数据
            liquidity_days=20,
            target_count=50
        )

    @staticmethod
    def balanced() -> EtfFilterConfig:
        """平衡型: 适中流动性 (默认)"""
        return EtfFilterConfig(
            min_avg_amount=5000,  # 5000万成交额
            min_turnover_rate=1.5,
            min_data_days=180,  # 半年数据
            liquidity_days=20,
            target_count=100
        )

    @staticmethod
    def aggressive() -> EtfFilterConfig:
        """激进型: 包含小ETF"""
        return EtfFilterConfig(
            min_avg_amount=3000,
            min_turnover_rate=1.0,
            min_data_days=180,
            liquidity_days=20,
            target_count=150
        )


if __name__ == '__main__':
    """测试代码"""
    logger.info('智能ETF筛选模块测试')

    # 测试: 平衡型筛选
    config = EtfFilterPresets.balanced()
    smart_filter = SmartETFFilter(config)

    filtered_etfs = smart_filter.filter_etfs()
    logger.info(f"筛选结果: {len(filtered_etfs)} 只ETF")
    if len(filtered_etfs) > 0:
        logger.info(f"前10只: {filtered_etfs[:10]}")
