"""
风险平价ETF策略 - ETF Risk Parity Strategy

核心理念:
- 每只ETF对组合的风险贡献相等
- 高波动ETF低配，低波动ETF高配
- 目标: 获得更稳定的收益(提升夏普比率)

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask
from database.pg_manager import get_db


@dataclass
class RiskParityConfig:
    """风险平价配置"""
    # 波动率计算窗口
    volatility_window: int = 60  # 日

    # 目标风险贡献比例 (None表示等风险贡献)
    target_risk_contributions: Dict[str, float] = None

    # 最小和最大权重限制
    min_weight: float = 0.05  # 最小5%
    max_weight: float = 0.40  # 最大40%

    # 再平衡频率
    rebalance_frequency: str = 'monthly'  # daily, weekly, monthly

    # 是否使用EWMA波动率（对近期波动赋予更高权重，应对极端行情）
    use_ewm_volatility: bool = True

    # 是否使用协方差矩阵 (考虑相关性)
    use_covariance: bool = False

    # 信号过滤 (只有符合条件的ETF才参与配置)
    select_buy: List[str] = None
    buy_at_least_count: int = 0

    # 组合级风控
    target_annual_vol: Optional[float] = 0.12
    max_total_weight: float = 0.95
    risk_multiplier_min: float = 0.0
    risk_multiplier_max: float = 1.0
    risk_off_drawdown_trigger: Optional[float] = -0.10
    risk_off_drawdown_exit: Optional[float] = -0.05
    risk_off_multiplier: float = 0.35


class RiskParityCalculator:
    """风险平价权重计算器"""

    @staticmethod
    def calculate_inverse_volatility_weights(
        prices: pd.DataFrame,
        window: int = 60,
        min_weight: float = 0.05,
        max_weight: float = 0.40,
        use_ewm: bool = True
    ) -> Dict[str, float]:
        """
        计算 inverse volatility 权重

        权重 ∝ 1/波动率

        Args:
            prices: 价格数据 {symbol: Series} 或 DataFrame (columns=symbols)
            window: 波动率计算窗口
            min_weight: 最小权重
            max_weight: 最大权重
            use_ewm: 是否使用EWMA波动率（混合EWMA与滚动，对近期波动更敏感）

        Returns:
            {symbol: weight} 权重字典
        """
        # 转换为DataFrame格式
        if isinstance(prices, dict):
            df = pd.DataFrame(prices)
        else:
            df = prices

        # 计算收益率
        returns = df.pct_change().dropna()

        # 计算波动率
        if len(returns) >= window:
            recent_returns = returns.tail(window)
        else:
            recent_returns = returns

        if use_ewm and len(returns) >= max(20, window // 3):
            # EWMA波动率（对近期波动更敏感，极端行情反应更快）
            ewm_vol = returns.ewm(span=window, min_periods=max(20, window // 3)).std().iloc[-1]
            rolling_vol = recent_returns.std()
            # 混合: 70% EWMA + 30% 滚动（保持稳定性）
            volatilities = 0.7 * ewm_vol + 0.3 * rolling_vol
        else:
            volatilities = recent_returns.std()

        # 设置波动率下限，避免除零
        volatilities = volatilities.clip(lower=0.001)

        # 计算inverse volatility权重
        inv_vols = 1 / volatilities.replace(0, np.nan)
        inv_vols = inv_vols.fillna(0)

        # 归一化
        total = inv_vols.sum()
        if total > 0:
            weights = (inv_vols / total).to_dict()
        else:
            # 等权作为后备
            n = len(df.columns)
            weights = {col: 1/n for col in df.columns}

        # 应用权重限制
        weights = RiskParityCalculator._apply_weight_limits(
            weights, min_weight, max_weight
        )

        # 重新归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}

        return weights

    @staticmethod
    def calculate_risk_parity_weights(
        prices: pd.DataFrame,
        window: int = 60,
        max_iterations: int = 100,
        tolerance: float = 1e-6
    ) -> Dict[str, float]:
        """
        计算真正的风险平价权重

        使用迭代方法使得每个资产的风险贡献相等

        Args:
            prices: 价格数据
            window: 波动率计算窗口
            max_iterations: 最大迭代次数
            tolerance: 收敛容差

        Returns:
            {symbol: weight} 权重字典
        """
        if isinstance(prices, dict):
            df = pd.DataFrame(prices)
        else:
            df = prices

        # 计算收益率
        returns = df.pct_change().dropna()

        # 使用最近window期的数据
        if len(returns) >= window:
            recent_returns = returns.tail(window)
        else:
            recent_returns = returns

        # 计算协方差矩阵
        cov_matrix = recent_returns.cov()

        n_assets = len(cov_matrix)
        symbols = cov_matrix.columns.tolist()

        # 初始化等权重
        weights = np.ones(n_assets) / n_assets

        # 迭代求解
        for iteration in range(max_iterations):
            # 计算每个资产的风险贡献
            portfolio_var = np.dot(weights, np.dot(cov_matrix.values, weights))
            marginal_contrib = np.dot(cov_matrix.values, weights)
            risk_contrib = weights * marginal_contrib

            # 目标: 所有资产的风险贡献相等
            target_risk = portfolio_var / n_assets

            # 更新权重
            new_weights = weights.copy()
            for i in range(n_assets):
                if risk_contrib[i] > 0:
                    new_weights[i] = weights[i] * (target_risk / risk_contrib[i])

            # 归一化
            new_weights = new_weights / new_weights.sum()

            # 检查收敛
            if np.max(np.abs(new_weights - weights)) < tolerance:
                weights = new_weights
                break

            weights = new_weights

        return {symbols[i]: weights[i] for i in range(n_assets)}

    @staticmethod
    def _apply_weight_limits(
        weights: Dict[str, float],
        min_weight: float,
        max_weight: float
    ) -> Dict[str, float]:
        """应用权重限制"""
        return {
            k: max(min_weight, min(max_weight, v))
            for k, v in weights.items()
        }


class RiskParityETFTask(PortfolioTask):
    """风险平价ETF回测任务"""

    def __init__(self,
                 symbols: List[str],
                 start_date: str,
                 end_date: str,
                 config: RiskParityConfig = None,
                 benchmark: str = '510300.SH',
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.0003):
        super().__init__(
            name='风险平价ETF策略',
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            benchmark=benchmark,
            target_annual_vol=(config.target_annual_vol if config else 0.12),
            max_total_weight=(config.max_total_weight if config else 0.95),
            risk_multiplier_min=(config.risk_multiplier_min if config else 0.0),
            risk_multiplier_max=(config.risk_multiplier_max if config else 1.0),
            risk_off_drawdown_trigger=(config.risk_off_drawdown_trigger if config else -0.10),
            risk_off_drawdown_exit=(config.risk_off_drawdown_exit if config else -0.05),
            risk_off_multiplier=(config.risk_off_multiplier if config else 0.35),
        )
        self.config = config or RiskParityConfig()


class RiskParityETFEngine(PortfolioBacktestEngine):
    """
    风险平价ETF回测引擎

    继承自PortfolioBacktestEngine,使用风险平价权重
    """

    def __init__(self, task: RiskParityETFTask):
        super().__init__(task)
        self.rp_config = task.config

        # 信号条件
        self.select_buy = self.rp_config.select_buy or []
        self.buy_at_least_count = self.rp_config.buy_at_least_count

    def run(self) -> Dict:
        """运行风险平价回测"""
        logger.info(f"开始风险平价ETF回测: {self.task.name}")
        logger.info(f"风险平价配置: window={self.rp_config.volatility_window}, "
                   f"min_w={self.rp_config.min_weight}, max_w={self.rp_config.max_weight}")

        # 获取交易日列表
        trading_days = self._get_trading_days()
        logger.info(f"交易日数量: {len(trading_days)}")

        # 逐日模拟
        last_rebalance_date = None
        rebalance_count = 0
        current_weights = {}

        for i, date in enumerate(trading_days):
            if i % 50 == 0:
                logger.info(f"处理进度: {i}/{len(trading_days)} ({i/len(trading_days)*100:.1f}%)")
            trades = []

            # 判断是否需要再平衡
            should_rebalance = self._should_rebalance_by_frequency(
                date, last_rebalance_date
            )

            if should_rebalance:
                # 1. 筛选符合条件的ETF
                qualified_symbols = self._filter_qualified_symbols(date)

                if qualified_symbols:
                    # 2. 计算风险平价权重
                    new_weights = self._calculate_risk_parity_weights(
                        qualified_symbols, date
                    )
                    new_weights = self._apply_risk_controls(date, new_weights)

                    # 3. 检查权重变化
                    if new_weights != current_weights:
                        # 4. 执行再平衡
                        prices = self._get_prices(date)
                        trades = self._execute_weighted_rebalance(
                            date, new_weights, prices
                        )

                        for trade in trades:
                            self.tracker.add_transaction(
                                date=date,
                                symbol=trade['symbol'],
                                action=trade['action'],
                                shares=trade['shares'],
                                price=trade['price'],
                                amount=trade['amount'],
                                commission=trade.get('commission', 0.0),
                                realized_pnl=trade.get('realized_pnl', 0.0),
                            )

                        current_weights = new_weights
                        rebalance_count += 1
                        last_rebalance_date = date
                        logger.debug(f"{date}: 再平衡, 持仓 {list(new_weights.keys())}")

                else:
                    # 没有符合条件的标的,清空持仓
                    prices = self._get_prices(date)
                    trades = self._close_all_positions(date, prices)
                    for trade in trades:
                        self.tracker.add_transaction(
                            date=date,
                            symbol=trade['symbol'],
                            action=trade['action'],
                            shares=trade['shares'],
                            price=trade['price'],
                            amount=trade['amount'],
                            commission=trade.get('commission', 0.0),
                            realized_pnl=trade.get('realized_pnl', 0.0),
                        )
                    current_weights = {}

            # 更新每日状态
            prices = self._get_prices(date)
            self.tracker.update_daily_state(date, prices, trades)
            if self.tracker.daily_states:
                self.portfolio_return_history.append(self.tracker.daily_states[-1].get('daily_return', 0.0))
            if not self.benchmark_returns.empty:
                dt = pd.to_datetime(date)
                if dt in self.benchmark_returns.index:
                    self.benchmark_return_history.append(float(self.benchmark_returns.get(dt, 0.0)))

        logger.info(f"回测完成,共再平衡 {rebalance_count} 次")

        # 计算最终指标
        metrics = self._calculate_final_metrics()

        # 保存到数据库
        if self.task.name:
            self._save_results(metrics)

        return metrics

    def _should_rebalance_by_frequency(self, date: str, last_rebalance: str) -> bool:
        """根据频率判断是否需要再平衡"""
        if last_rebalance is None:
            return True

        freq = self.rp_config.rebalance_frequency
        current = pd.to_datetime(date)
        last = pd.to_datetime(last_rebalance)

        if freq == 'daily':
            return True
        elif freq == 'weekly':
            return current.isocalendar()[1] != last.isocalendar()[1]
        elif freq == 'monthly':
            return current.month != last.month or current.year != last.year
        else:
            return True

    def _filter_qualified_symbols(self, date: str) -> List[str]:
        """筛选符合条件的ETF"""
        if not self.select_buy or self.buy_at_least_count == 0:
            return self.task.symbols

        qualified = []

        for symbol in self.task.symbols:
            # 检查买入条件
            buy_count = 0
            for condition in self.select_buy:
                if self._check_single_condition(symbol, condition, date):
                    buy_count += 1

            if buy_count >= self.buy_at_least_count:
                qualified.append(symbol)

        return qualified

    def _check_single_condition(self, symbol: str, condition: str, date: str) -> bool:
        """检查单个条件"""
        try:
            df = self.price_data.get(symbol)
            if df is None or df.empty or 'close' not in df.columns:
                return False

            # 简化版条件检查
            if 'roc(close,20) > 0' in condition:
                threshold = float(condition.split('>')[1].strip().rstrip(')'))
                if len(df) > 20:
                    return (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) > threshold

            elif 'roc(close,60) > 0' in condition:
                threshold = float(condition.split('>')[1].strip().rstrip(')'))
                if len(df) > 60:
                    return (df['close'].iloc[-1] / df['close'].iloc[-61] - 1) > threshold

            return False
        except:
            return False

    def _calculate_risk_parity_weights(self, symbols: List[str], date: str) -> Dict[str, float]:
        """计算风险平价权重"""
        # 获取历史价格数据
        window = self.rp_config.volatility_window

        # 构建价格DataFrame
        prices_dict = {}
        for symbol in symbols:
            df = self.price_data.get(symbol)
            if df is not None and 'close' in df.columns:
                prices_dict[symbol] = df['close']

        if not prices_dict:
            return {s: 1/len(symbols) for s in symbols}

        prices_df = pd.DataFrame(prices_dict)

        # 计算权重
        if self.rp_config.use_covariance:
            weights = RiskParityCalculator.calculate_risk_parity_weights(
                prices_df, window=window
            )
        else:
            weights = RiskParityCalculator.calculate_inverse_volatility_weights(
                prices_df,
                window=window,
                min_weight=self.rp_config.min_weight,
                max_weight=self.rp_config.max_weight,
                use_ewm=self.rp_config.use_ewm_volatility
            )

        return weights

    def _execute_weighted_rebalance(self, date: str, target_weights: Dict[str, float],
                                   prices: Dict[str, float]) -> List[Dict]:
        """执行加权再平衡"""
        trades = []
        portfolio_value = self.tracker.get_previous_value()

        # 1. 计算目标持仓数量
        target_shares = {}
        for symbol, weight in target_weights.items():
            target_value = portfolio_value * weight
            price = prices.get(symbol, 0)

            if price > 0:
                shares = int(target_value / price / 100) * 100  # 整手
                if shares > 0:
                    target_shares[symbol] = shares

        # 2. 计算买卖差额 (先卖后买)
        current_shares = {s: p['shares'] for s, p in self.tracker.holdings.items()}
        all_symbols = set(current_shares.keys()) | set(target_shares.keys())

        for symbol in sorted(all_symbols):
            current = current_shares.get(symbol, 0)
            target = target_shares.get(symbol, 0)
            if target >= current:
                continue
            sell_shares = current - target
            price = prices.get(symbol, 0)
            if price <= 0 or sell_shares <= 0:
                continue
            amount = sell_shares * price
            commission = amount * self.task.commission_rate
            avg_cost = self.tracker.holdings.get(symbol, {}).get('avg_cost', 0.0)
            realized_pnl = (price - avg_cost) * sell_shares
            proceeds = amount - commission

            new_shares = current - sell_shares
            if new_shares > 0:
                self.tracker.update_position(symbol, new_shares, avg_cost)
            elif symbol in self.tracker.holdings:
                del self.tracker.holdings[symbol]

            self.tracker.cash += proceeds
            trades.append({
                'symbol': symbol,
                'action': 'sell',
                'shares': sell_shares,
                'price': price,
                'amount': amount,
                'commission': commission,
                'realized_pnl': realized_pnl,
            })

        for symbol in sorted(all_symbols):
            current = current_shares.get(symbol, 0)
            target = target_shares.get(symbol, 0)
            if target <= current:
                continue
            buy_shares = target - current
            price = prices.get(symbol, 0)
            if price <= 0:
                continue
            amount = buy_shares * price
            commission = amount * self.task.commission_rate
            cost = amount + commission

            if self.tracker.cash < cost:
                continue

            new_shares = current + buy_shares
            old_cost = self.tracker.holdings.get(symbol, {}).get('shares', 0) * \
                       self.tracker.holdings.get(symbol, {}).get('avg_cost', 0)
            new_cost = old_cost + amount

            self.tracker.update_position(symbol, new_shares,
                                         new_cost / new_shares if new_shares > 0 else 0)
            self.tracker.cash -= cost

            trades.append({
                'symbol': symbol,
                'action': 'buy',
                'shares': buy_shares,
                'price': price,
                'amount': amount,
                'commission': commission,
                'realized_pnl': 0.0,
            })

        return trades


# 便捷函数
def run_risk_parity_etf(
        symbols: List[str],
        start_date: str = '20220101',
        end_date: str = None,
        config: RiskParityConfig = None,
        benchmark: str = '510300.SH',
        initial_capital: float = 1000000,
        commission_rate: float = 0.0003
) -> Dict:
    """
    快速运行风险平价ETF回测

    Args:
        symbols: ETF池
        start_date: 开始日期
        end_date: 结束日期 (None则使用当前日期)
        config: 风险平价配置
        benchmark: 基准
        initial_capital: 初始资金
        commission_rate: 手续费率

    Returns:
        回测结果字典
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    if config is None:
        config = RiskParityConfig(
            volatility_window=60,
            min_weight=0.10,
            max_weight=0.30,
            rebalance_frequency='monthly'
        )

    task = RiskParityETFTask(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        config=config,
        benchmark=benchmark,
        initial_capital=initial_capital,
        commission_rate=commission_rate
    )

    engine = RiskParityETFEngine(task)
    return engine.run()


if __name__ == '__main__':
    """测试代码"""
    logger.info('风险平价ETF策略测试')

    # 测试: 默认ETF池
    test_symbols = [
        '510300.SH',  # 沪深300ETF
        '510500.SH',  # 中证500ETF
        '159915.SZ',  # 创业板ETF
        '513100.SH',  # 纳指100ETF
        '518880.SH',  # 黄金ETF
        '511010.SH',  # 国债ETF
    ]

    result = run_risk_parity_etf(
        symbols=test_symbols,
        start_date='20220101'
    )

    # 打印结果
    print("\n" + "="*60)
    print(f"策略名称: {result['strategy_name']}")
    print(f"回测期间: {result['start_date']} ~ {result['end_date']}")
    print("="*60)
    print(f"总收益: {result['total_return']*100:.2f}%")
    print(f"年化收益: {result['annual_return']*100:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"Sortino比率: {result['sortino_ratio']:.2f}")
    print(f"Calmar比率: {result['calmar_ratio']:.2f}")
    print(f"最大回撤: {result['max_drawdown']*100:.2f}%")
    print("="*60)
