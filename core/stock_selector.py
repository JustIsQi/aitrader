"""
个股量化选股模块

功能:
1. 追涨策略选股
2. 低吸策略选股
3. 风险过滤
4. 排序评分

作者: AITrader
日期: 2026-01-21
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

try:
    import talib
except ImportError:
    logger.warning("talib未安装,部分技术指标计算将不可用")
    talib = None

from database.db_manager import get_db
from database.models.models import (
    StockHistory, StockMetadata, StockFundamentalDaily, StockRiskData
)


@dataclass
class ChaseStrategyConfig:
    """追涨策略配置 (动量突破5步Pipeline)"""
    # 第1步：涨幅筛选
    min_change_pct: float = 5.0         # 最小涨幅5%
    max_change_pct: float = 7.0         # 最大涨幅7%
    allow_failed_limit_up: bool = True  # 允许曾涨停未封住（盘中触板回落）
    limit_up_threshold: float = 9.5    # 涨停判定阈值（主板9.5%，创业板/科创板可调至19.5%）

    # 第2步：量能验证
    min_turnover_rate: float = 5.0      # 最小换手率5%
    max_turnover_rate: float = 10.0     # 最大换手率10%
    min_volume_ratio: float = 1.0       # 量比>1
    require_volume_step_up: bool = True # 要求成交量阶梯放大（连续3日递增）

    # 第4步：形态关键
    breakout_lookback_days: int = 20    # 突破回看天数
    require_breakout_or_ma_diverge: bool = True  # 要求突破近期平台/前高 或 均线刚发散
    ma_diverge_max_spread: float = 8.0  # 均线发散最大价差%（超过视为高位，排除）

    # 通用
    max_stocks_per_sector: int = 5      # 每板块最多选5只


@dataclass
class DipStrategyConfig:
    """低吸策略配置"""
    max_close_ma_deviation: float = 5.0  # 收盘价偏离均线≤5%（从3%放宽到5%）
    require_macd_golden_cross: bool = True  # MACD金叉
    max_volume_ratio_5d: float = 0.9  # 成交额≤5日均值的0.9（从0.8放宽到0.9）
    require_sector_inflow: bool = True  # 要求板块资金净流入
    max_stocks_per_sector: int = 5  # 每板块最多选5只
    enable_rsi_oversold: bool = False  # 启用RSI超卖条件
    rsi_oversold_threshold: float = 40.0  # RSI超卖阈值


@dataclass
class RiskFilterConfig:
    """风险过滤配置"""
    exclude_loss_maker: bool = True  # 排除业绩亏损
    exclude_reduction: bool = True  # 排除减持公告
    exclude_suspend: bool = True  # 排除停牌
    min_market_cap: float = 50.0  # 最小市值50亿(亿元)
    max_market_cap: float = 200.0  # 最大市值200亿(亿元)
    exclude_non_main_board: bool = True  # 排除非主板股票（科创板、创业板、北交所）


@dataclass
class SelectedStock:
    """选中的股票"""
    stock_code: str
    stock_name: str
    sector_name: str

    # 策略类型
    strategy_type: str  # 'chase' or 'dip'

    # 评分
    strength_score: float  # 综合得分
    net_inflow_ratio: float  # 资金净流入占比
    seal_rate: float  # 封单率 (连板股)

    # 详细数据
    close_price: float
    main_net_inflow: float
    volume_ratio: float

    # 选股指标 (用于调试)
    is_5d_high: bool = False
    is_limit_up: bool = False
    consecutive_boards: int = 0
    close_ma_deviation: float = 0.0
    macd_golden_cross: bool = False
    turnover_rate: float = 0.0
    is_breakout: bool = False
    is_ma_diverge: bool = False
    is_failed_limit_up: bool = False


class StockSelector:
    """
    个股量化选股器

    工作流程:
    1. 从强势板块中筛选股票
    2. 分别应用追涨/低吸策略
    3. 风险过滤
    4. 排序输出
    """

    def __init__(
        self,
        chase_config: ChaseStrategyConfig = None,
        dip_config: DipStrategyConfig = None,
        risk_config: RiskFilterConfig = None,
        db=None
    ):
        """
        初始化选股器

        Args:
            chase_config: 追涨策略配置
            dip_config: 低吸策略配置
            risk_config: 风险过滤配置
            db: 数据库连接
        """
        self.chase_config = chase_config or ChaseStrategyConfig()
        self.dip_config = dip_config or DipStrategyConfig()
        self.risk_config = risk_config or RiskFilterConfig()
        self.db = db if db else get_db()

    def get_stocks_in_sectors(
        self,
        sector_names: List[str],
        date: str
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        获取强势板块内的所有股票

        Args:
            sector_names: 板块名称列表
            date: 日期 (YYYYMMDD)

        Returns:
            按板块分组的股票字典 {sector_name: [(symbol, name), ...]}
        """
        try:
            with self.db.get_session() as session:
                # 特殊处理: 如果是"全市场",获取所有股票
                if "全市场" in sector_names:
                    from sqlalchemy import func

                    # 获取最近有数据的股票 (限制数量避免内存溢出)
                    date_obj = datetime.strptime(date, '%Y%m%d').date()

                    # 随机抽样或按流动性排序获取股票
                    stocks_query = session.query(
                        StockMetadata.symbol,
                        StockMetadata.name,
                        StockMetadata.sector
                    ).join(
                        StockHistory,
                        StockMetadata.symbol == StockHistory.symbol
                    ).filter(
                        StockHistory.date == date_obj
                    ).order_by(
                        StockHistory.amount.desc()  # 按成交额降序
                    ).limit(500)  # 限制为500只股票

                    stocks = stocks_query.all()

                    # 手动设置sector为"全市场"
                    sector_stocks = {"全市场": []}
                    for symbol, name, _ in stocks:
                        sector_stocks["全市场"].append((symbol, name))

                    logger.info(f"✓ 全市场模式: 获取到 {len(stocks)} 只股票")

                    return sector_stocks

                # 正常的板块筛选
                stocks = session.query(
                    StockMetadata.symbol,
                    StockMetadata.name,
                    StockMetadata.sector
                ).filter(
                    StockMetadata.sector.in_(sector_names)
                ).all()

                # 按板块分组
                sector_stocks = {}
                for symbol, name, sector in stocks:
                    if sector not in sector_stocks:
                        sector_stocks[sector] = []
                    sector_stocks[sector].append((symbol, name))

                logger.info(f"获取到 {len(stocks)} 只股票, 分布在 {len(sector_stocks)} 个板块")

                return sector_stocks

        except Exception as e:
            logger.error(f"获取板块股票失败: {e}")
            return {}

    def apply_chase_strategy(
        self,
        sector_stocks: Dict[str, List[Tuple[str, str]]],
        date: str
    ) -> List[SelectedStock]:
        """
        应用动量突破策略 (5步Pipeline)

        筛选条件:
        第1步：涨幅筛选 → 昨日涨幅5%-7%（或曾涨停未封住）
        第2步：量能验证 → 昨日换手5%-10%，量比>1，成交量阶梯放大
        第4步：形态关键 → 突破近期平台/前高，或均线刚发散（非高位）
        (第3步市值过滤 和 第5步开盘确认 在其他模块处理)

        Args:
            sector_stocks: 按板块分组的股票 {sector: [(code, name), ...]}
            date: 日期 (YYYYMMDD)

        Returns:
            选中的股票列表
        """
        selected = []

        date_obj = datetime.strptime(date, '%Y%m%d').date()
        # 回看天数取配置值和30天中较大的，保证均线计算有足够数据
        lookback = max(self.chase_config.breakout_lookback_days, 30)
        start_date_obj = date_obj - timedelta(days=int(lookback * 1.8))

        logger.info("=" * 60)
        logger.info("应用动量突破策略 (5步Pipeline)...")
        logger.info(f"  涨幅范围: {self.chase_config.min_change_pct}%-{self.chase_config.max_change_pct}%")
        logger.info(f"  换手率范围: {self.chase_config.min_turnover_rate}%-{self.chase_config.max_turnover_rate}%")
        logger.info(f"  量比阈值: >{self.chase_config.min_volume_ratio}")
        logger.info(f"  曾涨停未封住: {'是' if self.chase_config.allow_failed_limit_up else '否'}")
        logger.info("=" * 60)

        step_stats = {'total': 0, 'step1_pass': 0, 'step2_pass': 0, 'step4_pass': 0}

        for sector_name, stocks in sector_stocks.items():
            stock_codes = [s[0] for s in stocks]

            # 获取历史数据 (turnover_rate 来自 Wind 衍生指标表)
            try:
                from datafeed.db_dataloader import DbDataLoader

                loader = DbDataLoader(auto_download=False)
                dfs = loader.read_dfs(
                    symbols=stock_codes,
                    start_date=start_date_obj.strftime('%Y%m%d'),
                    end_date=date_obj.strftime('%Y%m%d'),
                )
                df = pd.concat(dfs.values(), ignore_index=True) if dfs else pd.DataFrame()

                if df.empty:
                    logger.debug(f"板块 {sector_name} 无历史数据")
                    continue

                # 按股票逐一分析
                for stock_code in stock_codes:
                    stock_df = df[df['symbol'] == stock_code].copy()

                    if stock_df.empty or len(stock_df) < 10:
                        continue

                    step_stats['total'] += 1
                    stock_name = next((s[1] for s in stocks if s[0] == stock_code), "")
                    latest = stock_df.iloc[-1]

                    # ========== 第1步：涨幅筛选 ==========
                    change_pct = latest['change_pct']
                    is_normal_range = (self.chase_config.min_change_pct <= change_pct <= self.chase_config.max_change_pct)

                    # 曾涨停未封住：盘中最高价触及涨停，但收盘未封住
                    is_failed_limit_up = False
                    limit_threshold = self.chase_config.limit_up_threshold
                    if self.chase_config.allow_failed_limit_up and not is_normal_range:
                        if len(stock_df) >= 2:
                            pre_close = stock_df.iloc[-2]['close']
                            if pre_close > 0:
                                intraday_max_pct = (latest['high'] - pre_close) / pre_close * 100
                                # 盘中触板(>=阈值) 但收盘未封住(change_pct < 阈值)
                                is_failed_limit_up = (intraday_max_pct >= limit_threshold and change_pct < limit_threshold and change_pct > 0)

                    if not is_normal_range and not is_failed_limit_up:
                        continue

                    step_stats['step1_pass'] += 1

                    # ========== 第2步：量能验证 ==========
                    # 2a. 换手率范围检查
                    turnover_rate = latest.get('turnover_rate', 0) or 0
                    if turnover_rate < self.chase_config.min_turnover_rate or turnover_rate > self.chase_config.max_turnover_rate:
                        continue

                    # 2b. 量比 > 1
                    volume_ratio = self._calculate_volume_ratio(stock_df)
                    if volume_ratio < self.chase_config.min_volume_ratio:
                        continue

                    # 2c. 成交量阶梯放大（连续3日递增）
                    if self.chase_config.require_volume_step_up:
                        if not self._check_volume_step_up(stock_df):
                            continue

                    step_stats['step2_pass'] += 1

                    # ========== 第4步：形态关键 ==========
                    is_breakout = False
                    is_ma_diverge = False

                    if self.chase_config.require_breakout_or_ma_diverge:
                        is_breakout = self._check_breakout_pattern(
                            stock_df,
                            lookback_days=self.chase_config.breakout_lookback_days
                        )
                        is_ma_diverge = self._check_ma_divergence(
                            stock_df,
                            max_spread=self.chase_config.ma_diverge_max_spread
                        )

                        if not is_breakout and not is_ma_diverge:
                            continue

                    step_stats['step4_pass'] += 1

                    # ========== 综合评分 ==========
                    # 评分维度: 量比(30%) + 换手率适中度(20%) + 涨幅强度(20%) + 形态(30%)
                    vol_score = min(volume_ratio / 3.0, 1.0) * 30  # 量比，封顶3

                    # 换手率越接近中间值(7.5%)越好
                    turnover_mid = (self.chase_config.min_turnover_rate + self.chase_config.max_turnover_rate) / 2
                    turnover_score = max(0, 1.0 - abs(turnover_rate - turnover_mid) / turnover_mid) * 20

                    # 涨幅越大越好（在范围内）
                    change_score = min(change_pct / self.chase_config.max_change_pct, 1.0) * 20

                    # 形态加分: 突破+均线发散双满足额外加分
                    pattern_score = 0
                    if is_breakout:
                        pattern_score += 20
                    if is_ma_diverge:
                        pattern_score += 10

                    strength_score = vol_score + turnover_score + change_score + pattern_score

                    selected.append(SelectedStock(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        sector_name=sector_name,
                        strategy_type='chase',
                        strength_score=strength_score,
                        net_inflow_ratio=0.0,
                        seal_rate=0.0,
                        close_price=latest['close'],
                        main_net_inflow=0.0,
                        volume_ratio=volume_ratio,
                        is_5d_high=is_breakout,
                        is_limit_up=is_normal_range,
                        consecutive_boards=0,
                        turnover_rate=turnover_rate,
                        is_breakout=is_breakout,
                        is_ma_diverge=is_ma_diverge,
                        is_failed_limit_up=is_failed_limit_up
                    ))

            except Exception as e:
                logger.error(f"分析板块 {sector_name} 追涨策略失败: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue

        logger.info(f"Pipeline统计: 总计={step_stats['total']}, "
                    f"第1步(涨幅)通过={step_stats['step1_pass']}, "
                    f"第2步(量能)通过={step_stats['step2_pass']}, "
                    f"第4步(形态)通过={step_stats['step4_pass']}")
        logger.info(f"✓ 追涨策略选中 {len(selected)} 只股票")

        # 按板块限制数量
        selected = self._limit_by_sector(selected, self.chase_config.max_stocks_per_sector)

        return selected

    def apply_dip_strategy(
        self,
        sector_stocks: Dict[str, List[Tuple[str, str]]],
        date: str
    ) -> List[SelectedStock]:
        """
        应用低吸策略

        筛选条件:
        1. 收盘价偏离5/10日线≤3%
        2. MACD金叉
        3. 成交额≤5日均值80%
        4. 所属板块资金净流入 (暂未实现)

        Args:
            sector_stocks: 按板块分组的股票
            date: 日期 (YYYYMMDD)

        Returns:
            选中的股票列表
        """
        selected = []

        date_obj = datetime.strptime(date, '%Y%m%d').date()
        start_date_obj = date_obj - timedelta(days=30)
        start_date_str = start_date_obj.strftime('%Y%m%d')

        logger.info("=" * 60)
        logger.info("应用低吸策略...")
        logger.info("=" * 60)

        for sector_name, stocks in sector_stocks.items():
            stock_codes = [s[0] for s in stocks]

            # 获取历史数据
            try:
                with self.db.get_session() as session:
                    query = session.query(
                        StockHistory.symbol,
                        StockHistory.date,
                        StockHistory.close,
                        StockHistory.volume
                    ).filter(
                        StockHistory.symbol.in_(stock_codes),
                        StockHistory.date >= start_date_obj,
                        StockHistory.date <= date_obj
                    ).order_by(StockHistory.date)

                    df = pd.read_sql(query.statement, session.bind)

                if df.empty:
                    continue

                # 按股票分析
                for stock_code in stock_codes:
                    stock_df = df[df['symbol'] == stock_code].copy()

                    if stock_df.empty or len(stock_df) < 10:
                        continue

                    stock_name = next((s[1] for s in stocks if s[0] == stock_code), "")

                    # 获取最新数据
                    latest = stock_df.iloc[-1]
                    current_close = latest['close']

                    # 1. 检查偏离度
                    ma5 = stock_df['close'].tail(5).mean()
                    ma10 = stock_df['close'].tail(10).mean()

                    deviation_5d = abs(current_close - ma5) / ma5 * 100
                    deviation_10d = abs(current_close - ma10) / ma10 * 100

                    if deviation_5d > self.dip_config.max_close_ma_deviation:
                        continue

                    # 2. 检查MACD金叉
                    if self.dip_config.require_macd_golden_cross:
                        if talib is not None:
                            closes = stock_df['close'].values
                            macd, signal, _ = talib.MACD(closes)

                            if len(macd) >= 2:
                                macd_golden_cross = macd[-1] > signal[-1] and macd[-2] <= signal[-2]
                            else:
                                macd_golden_cross = False
                        else:
                            # Fallback: 简单判断短期均线上穿长期均线
                            macd_golden_cross = ma5 > ma10
                    else:
                        macd_golden_cross = True

                    if not macd_golden_cross:
                        continue

                    # 3. 检查成交量 (缩量)
                    volume_ratio_5d = self._calculate_volume_ratio(stock_df)
                    if volume_ratio_5d > self.dip_config.max_volume_ratio_5d:
                        continue

                    # 4. 计算评分 (偏离越小越好)
                    strength_score = 100 - deviation_5d

                    selected.append(SelectedStock(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        sector_name=sector_name,
                        strategy_type='dip',
                        strength_score=strength_score,
                        net_inflow_ratio=0.0,
                        seal_rate=0.0,
                        close_price=current_close,
                        main_net_inflow=0.0,
                        volume_ratio=volume_ratio_5d,
                        close_ma_deviation=deviation_5d,
                        macd_golden_cross=macd_golden_cross
                    ))

            except Exception as e:
                logger.error(f"分析板块 {sector_name} 低吸策略失败: {e}")
                continue

        logger.info(f"✓ 低吸策略选中 {len(selected)} 只股票")

        # 按板块限制数量
        selected = self._limit_by_sector(selected, self.dip_config.max_stocks_per_sector)

        return selected

    def _check_volume_step_up(self, df: pd.DataFrame) -> bool:
        """
        检查成交量阶梯放大（连续3日递增）

        Args:
            df: 股票历史数据 (按日期升序)

        Returns:
            是否满足成交量阶梯放大条件
        """
        if len(df) < 3:
            return False

        vol_3 = df['volume'].iloc[-3]  # 前天
        vol_2 = df['volume'].iloc[-2]  # 昨天前一天
        vol_1 = df['volume'].iloc[-1]  # 昨天（最新）

        # 连续3日成交量递增
        if vol_3 > 0 and vol_2 > 0 and vol_1 > 0:
            return vol_1 > vol_2 > vol_3

        return False

    def _check_breakout_pattern(self, df: pd.DataFrame, lookback_days: int = 20) -> bool:
        """
        检查是否突破近期平台/前高

        判断逻辑:
        1. 收盘价突破近N日最高价（排除最后一天自身）
        2. 或收盘价突破近期窄幅整理平台的上沿

        Args:
            df: 股票历史数据 (按日期升序)
            lookback_days: 回看天数

        Returns:
            是否突破
        """
        if len(df) < lookback_days:
            # 数据不足，使用可用的全部数据（至少需要5天）
            if len(df) < 5:
                return False
            lookback_days = len(df) - 1

        current_close = df['close'].iloc[-1]

        # 方式1: 突破近N日最高收盘价（排除最后1天）
        historical_high = df['close'].iloc[-lookback_days - 1:-1].max()
        if current_close > historical_high:
            return True

        # 方式2: 突破近期整理平台
        # 计算近N日（排除最后1天）的价格波动率（标准差/均值）
        recent_closes = df['close'].iloc[-lookback_days - 1:-1]
        if len(recent_closes) >= 5:
            mean_price = recent_closes.mean()
            std_price = recent_closes.std()

            if mean_price > 0:
                volatility = std_price / mean_price
                # 窄幅整理：波动率 < 3%，表示价格在一个平台内横盘
                if volatility < 0.03:
                    platform_high = recent_closes.max()
                    # 突破平台上沿
                    if current_close > platform_high:
                        return True

        # 方式3: 突破近N日最高价（用high而非close）
        if 'high' in df.columns:
            historical_high_price = df['high'].iloc[-lookback_days - 1:-1].max()
            if current_close > historical_high_price:
                return True

        return False

    def _check_ma_divergence(self, df: pd.DataFrame, max_spread: float = 8.0) -> bool:
        """
        检查均线刚发散（非高位）

        判断逻辑:
        - MA5 > MA10 > MA20（多头排列）
        - (MA5 - MA20) / MA20 < max_spread%（非高位发散，排除已大涨的）
        - 前一天尚未满足多头排列（"刚"发散）

        Args:
            df: 股票历史数据 (按日期升序)
            max_spread: 均线发散最大价差百分比

        Returns:
            是否满足均线刚发散条件
        """
        if len(df) < 21:
            return False

        closes = df['close'].values

        # 计算当日均线
        ma5_today = closes[-5:].mean()
        ma10_today = closes[-10:].mean()
        ma20_today = closes[-20:].mean()

        # 检查今日多头排列: MA5 > MA10 > MA20
        if not (ma5_today > ma10_today > ma20_today):
            return False

        # 检查非高位: 发散幅度不能太大
        if ma20_today > 0:
            spread = (ma5_today - ma20_today) / ma20_today * 100
            if spread >= max_spread:
                return False  # 已经高位发散，排除
        else:
            return False

        # 检查"刚"发散: 前一天尚未满足多头排列
        if len(df) >= 22:
            closes_prev = closes[:-1]  # 排除最后一天
            ma5_prev = closes_prev[-5:].mean()
            ma10_prev = closes_prev[-10:].mean()
            ma20_prev = closes_prev[-20:].mean()

            prev_bullish = (ma5_prev > ma10_prev > ma20_prev)

            # 如果前一天已经是多头排列，检查发散是否在加速
            if prev_bullish:
                prev_spread = (ma5_prev - ma20_prev) / ma20_prev * 100 if ma20_prev > 0 else 0
                # 只要今天的发散比昨天更大一点点就算"正在发散"
                if spread <= prev_spread:
                    return False
        # 如果数据不足以计算前一天，只要当日满足就通过

        return True

    def _calculate_volume_ratio(self, df: pd.DataFrame) -> float:
        """
        计算量比

        Args:
            df: 股票历史数据

        Returns:
            量比 (当日成交量 / 近5日平均成交量)
        """
        if len(df) < 6:
            return 1.0

        today_volume = df['volume'].iloc[-1]
        avg_5d_volume = df['volume'].iloc[-6:-1].mean()

        if avg_5d_volume == 0:
            return 1.0

        return today_volume / avg_5d_volume

    def _limit_by_sector(
        self,
        stocks: List[SelectedStock],
        max_per_sector: int
    ) -> List[SelectedStock]:
        """
        按板块限制股票数量

        Args:
            stocks: 股票列表
            max_per_sector: 每板块最大数量

        Returns:
            限制后的股票列表
        """
        # 按板块分组
        sector_groups = {}
        for stock in stocks:
            if stock.sector_name not in sector_groups:
                sector_groups[stock.sector_name] = []
            sector_groups[stock.sector_name].append(stock)

        # 每个板块内按得分排序,取前N名
        result = []
        for sector_name, sector_stocks in sector_groups.items():
            sector_stocks.sort(key=lambda s: s.strength_score, reverse=True)
            result.extend(sector_stocks[:max_per_sector])

        return result

    def apply_risk_filter(
        self,
        stocks: List[SelectedStock],
        date: str
    ) -> List[SelectedStock]:
        """
        风险过滤

        过滤条件:
        - 板块类型 (exclude_non_main_board: 排除科创板、创业板、北交所)
        - 业绩亏损 (is_loss_maker)
        - 减持公告 (has_reduction_announcement)
        - 停牌 (is_suspended)
        - 流通盘 <50亿 or >500亿

        Args:
            stocks: 股票列表
            date: 日期 (YYYYMMDD)

        Returns:
            过滤后的股票列表
        """
        filtered = []
        risk_stats = {
            'non_main_board': 0,  # 新增：非主板股票计数
            'loss_maker': 0,
            'reduction': 0,
            'suspend': 0,
            'market_cap': 0,
            'total': len(stocks)
        }

        try:
            # 新增：板块类型过滤
            if self.risk_config.exclude_non_main_board:
                from database.models.models import AShareStockInfo

                # 提取纯数字代码（去除交易所后缀）
                stock_codes_with_suffix = [s.stock_code for s in stocks]
                stock_codes_clean = [code.split('.')[0] if '.' in code else code for code in stock_codes_with_suffix]

                with self.db.get_session() as session:
                    # 查询主板股票（使用纯数字代码匹配）
                    main_board_query = session.query(AShareStockInfo.stock_code).filter(
                        AShareStockInfo.stock_code.in_(stock_codes_clean),
                        ~AShareStockInfo.stock_code.like('688%'),      # 排除科创板
                        ~AShareStockInfo.stock_code.like('300%'),      # 排除创业板
                        AShareStockInfo.exchange_suffix != 'BJ'         # 排除北交所
                    )

                    main_board_codes_clean = set(row[0] for row in main_board_query.all())

                # 过滤掉非主板股票
                stocks = [s for s in stocks if s.stock_code.split('.')[0] in main_board_codes_clean]
                risk_stats['non_main_board'] = risk_stats['total'] - len(stocks)
                risk_stats['total'] = len(stocks)

            stock_codes = [s.stock_code for s in stocks]

            with self.db.get_session() as session:
                # 1. 获取风险数据
                risk_data = session.query(StockRiskData).filter(
                    StockRiskData.stock_code.in_(stock_codes)
                ).all()

                risk_dict = {r.stock_code: r for r in risk_data}

                # 2. 获取市值数据
                date_obj = datetime.strptime(date, '%Y%m%d').date()

                fundamental_data = session.query(
                    StockFundamentalDaily.symbol,
                    StockFundamentalDaily.circ_mv
                ).filter(
                    StockFundamentalDaily.symbol.in_(stock_codes),
                    StockFundamentalDaily.date == date_obj
                ).all()

                mv_dict = {f[0]: f[1] for f in fundamental_data if f[1]}

            for stock in stocks:
                # 检查风险数据
                risk = risk_dict.get(stock.stock_code)

                if risk:
                    # 业绩亏损
                    if self.risk_config.exclude_loss_maker and risk.is_loss_maker:
                        risk_stats['loss_maker'] += 1
                        continue

                    # 减持公告
                    if self.risk_config.exclude_reduction and risk.has_reduction_announcement:
                        risk_stats['reduction'] += 1
                        continue

                    # 停牌
                    if self.risk_config.exclude_suspend and risk.is_suspended:
                        risk_stats['suspend'] += 1
                        continue

                # 检查市值
                mv = mv_dict.get(stock.stock_code)
                if mv:
                    if mv < self.risk_config.min_market_cap or mv > self.risk_config.max_market_cap:
                        risk_stats['market_cap'] += 1
                        continue

                filtered.append(stock)

            logger.info("=" * 60)
            logger.info("风险过滤统计:")
            if self.risk_config.exclude_non_main_board:
                logger.info(f"  非主板股票: {risk_stats['non_main_board']}")
            logger.info(f"  总数: {risk_stats['total']}")
            logger.info(f"  业绩亏损: {risk_stats['loss_maker']}")
            logger.info(f"  减持公告: {risk_stats['reduction']}")
            logger.info(f"  停牌: {risk_stats['suspend']}")
            logger.info(f"  市值异常: {risk_stats['market_cap']}")
            logger.info(f"  ✓ 剩余: {len(filtered)}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"风险过滤失败: {e}")
            return stocks

        return filtered

    def rank_stocks(self, stocks: List[SelectedStock]) -> List[SelectedStock]:
        """
        排序股票

        排序规则: 综合得分降序

        Args:
            stocks: 股票列表

        Returns:
            排序后的股票列表
        """
        stocks.sort(key=lambda s: s.strength_score, reverse=True)
        return stocks

    def select_stocks(
        self,
        sector_names: List[str],
        date: str,
        strategy_type: str = 'both'
    ) -> Dict[str, List[SelectedStock]]:
        """
        综合选股

        Args:
            sector_names: 强势板块名称列表
            date: 日期 (YYYYMMDD)
            strategy_type: 'chase', 'dip', or 'both'

        Returns:
            按策略分类的股票字典 {'chase': [...], 'dip': [...]}
        """
        # 1. 获取板块内股票
        sector_stocks = self.get_stocks_in_sectors(sector_names, date)

        if not sector_stocks:
            logger.warning("板块内无股票")
            return {}

        result = {}

        # 2. 追涨策略
        if strategy_type in ['chase', 'both']:
            chase_stocks = self.apply_chase_strategy(sector_stocks, date)
            chase_stocks = self.apply_risk_filter(chase_stocks, date)
            chase_stocks = self.rank_stocks(chase_stocks)
            result['chase'] = chase_stocks

        # 3. 低吸策略
        if strategy_type in ['dip', 'both']:
            dip_stocks = self.apply_dip_strategy(sector_stocks, date)
            dip_stocks = self.apply_risk_filter(dip_stocks, date)
            dip_stocks = self.rank_stocks(dip_stocks)
            result['dip'] = dip_stocks

        return result


if __name__ == '__main__':
    """测试选股器"""
    from loguru import logger

    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level="INFO")

    # 创建选股器 (使用新的5步Pipeline配置)
    selector = StockSelector(
        chase_config=ChaseStrategyConfig(
            min_change_pct=5.0,
            max_change_pct=7.0,
            allow_failed_limit_up=True,
            min_turnover_rate=5.0,
            max_turnover_rate=10.0,
            min_volume_ratio=1.0,
            require_volume_step_up=True,
            require_breakout_or_ma_diverge=True
        ),
        dip_config=DipStrategyConfig(
            max_close_ma_deviation=5.0,
            require_macd_golden_cross=False
        ),
        risk_config=RiskFilterConfig(
            min_market_cap=50.0,
            max_market_cap=200.0,
            exclude_non_main_board=True
        )
    )

    # 测试选股
    test_date = "20240115"
    test_sectors = ["电子", "医药生物", "计算机"]

    selected = selector.select_stocks(
        sector_names=test_sectors,
        date=test_date,
        strategy_type='both'
    )

    print("\n✓ 追涨策略 (动量突破):")
    for stock in selected.get('chase', [])[:5]:
        print(f"  {stock.stock_code} {stock.stock_name}: "
              f"得分={stock.strength_score:.2f} "
              f"量比={stock.volume_ratio:.2f} "
              f"换手={stock.turnover_rate:.1f}% "
              f"突破={stock.is_breakout} 发散={stock.is_ma_diverge}")

    print("\n✓ 低吸策略:")
    for stock in selected.get('dip', [])[:5]:
        print(f"  {stock.stock_code} {stock.stock_name}: {stock.strength_score:.2f}")

    print("\n✓ 测试完成")
