"""
A股交易约束模块

实现A股市场特有的交易约束:
1. T+1结算规则 - 当日买入次日才能卖出
2. 涨跌停限制 - ±10% (ST股票±5%)
3. 手数限制 - 必须是100股的整数倍
"""

import math
import pandas as pd
from typing import Dict, Optional, Tuple
from loguru import logger


class TPlusOneTracker:
    """
    T+1交易限制跟踪器

    A股市场采用T+1结算制度,当日买入的证券只能在下一个交易日卖出。
    """

    def __init__(self):
        """初始化T+1跟踪器"""
        self.buy_dates: Dict[str, pd.Timestamp] = {}  # {symbol: buy_date}

    def can_sell(self, symbol: str, current_date: pd.Timestamp, position_size: float) -> bool:
        """
        检查股票是否可以卖出

        Args:
            symbol: 股票代码
            current_date: 当前日期
            position_size: 持仓数量

        Returns:
            bool: True可以卖出, False不能卖出
        """
        # 如果没有买入记录,说明是历史持仓,可以卖出
        if symbol not in self.buy_dates:
            return True

        # 计算持仓天数
        buy_date = self.buy_dates[symbol]
        days_held = (current_date - buy_date).days

        # T+1规则: 至少持有1天才能卖出
        can_sell = days_held >= 1

        if not can_sell:
            logger.debug(f"T+1限制: {symbol} 买入日期{buy_date}, 当前{current_date}, 持仓{days_held}天, 不能卖出")

        return can_sell

    def record_buy(self, symbol: str, date: pd.Timestamp) -> None:
        """
        记录买入日期

        Args:
            symbol: 股票代码
            date: 买入日期
        """
        self.buy_dates[symbol] = date
        logger.debug(f"T+1记录: {symbol} 买入于 {date}")

    def remove_position(self, symbol: str) -> None:
        """
        移除持仓记录(当仓位完全清空时)

        Args:
            symbol: 股票代码
        """
        if symbol in self.buy_dates:
            del self.buy_dates[symbol]
            logger.debug(f"T+1移除: {symbol} 持仓记录已清除")

    def get_holding_days(self, symbol: str, current_date: pd.Timestamp) -> int:
        """
        获取持仓天数

        Args:
            symbol: 股票代码
            current_date: 当前日期

        Returns:
            int: 持仓天数,如果没有买入记录返回0
        """
        if symbol not in self.buy_dates:
            return 0

        return (current_date - self.buy_dates[symbol]).days

    def clear(self) -> None:
        """清空所有记录"""
        self.buy_dates.clear()
        logger.debug("T+1记录已清空")


