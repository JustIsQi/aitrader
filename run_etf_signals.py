#!/usr/bin/env python3
"""
ETF策略信号生成主程序
专门处理ETF策略的买卖信号生成

功能:
- 自动过滤ETF策略(排除stocks_开头的A股策略文件)
- 生成独立的买卖信号报告
- 支持信号保存到数据库

使用方法:
    python run_etf_signals.py                              # 运行所有ETF策略(默认保存到数据库)
    python run_etf_signals.py --date 20251225             # 指定日期
    python run_etf_signals.py --output report.txt         # 输出到文件
    python run_etf_signals.py --no-save-to-db             # 不保存到数据库
"""
import argparse
import sys
from datetime import datetime
from loguru import logger

from database.pg_manager import get_db
from signals.multi_strategy_signals import MultiStrategySignalGenerator
from signals.signal_reporter import SignalReporter
from signals.strategy_parser import StrategyParser


class ETFSignalGenerator(MultiStrategySignalGenerator):
    """ETF策略信号生成器 - 只处理ETF策略，过滤A股选股策略"""

    def __init__(self, enable_smart_filter=True, filter_config=None, **kwargs):
        """
        初始化ETF信号生成器

        Args:
            enable_smart_filter: 是否启用智能ETF筛选 (默认True)
            filter_config: ETF筛选配置对象 (默认使用balanced模式)
            **kwargs: 其他传递给父类的参数
        """
        super().__init__(enable_smart_filter=enable_smart_filter,
                        filter_config=filter_config,
                        **kwargs)

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
            all_factor_exprs = []

            for strategy in strategies:
                if strategy.task is None:
                    continue

                # 不再从策略文件收集symbols,稍后从数据库动态获取
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

            # initial_symbols = None 表示从数据库全市场动态获取ETF池
            initial_symbols = None
            all_factor_exprs = list(set(all_factor_exprs))  # 去重

            # ========== ETF智能筛选 ==========
            if self.enable_smart_filter:
                from core.smart_etf_filter import SmartETFFilter, EtfFilterPresets

                # 使用提供的配置或默认balanced配置
                config = self.filter_config if self.filter_config else EtfFilterPresets.balanced()

                logger.info(f"🚀 启用ETF智能筛选,从数据库动态获取ETF池 (preset={'custom' if self.filter_config else 'balanced'})")
                smart_filter = SmartETFFilter(config)

                # 执行筛选 - 不传递initial_symbols,让filter从数据库获取全市场ETF
                filtered_symbols = smart_filter.filter_etfs(initial_symbols=None)

                # 更新策略的ETF池为筛选后的结果 (所有策略使用相同的ETF池)
                for strategy in strategies:
                    if strategy.task is None:
                        continue
                    # 所有策略使用相同的筛选后ETF池
                    strategy.task.symbols = filtered_symbols
                    logger.debug(f"  策略 {strategy.task.name}: 使用筛选后ETF池,共 {len(filtered_symbols)} 只ETF")

                # 使用筛选后的ETF池
                all_symbols = filtered_symbols
            else:
                # 即使禁用智能筛选,也从数据库获取基础ETF池
                logger.info("⚠️  ETF智能筛选已禁用,从数据库获取基础ETF池")
                from core.etf_universe import EtfUniverse
                universe = EtfUniverse()
                all_symbols = universe.get_all_etfs(min_data_days=180)
                # 更新所有策略的symbols
                for strategy in strategies:
                    if strategy.task is None:
                        continue
                    strategy.task.symbols = all_symbols
            # ========== 智能筛选结束 ==========

            print(f"  ✓ {len(strategies)} 个ETF策略, {len(all_symbols)} 个标的, {len(all_factor_exprs)} 个因子")

            # 批量计算并缓存因子
            factor_cache = FactorCache(all_symbols, '20200101', self.target_date, adjust_type='qfq')
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
  %(prog)s                                          # 运行所有ETF策略(默认使用平衡型筛选)
  %(prog)s --date 20251225                         # 指定分析日期
  %(prog)s --output report.txt                     # 输出到文件
  %(prog)s --save-to-db                            # 保存信号到数据库
  %(prog)s --filter-preset conservative            # 使用保守型筛选(大流动性ETF)
  %(prog)s --filter-preset aggressive              # 使用激进型筛选(包含小ETF)
  %(prog)s --filter-min-amount 10000               # 自定义最小成交额为1亿
  %(prog)s --filter-target-count 50                # 筛选50只ETF
  %(prog)s --disable-smart-filter                  # 禁用智能筛选(使用策略原始标的)
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
        default=40000,
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
        default=True,
        help='保存信号到数据库trader表 (默认开启)'
    )

    parser.add_argument(
        '--no-save-to-db',
        action='store_false',
        dest='save_to_db',
        help='不保存信号到数据库'
    )

    # ETF智能筛选控制
    parser.add_argument(
        '--enable-smart-filter',
        action='store_true',
        default=True,
        help='启用ETF智能筛选 (默认开启)'
    )

    parser.add_argument(
        '--disable-smart-filter',
        action='store_false',
        dest='enable_smart_filter',
        help='禁用ETF智能筛选'
    )

    parser.add_argument(
        '--filter-preset',
        type=str,
        choices=['conservative', 'balanced', 'aggressive'],
        default='balanced',
        help='ETF筛选预设: conservative(保守型), balanced(平衡型), aggressive(激进型) (默认: balanced)'
    )

    parser.add_argument(
        '--filter-min-amount',
        type=float,
        default=None,
        help='最小日均成交额(万元), 覆盖预设值 (例如: 5000表示5000万元)'
    )

    parser.add_argument(
        '--filter-min-turnover',
        type=float,
        default=None,
        help='最小换手率(%%), 覆盖预设值 (例如: 1.5表示1.5%%)'
    )

    parser.add_argument(
        '--filter-target-count',
        type=int,
        default=None,
        help='目标ETF数量, 覆盖预设值 (例如: 100表示筛选100只ETF)'
    )

    return parser.parse_args()


