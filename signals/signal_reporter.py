"""
信号报告生成器
格式化并输出多策略交易信号报告
"""
from typing import Dict, List
import pandas as pd
from datetime import datetime
from signals.multi_strategy_signals import StrategySignals, BuySignal, SellSignal


class SignalReporter:
    """信号报告生成器"""

    POSITION_DIVISOR = 10  # 固定仓位除数，用于计算每仓位金额

    def __init__(self, initial_capital: float = 20000):
        """
        初始化报告生成器

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.cash_per_position = initial_capital / self.POSITION_DIVISOR

    def generate_full_report(self,
                            all_signals: Dict[str, StrategySignals],
                            current_positions: pd.DataFrame) -> str:
        """
        生成完整报告

        Args:
            all_signals: 所有策略信号
            current_positions: 当前持仓

        Returns:
            报告字符串
        """
        lines = []
        lines.append("=" * 100)
        lines.append("多策略交易信号分析报告")
        lines.append("=" * 100)
        lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"分析策略数量: {len(all_signals)}")
        lines.append("")

        # 当前持仓摘要
        lines.extend(self._format_holdings_summary(current_positions))
        lines.append("")

        # 各策略信号详情
        lines.append("=" * 100)
        lines.append("各策略信号详情")
        lines.append("=" * 100)
        lines.append("")

        for strategy_name, signals in all_signals.items():
            lines.extend(self._format_strategy_signals(strategy_name, signals))
            lines.append("")

        # 跨策略信号汇总
        lines.extend(self._format_cross_strategy_aggregation(all_signals))
        lines.append("")

        # 操作建议汇总
        lines.extend(self._format_actionable_recommendations(all_signals, current_positions))
        lines.append("")

        return "\n".join(lines)

    def _format_holdings_summary(self, current_positions: pd.DataFrame) -> List[str]:
        """
        格式化当前持仓摘要

        Args:
            current_positions: 当前持仓

        Returns:
            格式化的行列表
        """
        lines = []
        lines.append("=" * 100)
        lines.append("当前持仓情况")
        lines.append("=" * 100)

        if current_positions.empty:
            lines.append("当前无持仓")
        else:
            total_value = current_positions['market_value'].sum()
            lines.append(f"持仓数量: {len(current_positions)}")
            lines.append(f"总市值: {total_value:.2f}元")
            lines.append("")
            lines.append(f"{'代码':<15} {'数量':>10} {'成本价':>10} {'现价':>10} {'市值':>12} {'盈亏%':>10}")
            lines.append("-" * 100)

            for _, row in current_positions.iterrows():
                profit_pct = (row['current_price'] - row['avg_cost']) / row['avg_cost'] * 100
                lines.append(
                    f"{row['symbol']:<15} "
                    f"{row['quantity']:>10.0f} "
                    f"{row['avg_cost']:>10.3f} "
                    f"{row['current_price']:>10.3f} "
                    f"{row['market_value']:>12.2f} "
                    f"{profit_pct:>10.2f}%"
                )

        return lines

    def _format_strategy_signals(self, strategy_name: str, signals: StrategySignals) -> List[str]:
        """
        格式化单个策略的信号

        Args:
            strategy_name: 策略名称
            signals: 策略信号

        Returns:
            格式化的行列表
        """
        lines = []
        lines.append("-" * 100)
        lines.append(f"策略: {strategy_name}")
        lines.append(f"分析标的数量: {len(signals.symbols_analyzed)}")
        lines.append("-" * 100)

        # 卖出信号
        if signals.sell_signals:
            lines.append(f"\n卖出信号 ({len(signals.sell_signals)}个):")
            lines.append(f"{'代码':<15} {'现价':>10} {'持仓量':>10} {'成本价':>10} {'盈亏%':>10} {'触发原因'}")
            lines.append("-" * 100)

            for sell in signals.sell_signals:
                lines.append(
                    f"{sell.symbol:<15} "
                    f"{sell.current_price:>10.3f} "
                    f"{sell.quantity:>10.0f} "
                    f"{sell.avg_cost:>10.3f} "
                    f"{sell.profit_loss_pct:>10.2f}% "
                    f"{sell.trigger_reason}"
                )
        else:
            lines.append("\n卖出信号: 无")

        # 买入信号
        if signals.buy_signals:
            lines.append(f"\n买入信号 ({len(signals.buy_signals)}个):")
            lines.append(f"{'排名':>6} {'代码':<15} {'价格':>10} {'评分':>12} {'建议数量':>10}")
            lines.append("-" * 100)

            for buy in signals.buy_signals:
                quantity = int(self.cash_per_position / buy.price) if buy.price > 0 else 0
                lines.append(
                    f"{buy.rank:>6} "
                    f"{buy.symbol:<15} "
                    f"{buy.price:>10.3f} "
                    f"{buy.score:>12.4f} "
                    f"{quantity:>10.0f}"
                )
        else:
            lines.append("\n买入信号: 无")

        # 持仓建议
        if signals.hold_recommendations:
            lines.append(f"\n持仓建议: {', '.join(signals.hold_recommendations)}")
        else:
            if not signals.sell_signals:
                lines.append("\n持仓建议: 无 (当前无持仓或全部建议卖出)")

        return lines

    def _format_cross_strategy_aggregation(self, all_signals: Dict[str, StrategySignals]) -> List[str]:
        """
        格式化跨策略信号汇总

        Args:
            all_signals: 所有策略信号

        Returns:
            格式化的行列表
        """
        lines = []
        lines.append("=" * 100)
        lines.append("跨策略信号汇总")
        lines.append("=" * 100)

        # 统计买入信号
        buy_counts = {}
        buy_scores = {}

        for strategy_name, signals in all_signals.items():
            for buy in signals.buy_signals:
                if buy.symbol not in buy_counts:
                    buy_counts[buy.symbol] = []
                    buy_scores[buy.symbol] = []

                buy_counts[buy.symbol].append(strategy_name)
                buy_scores[buy.symbol].append(buy.score)

        # 统计卖出信号
        sell_counts = {}
        for strategy_name, signals in all_signals.items():
            for sell in signals.sell_signals:
                if sell.symbol not in sell_counts:
                    sell_counts[sell.symbol] = []

                sell_counts[sell.symbol].append(strategy_name)

        # 显示买入汇总
        if buy_counts:
            lines.append("\n买入信号汇总 (按推荐策略数量排序):")
            lines.append(f"{'代码':<15} {'推荐策略数':>12} {'平均评分':>12} {'推荐策略'}")
            lines.append("-" * 100)

            # 按推荐数量排序
            sorted_buys = sorted(buy_counts.items(), key=lambda x: len(x[1]), reverse=True)

            for symbol, strategies in sorted_buys:
                avg_score = sum(buy_scores[symbol]) / len(buy_scores[symbol])
                lines.append(
                    f"{symbol:<15} "
                    f"{len(strategies):>12} "
                    f"{avg_score:>12.4f} "
                    f"{', '.join(strategies[:3])}{'...' if len(strategies) > 3 else ''}"
                )
        else:
            lines.append("\n买入信号汇总: 无买入建议")

        # 显示卖出汇总
        if sell_counts:
            lines.append("\n卖出信号汇总 (按推荐策略数量排序):")
            lines.append(f"{'代码':<15} {'推荐策略数':>12} {'推荐策略'}")
            lines.append("-" * 100)

            sorted_sells = sorted(sell_counts.items(), key=lambda x: len(x[1]), reverse=True)

            for symbol, strategies in sorted_sells:
                lines.append(
                    f"{symbol:<15} "
                    f"{len(strategies):>12} "
                    f"{', '.join(strategies[:3])}{'...' if len(strategies) > 3 else ''}"
                )
        else:
            lines.append("\n卖出信号汇总: 无卖出建议")

        return lines

    def _format_actionable_recommendations(self,
                                          all_signals: Dict[str, StrategySignals],
                                          current_positions: pd.DataFrame) -> List[str]:
        """
        格式化操作建议

        Args:
            all_signals: 所有策略信号
            current_positions: 当前持仓

        Returns:
            格式化的行列表
        """
        lines = []
        lines.append("=" * 100)
        lines.append("操作建议汇总")
        lines.append("=" * 100)

        # 获取当前持仓集合
        if current_positions.empty:
            holding_symbols = set()
        else:
            holding_symbols = set(current_positions['symbol'].tolist())

        # 统计卖出信号 (按策略数量)
        sell_counts = {}
        sell_details = {}

        for strategy_name, signals in all_signals.items():
            for sell in signals.sell_signals:
                if sell.symbol not in sell_counts:
                    sell_counts[sell.symbol] = []
                    sell_details[sell.symbol] = sell

                sell_counts[sell.symbol].append(strategy_name)

        # 优先级1: 强烈建议卖出 (2个以上策略推荐)
        priority_sells = {s: strategies for s, strategies in sell_counts.items() if len(strategies) >= 2}

        if priority_sells:
            lines.append("\n【优先处理】强烈建议卖出 (2个以上策略推荐):")
            for symbol, strategies in priority_sells.items():
                sell = sell_details[symbol]
                lines.append(f"  {symbol}: {', '.join(strategies)}")
                lines.append(f"     持仓{sell.quantity:.0f}股 @ {sell.avg_cost:.3f}元, "
                           f"现价{sell.current_price:.3f}元, 盈亏{sell.profit_loss_pct:.2f}%")
        elif sell_counts:
            lines.append("\n【建议关注】卖出信号 (1个策略推荐):")
            for symbol, strategies in sell_counts.items():
                sell = sell_details[symbol]
                lines.append(f"  {symbol}: {strategies[0]}")
                lines.append(f"     持仓{sell.quantity:.0f}股 @ {sell.avg_cost:.3f}元, "
                           f"现价{sell.current_price:.3f}元, 盈亏{sell.profit_loss_pct:.2f}%")
        else:
            lines.append("\n【无卖出建议】")

        # 统计买入信号
        buy_counts = {}
        buy_scores = {}
        buy_prices = {}

        for strategy_name, signals in all_signals.items():
            for buy in signals.buy_signals:
                if buy.symbol not in buy_counts:
                    buy_counts[buy.symbol] = []
                    buy_scores[buy.symbol] = []
                    buy_prices[buy.symbol] = buy.price

                buy_counts[buy.symbol].append(strategy_name)
                buy_scores[buy.symbol].append(buy.score)

        # 计算平均评分
        buy_avg_scores = {}
        for symbol in buy_counts:
            buy_avg_scores[symbol] = sum(buy_scores[symbol]) / len(buy_scores[symbol])

        # 按推荐数量和评分排序
        sorted_buys = sorted(
            buy_avg_scores.items(),
            key=lambda x: (len(buy_counts[x[0]]), x[1]),
            reverse=True
        )

        # 优先级2: 建议买入
        if sorted_buys:
            lines.append(f"\n【建议买入】 ({len(sorted_buys)}个信号)")

            for rank, (symbol, avg_score) in enumerate(sorted_buys, 1):
                strategies = buy_counts[symbol]
                price = buy_prices[symbol]

                if price and price > 0:
                    quantity = int(self.cash_per_position / price)
                    investment = quantity * price

                    lines.append(f"  {rank}. {symbol} - {len(strategies)}个策略推荐, 平均评分{avg_score:.4f}")
                    lines.append(f"     策略: {', '.join(strategies[:2])}{'...' if len(strategies) > 2 else ''}")
                    lines.append(f"     建议: 买入{quantity}股 @ {price:.3f}元, 投入{investment:.2f}元")
        else:
            lines.append("\n【无买入建议】")

        lines.append("\n" + "=" * 100)
        lines.append("注意: 以上建议仅供参考，实际操作请结合市场情况和个人判断")
        lines.append("=" * 100)

        return lines


if __name__ == '__main__':
    # 测试报告生成器
    from multi_strategy_signals import BuySignal, SellSignal, StrategySignals

    # 创建模拟信号
    test_signals = {
        '策略1': StrategySignals(
            strategy_name='策略1',
            buy_signals=[
                BuySignal(symbol='513100.SH', score=0.05, rank=1, price=1.38, suggested_quantity=72),
                BuySignal(symbol='518880.SH', score=0.04, rank=2, price=5.45, suggested_quantity=18)
            ],
            sell_signals=[
                SellSignal(symbol='159915.SZ', current_price=0.92, quantity=200,
                          avg_cost=0.85, profit_loss_pct=8.24, trigger_reason='满足卖出条件')
            ],
            hold_recommendations=['510300.SH'],
            symbols_analyzed=['513100.SH', '518880.SH', '159915.SZ', '510300.SH'],
            analysis_date='20251226'
        ),
        '策略2': StrategySignals(
            strategy_name='策略2',
            buy_signals=[
                BuySignal(symbol='513100.SH', score=0.06, rank=1, price=1.38, suggested_quantity=72)
            ],
            sell_signals=[
                SellSignal(symbol='159915.SZ', current_price=0.92, quantity=200,
                          avg_cost=0.85, profit_loss_pct=8.24, trigger_reason='满足卖出条件')
            ],
            hold_recommendations=[],
            symbols_analyzed=['513100.SH', '159915.SZ'],
            analysis_date='20251226'
        )
    }

    # 创建模拟持仓
    import pandas as pd
    test_positions = pd.DataFrame({
        'symbol': ['513100.SH', '159915.SZ', '510300.SH'],
        'quantity': [100, 200, 150],
        'avg_cost': [1.25, 0.85, 4.20],
        'current_price': [1.38, 0.92, 4.35],
        'market_value': [138.0, 184.0, 652.5],
        'updated_at': pd.to_datetime(['2025-12-26'] * 3)
    })

    # 生成报告
    reporter = SignalReporter()
    report = reporter.generate_full_report(test_signals, test_positions)
    print(report)
