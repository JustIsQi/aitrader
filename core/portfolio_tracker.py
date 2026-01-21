"""
组合状态追踪器

用于追踪组合回测过程中的每日状态，包括：
- 组合净值（持仓市值 + 现金）
- 持仓明细（标的、数量、成本、权重）
- 每日收益率
- 累计收益率
- 最大回撤
- 换手率
- 交易历史
"""
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class PortfolioStateTracker:
    """组合状态追踪器"""

    def __init__(self, initial_capital: float = 1000000):
        """
        初始化组合状态追踪器

        Args:
            initial_capital: 初始资金，默认100万
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital  # 当前现金
        self.holdings = {}  # 当前持仓 {symbol: {'shares': int, 'avg_cost': float}}
        self.daily_states = []  # 每日状态记录
        self.transaction_history = []  # 交易历史 [{'date', 'symbol', 'action', 'shares', 'price', 'amount'}]

    def get_previous_value(self) -> float:
        """获取前一日的组合市值"""
        if self.daily_states:
            return self.daily_states[-1]['portfolio_value']
        return self.initial_capital

    def update_daily_state(self, date: str, prices: Dict[str, float], trades: List[Dict]):
        """
        更新每日组合状态

        Args:
            date: 日期 (YYYY-MM-DD)
            prices: 价格字典 {symbol: close_price}
            trades: 当日交易列表 [{'symbol': '510300.SH', 'action': 'buy', 'shares': 100, 'price': 4.5, 'amount': 450}]

        Returns:
            当日状态字典
        """
        # 1. 计算持仓市值
        portfolio_value = self.cash
        holdings_detail = []

        for symbol, position in self.holdings.items():
            shares = position['shares']
            price = prices.get(symbol, 0)

            if price > 0:
                market_value = shares * price
                portfolio_value += market_value

                holdings_detail.append({
                    'symbol': symbol,
                    'shares': shares,
                    'avg_cost': position['avg_cost'],
                    'price': price,
                    'market_value': market_value,
                    'weight': market_value / portfolio_value if portfolio_value > 0 else 0
                })

        # 2. 计算收益率
        previous_value = self.get_previous_value()
        daily_return = (portfolio_value / previous_value - 1) if previous_value > 0 else 0
        cumulative_return = (portfolio_value / self.initial_capital - 1)

        # 3. 计算回撤
        max_drawdown = self._calculate_max_drawdown(portfolio_value)

        # 4. 计算换手率
        turnover_rate = self._calculate_turnover_rate(window=20)

        # 5. 构建状态字典
        state = {
            'date': date,
            'portfolio_value': portfolio_value,
            'daily_return': daily_return,
            'cumulative_return': cumulative_return,
            'cash': self.cash,
            'holdings': holdings_detail,
            'trades_today': trades,
            'daily_max_drawdown': max_drawdown['daily'],
            'running_max_drawdown': max_drawdown['running'],
            'turnover_rate': turnover_rate,
            'position_count': len(self.holdings)
        }

        self.daily_states.append(state)

        return state

    def _calculate_max_drawdown(self, current_value: float) -> Dict:
        """
        计算最大回撤

        Args:
            current_value: 当前组合市值

        Returns:
            {'daily': 当日回撤, 'running': 运行最大回撤}
        """
        if not self.daily_states:
            return {'daily': 0.0, 'running': 0.0}

        # 获取所有历史净值
        all_values = [s['portfolio_value'] for s in self.daily_states] + [current_value]

        # 计算历史最高点
        peak = max(all_values)

        # 当日回撤
        daily_drawdown = (current_value - peak) / peak if peak > 0 else 0

        # 运行最大回撤
        running_max_dd = min(s['running_max_drawdown'] for s in self.daily_states)
        running_max_dd = min(running_max_dd, daily_drawdown)

        return {
            'daily': daily_drawdown,
            'running': running_max_dd
        }

    def _calculate_turnover_rate(self, window: int = 20) -> float:
        """
        计算换手率（滚动N日）

        公式：换手率 = (买入金额 + 卖出金额) / (2 × 平均组合市值)

        Args:
            window: 滚动窗口天数，默认20日

        Returns:
            换手率（0-1之间的小数）
        """
        if not self.transaction_history:
            return 0.0

        # 获取最近的交易日期
        last_trade_date = None
        if self.transaction_history:
            last_trade_date = self.transaction_history[-1]['date']

        if last_trade_date is None:
            return 0.0

        # 筛选最近N天的交易
        if isinstance(last_trade_date, str):
            last_trade_date = datetime.strptime(last_trade_date, '%Y-%m-%d').date()

        recent_trades = []
        for trade in self.transaction_history:
            trade_date = trade['date']
            if isinstance(trade_date, str):
                trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
            elif isinstance(trade_date, datetime):
                trade_date = trade_date.date()

            days_diff = (last_trade_date - trade_date).days
            if days_diff < window:
                recent_trades.append(trade)

        if not recent_trades:
            return 0.0

        # 计算买入和卖出金额
        buy_amount = sum(t['amount'] for t in recent_trades if t['action'] == 'buy')
        sell_amount = sum(t['amount'] for t in recent_trades if t['action'] == 'sell')

        # 计算平均组合市值
        window_states = self.daily_states[-window:] if len(self.daily_states) >= window else self.daily_states
        if not window_states:
            return 0.0

        avg_portfolio_value = sum(s['portfolio_value'] for s in window_states) / len(window_states)

        if avg_portfolio_value == 0:
            return 0.0

        turnover = (buy_amount + sell_amount) / (2 * avg_portfolio_value)
        return turnover

    def add_transaction(self, date: str, symbol: str, action: str, shares: int, price: float, amount: float):
        """
        添加交易记录

        Args:
            date: 交易日期
            symbol: 标的代码
            action: 'buy' or 'sell'
            shares: 交易数量
            price: 交易价格
            amount: 交易金额
        """
        self.transaction_history.append({
            'date': datetime.strptime(date, '%Y-%m-%d').date() if isinstance(date, str) else date,
            'symbol': symbol,
            'action': action,
            'shares': shares,
            'price': price,
            'amount': amount
        })

    def update_position(self, symbol: str, shares: int, avg_cost: float):
        """
        更新持仓

        Args:
            symbol: 标的代码
            shares: 持仓数量
            avg_cost: 平均成本
        """
        if shares > 0:
            self.holdings[symbol] = {
                'shares': shares,
                'avg_cost': avg_cost
            }
        elif symbol in self.holdings:
            del self.holdings[symbol]

    def get_current_holdings_value(self, prices: Dict[str, float]) -> float:
        """
        获取当前持仓市值

        Args:
            prices: 价格字典

        Returns:
            持仓总市值
        """
        total_value = 0.0
        for symbol, position in self.holdings.items():
            price = prices.get(symbol, 0)
            if price > 0:
                total_value += position['shares'] * price
        return total_value

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """
        获取组合总市值（持仓 + 现金）

        Args:
            prices: 价格字典

        Returns:
            组合总市值
        """
        return self.cash + self.get_current_holdings_value(prices)

    def get_holdings_summary(self) -> List[Dict]:
        """
        获取持仓摘要

        Returns:
            持仓列表 [{'symbol', 'shares', 'avg_cost'}]
        """
        return [
            {
                'symbol': symbol,
                'shares': position['shares'],
                'avg_cost': position['avg_cost']
            }
            for symbol, position in self.holdings.items()
        ]

    def reset(self):
        """重置追踪器（用于重新开始回测）"""
        self.cash = self.initial_capital
        self.holdings = {}
        self.daily_states = []
        self.transaction_history = []

    def get_summary(self) -> Dict:
        """
        获取追踪器摘要

        Returns:
            摘要字典
        """
        if not self.daily_states:
            return {
                'initial_capital': self.initial_capital,
                'current_value': self.initial_capital,
                'total_return': 0.0,
                'daily_states_count': 0,
                'total_trades': len(self.transaction_history),
                'current_holdings': len(self.holdings)
            }

        last_state = self.daily_states[-1]

        return {
            'initial_capital': self.initial_capital,
            'current_value': last_state['portfolio_value'],
            'total_return': last_state['cumulative_return'],
            'daily_states_count': len(self.daily_states),
            'total_trades': len(self.transaction_history),
            'current_holdings': len(self.holdings),
            'max_drawdown': min(s['running_max_drawdown'] for s in self.daily_states),
            'avg_turnover_rate': np.mean([s['turnover_rate'] for s in self.daily_states])
        }
