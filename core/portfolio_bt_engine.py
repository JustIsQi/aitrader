"""
ETF组合回测引擎

与 bt_engine.py 的区别：
- bt_engine: 单一标的轮动策略（TopK选股，每次只持有1-2个标的）
- portfolio_bt_engine: 组合策略（将符合条件的所有标的打包成组合，同时持有多个）

核心功能：
1. 按策略信号筛选符合条件的标的
2. 构建等权组合
3. 信号变化时触发再平衡
4. 记录每日组合状态（净值、持仓、换手率、回撤等）
5. 计算高级绩效指标（Sortino、Calmar、VaR、胜率等）
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from loguru import logger

from datafeed.db_dataloader import DbDataLoader
from database.factor_cache import FactorCache
from core.portfolio_tracker import PortfolioStateTracker
from core.portfolio_metrics import PortfolioMetrics
from database.pg_manager import get_db


@dataclass
class PortfolioTask:
    """组合回测任务配置"""
    name: str  # 策略名称
    symbols: List[str]  # 标的池
    start_date: str  # 开始日期 (YYYYMMDD)
    end_date: str  # 结束日期 (YYYYMMDD)

    # 资金配置
    initial_capital: float = 1000000  # 初始资金
    commission_rate: float = 0.0003  # 手续费率（万三）

    # 基准
    benchmark: str = '510300.SH'  # 基准代码

    # 信号条件（复用现有信号生成器）
    select_buy: List[str] = field(default_factory=list)  # 买入条件
    buy_at_least_count: int = 0  # 至少满足N个买入条件
    select_sell: List[str] = field(default_factory=list)  # 卖出条件
    sell_at_least_count: int = 1  # 至少满足N个卖出条件

    # 组合配置
    weight_type: str = 'equal'  # 权重类型（目前仅支持'equal'）
    rebalance_on_signal_change: bool = True  # 信号变化时再平衡


class PortfolioBacktestEngine:
    """ETF组合回测引擎"""

    def __init__(self, task: PortfolioTask):
        """
        初始化组合回测引擎

        Args:
            task: 组合回测任务配置
        """
        self.task = task
        self.db = get_db()
        self.tracker = PortfolioStateTracker(initial_capital=task.initial_capital)

        # 加载数据
        self._load_data()

        logger.info(f"初始化组合回测引擎: {task.name}")
        logger.info(f"标的池: {len(task.symbols)} 个标的")
        logger.info(f"日期范围: {task.start_date} ~ {task.end_date}")

    def _load_data(self):
        """加载价格数据"""
        logger.info("加载价格数据...")

        # 加载所有标的的价格数据
        raw_data = DbDataLoader().read_dfs(
            symbols=self.task.symbols,
            start_date=self.task.start_date,
            end_date=self.task.end_date
        )

        # 将日期设为索引（DbDataLoader返回的数据框没有日期索引）
        self.price_data = {}
        for symbol, df in raw_data.items():
            if 'date' in df.columns and not df.empty:
                df_copy = df.copy()
                df_copy['date'] = pd.to_datetime(df_copy['date'])
                df_copy = df_copy.set_index('date')
                df_copy = df_copy.sort_index()
                self.price_data[symbol] = df_copy
            else:
                self.price_data[symbol] = df

        # 初始化因子缓存
        all_factors = list(set(self.task.select_buy + self.task.select_sell))
        self.factor_cache = None  # 延迟初始化，节省内存

        logger.info(f"价格数据加载完成，共 {len(self.price_data)} 个标的")

    def run(self) -> Dict:
        """
        运行组合回测

        Returns:
            回测结果字典，包含所有绩效指标
        """
        logger.info(f"开始组合回测...")

        # 获取交易日列表
        trading_days = self._get_trading_days()
        logger.info(f"交易日数量: {len(trading_days)}")

        # 逐日模拟
        previous_signals = None
        rebalance_count = 0

        for i, date in enumerate(trading_days):
            if i % 50 == 0:
                logger.info(f"处理进度: {i}/{len(trading_days)} ({i/len(trading_days)*100:.1f}%)")

            # 1. 获取当前价格
            prices = self._get_prices(date)

            # 2. 使用信号生成器获取当前信号
            current_signals = self._get_signals(date)

            # 3. 检查信号是否变化（再平衡触发）
            if self._should_rebalance(current_signals, previous_signals):
                logger.debug(f"{date}: 信号变化，触发再平衡")
                logger.debug(f"  当前标的: {current_signals}")
                logger.debug(f"  前次标的: {previous_signals}")

                # 4. 生成目标组合（等权）
                if current_signals:
                    target_portfolio = self._generate_target_portfolio(current_signals)

                    # 5. 执行再平衡交易
                    trades = self._execute_rebalance(date, target_portfolio, prices)

                    # 记录交易历史
                    for trade in trades:
                        self.tracker.add_transaction(
                            date=date,
                            symbol=trade['symbol'],
                            action=trade['action'],
                            shares=trade['shares'],
                            price=trade['price'],
                            amount=trade['amount']
                        )

                    rebalance_count += 1
                else:
                    # 如果没有符合条件的标的，清空持仓
                    trades = self._close_all_positions(date, prices)
                    logger.debug(f"{date}: 无符合条件的标的，清空持仓")

                previous_signals = current_signals
            else:
                trades = []

            # 6. 更新每日状态（净值、回撤、换手率）
            self.tracker.update_daily_state(date, prices, trades)

        logger.info(f"回测完成，共再平衡 {rebalance_count} 次")

        # 计算最终指标
        metrics = self._calculate_final_metrics()

        # 保存到数据库
        if self.task.name:
            self._save_results(metrics)

        return metrics

    def _get_trading_days(self) -> List[str]:
        """
        获取交易日列表

        Returns:
            交易日列表 ['2024-01-01', '2024-01-02', ...]
        """
        if not self.price_data:
            return []

        # 使用第一个标的的交易日作为基准
        first_symbol = list(self.price_data.keys())[0]
        df = self.price_data[first_symbol]

        # 筛选日期范围
        start = pd.to_datetime(self.task.start_date)
        end = pd.to_datetime(self.task.end_date)

        df_dates = pd.to_datetime(df.index)
        trading_days = df_dates[(df_dates >= start) & (df_dates <= end)]

        return [d.strftime('%Y-%m-%d') for d in trading_days]

    def _get_prices(self, date: str) -> Dict[str, float]:
        """
        获取指定日期的价格

        Args:
            date: 日期 (YYYY-MM-DD)

        Returns:
            价格字典 {symbol: close_price}
        """
        prices = {}
        target_date = pd.to_datetime(date)

        for symbol, df in self.price_data.items():
            if df.empty or 'close' not in df.columns:
                continue

            # 找到最接近日期的数据
            df_dates = pd.to_datetime(df.index)

            # 筛选 <= target_date 的数据
            valid_dates = df_dates[df_dates <= target_date]

            if len(valid_dates) > 0:
                closest_date = valid_dates.max()
                prices[symbol] = df.loc[closest_date, 'close']

        return prices

    def _get_signals(self, date: str) -> List[str]:
        """
        使用信号生成器获取符合条件的标的列表

        Args:
            date: 日期 (YYYY-MM-DD)

        Returns:
            符合条件的标的列表 ['510300.SH', '510500.SH', ...]
        """
        # 延迟初始化因子缓存
        if self.factor_cache is None:
            all_factors = list(set(self.task.select_buy + self.task.select_sell))
            self.factor_cache = FactorCache(
                symbols=self.task.symbols,
                start_date='20200101',  # 扩展起始日期以便计算因子
                end_date=self.task.end_date
            )
            self.factor_cache.calculate_factors(all_factors)

        buy_symbols = []

        for symbol in self.task.symbols:
            # 检查买入条件
            buy_count = 0
            for condition in self.task.select_buy:
                try:
                    df_factor = self.factor_cache.get_factor(condition)
                    if df_factor is None:
                        continue

                    # 转换日期格式
                    date_formatted = date.replace('-', '')

                    if date_formatted in df_factor.index and symbol in df_factor.columns:
                        value = df_factor.loc[date_formatted, symbol]
                        if pd.notna(value) and value:
                            buy_count += 1
                except Exception as e:
                    logger.debug(f"检查买入条件失败 {symbol} {condition}: {e}")
                    continue

            # 判断是否满足买入条件
            threshold = self.task.buy_at_least_count if self.task.buy_at_least_count > 0 else len(self.task.select_buy)
            if buy_count >= threshold:
                # 检查卖出条件
                sell_count = 0
                for condition in self.task.select_sell:
                    try:
                        df_factor = self.factor_cache.get_factor(condition)
                        if df_factor is None:
                            continue

                        date_formatted = date.replace('-', '')

                        if date_formatted in df_factor.index and symbol in df_factor.columns:
                            value = df_factor.loc[date_formatted, symbol]
                            if pd.notna(value) and value:
                                sell_count += 1
                    except Exception as e:
                        logger.debug(f"检查卖出条件失败 {symbol} {condition}: {e}")
                        continue

                # 如果不满足卖出条件，则买入
                if sell_count < self.task.sell_at_least_count:
                    buy_symbols.append(symbol)

        return buy_symbols

    def _should_rebalance(self, current_signals: List[str], previous_signals: Optional[List[str]]) -> bool:
        """
        信号变化时触发再平衡

        Args:
            current_signals: 当前信号列表
            previous_signals: 前一次信号列表

        Returns:
            True 表示需要再平衡
        """
        if previous_signals is None:
            return True  # 首次运行

        return set(current_signals) != set(previous_signals)

    def _generate_target_portfolio(self, symbols: List[str]) -> Dict[str, float]:
        """
        生成等权组合

        Args:
            symbols: 标的列表

        Returns:
            权重字典 {symbol: weight}
        """
        if not symbols:
            return {}

        n = len(symbols)
        weight = 1.0 / n

        return {symbol: weight for symbol in symbols}

    def _execute_rebalance(self, date: str, target_weights: Dict[str, float], prices: Dict[str, float]) -> List[Dict]:
        """
        执行再平衡交易

        Args:
            date: 交易日期
            target_weights: 目标权重 {symbol: weight}
            prices: 当前价格

        Returns:
            交易列表
        """
        trades = []
        portfolio_value = self.tracker.get_previous_value()

        # 1. 计算目标持仓数量
        target_shares = {}
        for symbol, weight in target_weights.items():
            target_value = portfolio_value * weight
            price = prices.get(symbol, 0)

            if price > 0:
                # 整手交易（100股）
                shares = int(target_value / price / 100) * 100
                if shares > 0:
                    target_shares[symbol] = shares

        # 2. 计算买卖差额
        current_shares = {s: p['shares'] for s, p in self.tracker.holdings.items()}
        all_symbols = set(current_shares.keys()) | set(target_shares.keys())

        for symbol in all_symbols:
            current = current_shares.get(symbol, 0)
            target = target_shares.get(symbol, 0)

            if target > current:
                # 买入
                buy_shares = target - current
                price = prices.get(symbol, 0)

                if price > 0:
                    amount = buy_shares * price
                    cost = amount * (1 + self.task.commission_rate)

                    if self.tracker.cash >= cost:
                        # 更新持仓
                        old_shares = current
                        old_cost = self.tracker.holdings.get(symbol, {}).get('shares', 0) * \
                                   self.tracker.holdings.get(symbol, {}).get('avg_cost', 0)
                        new_cost = old_cost + amount
                        new_shares = old_shares + buy_shares

                        self.tracker.update_position(symbol, new_shares, new_cost / new_shares if new_shares > 0 else 0)
                        self.tracker.cash -= cost

                        trades.append({
                            'symbol': symbol,
                            'action': 'buy',
                            'shares': buy_shares,
                            'price': price,
                            'amount': amount
                        })
                    else:
                        logger.debug(f"{date}: 资金不足，无法买入 {symbol} {buy_shares}股")

            elif target < current:
                # 卖出
                sell_shares = current - target
                price = prices.get(symbol, 0)

                if price > 0 and sell_shares > 0:
                    amount = sell_shares * price
                    proceeds = amount * (1 - self.task.commission_rate)

                    # 更新持仓
                    new_shares = current - sell_shares

                    if new_shares > 0:
                        # 保持平均成本不变
                        avg_cost = self.tracker.holdings[symbol]['avg_cost']
                        self.tracker.update_position(symbol, new_shares, avg_cost)
                    else:
                        # 清仓
                        if symbol in self.tracker.holdings:
                            del self.tracker.holdings[symbol]

                    self.tracker.cash += proceeds

                    trades.append({
                        'symbol': symbol,
                        'action': 'sell',
                        'shares': sell_shares,
                        'price': price,
                        'amount': amount
                    })

        return trades

    def _close_all_positions(self, date: str, prices: Dict[str, float]) -> List[Dict]:
        """
        清空所有持仓

        Args:
            date: 交易日期
            prices: 当前价格

        Returns:
            交易列表
        """
        trades = []

        for symbol, position in list(self.tracker.holdings.items()):
            shares = position['shares']
            price = prices.get(symbol, 0)

            if price > 0 and shares > 0:
                amount = shares * price
                proceeds = amount * (1 - self.task.commission_rate)

                self.tracker.cash += proceeds
                del self.tracker.holdings[symbol]

                trades.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'shares': shares,
                    'price': price,
                    'amount': amount
                })

        return trades

    def _calculate_final_metrics(self) -> Dict:
        """
        计算最终绩效指标

        Returns:
            指标字典
        """
        if not self.tracker.daily_states:
            logger.warning("没有每日状态数据，返回默认值")
            return {
                'strategy_name': self.task.name,
                'start_date': self.task.start_date,
                'end_date': self.task.end_date,
                'initial_capital': self.task.initial_capital,
                'final_value': self.task.initial_capital,
                'total_return': 0.0,
                'annual_return': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'max_drawdown': 0.0,
                'var_95': 0.0,
                'cvar_95': 0.0,
                'win_rates': {'daily': 0.0, 'weekly': 0.0, 'monthly': 0.0},
                'monthly_returns': {},
                'avg_turnover_rate': 0.0,
                'total_trades': 0,
                'equity_curve': [],
                'final_holdings': []
            }

        # 初始化指标计算器
        metrics_calculator = PortfolioMetrics(self.tracker.daily_states)

        # 获取基础指标
        final_state = self.tracker.daily_states[-1]
        total_return = final_state['cumulative_return']

        # 计算高级指标
        all_metrics = metrics_calculator.calculate_all_metrics()

        # 构建结果字典
        result = {
            'strategy_name': self.task.name,
            'start_date': self.task.start_date,
            'end_date': self.task.end_date,
            'initial_capital': self.task.initial_capital,
            'final_value': final_state['portfolio_value'],
            'total_return': total_return,
            'annual_return': all_metrics['annual_return'],
            'sharpe_ratio': all_metrics['sharpe_ratio'],
            'sortino_ratio': all_metrics['sortino_ratio'],
            'calmar_ratio': all_metrics['calmar_ratio'],
            'max_drawdown': all_metrics['max_drawdown'],
            'var_95': all_metrics['var_95'],
            'cvar_95': all_metrics['cvar_95'],
            'win_rates': all_metrics['win_rates'],
            'monthly_returns': all_metrics['monthly_returns'],
            'avg_turnover_rate': all_metrics['avg_turnover_rate'],
            'total_trades': len(self.tracker.transaction_history),
            'equity_curve': metrics_calculator.get_equity_curve(),
            'final_holdings': final_state['holdings']
        }

        logger.success(f"回测完成!")
        logger.success(f"总收益: {total_return*100:.2f}%")
        logger.success(f"年化收益: {result['annual_return']*100:.2f}%")
        logger.success(f"夏普比率: {result['sharpe_ratio']:.2f}")
        logger.success(f"最大回撤: {result['max_drawdown']*100:.2f}%")
        logger.success(f"Sortino比率: {result['sortino_ratio']:.2f}")
        logger.success(f"平均换手率: {result['avg_turnover_rate']*100:.2f}%")

        return result

    def _save_results(self, metrics: Dict):
        """
        保存回测结果到数据库

        Args:
            metrics: 回测指标字典
        """
        try:
            from database.models.models import StrategyBacktest
            from database.pg_manager import get_db
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            db = get_db()

            # 准备数据
            portfolio_config = {
                'weight_type': self.task.weight_type,
                'rebalance_on_signal_change': self.task.rebalance_on_signal_change,
                'select_buy': self.task.select_buy,
                'select_sell': self.task.select_sell,
                'buy_at_least_count': self.task.buy_at_least_count,
                'sell_at_least_count': self.task.sell_at_least_count
            }

            # 创建回测记录
            backtest = StrategyBacktest(
                strategy_name=self.task.name,
                asset_type='etf',
                start_date=datetime.strptime(self.task.start_date, '%Y%m%d').date(),
                end_date=datetime.strptime(self.task.end_date, '%Y%m%d').date(),
                initial_capital=self.task.initial_capital,

                # 回测类型
                backtest_type='portfolio',
                portfolio_config=portfolio_config,

                # 基础指标
                total_return=metrics['total_return'],
                annual_return=metrics['annual_return'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown=metrics['max_drawdown'],

                # 高级指标
                sortino_ratio=metrics.get('sortino_ratio'),
                calmar_ratio=metrics.get('calmar_ratio'),
                var_95=metrics.get('var_95'),
                cvar_95=metrics.get('cvar_95'),
                information_ratio=metrics.get('information_ratio'),
                avg_turnover_rate=metrics.get('avg_turnover_rate'),
                win_rates=metrics.get('win_rates'),
                monthly_returns=metrics.get('monthly_returns'),

                # 详细数据
                equity_curve=metrics['equity_curve'],
                final_holdings=metrics.get('final_holdings', []),

                # 交易统计
                total_trades=metrics['total_trades'],

                status='completed'
            )

            # 保存到数据库
            with db.get_session() as session:
                session.add(backtest)
                session.commit()
                logger.info(f"✓ 保存回测结果到数据库: ID={backtest.id}")

        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")
            import traceback
            traceback.print_exc()


# 便捷函数
def run_portfolio_backtest(
    name: str,
    symbols: List[str],
    start_date: str,
    end_date: str,
    select_buy: List[str],
    select_sell: List[str] = None,
    buy_at_least_count: int = 0,
    sell_at_least_count: int = 1,
    initial_capital: float = 1000000,
    commission_rate: float = 0.0003
) -> Dict:
    """
    快速运行组合回测

    使用示例:
        result = run_portfolio_backtest(
            name='ETF组合策略',
            symbols=['510300.SH', '510500.SH', '159915.SZ'],
            start_date='20200101',
            end_date='20251215',
            select_buy=['roc(close,20) > 0.05', 'ma(close,5) > ma(close,20)'],
            select_sell=['roc(close,20) < -0.05'],
            buy_at_least_count=2
        )

    Args:
        name: 策略名称
        symbols: 标的池
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        select_buy: 买入条件列表
        select_sell: 卖出条件列表
        buy_at_least_count: 至少满足N个买入条件
        sell_at_least_count: 至少满足N个卖出条件
        initial_capital: 初始资金
        commission_rate: 手续费率

    Returns:
        回测结果字典
    """
    task = PortfolioTask(
        name=name,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        select_buy=select_buy,
        select_sell=select_sell or [],
        buy_at_least_count=buy_at_least_count,
        sell_at_least_count=sell_at_least_count,
        initial_capital=initial_capital,
        commission_rate=commission_rate
    )

    engine = PortfolioBacktestEngine(task)
    return engine.run()
