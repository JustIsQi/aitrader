"""
多策略信号生成器
集成所有策略,生成独立的买卖信号
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from database.pg_manager import get_db
from signals.strategy_parser import StrategyParser, ParsedStrategy, StrategyType
from database.factor_cache import FactorCache


@dataclass
class BuySignal:
    """买入信号"""
    symbol: str
    score: float
    rank: int
    price: float
    suggested_quantity: int


@dataclass
class SellSignal:
    """卖出信号"""
    symbol: str
    current_price: float
    quantity: int
    avg_cost: float
    profit_loss_pct: float
    trigger_reason: str


@dataclass
class StrategySignals:
    """策略信号集合"""
    strategy_name: str
    buy_signals: List[BuySignal]
    sell_signals: List[SellSignal]
    hold_recommendations: List[str]
    symbols_analyzed: List[str]
    analysis_date: str


class MultiStrategySignalGenerator:
    """多策略信号生成器"""

    def __init__(self):
        """
        初始化信号生成器
        """
        self.db = get_db()
        self.parser = StrategyParser('strategies')
        self.target_date = datetime.now().strftime('%Y%m%d')

    def generate_signals(self,
                        current_positions: pd.DataFrame = None,
                        target_date: str = None) -> Dict[str, StrategySignals]:
        """
        生成所有策略的信号

        Args:
            current_positions: 当前持仓 DataFrame
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            策略信号字典 {strategy_name: StrategySignals}
        """
        if target_date:
            self.target_date = target_date

        # 获取当前持仓
        if current_positions is None:
            current_positions = self.db.get_positions()

        # 解析所有策略
        strategies = self.parser.parse_all_strategies()

        if not strategies:
            logger.warning("没有可用的策略")
            return {}

        # 收集所有唯一标的和因子表达式
        all_symbols = set()
        all_factor_exprs = []

        for strategy in strategies:
            if strategy.task is None:
                continue

            all_symbols.update(strategy.task.symbols)
            all_factor_exprs.extend(strategy.task.select_buy)
            all_factor_exprs.extend(strategy.task.select_sell)

            if strategy.task.order_by_signal:
                all_factor_exprs.append(strategy.task.order_by_signal)

        all_symbols = list(all_symbols)
        all_factor_exprs = list(set(all_factor_exprs))  # 去重

        print(f"  ✓ {len(strategies)} 个策略, {len(all_symbols)} 个标的, {len(all_factor_exprs)} 个因子")

        # 批量计算并缓存因子
        factor_cache = FactorCache(all_symbols, '20200101', self.target_date)
        factor_cache.calculate_factors(all_factor_exprs)

        # 生成每个策略的信号
        print(f"  生成各策略信号...")
        all_signals = {}

        for idx, strategy in enumerate(strategies, 1):
            if strategy.task is None:
                continue

            signals = self._generate_strategy_signals(
                strategy,
                current_positions,
                factor_cache
            )
            all_signals[strategy.task.name] = signals

        print(f"  ✓ 完成 {len(all_signals)} 个策略")

        return all_signals

    def _generate_strategy_signals(self,
                                   strategy: ParsedStrategy,
                                   current_positions: pd.DataFrame,
                                   factor_cache: FactorCache) -> StrategySignals:
        """
        生成单个策略的信号

        Args:
            strategy: 解析后的策略
            current_positions: 当前持仓
            factor_cache: 因子缓存

        Returns:
            策略信号对象
        """
        task = strategy.task

        # 获取持仓标的集合
        if current_positions.empty:
            holding_symbols = set()
        else:
            holding_symbols = set(current_positions['symbol'].tolist())

        # 获取 close 价格
        df_close = factor_cache.get_factor('close')
        if df_close is None or df_close.empty:
            return StrategySignals(
                strategy_name=task.name,
                buy_signals=[],
                sell_signals=[],
                hold_recommendations=[],
                symbols_analyzed=task.symbols,
                analysis_date=self.target_date
            )

        # 检查卖出信号
        sell_signals = []
        if task.select_sell:
            sell_signals = self._check_sell_conditions(
                task, factor_cache, holding_symbols, df_close, current_positions
            )

        # 检查买入信号
        buy_signals = []
        if task.select_buy:
            buy_signals = self._check_buy_conditions(
                task, factor_cache, holding_symbols, df_close
            )

        # 生成持仓建议 (既不在买入也不在卖出的持仓标的)
        hold_recommendations = []
        for symbol in task.symbols:
            if symbol in holding_symbols:
                is_sell = any(s.symbol == symbol for s in sell_signals)
                is_buy = any(b.symbol == symbol for b in buy_signals)

                if not is_sell and not is_buy:
                    hold_recommendations.append(symbol)

        return StrategySignals(
            strategy_name=task.name,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            hold_recommendations=hold_recommendations,
            symbols_analyzed=task.symbols,
            analysis_date=self.target_date
        )

    def _check_sell_conditions(self,
                               task,
                               factor_cache: FactorCache,
                               holding_symbols: set,
                               df_close: pd.DataFrame,
                               current_positions: pd.DataFrame) -> List[SellSignal]:
        """
        检查卖出条件

        Args:
            task: 策略任务
            factor_cache: 因子缓存
            holding_symbols: 持仓标的集合
            df_close: 收盘价 DataFrame
            current_positions: 当前持仓

        Returns:
            卖出信号列表
        """
        sell_signals = []
        sell_candidates = set()

        # 检查每个卖出条件 (OR 逻辑)
        for condition in task.select_sell:
            df_condition = factor_cache.get_factor(condition)
            if df_condition is None or df_condition.empty:
                continue

            # 转换为 0/1
            df_condition = df_condition.replace({True: 1, False: 0})
            latest_values = df_condition.iloc[-1]

            # 找出满足条件的标的
            symbols_sell = latest_values[latest_values == 1].index.tolist()

            # 只关注已持仓的标的
            symbols_to_sell = [s for s in symbols_sell if s in holding_symbols]
            sell_candidates.update(symbols_to_sell)

        # 生成卖出信号
        for symbol in sell_candidates:
            if symbol not in df_close.columns:
                continue

            sell_price = df_close.iloc[-1][symbol]

            # 获取持仓信息
            if not current_positions.empty:
                position_rows = current_positions[current_positions['symbol'] == symbol]
                if position_rows.empty:
                    continue

                position = position_rows.iloc[0]
                quantity = int(position['quantity'])
                avg_cost = position['avg_cost']
            else:
                continue

            # 计算盈亏百分比
            profit_loss_pct = (sell_price - avg_cost) / avg_cost * 100

            sell_signals.append(SellSignal(
                symbol=symbol,
                current_price=sell_price,
                quantity=quantity,
                avg_cost=avg_cost,
                profit_loss_pct=profit_loss_pct,
                trigger_reason=f"满足 {len(task.select_sell)} 个卖出条件中的 {task.sell_at_least_count} 个"
            ))

        return sell_signals

    def _check_buy_conditions(self,
                              task,
                              factor_cache: FactorCache,
                              holding_symbols: set,
                              df_close: pd.DataFrame) -> List[BuySignal]:
        """
        检查买入条件

        Args:
            task: 策略任务
            factor_cache: 因子缓存
            holding_symbols: 持仓标的集合
            df_close: 收盘价 DataFrame

        Returns:
            买入信号列表
        """
        buy_signals = []

        # 统计每个标的满足的买入条件数量
        buy_condition_counts = {}

        for condition in task.select_buy:
            df_condition = factor_cache.get_factor(condition)
            if df_condition is None or df_condition.empty:
                continue

            # 转换为 0/1
            df_condition = df_condition.replace({True: 1, False: 0})
            latest_values = df_condition.iloc[-1]

            # 统计满足条件的标的
            for symbol in task.symbols:
                if symbol in latest_values.index:
                    buy_condition_counts[symbol] = buy_condition_counts.get(symbol, 0) + latest_values[symbol]

        # 确定买入阈值
        buy_threshold = task.buy_at_least_count if task.buy_at_least_count > 0 else len(task.select_buy)

        # 筛选满足条件的标的
        qualified_symbols = [
            s for s, count in buy_condition_counts.items()
            if count >= buy_threshold
        ]

        if not qualified_symbols:
            return buy_signals

        # 如果没有排序信号,所有符合条件的都是买入信号
        if not task.order_by_signal:
            for symbol in qualified_symbols:
                if symbol in df_close.columns and symbol not in holding_symbols:
                    buy_signals.append(BuySignal(
                        symbol=symbol,
                        score=buy_condition_counts[symbol],
                        rank=0,
                        price=df_close.iloc[-1][symbol],
                        suggested_quantity=0
                    ))
            return buy_signals

        # 按排序信号评分
        df_order = factor_cache.get_factor(task.order_by_signal)
        if df_order is None or df_order.empty:
            return buy_signals

        latest_order = df_order.iloc[-1]

        # 计算评分并排序
        scored_symbols = []
        for symbol in qualified_symbols:
            if symbol in latest_order.index and pd.notna(latest_order[symbol]):
                scored_symbols.append((symbol, latest_order[symbol]))

        # 排序 (默认降序)
        descending = task.order_by_DESC if hasattr(task, 'order_by_DESC') else True
        scored_symbols.sort(key=lambda x: x[1], reverse=descending)

        # 应用 topK 限制
        top_k = task.order_by_topK if task.order_by_topK > 0 else len(scored_symbols)

        # 应用 dropN 限制 (跳过前 N 个)
        drop_n = task.order_by_dropN if hasattr(task, 'order_by_dropN') else 0
        start_idx = drop_n if drop_n > 0 else 0
        end_idx = start_idx + top_k if top_k > 0 else len(scored_symbols)

        for rank, (symbol, score) in enumerate(scored_symbols[start_idx:end_idx], start_idx + 1):
            if symbol in df_close.columns and symbol not in holding_symbols:
                buy_signals.append(BuySignal(
                    symbol=symbol,
                    score=score,
                    rank=rank,
                    price=df_close.iloc[-1][symbol],
                    suggested_quantity=0
                ))

        return buy_signals


if __name__ == '__main__':
    # 测试信号生成器
    generator = MultiStrategySignalGenerator()

    # 生成信号
    signals = generator.generate_signals()

    # 打印结果
    print("\n信号生成结果:")
    for strategy_name, strategy_signals in signals.items():
        print(f"\n{strategy_name}:")
        print(f"  买入: {len(strategy_signals.buy_signals)}")
        print(f"  卖出: {len(strategy_signals.sell_signals)}")
        print(f"  持有: {len(strategy_signals.hold_recommendations)}")
