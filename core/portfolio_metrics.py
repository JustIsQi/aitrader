"""
组合绩效指标计算器

计算高级绩效指标，包括：
- Sortino比率（只考虑下行波动）
- Calmar比率（年化收益/最大回撤）
- VaR (Value at Risk)
- CVaR (Conditional VaR)
- 月度收益
- 胜率（日/周/月）
- 信息比率（相对基准）
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from loguru import logger


class PortfolioMetrics:
    """组合绩效指标计算器"""

    def __init__(self, daily_states: List[Dict], risk_free_rate: float = 0.03):
        """
        初始化绩效指标计算器

        Args:
            daily_states: 每日状态列表（从PortfolioStateTracker获取）
            risk_free_rate: 无风险利率，默认3%
        """
        self.daily_states = daily_states
        self.risk_free_rate = risk_free_rate
        self.returns = self._extract_returns()

    def _extract_returns(self) -> np.ndarray:
        """
        提取每日收益率

        Returns:
            每日收益率数组
        """
        if not self.daily_states:
            return np.array([])

        returns = []
        for state in self.daily_states:
            returns.append(state.get('daily_return', 0.0))

        return np.array(returns)

    def calculate_sortino_ratio(self) -> float:
        """
        计算Sortino比率（只考虑下行波动）

        公式: (年化收益 - 无风险利率) / 下行标准差

        Returns:
            Sortino比率
        """
        if len(self.returns) == 0:
            return 0.0

        # 年化收益
        annual_return = self._calculate_annual_return()

        # 下行波动率（只考虑负收益）
        downside_returns = self.returns[self.returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0

        if downside_std == 0:
            return 0.0

        sortino = (annual_return - self.risk_free_rate) / downside_std
        return sortino

    def calculate_calmar_ratio(self) -> float:
        """
        计算Calmar比率

        公式: 年化收益 / |最大回撤|

        Returns:
            Calmar比率
        """
        if not self.daily_states:
            return 0.0

        # 年化收益
        annual_return = self._calculate_annual_return()

        # 最大回撤
        max_dd = min(s['running_max_drawdown'] for s in self.daily_states)

        if max_dd == 0:
            return 0.0

        calmar = annual_return / abs(max_dd)
        return calmar

    def calculate_var(self, confidence: float = 0.95) -> float:
        """
        计算VaR（Value at Risk，风险价值）

        在给定置信水平下的最大损失比例

        Args:
            confidence: 置信水平，默认95%

        Returns:
            VaR值（负数表示损失）
        """
        if len(self.returns) == 0:
            return 0.0

        # 计算分位数
        var = np.percentile(self.returns, (1 - confidence) * 100)
        return var

    def calculate_cvar(self, confidence: float = 0.95) -> float:
        """
        计算CVaR（Conditional VaR，条件风险价值/期望损失）

        超过VaR的损失的平均值

        Args:
            confidence: 置信水平，默认95%

        Returns:
            CVaR值（负数表示损失）
        """
        if len(self.returns) == 0:
            return 0.0

        var = self.calculate_var(confidence)

        # 计算小于等于VaR的收益率的平均值
        cvar = self.returns[self.returns <= var].mean()

        # 如果没有超过VaR的值，返回VaR
        if np.isnan(cvar):
            return var

        return cvar

    def calculate_monthly_returns(self) -> Dict[str, float]:
        """
        计算月度收益

        Returns:
            月度收益字典 {'2024-01': 0.05, '2024-02': -0.03, ...}
        """
        if not self.daily_states:
            return {}

        monthly_returns = {}

        for state in self.daily_states:
            date = pd.to_datetime(state['date'])
            month_key = f"{date.year}-{date.month:02d}"

            if month_key not in monthly_returns:
                monthly_returns[month_key] = []

            monthly_returns[month_key].append(state['daily_return'])

        # 计算每月累计收益
        monthly_cumulative = {}
        for month, returns in monthly_returns.items():
            # (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
            monthly_cumulative[month] = (np.array(returns) + 1).prod() - 1

        return monthly_cumulative

    def calculate_win_rate(self) -> Dict[str, float]:
        """
        计算胜率（日胜率、周胜率、月胜率）

        Returns:
            胜率字典 {'daily': 60.0, 'weekly': 65.0, 'monthly': 70.0}
        """
        if len(self.returns) == 0:
            return {'daily': 0.0, 'weekly': 0.0, 'monthly': 0.0}

        # 日胜率
        daily_win_rate = (self.returns > 0).sum() / len(self.returns) * 100

        # 周胜率（聚合周收益）
        weekly_returns = []
        for i in range(0, len(self.returns), 5):
            week_returns = self.returns[i:i+5]
            if len(week_returns) > 0:
                weekly_returns.append((week_returns + 1).prod() - 1)

        if weekly_returns:
            weekly_win_rate = (np.array(weekly_returns) > 0).sum() / len(weekly_returns) * 100
        else:
            weekly_win_rate = 0.0

        # 月胜率
        monthly_returns_dict = self.calculate_monthly_returns()
        if monthly_returns_dict:
            monthly_win_rate = sum(1 for r in monthly_returns_dict.values() if r > 0) / len(monthly_returns_dict) * 100
        else:
            monthly_win_rate = 0.0

        return {
            'daily': daily_win_rate,
            'weekly': weekly_win_rate,
            'monthly': monthly_win_rate
        }

    def calculate_information_ratio(self, benchmark_returns: np.ndarray) -> float:
        """
        计算信息比率（相对基准的超额收益/跟踪误差）

        Args:
            benchmark_returns: 基准收益率数组（与self.returns长度相同）

        Returns:
            信息比率
        """
        if len(self.returns) == 0 or len(benchmark_returns) != len(self.returns):
            return 0.0

        # 超额收益
        excess_returns = self.returns - benchmark_returns

        # 跟踪误差（超额收益的标准差）
        tracking_error = excess_returns.std() * np.sqrt(252)

        if tracking_error == 0:
            return 0.0

        # 信息比率（年化超额收益 / 跟踪误差）
        ir = excess_returns.mean() * 252 / tracking_error
        return ir

    def _calculate_annual_return(self) -> float:
        """
        计算年化收益率

        Returns:
            年化收益率
        """
        if not self.daily_states:
            return 0.0

        first_state = self.daily_states[0]
        last_state = self.daily_states[-1]

        total_return = last_state['cumulative_return']

        # 计算天数
        days = len(self.daily_states)

        # 年化收益: (1 + total_return) ^ (252 / days) - 1
        annual_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0

        return annual_return

    def calculate_all_metrics(self) -> Dict:
        """
        计算所有绩效指标

        Returns:
            所有指标的字典
        """
        if not self.daily_states:
            return {}

        annual_return = self._calculate_annual_return()

        # 计算波动率
        volatility = self.returns.std() * np.sqrt(252) if len(self.returns) > 0 else 0

        # 计算夏普比率
        sharpe_ratio = (annual_return - self.risk_free_rate) / volatility if volatility > 0 else 0

        # 最大回撤
        max_drawdown = min(s['running_max_drawdown'] for s in self.daily_states)

        # 高级指标
        sortino_ratio = self.calculate_sortino_ratio()
        calmar_ratio = self.calculate_calmar_ratio()
        var_95 = self.calculate_var(0.95)
        cvar_95 = self.calculate_cvar(0.95)

        # 胜率
        win_rates = self.calculate_win_rate()

        # 月度收益
        monthly_returns = self.calculate_monthly_returns()

        # 平均换手率
        avg_turnover_rate = np.mean([s['turnover_rate'] for s in self.daily_states])

        return {
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'win_rates': win_rates,
            'monthly_returns': monthly_returns,
            'avg_turnover_rate': avg_turnover_rate
        }

    def get_equity_curve(self) -> List[Dict]:
        """
        获取净值曲线

        Returns:
            净值曲线列表 [{'date': '2024-01-01', 'value': 1000000}, ...]
        """
        if not self.daily_states:
            return []

        return [
            {
                'date': state['date'],
                'value': state['portfolio_value']
            }
            for state in self.daily_states
        ]

    def get_drawdown_series(self) -> List[Dict]:
        """
        获取回撤序列

        Returns:
            回撤序列列表 [{'date': '2024-01-01', 'drawdown': -0.05}, ...]
        """
        if not self.daily_states:
            return []

        return [
            {
                'date': state['date'],
                'drawdown': state['running_max_drawdown']
            }
            for state in self.daily_states
        ]

    def get_returns_distribution(self) -> Dict:
        """
        获取收益率分布统计

        Returns:
            分布统计字典
        """
        if len(self.returns) == 0:
            return {}

        return {
            'mean': float(self.returns.mean()),
            'std': float(self.returns.std()),
            'min': float(self.returns.min()),
            'max': float(self.returns.max()),
            'median': float(np.median(self.returns)),
            'skewness': float(self._calculate_skewness()),
            'kurtosis': float(self._calculate_kurtosis())
        }

    def _calculate_skewness(self) -> float:
        """计算偏度"""
        from scipy import stats
        if len(self.returns) < 3:
            return 0.0
        return stats.skew(self.returns)

    def _calculate_kurtosis(self) -> float:
        """计算峰度"""
        from scipy import stats
        if len(self.returns) < 4:
            return 0.0
        return stats.kurtosis(self.returns)
