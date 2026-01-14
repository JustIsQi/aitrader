"""
智能选股模块 - Smart Stock Filter

功能:
1. 多层级股票筛选 (基础 → 市值 → 流动性 → 技术)
2. 高性能预筛选,大幅减少计算量
3. 可配置的筛选条件
4. 与现有 StockUniverse 和 MultiStrategySignalGenerator 无缝集成

作者: AITrader
日期: 2026-01-07
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from core.stock_universe import StockUniverse
from database.pg_manager import get_db


@dataclass
class FilterConfig:
    """筛选配置"""
    # 基础过滤
    exclude_st: bool = True
    exclude_suspend: bool = True
    exclude_new_ipo_days: int = 60  # 上市60天内
    exclude_restricted_stocks: bool = True  # 排除限制交易股票（科创板、创业板、北交所）

    # 市值筛选
    min_market_cap: Optional[float] = 50  # 最小市值50亿

    # 流动性筛选
    min_turnover_rate: Optional[float] = 1.5  # 最小换手率1.5%
    min_avg_amount: Optional[float] = 5000  # 最小日均成交额5000万
    liquidity_days: int = 20  # 流动性统计天数

    # 目标数量
    target_count: int = 1000  # 目标股票数量

    # 数据配置
    min_data_days: int = 180  # 最小历史数据天数


class SmartStockFilter:
    """
    智能选股器

    核心功能:
    1. 多层级筛选: 基础 → 市值 → 流动性
    2. 性能优化: 快速过滤,减少后续计算量
    3. 灵活配置: 支持不同策略使用不同筛选条件
    """

    def __init__(self, config: FilterConfig = None, db=None):
        """
        初始化智能选股器

        Args:
            config: 筛选配置
            db: 数据库连接
        """
        self.config = config or FilterConfig()
        self.db = db if db else get_db()
        self.universe = StockUniverse(db=self.db)

    def filter_stocks(self,
                      initial_symbols: List[str] = None) -> List[str]:
        """
        执行多层级筛选

        Args:
            initial_symbols: 初始股票列表 (如策略指定的股票池)

        Returns:
            筛选后的股票代码列表
        """
        import time
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"智能选股开始 - 初始股票数: {len(initial_symbols) if initial_symbols else '全市场'}")
        logger.info("=" * 60)

        # 第0层: 基础过滤
        symbols = self._layer0_base_filter(initial_symbols)
        logger.info(f"✓ 第0层(基础过滤): {len(symbols)} 只股票")

        if not symbols:
            logger.warning("基础过滤后无股票")
            return []

        # 第1层: 市值筛选
        symbols = self._layer1_market_cap_filter(symbols)
        logger.info(f"✓ 第1层(市值筛选): {len(symbols)} 只股票")

        if not symbols:
            logger.warning("市值筛选后无股票")
            return []

        # 第2层: 流动性筛选
        symbols = self._layer2_liquidity_filter(symbols)
        logger.info(f"✓ 第2层(流动性筛选): {len(symbols)} 只股票")

        # 最终限制数量
        if len(symbols) > self.config.target_count:
            symbols = self._limit_by_score(symbols)
            logger.info(f"✓ 最终限制: {len(symbols)} 只股票 (目标{self.config.target_count}只)")

        elapsed = time.time() - start_time
        reduction_pct = (1 - len(symbols) / 5298) * 100  # 相对于全市场5298只
        logger.success(f"✓ 筛选完成! 最终: {len(symbols)} 只股票, 减少 {reduction_pct:.1f}%, 耗时 {elapsed:.2f}秒")
        logger.info("=" * 60)

        return symbols

    def _layer0_base_filter(self, initial_symbols: List[str]) -> List[str]:
        """
        第0层: 基础过滤

        过滤条件:
        - ST股票
        - 停牌股票
        - 新上市股票
        - 数据不足股票
        - 限制交易股票（科创板、创业板、北交所）
        """
        # 如果提供了初始股票列表,使用它
        if initial_symbols:
            base_symbols = initial_symbols
        else:
            # 否则从全市场获取
            base_symbols = self.universe.get_all_stocks(
                exclude_st=self.config.exclude_st,
                exclude_suspend=self.config.exclude_suspend,
                min_data_days=self.config.min_data_days,
                exclude_restricted_stocks=self.config.exclude_restricted_stocks
            )

        # 过滤新上市股票
        if self.config.exclude_new_ipo_days > 0:
            base_symbols = self._filter_new_ipos(base_symbols)

        return base_symbols

    def _layer1_market_cap_filter(self, symbols: List[str]) -> List[str]:
        """
        第1层: 市值筛选

        策略: 绝对市值 (如>50亿)
        """
        if not self.config.min_market_cap:
            return symbols

        try:
            filtered = self.universe.filter_by_market_cap(
                symbols,
                min_mv=self.config.min_market_cap
            )
            logger.debug(f"市值筛选(>{self.config.min_market_cap}亿): {len(symbols)} -> {len(filtered)}")
            return filtered
        except Exception as e:
            logger.error(f"市值筛选失败: {e}")
            return symbols

    def _layer2_liquidity_filter(self, symbols: List[str]) -> List[str]:
        """
        第2层: 流动性筛选

        指标:
        - 换手率
        - 日均成交额
        """
        if not self.config.min_turnover_rate and not self.config.min_avg_amount:
            return symbols

        try:
            from datafeed.db_dataloader import DbDataLoader

            # 批量获取历史数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.strptime(end_date, '%Y%m%d') -
                         timedelta(days=self.config.liquidity_days)).strftime('%Y%m%d')

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

    def _filter_new_ipos(self, symbols: List[str]) -> List[str]:
        """过滤新上市股票"""
        try:
            cutoff_date = (datetime.now() -
                          timedelta(days=self.config.exclude_new_ipo_days)).date()

            with self.db.get_session() as session:
                from database.models import StockMetadata

                # 获取股票元数据
                query = session.query(
                    StockMetadata.symbol,
                    StockMetadata.list_date
                ).filter(
                    StockMetadata.symbol.in_(symbols)
                )

                results = query.all()

                # 筛选上市日期早于截止日期的股票
                filtered = []
                for symbol, list_date in results:
                    if list_date is None:
                        # 如果没有上市日期,保留该股票
                        filtered.append(symbol)
                    elif list_date < cutoff_date:
                        filtered.append(symbol)
                    # 否则过滤掉(新上市)

                logger.debug(f"新股过滤: {len(symbols)} -> {len(filtered)}")
                return filtered

        except Exception as e:
            logger.error(f"新股过滤失败: {e}")
            return symbols

    def _limit_by_score(self, symbols: List[str]) -> List[str]:
        """
        按综合评分限制数量

        策略: 按市值排序,选择前N只
        """
        try:
            with self.db.get_session() as session:
                from database.models import StockFundamentalDaily

                # 按市值排序,取前N只
                query = session.query(
                    StockFundamentalDaily.symbol
                ).filter(
                    StockFundamentalDaily.symbol.in_(symbols)
                ).order_by(
                    StockFundamentalDaily.total_mv.desc()
                ).limit(self.config.target_count)

                results = query.all()
                return [r[0] for r in results]

        except Exception as e:
            logger.error(f"数量限制失败: {e}")
            return symbols[:self.config.target_count]


# 预定义配置模板
class FilterPresets:
    """预设筛选配置"""

    @staticmethod
    def conservative() -> FilterConfig:
        """保守型: 大市值 + 高流动性"""
        return FilterConfig(
            exclude_st=True,
            exclude_suspend=True,
            exclude_new_ipo_days=252,  # 1年
            min_market_cap=100,  # 100亿以上
            min_turnover_rate=2.0,
            min_avg_amount=10000,  # 1亿成交额
            target_count=500
        )

    @staticmethod
    def balanced() -> FilterConfig:
        """平衡型: 中等市值 + 适中流动性 (默认)"""
        return FilterConfig(
            exclude_st=True,
            exclude_suspend=True,
            exclude_new_ipo_days=60,
            min_market_cap=50,  # 50亿以上
            min_turnover_rate=1.5,
            min_avg_amount=5000,
            target_count=1000
        )

    @staticmethod
    def aggressive() -> FilterConfig:
        """激进型: 较低市值要求"""
        return FilterConfig(
            exclude_st=True,
            exclude_suspend=True,
            exclude_new_ipo_days=60,
            min_market_cap=30,  # 30亿以上
            min_turnover_rate=1.0,
            min_avg_amount=3000,
            target_count=1500
        )


if __name__ == '__main__':
    """测试代码"""
    logger.info('智能选股模块测试')

    # 测试: 平衡型筛选
    config = FilterPresets.balanced()
    smart_filter = SmartStockFilter(config)

    filtered_stocks = smart_filter.filter_stocks()
    logger.info(f"筛选结果: {len(filtered_stocks)} 只股票")
    if len(filtered_stocks) > 0:
        logger.info(f"前10只: {filtered_stocks[:10]}")