def run_etf_strategy_backtest(strategy_task, lookback_days=20):
    """
    运行单个ETF策略的近N天回测

    Args:
        strategy_task: 策略Task对象
        lookback_days: 回测天数(默认20天)

    Returns:
        dict: 回测指标字典
    """
    from datetime import datetime, timedelta
    from core.backtrader_engine import Engine
    from core.backtest_utils import extract_backtest_metrics
    import copy

    # 计算回测日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')

    # 复制task并设置日期范围
    backtest_task = copy.deepcopy(strategy_task)
    backtest_task.start_date = start_date
    backtest_task.end_date = end_date

    # 运行回测
    engine = Engine()
    result = engine.run(backtest_task)

    # 提取指标（传递engine对象而不是result列表）
    # 因为engine.perf、engine.hist_trades等属性在engine对象上
    metrics = extract_backtest_metrics(engine, backtest_task)
    metrics['strategy_name'] = backtest_task.name
    metrics['strategy_version'] = None  # ETF策略暂无版本
    metrics['asset_type'] = 'etf'

    return metrics


def run_etf_backtests(etf_strategies, lookback_days=20, max_workers=2):
    """
    批量运行ETF策略回测(并发)

    Args:
        etf_strategies: ETF策略列表(ParsedStrategy对象)
        lookback_days: 回测天数
        max_workers: 最大并发数

    Returns:
        dict: {strategy_name: backtest_id}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    backtest_results = {}
    db = get_db()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_etf_strategy_backtest, strategy.task, lookback_days): strategy.task.name
            for strategy in etf_strategies if strategy.task is not None
        }

        for future in as_completed(futures):
            strategy_name = futures[future]
            try:
                metrics = future.result()

                # 保存到数据库
                backtest_id = db.save_backtest_result(**metrics)
                backtest_results[strategy_name] = backtest_id

                print(f"  ✓ 回测完成: {strategy_name} (ID: {backtest_id})")
            except Exception as e:
                logger.error(f"回测失败 {strategy_name}: {e}")
                backtest_results[strategy_name] = None

    return backtest_results


def save_signals_to_db(all_signals: dict, db, backtest_results: dict = None):
    """
    保存所有策略信号到数据库（仅保存top20买入信号）

    Args:
        all_signals: 策略信号字典 {strategy_name: StrategySignals}
        db: 数据库管理器实例
        backtest_results: 策略回测结果 {strategy_name: backtest_id}
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

    # 对买入信号排序并只保留top20
    # 排序规则: 策略数量多的优先，相同时平均分数高的优先
    total_buy_signals = len(buy_signals_by_symbol)
    if total_buy_signals > 20:
        print(f"      注意: 共 {total_buy_signals} 个买入信号，仅保存前 20 个")

        sorted_buy_signals = sorted(
            buy_signals_by_symbol.items(),
            key=lambda x: (
                len(x[1]),  # 策略数量越多越好
                -sum(s['score'] for s in x[1]) / len(x[1])  # 平均分数越高越好（负号表示降序）
            ),
            reverse=True
        )[:20]  # 只取前20个

        buy_signals_by_symbol = dict(sorted_buy_signals)

    # 插入买入信号
    buy_count = 0
    for symbol, signals_list in buy_signals_by_symbol.items():
        strategies = [s['strategy'] for s in signals_list]
        avg_score = sum(s['score'] for s in signals_list) / len(signals_list)
        min_rank = min(s['rank'] for s in signals_list)
        price = signals_list[0]['price']
        quantity = signals_list[0]['quantity']

        # 插入信号
        trader_id = db.insert_trader_signal(
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

        # 关联回测结果
        if backtest_results and strategies and trader_id:
            first_strategy = strategies[0]
            backtest_id = backtest_results.get(first_strategy)
            if backtest_id:
                db.associate_signal_with_backtest(
                    trader_id=trader_id,
                    backtest_id=backtest_id,
                    strategy_name=first_strategy
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

    print(f"      ✓ 保存信号: {buy_count}个买入(top20), {sell_count}个卖出")


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

    # 显示筛选配置
    if args.enable_smart_filter:
        print(f"智能筛选: 启用 ({args.filter_preset}模式)")
    else:
        print(f"智能筛选: 禁用")
    print("=" * 100)

    try:
        # 初始化数据库 (禁用详细日志)
        logger.disable("database.db_manager")
        logger.disable("datafeed.db_dataloader")
        logger.disable("core.stock_universe")  # 禁用股票池相关日志,ETF策略不需要

        print("\n[1/7] 初始化数据库连接...")
        db = get_db()
        print("      ✓ 数据库连接成功")

        logger.enable("database.db_manager")

        # 获取当前持仓
        print("\n[2/7] 加载当前持仓...")
        current_positions = db.get_positions()

        if current_positions.empty:
            print("      ⚠️  当前无持仓")
        else:
            total_value = current_positions['market_value'].sum()
            print(f"      ✓ 持仓数量: {len(current_positions)}")
            print(f"      ✓ 总市值: {total_value:.2f}元")

        # 构建筛选配置
        filter_config = None
        if args.enable_smart_filter:
            print("\n[3/7] 构建ETF筛选配置...")
            from core.smart_etf_filter import EtfFilterConfig, EtfFilterPresets

            # 获取预设
            preset_map = {
                'conservative': EtfFilterPresets.conservative,
                'balanced': EtfFilterPresets.balanced,
                'aggressive': EtfFilterPresets.aggressive
            }
            filter_config = preset_map[args.filter_preset]()

            # CLI覆盖
            if args.filter_min_amount is not None:
                filter_config.min_avg_amount = args.filter_min_amount
                print(f"      ✓ 覆盖最小成交额: {args.filter_min_amount}万元")
            if args.filter_min_turnover is not None:
                filter_config.min_turnover_rate = args.filter_min_turnover
                print(f"      ✓ 覆盖最小换手率: {args.filter_min_turnover}%")
            if args.filter_target_count is not None:
                filter_config.target_count = args.filter_target_count
                print(f"      ✓ 覆盖目标数量: {args.filter_target_count}只")

            print(f"      ✓ 预设模式: {args.filter_preset}")
            print(f"      ✓ 最小成交额: {filter_config.min_avg_amount}万元")
            print(f"      ✓ 最小换手率: {filter_config.min_turnover_rate}%")
            print(f"      ✓ 目标数量: {filter_config.target_count}只")

        # 初始化信号生成器
        print("\n[4/7] 初始化ETF信号生成器...")
        generator = ETFSignalGenerator(
            enable_smart_filter=args.enable_smart_filter,
            filter_config=filter_config
        )
        print("      ✓ ETF信号生成器初始化完成")

        # 生成信号
        print("\n[5/7] 生成策略信号...")
        print("  加载数据并计算因子...")
        all_signals = generator.generate_signals(
            current_positions=current_positions,
            target_date=args.date
        )

        if not all_signals:
            print("\n⚠️  没有生成任何策略信号")
            return

        # 运行策略回测
        backtest_results = None
        if args.save_to_db:
            print("\n[6/7] 运行策略回测(近20天)...")

            # 从生成的信号中获取策略列表
            from signals.strategy_parser import StrategyParser
            parser = StrategyParser(strategy_dir="strategies")
            all_strategies = parser.parse_all_strategies()
            etf_strategies = [s for s in all_strategies if not s.filename.startswith('stocks_')]

            # 只回测有信号的策略
            strategy_names_with_signals = set(all_signals.keys())
            valid_strategies = [s for s in etf_strategies if s.task is not None and s.task.name in strategy_names_with_signals]

            print(f"  发现 {len(valid_strategies)} 个策略需要回测")

            # 运行回测(并发)
            if valid_strategies:
                backtest_results = run_etf_backtests(
                    etf_strategies=valid_strategies,
                    lookback_days=20,
                    max_workers=2
                )
            else:
                print("  ⚠️  没有需要回测的策略")
                backtest_results = {}

        # 生成报告
        print("\n[7/7] 生成分析报告...")
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
            print("\n保存信号到数据库...")
            save_signals_to_db(all_signals, db, backtest_results)

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
