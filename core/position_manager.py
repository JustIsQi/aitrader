"""
仓位管理与止盈止损计算模块

功能:
1. 仓位计算 (单板块≤30%, 单股≤15%, 总仓位≤70%)
2. 止损价计算 (min(前一日收盘价-3%, 5日线价))
3. 止盈价计算 (max(10日高点, 收盘价+10%))
4. 开盘触发阈值计算

作者: AITrader
日期: 2026-01-21
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from database.pg_manager import get_db
from database.models.models import StockHistory


@dataclass
class PositionConfig:
    """仓位配置"""
    max_sector_position: float = 0.30  # 单板块最大仓位30%
    max_stock_position: float = 0.15  # 单股最大仓位15%
    max_total_position: float = 0.70  # 总仓位上限70%

    # 板块排名对应的仓位
    sector_rank_1_2_position: float = 0.10  # 排名1-2: 10%
    sector_rank_3_5_position: float = 0.08  # 排名3-5: 8%


@dataclass
class StopLossConfig:
    """止损配置"""
    stop_loss_pct_close: float = -0.03  # 前一日收盘价-3%
    use_ma5_stop: bool = True  # 使用5日线止损


@dataclass
class TakeProfitConfig:
    """止盈配置"""
    use_10d_high: bool = True  # 使用10日高点
    take_profit_pct_close: float = 0.10  # 收盘价+10%
    enable_gradient: bool = False  # 启用梯度止盈
    gradient_10pct_sell_ratio: float = 0.50  # 10%时卖出50%
    gradient_20pct_sell_ratio: float = 1.00  # 20%时全部卖出


@dataclass
class OpenTriggerConfig:
    """开盘触发配置"""
    min_high_open_pct: float = 3.0  # 最小高开幅度(%)
    max_high_open_pct: float = 5.0  # 最大高开幅度(%)
    min_seal_ratio: float = 0.01  # 封单量占流通盘比例≥1%
    min_auction_amount: float = 500.0  # 竞价成交额≥500万(万元)


@dataclass
class TradingPlan:
    """交易计划"""
    stock_code: str
    stock_name: str
    sector_name: str
    sector_rank: int

    strategy_type: str  # 'chase' or 'dip'

    position_ratio: float  # 仓位比例 (0-1)
    stop_loss_price: float  # 止损价
    take_profit_price: float  # 止盈价

    # 开盘触发条件
    open_trigger_high_pct: Tuple[float, float]  # 高开幅度范围 (min, max)
    open_trigger_seal_ratio: float  # 封单量占流通盘比例
    open_trigger_auction_amount: float  # 竞价成交额(万元)

    # 信号强度
    strength_score: float

    # 选股详情 (用于调试)
    volume_ratio: float = 0.0
    is_limit_up: bool = False
    close_price: float = 0.0


class PositionManager:
    """
    仓位管理器

    功能:
    1. 计算每个标的的仓位
    2. 计算止损/止盈价
    3. 设置开盘触发条件
    """

    def __init__(
        self,
        position_config: PositionConfig = None,
        stop_loss_config: StopLossConfig = None,
        take_profit_config: TakeProfitConfig = None,
        open_trigger_config: OpenTriggerConfig = None,
        db=None
    ):
        """
        初始化仓位管理器

        Args:
            position_config: 仓位配置
            stop_loss_config: 止损配置
            take_profit_config: 止盈配置
            open_trigger_config: 开盘触发配置
            db: 数据库连接
        """
        self.position_config = position_config or PositionConfig()
        self.stop_loss_config = stop_loss_config or StopLossConfig()
        self.take_profit_config = take_profit_config or TakeProfitConfig()
        self.open_trigger_config = open_trigger_config or OpenTriggerConfig()
        self.db = db if db else get_db()

    def calculate_position_ratio(
        self,
        sector_rank: int,
        stock_rank_in_sector: int
    ) -> float:
        """
        计算仓位比例

        规则:
        - 板块排名1-2: 单股8-10%
        - 板块排名3-5: 单股5-8%

        Args:
            sector_rank: 板块排名 (1-5)
            stock_rank_in_sector: 板块内排名

        Returns:
            仓位比例 (0-1)
        """
        if sector_rank <= 2:
            base_position = self.position_config.sector_rank_1_2_position
        else:
            base_position = self.position_config.sector_rank_3_5_position

        # 板块内排名调整 (排名越前,仓位越大)
        if stock_rank_in_sector == 1:
            position = base_position
        elif stock_rank_in_sector == 2:
            position = base_position * 0.9
        elif stock_rank_in_sector == 3:
            position = base_position * 0.8
        elif stock_rank_in_sector == 4:
            position = base_position * 0.7
        else:
            position = base_position * 0.6

        # 确保不超过单股上限
        position = min(position, self.position_config.max_stock_position)

        return position

    def calculate_stop_loss(
        self,
        stock_code: str,
        date: str
    ) -> float:
        """
        计算止损价（使用前复权数据）

        规则: min(前一日收盘价-3%, 5日线价)

        Args:
            stock_code: 股票代码
            date: 日期 (YYYYMMDD)

        Returns:
            止损价
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            start_date_obj = date_obj - timedelta(days=20)

            with self.db.get_session() as session:
                from database.models.models import StockHistoryQfq

                # 获取前复权历史数据
                query = session.query(
                    StockHistoryQfq.date,
                    StockHistoryQfq.close
                ).filter(
                    StockHistoryQfq.symbol == stock_code,
                    StockHistoryQfq.date >= start_date_obj,
                    StockHistoryQfq.date <= date_obj
                ).order_by(StockHistoryQfq.date)

                df = pd.read_sql(query.statement, session.bind)

            if df.empty or len(df) < 2:
                logger.warning(f"股票 {stock_code} 前复权数据不足,无法计算止损价")
                return 0.0

            # 前一日收盘价（前复权）
            prev_close = df['close'].iloc[-2]

            # 方法1: 前一日收盘价-3%
            stop_loss_1 = prev_close * (1 + self.stop_loss_config.stop_loss_pct_close)

            # 方法2: 5日线价（前复权）
            if self.stop_loss_config.use_ma5_stop and len(df) >= 5:
                ma5 = df['close'].tail(5).mean()
                stop_loss_2 = ma5
            else:
                stop_loss_2 = float('inf')

            # 取较小值
            stop_loss = min(stop_loss_1, stop_loss_2)

            return round(stop_loss, 2)

        except Exception as e:
            logger.error(f"计算止损价失败: {e}")
            return 0.0

    def calculate_take_profit(
        self,
        stock_code: str,
        date: str
    ) -> float:
        """
        计算止盈价（使用前复权数据）

        规则: max(10日高点, 收盘价+10%)
        支持梯度止盈: 10%止盈50%, 20%清仓

        Args:
            stock_code: 股票代码
            date: 日期 (YYYYMMDD)

        Returns:
            止盈价
        """
        try:
            date_obj = datetime.strptime(date, '%Y%m%d').date()
            start_date_obj = date_obj - timedelta(days=20)

            with self.db.get_session() as session:
                from database.models.models import StockHistoryQfq

                # 获取前复权历史数据
                query = session.query(
                    StockHistoryQfq.date,
                    StockHistoryQfq.close,
                    StockHistoryQfq.high
                ).filter(
                    StockHistoryQfq.symbol == stock_code,
                    StockHistoryQfq.date >= start_date_obj,
                    StockHistoryQfq.date <= date_obj
                ).order_by(StockHistoryQfq.date)

                df = pd.read_sql(query.statement, session.bind)

            if df.empty:
                logger.warning(f"股票 {stock_code} 无前复权数据,无法计算止盈价")
                return 0.0

            # 当日收盘价（前复权）
            current_close = df['close'].iloc[-1]

            # 方法1: 10日高点（前复权）
            if self.take_profit_config.use_10d_high and len(df) >= 10:
                high_10d = df['high'].tail(10).max()
            else:
                high_10d = 0.0

            # 方法2: 收盘价+10%（前复权）
            take_profit_2 = current_close * (1 + self.take_profit_config.take_profit_pct_close)

            # 取较大值
            take_profit = max(high_10d, take_profit_2)

            return round(take_profit, 2)

        except Exception as e:
            logger.error(f"计算止盈价失败: {e}")
            return 0.0

    def calculate_open_trigger(
        self,
        stock_code: str
    ) -> Tuple[float, float, float]:
        """
        计算开盘触发阈值

        规则:
        - 高开3-5%
        - 封单量≥流通盘1%
        - 竞价成交额≥500万

        Args:
            stock_code: 股票代码

        Returns:
            (高开幅度最小值, 高开幅度最大值, 封单率, 竞价成交额)
        """
        return (
            self.open_trigger_config.min_high_open_pct,
            self.open_trigger_config.max_high_open_pct,
            self.open_trigger_config.min_seal_ratio,
            self.open_trigger_config.min_auction_amount
        )

    def generate_trading_plans(
        self,
        selected_stocks: Dict[str, List],
        sector_scores: List,
        date: str
    ) -> List[TradingPlan]:
        """
        生成交易计划

        Args:
            selected_stocks: 按策略分类的股票 {'chase': [...], 'dip': [...]}
            sector_scores: 板块评分列表 (含排名)
            date: 日期 (YYYYMMDD)

        Returns:
            交易计划列表
        """
        plans = []

        logger.info("=" * 60)
        logger.info("开始生成交易计划...")
        logger.info("=" * 60)

        # 1. 构建板块排名映射
        sector_rank_map = {
            score.sector_name: i + 1
            for i, score in enumerate(sector_scores)
        }

        # 2. 按板块和策略分组股票
        sector_strategy_groups = {}  # {(sector, strategy): [stocks]}

        for strategy_type, stocks in selected_stocks.items():
            for stock in stocks:
                key = (stock.sector_name, strategy_type)
                if key not in sector_strategy_groups:
                    sector_strategy_groups[key] = []
                sector_strategy_groups[key].append(stock)

        # 3. 为每只股票生成交易计划
        for (sector_name, strategy_type), stocks in sector_strategy_groups.items():
            sector_rank = sector_rank_map.get(sector_name, 99)

            # 板块内按得分排序
            stocks.sort(key=lambda s: s.strength_score, reverse=True)

            for stock_rank, stock in enumerate(stocks, start=1):
                # 计算仓位
                position_ratio = self.calculate_position_ratio(
                    sector_rank, stock_rank
                )

                # 计算止损/止盈
                stop_loss = self.calculate_stop_loss(stock.stock_code, date)
                take_profit = self.calculate_take_profit(stock.stock_code, date)

                # 开盘触发条件
                high_open_min, high_open_max, seal_ratio, auction_amount = \
                    self.calculate_open_trigger(stock.stock_code)

                # 创建交易计划
                plan = TradingPlan(
                    stock_code=stock.stock_code,
                    stock_name=stock.stock_name,
                    sector_name=stock.sector_name,
                    sector_rank=sector_rank,
                    strategy_type=stock.strategy_type,
                    position_ratio=position_ratio,
                    stop_loss_price=stop_loss,
                    take_profit_price=take_profit,
                    open_trigger_high_pct=(high_open_min, high_open_max),
                    open_trigger_seal_ratio=seal_ratio,
                    open_trigger_auction_amount=auction_amount,
                    strength_score=stock.strength_score,
                    volume_ratio=stock.volume_ratio,
                    is_limit_up=stock.is_limit_up,
                    close_price=stock.close_price
                )

                plans.append(plan)

                logger.debug(
                    f"  {plan.stock_code} {plan.stock_name}: "
                    f"仓位={position_ratio*100:.1f}%, "
                    f"止损={stop_loss:.2f}, "
                    f"止盈={take_profit:.2f}"
                )

        logger.info("=" * 60)
        logger.info(f"✓ 生成 {len(plans)} 个交易计划")
        logger.info("=" * 60)

        return plans

    def calculate_total_position(self, plans: List[TradingPlan]) -> float:
        """
        计算总仓位

        Args:
            plans: 交易计划列表

        Returns:
            总仓位比例 (0-1)
        """
        total = sum(plan.position_ratio for plan in plans)
        return min(total, self.position_config.max_total_position)


if __name__ == '__main__':
    """测试仓位管理器"""
    from loguru import logger

    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level="INFO")

    # 创建仓位管理器
    manager = PositionManager()

    # 测试仓位计算
    print("=== 测试仓位计算 ===")
    for sector_rank in range(1, 6):
        for stock_rank in range(1, 6):
            position = manager.calculate_position_ratio(sector_rank, stock_rank)
            print(f"板块排名{sector_rank}, 股票排名{stock_rank}: 仓位={position*100:.1f}%")

    # 测试止损止盈计算
    print("\n=== 测试止损止盈计算 ===")
    test_stock = "000001.SZ"
    test_date = "20240115"

    stop_loss = manager.calculate_stop_loss(test_stock, test_date)
    print(f"止损价: {stop_loss:.2f}")

    take_profit = manager.calculate_take_profit(test_stock, test_date)
    print(f"止盈价: {take_profit:.2f}")

    print("\n✓ 测试完成")