class PriceLimitChecker:
    """
    涨跌停限制检查器

    A股市场有价格涨跌幅限制:
    - 普通股票: ±10%
    - ST股票: ±5%
    - 科创板/创业板: ±20%
    - 北交所: ±30%
    """

    # 涨跌幅限制
    LIMIT_REGULAR = 0.10    # 普通股±10%
    LIMIT_ST = 0.05         # ST股±5%
    LIMIT_STAR = 0.20       # 科创板/创业板±20%
    LIMIT_BEIJING = 0.30    # 北交所±30%

    def __init__(self, st_stocks: set = None):
        """
        初始化涨跌停检查器

        Args:
            st_stocks: ST股票代码集合
        """
        self.st_stocks = st_stocks if st_stocks else set()
        self.new_ipo_stocks: Dict[str, pd.Timestamp] = {}  # 新股上市日期

    def _is_st_stock(self, symbol: str) -> bool:
        """
        判断是否为ST股票

        Args:
            symbol: 股票代码

        Returns:
            bool: True是ST股票
        """
        return symbol in self.st_stocks

    def _is_star_market(self, symbol: str) -> bool:
        """
        判断是否为科创板/创业板(20%涨跌停)

        Args:
            symbol: 股票代码

        Returns:
            bool: True是20%涨跌停股票
        """
        # 科创板: 688xxx.SH
        if symbol.startswith('688') and symbol.endswith('.SH'):
            return True
        # 创业板: 30xxxx.SZ
        if symbol.startswith('30') and symbol.endswith('.SZ'):
            return True
        return False

    def _is_beijing_market(self, symbol: str) -> bool:
        """
        判断是否为北交所(30%涨跌停)

        Args:
            symbol: 股票代码

        Returns:
            bool: True是北交所股票
        """
        # 北交所: 8xxxxx.BJ
        return symbol.endswith('.BJ')

    def _is_new_ipo(self, symbol: str, current_date: pd.Timestamp) -> bool:
        """
        判断是否为新上市股票(前5日无涨跌停限制)

        Args:
            symbol: 股票代码
            current_date: 当前日期

        Returns:
            bool: True是新上市股票
        """
        if symbol not in self.new_ipo_stocks:
            return False

        days_since_listing = (current_date - self.new_ipo_stocks[symbol]).days
        return days_since_listing <= 5

    def get_limit(self, symbol: str, current_date: pd.Timestamp = None) -> float:
        """
        获取股票的涨跌停限制

        Args:
            symbol: 股票代码
            current_date: 当前日期(用于判断新股)

        Returns:
            float: 涨跌停限制(如0.10表示10%)
        """
        # 新股前5日无限制
        if current_date and self._is_new_ipo(symbol, current_date):
            return 1.0  # 无限制

        # 北交所30%
        if self._is_beijing_market(symbol):
            return self.LIMIT_BEIJING

        # 科创板/创业板20%
        if self._is_star_market(symbol):
            return self.LIMIT_STAR

        # ST股票5%
        if self._is_st_stock(symbol):
            return self.LIMIT_ST

        # 普通股票10%
        return self.LIMIT_REGULAR

    def is_limit_hit(self, symbol: str, order_price: float, prev_close: float,
                     current_date: pd.Timestamp = None) -> Tuple[bool, str]:
        """
        检查订单价格是否触及涨跌停

        Args:
            symbol: 股票代码
            order_price: 订单价格
            prev_close: 前收盘价
            current_date: 当前日期

        Returns:
            tuple: (is_hit, limit_type)
                - is_hit: 是否触及涨跌停
                - limit_type: 限制类型 ('REGULAR', 'ST', 'STAR', 'BEIJING', 'NEW_IPO', 'NONE')
        """
        if prev_close == 0:
            return False, 'NONE'

        change_pct = abs(order_price - prev_close) / prev_close
        limit = self.get_limit(symbol, current_date)

        # 判断限制类型
        if current_date and self._is_new_ipo(symbol, current_date):
            limit_type = 'NEW_IPO'
        elif self._is_beijing_market(symbol):
            limit_type = 'BEIJING'
        elif self._is_star_market(symbol):
            limit_type = 'STAR'
        elif self._is_st_stock(symbol):
            limit_type = 'ST'
        else:
            limit_type = 'REGULAR'

        is_hit = change_pct >= limit

        if is_hit:
            logger.warning(f"涨跌停限制: {symbol} 价格{order_price:.2f} 前收{prev_close:.2f} "
                         f"涨跌幅{change_pct*100:.2f}% 限制{limit*100:.1f}% ({limit_type})")

        return is_hit, limit_type

    def get_limit_price(self, symbol: str, prev_close: float, direction: str,
                        current_date: pd.Timestamp = None) -> float:
        """
        计算涨停或跌停价格

        Args:
            symbol: 股票代码
            prev_close: 前收盘价
            direction: 'up'涨停或'down'跌停
            current_date: 当前日期

        Returns:
            float: 涨停或跌停价格
        """
        limit = self.get_limit(symbol, current_date)

        if direction == 'up':
            return prev_close * (1 + limit)
        elif direction == 'down':
            return prev_close * (1 - limit)
        else:
            raise ValueError(f"无效的direction参数: {direction}")

    def update_st_stocks(self, st_stocks: set) -> None:
        """
        更新ST股票列表

        Args:
            st_stocks: ST股票代码集合
        """
        self.st_stocks = st_stocks
        logger.info(f"ST股票列表已更新, 共{len(st_stocks)}只")


