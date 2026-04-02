"""
优化版ETF组合策略 - Optimized ETF Portfolio Strategy

在原有策略基础上优化:
1. 改进买入条件: 多维度确认(动量+趋势+技术面)
2. 添加仓位管理: 根据信号强度动态调整仓位
3. 添加止损/止盈: ATR动态止损

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger

from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask


@dataclass
class OptimizedPortfolioConfig:
    """优化策略配置"""
    # 仓位管理
    use_position_sizing: bool = True  # 是否根据信号强度调整仓位
    min_position_weight: float = 0.05  # 最小单个持仓权重
    max_position_weight: float = 0.30  # 最大单个持仓权重

    # 止损止盈
    use_atr_stop_loss: bool = True  # 使用ATR动态止损
    atr_stop_loss_multiplier: float = 2.0  # ATR止损倍数
    atr_take_profit_multiplier: float = 3.0  # ATR止盈倍数

    # 信号强度计算权重
    signal_weights: Dict[str, float] = None  # 各信号条件权重

    # 最大持仓数
    max_positions: int = 10

    def __post_init__(self):
        if self.signal_weights is None:
            self.signal_weights = {
                'momentum_short': 0.30,  # 短期动量
                'momentum_long': 0.30,   # 长期动量
                'trend': 0.25,          # 趋势强度
                'volume': 0.15,          # 成交量确认
            }


class OptimizedETFPortfolioEngine(PortfolioBacktestEngine):
    """
    优化版ETF组合策略引擎

    改进点:
    1. 更严格的买入条件(多维度确认)
    2. 根据信号强度分配权重
    3. ATR动态止损止盈
    """

    def __init__(self, task: PortfolioTask, config: OptimizedPortfolioConfig = None):
        super().__init__(task)
        self.config = config or OptimizedPortfolioConfig()

        # 存储每个持仓的入场价格和止损价
        self.entry_prices: Dict[str, float] = {}
        self.stop_losses: Dict[str, float] = {}
        self.take_profits: Dict[str, float] = {}

    def run(self) -> Dict:
        """运行优化策略回测"""
        logger.info(f"开始优化版ETF组合策略回测: {self.task.name}")
        logger.info(f"优化配置: 仓位管理={self.config.use_position_sizing}, "
                   f"ATR止损={self.config.use_atr_stop_loss}")

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

            # 2. 检查止损止盈
            self._check_stop_loss_take_profit(date, prices)

            # 3. 使用信号生成器获取当前信号
            current_signals = self._get_optimized_signals(date)

            # 4. 检查信号是否变化
            if self._should_rebalance(current_signals, previous_signals):
                logger.debug(f"{date}: 信号变化，触发再平衡")
                logger.debug(f"  当前标的: {current_signals}")

                # 5. 生成目标组合(根据信号强度加权)
                if current_signals:
                    target_portfolio = self._generate_optimized_portfolio(
                        current_signals, date, prices
                    )

                    # 6. 执行再平衡
                    trades = self._execute_rebalance(date, target_portfolio, prices)

                    for trade in trades:
                        self.tracker.add_transaction(
                            date=date,
                            symbol=trade['symbol'],
                            action=trade['action'],
                            shares=trade['shares'],
                            price=trade['price'],
                            amount=trade['amount']
                        )

                        # 记录入场价格
                        if trade['action'] == 'buy':
                            self.entry_prices[trade['symbol']] = trade['price']

                    rebalance_count += 1
                else:
                    # 如果没有符合条件的标的，清空持仓
                    trades = self._close_all_positions(date, prices)
                    logger.debug(f"{date}: 无符合条件的标的，清空持仓")
                    self.entry_prices.clear()

                previous_signals = current_signals

            # 7. 更新每日状态
            self.tracker.update_daily_state(date, prices, [])

        logger.info(f"回测完成，共再平衡 {rebalance_count} 次")

        # 计算最终指标
        metrics = self._calculate_final_metrics()

        # 保存到数据库
        if self.task.name:
            self._save_results(metrics)

        return metrics

    def _get_optimized_signals(self, date: str) -> List[str]:
        """
        获取优化后的信号列表

        改进的买入条件:
        1. 短期动量(ROC20) > 3%
        2. 长期动量(ROC60) > 5%
        3. 趋势强度(trend_score) > 0.02
        4. RSI在30-70之间(未超买超卖)
        5. 成交量确认
        """
        buy_symbols = []
        cfg = self.config

        for symbol in self.task.symbols:
            # 计算综合信号强度
            signal_strength = self._calculate_signal_strength(symbol, date)

            # 信号强度 > 0.5 认为可以买入
            if signal_strength > 0.5:
                # 进一步检查止损条件
                if self._check_entry_conditions(symbol, date):
                    buy_symbols.append((symbol, signal_strength))

        # 按信号强度排序
        buy_symbols.sort(key=lambda x: x[1], reverse=True)

        # 只返回symbol列表
        return [s[0] for s in buy_symbols[:cfg.max_positions]]

    def _calculate_signal_strength(self, symbol: str, date: str) -> float:
        """
        计算信号强度 (0-1)

        综合多个维度的信号
        """
        try:
            df = self.price_data.get(symbol)
            if df is None or df.empty or 'close' not in df.columns:
                return 0.0

            cfg = self.config
            weights = cfg.signal_weights

            score = 0.0
            total_weight = 0.0

            # 1. 短期动量 (ROC20 > 3%)
            if len(df['close']) > 20:
                roc20 = df['close'].iloc[-1] / df['close'].iloc[-21] - 1
                if roc20 > 0.03:
                    score += weights['momentum_short'] * min(roc20 / 0.10, 1.0)
                total_weight += weights['momentum_short']

            # 2. 长期动量 (ROC60 > 5%)
            if len(df['close']) > 60:
                roc60 = df['close'].iloc[-1] / df['close'].iloc[-61] - 1
                if roc60 > 0.05:
                    score += weights['momentum_long'] * min(roc60 / 0.15, 1.0)
                total_weight += weights['momentum_long']

            # 3. 趋势强度 (trend_score)
            try:
                from datafeed.factor_extends import trend_score
                ts = trend_score(df['close'], 25)
                if len(ts) > 0 and not pd.isna(ts.iloc[-1]):
                    if ts.iloc[-1] > 0.02:
                        score += weights['trend'] * min(ts.iloc[-1] / 0.10, 1.0)
                    total_weight += weights['trend']
            except:
                pass

            # 4. 成交量确认
            if 'volume' in df.columns and len(df['volume']) > 20:
                vol_ma5 = df['volume'].iloc[-5:].mean()
                vol_ma20 = df['volume'].iloc[-20:].mean()
                if vol_ma5 > vol_ma20 * 1.1:  # 放量10%
                    score += weights['volume']
                total_weight += weights['volume']

            # 归一化到0-1
            if total_weight > 0:
                return min(score / total_weight, 1.0)
            return 0.0

        except Exception as e:
            logger.debug(f"计算信号强度失败 {symbol}: {e}")
            return 0.0

    def _check_entry_conditions(self, symbol: str, date: str) -> bool:
        """检查入场条件"""
        try:
            df = self.price_data.get(symbol)
            if df is None or df.empty or 'close' not in df.columns:
                return False

            # RSI检查 (避免超买)
            try:
                rsi = self._calculate_rsi(df['close'], 14)
                latest_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
                if latest_rsi > 70:  # 超买不入场
                    return False
            except:
                pass

            return True
        except:
            return False

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _generate_optimized_portfolio(self, symbols: List[str], date: str,
                                   prices: Dict[str, float]) -> Dict[str, float]:
        """
        生成优化的组合权重

        根据信号强度分配权重
        """
        cfg = self.config

        if not symbols:
            return {}

        # 计算每个标的的信号强度
        signal_strengths = []
        for symbol in symbols:
            strength = self._calculate_signal_strength(symbol, date)
            signal_strengths.append((symbol, strength))

        # 根据信号强度计算权重
        total_strength = sum(s[1] for s in signal_strengths)

        if total_strength <= 0:
            # 等权作为后备
            weight = 1.0 / len(symbols)
            return {s: weight for s in symbols}

        # 按信号强度加权
        raw_weights = {}
        for symbol, strength in signal_strengths:
            raw_weights[symbol] = strength / total_strength

        # 限制单只权重范围
        final_weights = {}
        for symbol, weight in raw_weights.items():
            final_weights[symbol] = max(cfg.min_position_weight,
                                      min(cfg.max_position_weight, weight))

        # 重新归一化
        total = sum(final_weights.values())
        return {k: v/total for k, v in final_weights.items()}

    def _check_stop_loss_take_profit(self, date: str, prices: Dict[str, float]):
        """检查止损止盈"""
        if not self.config.use_atr_stop_loss:
            return

        for symbol in list(self.tracker.holdings.keys()):
            current_price = prices.get(symbol)
            if current_price is None or current_price <= 0:
                continue

            entry_price = self.entry_prices.get(symbol)
            if entry_price is None:
                continue

            # 计算ATR
            df = self.price_data.get(symbol)
            if df is None or df.empty:
                continue

            atr = self._calculate_atr(df)
            latest_atr = atr.iloc[-1] if len(atr) > 0 else current_price * 0.02

            # 动态止损价
            stop_loss_price = entry_price - latest_atr * self.config.atr_stop_loss_multiplier
            take_profit_price = entry_price + latest_atr * self.config.atr_take_profit_multiplier

            # 检查是否触发
            if current_price <= stop_loss_price:
                # 触发止损
                logger.debug(f"{date}: {symbol} 触发止损, 价格={current_price:.2f}, "
                           f"止损价={stop_loss_price:.2f}")
                self._close_position(symbol, date, prices, reason='stop_loss')

            elif current_price >= take_profit_price:
                # 触发止盈
                logger.debug(f"{date}: {symbol} 触发止盈, 价格={current_price:.2f}, "
                           f"止盈价={take_profit_price:.2f}")
                self._close_position(symbol, date, prices, reason='take_profit')

    def _calculate_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """计算ATR"""
        high = df.get('high', df['close'])
        low = df.get('low', df['close'])
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _close_position(self, symbol: str, date: str, prices: Dict[str, float],
                      reason: str = ''):
        """平仓单个标的"""
        position = self.tracker.holdings.get(symbol)
        if position is None:
            return

        shares = position['shares']
        price = prices.get(symbol, 0)

        if price > 0 and shares > 0:
            amount = shares * price
            proceeds = amount * (1 - self.task.commission_rate)

            # 清仓
            del self.tracker.holdings[symbol]
            self.tracker.cash += proceeds
            self.entry_prices.pop(symbol, None)

            logger.debug(f"{date}: 平仓 {symbol} {shares}股, 原因={reason}, "
                        f"收入={proceeds:.0f}")

    def _should_rebalance(self, current_signals: List[str],
                        previous_signals: Optional[List[str]]) -> bool:
        """判断是否需要再平衡"""
        if previous_signals is None:
            return True

        return set(current_signals) != set(previous_signals)


# 便捷函数
def run_optimized_etf_portfolio(
        symbols: List[str],
        start_date: str = '20220101',
        end_date: str = None,
        name: str = '优化版ETF组合策略',
        initial_capital: float = 1000000,
        commission_rate: float = 0.0003,
        config: OptimizedPortfolioConfig = None
) -> Dict:
    """
    运行优化版ETF组合策略

    Args:
        symbols: ETF池
        start_date: 回测开始日期
        end_date: 回测结束日期
        name: 策略名称
        initial_capital: 初始资金
        commission_rate: 手续费率
        config: 优化配置

    Returns:
        回测结果字典
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    # 优化的买入条件
    select_buy = [
        'roc(close,20) > 0.03',  # 短期动量 > 3%
        'roc(close,60) > 0.05',  # 长期动量 > 5%
    ]
    select_sell = [
        'roc(close,20) < -0.03',  # 动量转负
        'close < ma(close,20)*0.95',  # 跌破均线5%
    ]

    task = PortfolioTask(
        name=name,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission_rate=commission_rate,
        select_buy=select_buy,
        buy_at_least_count=1,
        select_sell=select_sell,
        sell_at_least_count=1,
    )

    engine = OptimizedETFPortfolioEngine(task, config)
    return engine.run()


# 默认ETF池
DEFAULT_OPTIMIZED_POOL = [
    '510300.SH',  # 沪深300ETF
    '510500.SH',  # 中证500ETF
    '159915.SZ',  # 创业板ETF
    '512100.SH',  # 中证1000ETF
    '588000.SH',  # 科创50ETF
    '513100.SH',  # 纳指100ETF
    '518880.SH',  # 黄金ETF
    '512010.SH',  # 医药ETF
    '159928.SZ',  # 消费ETF
    '515880.SH',  # 通信ETF
]


if __name__ == '__main__':
    """测试代码"""
    logger.info('优化版ETF组合策略测试')

    result = run_optimized_etf_portfolio(
        symbols=DEFAULT_OPTIMIZED_POOL,
        start_date='20220101',
        config=OptimizedPortfolioConfig(
            use_position_sizing=True,
            use_atr_stop_loss=True,
            max_positions=8
        )
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
