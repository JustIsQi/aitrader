#!/usr/bin/env python3
"""
ETF策略信号生成主程序
专门处理ETF策略的买卖信号生成

功能:
- 自动过滤ETF策略(排除stocks_开头的A股策略文件)
- 生成独立的买卖信号报告
- 支持信号保存到数据库

使用方法:
    python run_etf_signals.py                              # 运行所有ETF策略
    python run_etf_signals.py --date 20251225             # 指定日期
    python run_etf_signals.py --output report.txt         # 输出到文件
    python run_etf_signals.py --save-to-db                # 保存到数据库
"""
import argparse
import sys
from datetime import datetime

from database.pg_manager import get_db
from signals.multi_strategy_signals import MultiStrategySignalGenerator
from signals.signal_reporter import SignalReporter
from signals.strategy_parser import StrategyParser


class ETFSignalGenerator(MultiStrategySignalGenerator):
    """ETF策略信号生成器 - 只处理ETF策略，过滤A股选股策略"""

    def generate_signals(self,
                        current_positions=None,
                        target_date=None):
        """
        生成ETF策略信号（自动过滤stocks_开头的A股策略）

        Args:
            current_positions: 当前持仓 DataFrame
            target_date: 目标日期 (YYYYMMDD)

        Returns:
            策略信号字典 {strategy_name: StrategySignals}
        """
        # 临时保存原始parser
        original_parser = self.parser

        # 创建临时parser并过滤策略
        try:
            # 解析所有策略
            all_strategies = self.parser.parse_all_strategies()

            # 过滤掉A股策略（stocks_开头的文件）
            etf_strategies = [s for s in all_strategies if not s.filename.startswith('stocks_')]

            if not etf_strategies:
                from loguru import logger
                logger.warning("没有发现任何ETF策略（已过滤所有A股选股策略）")
                return {}

            # 打印过滤信息
            total_count = len(all_strategies)
            etf_count = len(etf_strategies)
            filtered_count = total_count - etf_count

            print(f"  ✓ 策略过滤: 共{total_count}个策略，ETF策略{etf_count}个，已过滤A股策略{filtered_count}个")

            # 临时替换parser的解析结果
            # 这里我们需要手动处理，因为parser没有直接设置策略列表的方法
            # 所以我们重写generate_signals的逻辑

            # 继续使用父类的逻辑，但需要注入过滤后的策略
            # 为了简单起见，我们直接在这里复制父类逻辑并使用过滤后的策略

            if target_date:
                self.target_date = target_date

            # 获取当前持仓
            if current_positions is None:
                current_positions = self.db.get_positions()

            # 使用过滤后的ETF策略
            strategies = etf_strategies

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

            # 完全重写ETF信号生成逻辑，不调用父类方法
            # 因为父类方法使用StrategyLoader加载A股策略，不适合ETF
            from loguru import logger
            from database.factor_cache import FactorCache
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import os

            initial_symbols = list(all_symbols)
            all_factor_exprs = list(set(all_factor_exprs))  # 去重

            # ========== ETF不使用智能选股筛选 ==========
            logger.info("⚠️  ETF策略不使用智能选股筛选，使用完整标的池")
            all_symbols = initial_symbols
            # ========== 智能选股结束 ==========

            print(f"  ✓ {len(strategies)} 个ETF策略, {len(all_symbols)} 个标的, {len(all_factor_exprs)} 个因子")

            # 批量计算并缓存因子
            factor_cache = FactorCache(all_symbols, '20200101', self.target_date)
            factor_cache.calculate_factors(all_factor_exprs)

            # 生成每个策略的信号（并发执行）
            print(f"  生成各策略信号（并发执行）...")
            all_signals = {}

            # 过滤出有效的策略
            valid_strategies = [s for s in strategies if s.task is not None]

            if not valid_strategies:
                logger.warning("没有有效的ETF策略")
                return {}

            # 使用线程池并发执行策略信号生成
            max_workers = min(os.cpu_count() or 4, len(valid_strategies))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(
                        self._generate_strategy_signals,
                        strategy,
                        current_positions,
                        factor_cache
                    ): strategy
                    for strategy in valid_strategies
                }

                # 收集结果
                completed_count = 0
                for future in as_completed(futures):
                    strategy = futures[future]
                    try:
                        signals = future.result()
                        all_signals[strategy.task.name] = signals
                        completed_count += 1
                        print(f"  ✓ [{completed_count}/{len(valid_strategies)}] {strategy.task.name}")
                    except Exception as e:
                        logger.error(f"策略 {strategy.task.name} 执行失败: {e}")
                        # 为失败的策略创建空信号
                        from signals.multi_strategy_signals import StrategySignals
                        all_signals[strategy.task.name] = StrategySignals(
                            strategy_name=strategy.task.name,
                            buy_signals=[],
                            sell_signals=[],
                            hold_recommendations=[],
                            symbols_analyzed=strategy.task.symbols,
                            analysis_date=self.target_date
                        )

            print(f"  ✓ 完成 {len(all_signals)} 个ETF策略")

            return all_signals

        except Exception as e:
            # 恢复原始parser
            self.parser = original_parser
            raise


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='ETF策略交易信号分析（仅处理ETF策略，排除A股选股策略）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                              # 运行所有ETF策略
  %(prog)s --date 20251225             # 指定分析日期
  %(prog)s --output report.txt         # 输出到文件
  %(prog)s --save-to-db                # 保存信号到数据库
        '''
    )

    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='分析日期 (YYYYMMDD), 默认为最新可用日期'
    )

    parser.add_argument(
        '--initial-capital',
        type=float,
        default=20000,
        help='初始资金 (默认: 20000)'
    )

    parser.add_argument(
        '--strategies',
        type=str,
        nargs='+',
        default=None,
        help='指定要运行的策略名称 (默认: 运行所有ETF策略)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出报告到文件'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细执行信息'
    )

    parser.add_argument(
        '--save-to-db',
        action='store_true',
        help='保存信号到数据库trader表'
    )

    return parser.parse_args()


def save_signals_to_db(all_signals: dict, db):
    """
    保存所有策略信号到数据库

    Args:
        all_signals: 策略信号字典 {strategy_name: StrategySignals}
        db: 数据库管理器实例
    """
    from signals.multi_strategy_signals import StrategySignals
    from datetime import datetime

    # 获取当前日期 YYYY-MM-DD
    signal_date = datetime.now().strftime('%Y-%m-%d')

    # 收集所有买入和卖出信号
    buy_signals_by_symbol = {}  # symbol -> [{'strategy': name, 'score': val, 'rank': r, 'price': p}]
    sell_signals_by_symbol = {}  # symbol -> [{'strategy': name, 'price': p}]

    for strategy_name, signals in all_signals.items():
        # 收集买入信号
        for buy_signal in signals.buy_signals:
            if buy_signal.symbol not in buy_signals_by_symbol:
                buy_signals_by_symbol[buy_signal.symbol] = []

            buy_signals_by_symbol[buy_signal.symbol].append({
                'strategy': strategy_name,
                'score': buy_signal.score,
                'rank': buy_signal.rank,
                'price': buy_signal.price,
                'quantity': buy_signal.suggested_quantity
            })

        # 收集卖出信号
        for sell_signal in signals.sell_signals:
            if sell_signal.symbol not in sell_signals_by_symbol:
                sell_signals_by_symbol[sell_signal.symbol] = []

            sell_signals_by_symbol[sell_signal.symbol].append({
                'strategy': strategy_name,
                'price': sell_signal.current_price
            })

    # 插入买入信号
    buy_count = 0
    for symbol, signals_list in buy_signals_by_symbol.items():
        strategies = [s['strategy'] for s in signals_list]
        avg_score = sum(s['score'] for s in signals_list) / len(signals_list)
        min_rank = min(s['rank'] for s in signals_list)
        price = signals_list[0]['price']
        quantity = signals_list[0]['quantity']

        db.insert_trader_signal(
            symbol=symbol,
            signal_type='buy',
            strategies=strategies,
            signal_date=signal_date,
            price=price,
            score=avg_score,
            rank=min_rank,
            quantity=quantity,
            asset_type='etf'
        )
        buy_count += 1

    # 插入卖出信号
    sell_count = 0
    for symbol, signals_list in sell_signals_by_symbol.items():
        strategies = [s['strategy'] for s in signals_list]
        price = signals_list[0]['price']

        db.insert_trader_signal(
            symbol=symbol,
            signal_type='sell',
            strategies=strategies,
            signal_date=signal_date,
            price=price,
            asset_type='etf'
        )
        sell_count += 1

    print(f"      ✓ 保存信号: {buy_count}个买入, {sell_count}个卖出")


def main():
    """主函数"""
    args = parse_arguments()

    # 配置日志
    if args.verbose:
        logger.add(sys.stderr, level='INFO')

    print("\n" + "=" * 100)
    print("ETF策略交易信号分析系统")
    print("=" * 100)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"策略类型: ETF策略（已自动过滤A股选股策略）")
    if args.date:
        print(f"分析日期: {args.date}")
    else:
        print(f"分析日期: 最新可用日期")
    print(f"初始资金: {args.initial_capital:.0f}元")
    print("=" * 100)

    try:
        # 初始化数据库 (禁用详细日志)
        from loguru import logger

        logger.disable("database.db_manager")
        logger.disable("datafeed.db_dataloader")
        logger.disable("core.stock_universe")  # 禁用股票池相关日志,ETF策略不需要

        print("\n[1/5] 初始化数据库连接...")
        db = get_db()
        print("      ✓ 数据库连接成功")

        logger.enable("database.db_manager")

        # 获取当前持仓
        print("\n[2/5] 加载当前持仓...")
        current_positions = db.get_positions()

        if current_positions.empty:
            print("      ⚠️  当前无持仓")
        else:
            total_value = current_positions['market_value'].sum()
            print(f"      ✓ 持仓数量: {len(current_positions)}")
            print(f"      ✓ 总市值: {total_value:.2f}元")

        # 初始化信号生成器
        print("\n[3/5] 初始化ETF信号生成器...")
        generator = ETFSignalGenerator()
        print("      ✓ ETF信号生成器初始化完成")

        # 生成信号
        print("\n[4/5] 生成策略信号...")
        print("  加载数据并计算因子...")
        all_signals = generator.generate_signals(
            current_positions=current_positions,
            target_date=args.date
        )

        if not all_signals:
            print("\n⚠️  没有生成任何策略信号")
            return

        # 生成报告
        print("\n[5/5] 生成分析报告...")
        reporter = SignalReporter(
            initial_capital=args.initial_capital
        )

        report = reporter.generate_full_report(all_signals, current_positions)

        # 输出报告
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n✓ 报告已保存到: {args.output}")
            print(f"  文件大小: {len(report.encode('utf-8'))} 字节")
        else:
            print("\n" + report)

        # 保存信号到数据库
        if args.save_to_db:
            print("\n[6/6] 保存信号到数据库...")
            save_signals_to_db(all_signals, db)

        print(f"\n分析完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        logger.exception("执行过程中发生错误")
        print(f"\n❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