class LotSizeRounder:
    """
    手数调整器

    A股买卖必须是整手(100股)或其整数倍:
    - 普通股票: 100股/手
    - 部分ETF: 100份/手
    """

    def __init__(self, lot_size: int = 100):
        """
        初始化手数调整器

        Args:
            lot_size: 每手股数,默认100
        """
        self.lot_size = lot_size

    def round_to_lot(self, size: float) -> int:
        """
        将数量调整为整手

        Args:
            size: 目标数量(股)

        Returns:
            int: 调整后的整手数量
        """
        rounded = int(math.floor(size / self.lot_size) * self.lot_size)
        return rounded

    def adjust_order_size(self, target_value: float, price: float) -> Optional[int]:
        """
        根据目标金额计算整手数量

        Args:
            target_value: 目标金额(元)
            price: 当前价格(元)

        Returns:
            int: 整手数量,如果不足1手返回None
        """
        raw_shares = target_value / price
        rounded_shares = self.round_to_lot(raw_shares)

        # 至少1手
        if rounded_shares < self.lot_size:
            logger.debug(f"目标金额{target_value:.2f}元, 价格{price:.2f}元, "
                        f"计算{raw_shares:.0f}股, 不足1手({self.lot_size}股)")
            return None

        return rounded_shares

    def get_actual_value(self, shares: int, price: float) -> float:
        """
        获取整手对应的价值

        Args:
            shares: 股数(整手)
            price: 价格

        Returns:
            float: 实际价值
        """
        return shares * price

    def adjust_to_lot(self, size: float, min_shares: int = None) -> int:
        """
        调整到整手,可指定最小股数

        Args:
            size: 原始数量
            min_shares: 最小股数(可选),默认为lot_size

        Returns:
            int: 调整后的整手数量
        """
        if min_shares is None:
            min_shares = self.lot_size

        rounded = self.round_to_lot(size)

        # 如果不足最小股数,返回最小股数
        if rounded < min_shares:
            return min_shares

        return rounded


def validate_order_compliance(symbol: str, order_size: int, order_price: float,
                              prev_close: float, t1_tracker: TPlusOneTracker = None,
                              limit_checker: PriceLimitChecker = None,
                              lot_rounder: LotSizeRounder = None,
                              current_date: pd.Timestamp = None,
                              is_sell: bool = False) -> Tuple[bool, str]:
    """
    验证订单是否符合A股交易规则

    Args:
        symbol: 股票代码
        order_size: 订单数量
        order_price: 订单价格
        prev_close: 前收盘价
        t1_tracker: T+1跟踪器(可选)
        limit_checker: 涨跌停检查器(可选)
        lot_rounder: 手数调整器(可选)
        current_date: 当前日期
        is_sell: 是否为卖出订单

    Returns:
        tuple: (is_valid, error_message)
            - is_valid: 是否合规
            - error_message: 错误信息(如果不合规)
    """
    # 1. 检查T+1规则(仅卖出)
    if is_sell and t1_tracker:
        if not t1_tracker.can_sell(symbol, current_date, order_size):
            return False, f"T+1限制: {symbol} 当日买入次日才能卖出"

    # 2. 检查涨跌停
    if limit_checker:
        is_hit, _ = limit_checker.is_limit_hit(symbol, order_price, prev_close, current_date)
        if is_hit:
            return False, f"涨跌停限制: {symbol} 订单价格{order_price:.2f}触及涨跌停"

    # 3. 检查手数
    if lot_rounder:
        if order_size % lot_rounder.lot_size != 0:
            return False, f"手数限制: {symbol} 订单数量{order_size}不是{lot_rounder.lot_size}的整数倍"

    return True, ""


# 便捷函数
def check_buy_order(symbol: str, size: int, price: float, prev_close: float,
                    t1_tracker: TPlusOneTracker = None,
                    limit_checker: PriceLimitChecker = None,
                    lot_rounder: LotSizeRounder = None,
                    current_date: pd.Timestamp = None) -> Tuple[bool, str]:
    """检查买入订单"""
    return validate_order_compliance(
        symbol, size, price, prev_close,
        t1_tracker, limit_checker, lot_rounder,
        current_date, is_sell=False
    )


def check_sell_order(symbol: str, size: int, price: float, prev_close: float,
                     t1_tracker: TPlusOneTracker = None,
                     limit_checker: PriceLimitChecker = None,
                     lot_rounder: LotSizeRounder = None,
                     current_date: pd.Timestamp = None) -> Tuple[bool, str]:
    """检查卖出订单"""
    return validate_order_compliance(
        symbol, size, price, prev_close,
        t1_tracker, limit_checker, lot_rounder,
        current_date, is_sell=True
    )
