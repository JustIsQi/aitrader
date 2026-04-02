"""
多策略ETF轮动框架 - ETF Multi Strategy Rotation

核心功能:
1. 市场环境识别模块 (趋势/震荡, 高风险偏好/低风险偏好)
2. 多子策略组合 (趋势跟踪、均值回归、动量轮动、防御策略)
3. 动态权重分配 (根据市场环境自动切换)

作者: AITrader
日期: 2026-02-14
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger

from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask


@dataclass
class MarketRegime:
    """市场环境"""
    trend_vs_range: str  # 'trend' 或 'range'
    risk_appetite: str  # 'high' 或 'low'
    volatility_level: str  # 'low', 'medium', 'high'
    confidence: float  # 判断置信度 0-1


@dataclass
class SubStrategy:
    """子策略定义"""
    name: str
    description: str

    # 买入条件 (因子表达式列表)
    select_buy: List[str] = field(default_factory=list)
    buy_at_least_count: int = 1

    # 卖出条件
    select_sell: List[str] = field(default_factory=list)
    sell_at_least_count: int = 1

    # 最适合的市场环境
    preferred_regime: Dict[str, str] = field(default_factory=dict)
    # 例如: {'trend_vs_range': 'trend', 'risk_appetite': 'high'}

    # 权重范围
    min_weight: float = 0.0
    max_weight: float = 1.0


class MarketRegimeDetector:
    """
    市场环境识别器

    使用多种指标判断当前市场环境
    增加防抖动机制：连续多次检测到相同环境才会切换
    """

    def __init__(self, benchmark: str = '510300.SH', regime_confirm_count: int = 3):
        """
        初始化市场环境识别器

        Args:
            benchmark: 基准指数代码 (默认沪深300)
            regime_confirm_count: 需要连续确认几次才切换环境（防抖动）
        """
        self.benchmark = benchmark
        self._cache_data = None
        self.regime_confirm_count = regime_confirm_count
        self._regime_history: List[str] = []  # 历史环境记录
        self._last_confirmed_regime: Optional[MarketRegime] = None  # 最后确认的环境

    def detect(self, symbols_data: Dict[str, pd.DataFrame],
               current_date: str) -> MarketRegime:
        """
        检测当前市场环境

        Args:
            symbols_data: {symbol: DataFrame} 所有标的的数据
            current_date: 当前日期 (YYYY-MM-DD)

        Returns:
            MarketRegime 市场环境对象
        """
        regime = MarketRegime(
            trend_vs_range='unknown',
            risk_appetite='medium',
            volatility_level='medium',
            confidence=0.5
        )

        # 获取基准数据
        benchmark_df = symbols_data.get(self.benchmark)
        if benchmark_df is None or benchmark_df.empty:
            logger.warning(f"无法获取基准{self.benchmark}数据,使用默认市场环境")
            return regime

        # 获取当前日期的数据
        try:
            target_date = pd.to_datetime(current_date)
            if isinstance(benchmark_df.index, pd.DatetimeIndex):
                idx = benchmark_df.index.get_indexer(target_date, method='ffill')
                if idx >= 0:
                    hist_df = benchmark_df.iloc[:idx+1]
                else:
                    return regime
            else:
                return regime

            if len(hist_df) < 60:
                return regime

            # 1. 判断趋势 vs 震荡 (使用ADX和价格特征)
            regime.trend_vs_range = self._detect_trend_vs_range(hist_df)

            # 2. 判断风险偏好 (基于近期收益率和波动)
            regime.risk_appetite = self._detect_risk_appetite(hist_df)

            # 3. 判断波动率水平
            regime.volatility_level = self._detect_volatility_level(hist_df)

            # 4. 计算综合置信度
            regime.confidence = 0.6  # 基于多个指标综合判断

        except Exception as e:
            logger.debug(f"市场环境检测失败: {e}")

        # 防抖动：记录本次检测结果，只有连续确认才切换
        regime_key = f"{regime.trend_vs_range}|{regime.risk_appetite}"
        self._regime_history.append(regime_key)
        if len(self._regime_history) > self.regime_confirm_count:
            self._regime_history = self._regime_history[-self.regime_confirm_count:]

        # 检查最近N次是否一致（允许60%多数一致即可）
        if self._last_confirmed_regime is not None and len(self._regime_history) >= self.regime_confirm_count:
            from collections import Counter
            counter = Counter(self._regime_history)
            most_common_key, count = counter.most_common(1)[0]
            threshold = self.regime_confirm_count * 0.6

            if count >= threshold:
                # 多数一致，确认切换
                parts = most_common_key.split('|')
                regime.trend_vs_range = parts[0]
                regime.risk_appetite = parts[1]
                self._last_confirmed_regime = regime
            else:
                # 不够一致，保持上次确认的环境
                regime = self._last_confirmed_regime
                logger.debug(f"市场环境检测不稳定（{counter}），维持上次确认环境: "
                           f"trend={regime.trend_vs_range}, risk={regime.risk_appetite}")
        else:
            self._last_confirmed_regime = regime

        return regime

    def _detect_trend_vs_range(self, df: pd.DataFrame) -> str:
        """判断趋势市场 vs 震荡市场"""
        close = df['close']

        # 方法1: 计算价格的线性回归R²
        if len(close) >= 20:
            x = np.arange(len(close))
            z = np.polyfit(x, close.values, 1)
            p = np.poly1d(z)
            y_hat = p(x)
            y_bar = np.mean(close.values)
            ss_tot = np.sum((close.values - y_bar) ** 2)
            ss_res = np.sum((close.values - y_hat) ** 2)

            if ss_tot > 0:
                r_squared = 1 - ss_res / ss_tot
                # R² > 0.3 认为是趋势市场
                if r_squared > 0.3:
                    return 'trend'
                elif r_squared < 0.1:
                    return 'range'

        # 方法2: 使用价格在均线间的波动
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        latest = close.iloc[-1]

        if len(ma20) >= 2 and len(ma60) >= 2:
            ma20_latest = ma20.iloc[-1]
            ma60_latest = ma60.iloc[-1]

            # 均线多头排列且价格在MA20之上 -> 趋势
            if ma20_latest > ma60_latest and latest > ma20_latest:
                return 'trend'
            # 均线纠缠 -> 震荡
            elif abs(ma20_latest - ma60_latest) / ma60_latest < 0.02:
                return 'range'

        return 'trend'  # 默认

    def _detect_risk_appetite(self, df: pd.DataFrame) -> str:
        """判断风险偏好"""
        close = df['close']

        # 计算近期收益率
        if len(close) >= 20:
            ret_20 = (close.iloc[-1] / close.iloc[-20] - 1) * 100

            # 计算波动率
            returns = close.pct_change().dropna()
            volatility = returns.tail(20).std() * np.sqrt(252) * 100

            # 高收益 + 低波动 -> 高风险偏好
            if ret_20 > 5 and volatility < 30:
                return 'high'
            # 低收益或高波动 -> 低风险偏好
            elif ret_20 < -5 or volatility > 40:
                return 'low'

        return 'medium'

    def _detect_volatility_level(self, df: pd.DataFrame) -> str:
        """判断波动率水平"""
        close = df['close']
        returns = close.pct_change().dropna()

        if len(returns) >= 20:
            vol = returns.tail(20).std() * np.sqrt(252) * 100

            if vol < 15:
                return 'low'
            elif vol < 30:
                return 'medium'
            else:
                return 'high'

        return 'medium'


class MultiStrategyETFManager:
    """
    多策略ETF管理器

    功能:
    1. 注册多个子策略
    2. 根据市场环境动态分配权重
    3. 生成最终交易信号
    """

    def __init__(self, benchmark: str = '510300.SH'):
        """
        初始化多策略管理器

        Args:
            benchmark: 基准指数
        """
        self.benchmark = benchmark
        self.strategies: Dict[str, SubStrategy] = {}
        self.regime_detector = MarketRegimeDetector(benchmark)

        # 注册默认策略
        self._register_default_strategies()

    def _register_default_strategies(self):
        """注册默认子策略"""

        # 1. 趋势跟踪策略
        self.strategies['trend_follow'] = SubStrategy(
            name='trend_follow',
            description='趋势跟踪策略: 在明确趋势中表现好',
            select_buy=[
                'roc(close,20) > 0.03',  # 中期动量
                'trend_score(close,25) > 0.02',  # 趋势强度
                'ma(close,5) > ma(close,20)',  # 短期均线向上
            ],
            buy_at_least_count=2,
            select_sell=[
                'roc(close,20) < -0.03',
                'close < ma(close,20)*0.97',
            ],
            sell_at_least_count=1,
            preferred_regime={'trend_vs_range': 'trend'},
            min_weight=0.3,
            max_weight=1.0
        )

        # 2. 均值回归策略
        self.strategies['mean_reversion'] = SubStrategy(
            name='mean_reversion',
            description='均值回归策略: 在震荡市中表现好',
            select_buy=[
                'roc(close,5) < -0.02',  # 短期超跌
                'RSI(close,14) < 40',  # RSI超卖
                'close < ma(close,20)*0.97',  # 价格低于均线
            ],
            buy_at_least_count=2,
            select_sell=[
                'roc(close,5) > 0.03',
                'RSI(close,14) > 60',
                'close > ma(close,20)*1.02',
            ],
            sell_at_least_count=1,
            preferred_regime={'trend_vs_range': 'range'},
            min_weight=0.2,
            max_weight=0.8
        )

        # 3. 动量轮动策略
        self.strategies['momentum_rotation'] = SubStrategy(
            name='momentum_rotation',
            description='动量轮动策略: 选择强势板块',
            select_buy=[
                'roc(close,20) > 0.05',  # 强势动量
                'roc(close,60) > 0.08',  # 长期动量确认
                'ma(volume,5) > ma(volume,20)',  # 成交量放大
            ],
            buy_at_least_count=3,
            select_sell=[
                'roc(close,20) < 0',
                'ma(volume,5) < ma(volume,20)',
            ],
            sell_at_least_count=1,
            preferred_regime={'risk_appetite': 'high'},
            min_weight=0.3,
            max_weight=1.0
        )

        # 4. 防御策略
        self.strategies['defensive'] = SubStrategy(
            name='defensive',
            description='防御策略: 债券、黄金等防御资产',
            select_buy=[
                'roc(close,20) > -0.01',  # 只要不大跌就可以
                'ma(close,5) > ma(close,60)',  # 长期趋势向上
            ],
            buy_at_least_count=1,
            select_sell=[
                'roc(close,5) < -0.03',  # 短期大跌止损
            ],
            sell_at_least_count=1,
            preferred_regime={'risk_appetite': 'low', 'trend_vs_range': 'range'},
            min_weight=0.0,
            max_weight=1.0
        )

    def add_strategy(self, strategy: SubStrategy):
        """添加自定义策略"""
        self.strategies[strategy.name] = strategy
        logger.info(f"添加子策略: {strategy.name} - {strategy.description}")

    def get_strategy_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """
        根据市场环境计算各策略权重

        Args:
            regime: 当前市场环境

        Returns:
            {strategy_name: weight} 权重字典
        """
        weights = {}

        for name, strategy in self.strategies.items():
            # 基础权重
            weight = 0.25  # 默认均分

            # 根据市场环境调整
            if strategy.preferred_regime:
                match_score = 0

                for key, preferred_value in strategy.preferred_regime.items():
                    actual_value = getattr(regime, key, None)
                    if actual_value == preferred_value:
                        match_score += 1

                # 匹配度越高,权重越高
                if match_score > 0:
                    weight = 0.25 + match_score * 0.15

            # 限制在范围内
            weight = max(strategy.min_weight, min(strategy.max_weight, weight))
            weights[name] = weight

        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}

        return weights

    def get_combined_signals(self,
                           symbols: List[str],
                           symbols_data: Dict[str, pd.DataFrame],
                           current_date: str,
                           regime: MarketRegime,
                           weights: Dict[str, float] = None) -> Dict[str, float]:
        """
        获取综合信号

        Args:
            symbols: ETF池
            symbols_data: 各ETF数据
            current_date: 当前日期
            regime: 市场环境
            weights: 策略权重 (None则自动计算)

        Returns:
            {symbol: signal_score} 信号得分字典
        """
        if weights is None:
            weights = self.get_strategy_weights(regime)

        logger.debug(f"当前市场环境: trend={regime.trend_vs_range}, "
                    f"risk={regime.risk_appetite}, 策略权重={weights}")

        # 各策略的信号
        strategy_signals = {}

        for name, strategy in self.strategies.items():
            if weights.get(name, 0) <= 0:
                continue

            signals = self._calculate_strategy_signals(
                strategy, symbols, symbols_data, current_date
            )
            strategy_signals[name] = signals

        # 加权综合
        combined = {}
        for symbol in symbols:
            score = 0.0
            for name, signals in strategy_signals.items():
                score += signals.get(symbol, 0) * weights.get(name, 0)
            combined[symbol] = score

        return combined

    def _calculate_strategy_signals(self,
                                   strategy: SubStrategy,
                                   symbols: List[str],
                                   symbols_data: Dict[str, pd.DataFrame],
                                   current_date: str) -> Dict[str, float]:
        """计算单个策略的信号"""
        signals = {}

        for symbol in symbols:
            df = symbols_data.get(symbol)
            if df is None or df.empty:
                signals[symbol] = 0.0
                continue

            # 检查买入条件
            buy_count = 0
            for condition in strategy.select_buy:
                if self._check_condition(df, condition, current_date):
                    buy_count += 1

            # 检查卖出条件
            sell_count = 0
            for condition in strategy.select_sell:
                if self._check_condition(df, condition, current_date):
                    sell_count += 1

            # 计算信号得分
            required_buys = max(1, strategy.buy_at_least_count)
            if sell_count >= strategy.sell_at_least_count:
                signals[symbol] = -1.0  # 强卖出
            elif buy_count >= required_buys:
                # 买入强度 (满足条件越多,信号越强)
                signals[symbol] = 0.5 + (buy_count / len(strategy.select_buy)) * 0.5
            else:
                signals[symbol] = 0.0

        return signals

    def _check_condition(self, df: pd.DataFrame, condition: str, current_date: str) -> bool:
        """检查单个条件是否满足"""
        try:
            # 简化版实现,实际应该用factor_cache
            from datafeed.factor_expr import FactorExpr

            # 获取计算所需的因子表达式
            required_cols = set()
            if 'roc(close,' in condition:
                required_cols.add('close')
            if 'ma(close,' in condition:
                required_cols.add('close')
            if 'ma(volume,' in condition:
                required_cols.add('volume')
            if 'RSI(' in condition:
                required_cols.add('close')
            if 'trend_score(' in condition:
                required_cols.add('close')

            # 检查数据完整性
            if not all(col in df.columns for col in required_cols):
                return False

            # 简化判断 (实际应该使用FactorExpr)
            if 'roc(close,20) > 0.03' in condition:
                latest = df['close'].iloc[-1]
                past_20 = df['close'].iloc[-21] if len(df) > 20 else df['close'].iloc[0]
                return (latest / past_20 - 1) > 0.03 if past_20 > 0 else False

            elif 'roc(close,60) > 0.08' in condition:
                latest = df['close'].iloc[-1]
                past_60 = df['close'].iloc[-61] if len(df) > 60 else df['close'].iloc[0]
                return (latest / past_60 - 1) > 0.08 if past_60 > 0 else False

            elif 'roc(close,5) < -0.02' in condition:
                latest = df['close'].iloc[-1]
                past_5 = df['close'].iloc[-6] if len(df) > 5 else df['close'].iloc[0]
                return (latest / past_5 - 1) < -0.02 if past_5 > 0 else False

            elif 'ma(close,5) > ma(close,20)' in condition:
                ma5 = df['close'].rolling(5).mean().iloc[-1]
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                return ma5 > ma20 if not pd.isna(ma5) and not pd.isna(ma20) else False

            elif 'close < ma(close,20)*0.97' in condition:
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                latest = df['close'].iloc[-1]
                return latest < ma20 * 0.97 if not pd.isna(ma20) else False

            elif 'close < ma(close,20)*0.95' in condition:
                ma20 = df['close'].rolling(20).mean().iloc[-1]
                latest = df['close'].iloc[-1]
                return latest < ma20 * 0.95 if not pd.isna(ma20) else False

            elif 'trend_score(close,25) >' in condition:
                try:
                    from datafeed.factor_extends import trend_score
                    ts = trend_score(df['close'], 25)
                    threshold = float(condition.split('>')[1].strip())
                    return ts.iloc[-1] > threshold if len(ts) > 0 and not pd.isna(ts.iloc[-1]) else False
                except:
                    return False

            # 更多条件可以继续添加...
            return False

        except Exception as e:
            logger.debug(f"条件检查失败 {condition}: {e}")
            return False


class MultiStrategyETFTask(PortfolioTask):
    """多策略ETF回测任务"""

    def __init__(self,
                 symbols: List[str],
                 start_date: str,
                 end_date: str,
                 benchmark: str = '510300.SH',
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.0003,

                 # 策略配置
                 min_signal_score: float = 0.3,  # 最小信号得分才能买入
                 max_positions: int = 10,  # 最大持仓数
                 rebalance_frequency: str = 'monthly',  # 再平衡频率
                 ):
        super().__init__(
            name='多策略ETF轮动',
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            benchmark=benchmark,
        )

        self.min_signal_score = min_signal_score
        self.max_positions = max_positions
        self.rebalance_frequency = rebalance_frequency


class MultiStrategyETFEngine(PortfolioBacktestEngine):
    """
    多策略ETF回测引擎

    继承自PortfolioBacktestEngine,增加市场环境识别和动态权重功能
    """

    def __init__(self, task: MultiStrategyETFTask):
        super().__init__(task)

        self.multi_strategy = MultiStrategyETFManager(
            benchmark=task.benchmark
        )

        # 缓存市场环境
        self._regime_cache: Dict[str, MarketRegime] = {}

    def run(self) -> Dict:
        """
        运行多策略回测

        Returns:
            回测结果字典
        """
        logger.info(f"开始多策略ETF回测: {self.task.name}")

        # 获取交易日列表
        trading_days = self._get_trading_days()
        logger.info(f"交易日数量: {len(trading_days)}")

        # 逐日模拟
        previous_signals = None
        last_rebalance_date = None
        rebalance_count = 0

        for i, date in enumerate(trading_days):
            if i % 50 == 0:
                logger.info(f"处理进度: {i}/{len(trading_days)} ({i/len(trading_days)*100:.1f}%)")

            # 判断是否需要再平衡
            should_rebalance = self._should_rebalance_dynamic(
                date, last_rebalance_date, previous_signals
            )

            if should_rebalance:
                # 1. 检测市场环境
                regime = self._detect_regime(date)
                logger.debug(f"{date}: 市场环境 - trend={regime.trend_vs_range}, "
                           f"risk={regime.risk_appetite}, vol={regime.volatility_level}")

                # 2. 获取综合信号
                current_signals = self._get_multi_strategy_signals(date, regime)

                # 3. 筛选符合条件的前N个
                selected = self._select_top_signals(current_signals)

                if selected:
                    # 4. 生成目标组合
                    target_portfolio = self._generate_weighted_portfolio(selected, current_signals)

                    # 5. 执行再平衡
                    prices = self._get_prices(date)
                    trades = self._execute_rebalance(date, target_portfolio, prices)

                    for trade in trades:
                        self.tracker.add_transaction(
                            date=date, symbol=trade['symbol'],
                            action=trade['action'], shares=trade['shares'],
                            price=trade['price'], amount=trade['amount']
                        )

                    rebalance_count += 1
                    last_rebalance_date = date

                previous_signals = selected

            # 6. 更新每日状态
            prices = self._get_prices(date)
            self.tracker.update_daily_state(date, prices, [])

        logger.info(f"回测完成,共再平衡 {rebalance_count} 次")

        # 计算最终指标
        metrics = self._calculate_final_metrics()

        # 保存到数据库
        if self.task.name:
            self._save_results(metrics)

        return metrics

    def _detect_regime(self, date: str) -> MarketRegime:
        """检测市场环境"""
        if date in self._regime_cache:
            return self._regime_cache[date]

        # 获取所有标的数据
        regime = self.multi_strategy.regime_detector.detect(
            self.price_data, date
        )
        self._regime_cache[date] = regime
        return regime

    def _should_rebalance_dynamic(self, date: str, last_rebalance: str,
                                 previous_signals: List[str]) -> bool:
        """判断是否需要再平衡（增加最小间隔防抖动）"""
        if last_rebalance is None:
            return True

        # 最小再平衡间隔：至少5个交易日
        min_interval_days = 5
        date_dt = pd.to_datetime(date)
        last_dt = pd.to_datetime(last_rebalance)
        if (date_dt - last_dt).days < min_interval_days:
            return False

        # 根据频率判断
        freq = self.task.rebalance_frequency
        if freq == 'daily':
            return True
        elif freq == 'weekly':
            # 简化: 每周第一天
            weekday = pd.to_datetime(date).weekday()
            last_weekday = pd.to_datetime(last_rebalance).weekday() if last_rebalance else -1
            return weekday < last_weekday
        elif freq == 'monthly':
            # 简化: 每月第一天
            day = pd.to_datetime(date).day
            last_day = pd.to_datetime(last_rebalance).day if last_rebalance else 32
            return day <= 7 and last_day > 7
        else:
            # 按信号变化
            return True

    def _get_multi_strategy_signals(self, date: str,
                                    regime: MarketRegime) -> Dict[str, float]:
        """获取多策略综合信号"""
        weights = self.multi_strategy.get_strategy_weights(regime)
        return self.multi_strategy.get_combined_signals(
            self.task.symbols, self.price_data, date, regime, weights
        )

    def _select_top_signals(self, signals: Dict[str, float]) -> List[str]:
        """筛选符合条件的信号"""
        task = self.task
        min_score = getattr(task, 'min_signal_score', 0.3)
        max_pos = getattr(task, 'max_positions', 10)

        # 筛选得分符合条件的
        qualified = {s: v for s, v in signals.items() if v >= min_score}

        # 按得分排序
        sorted_items = sorted(qualified.items(), key=lambda x: x[1], reverse=True)

        # 取前N个
        return [s for s, _ in sorted_items[:max_pos]]

    def _generate_weighted_portfolio(self, symbols: List[str],
                                    signals: Dict[str, float]) -> Dict[str, float]:
        """生成加权组合 (根据信号强度分配权重)"""
        if not symbols:
            return {}

        # 获取信号强度
        signal_values = {s: signals.get(s, 0) for s in symbols}
        total = sum(signal_values.values())

        if total <= 0:
            # 等权
            weight = 1.0 / len(symbols)
            return {s: weight for s in symbols}

        # 按信号强度加权
        return {s: signal_values[s] / total for s in symbols}


# 便捷函数
def run_multi_strategy_etf(
        name: str = '多策略ETF轮动',
        symbols: List[str] = None,
        start_date: str = '20220101',
        end_date: str = None,
        benchmark: str = '510300.SH',
        initial_capital: float = 1000000,
        min_signal_score: float = 0.3,
        max_positions: int = 8,
        rebalance_frequency: str = 'monthly'
) -> Dict:
    """
    快速运行多策略ETF回测

    Args:
        name: 策略名称
        symbols: ETF池 (None则使用默认池)
        start_date: 开始日期
        end_date: 结束日期 (None则使用当前日期)
        benchmark: 基准
        initial_capital: 初始资金
        min_signal_score: 最小信号得分
        max_positions: 最大持仓数
        rebalance_frequency: 再平衡频率

    Returns:
        回测结果字典
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    if symbols is None:
        # 默认ETF池 (宽基指数 + 行业ETF + 商品ETF + QDII)
        symbols = [
            # A股宽基
            '510300.SH', '510500.SH', '159915.SZ', '512100.SH',
            '588000.SH', '563300.SH',
            # 行业主题
            '512010.SH', '159928.SZ', '515880.SH',
            # 商品
            '518880.SH', '159985.SZ',
            # QDII
            '513100.SH', '513520.SH', '513330.SH',
        ]

    task = MultiStrategyETFTask(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        benchmark=benchmark,
        initial_capital=initial_capital,
        min_signal_score=min_signal_score,
        max_positions=max_positions,
        rebalance_frequency=rebalance_frequency
    )

    engine = MultiStrategyETFEngine(task)
    return engine.run()


if __name__ == '__main__':
    """测试代码"""
    logger.info('多策略ETF轮动测试')

    # 测试: 近3年回测
    result = run_multi_strategy_etf(
        start_date='20220101',
        max_positions=8,
        rebalance_frequency='monthly'
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
