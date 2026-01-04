#!/usr/bin/env python3
"""
多策略信号分析主程序
集成所有策略，生成独立的买卖信号报告

使用方法:
    python run_multi_strategy_signals.py                              # 运行所有策略
    python run_multi_strategy_signals.py --date 20251225             # 指定日期
    python run_multi_strategy_signals.py --output report.txt         # 输出到文件
    python run_multi_strategy_signals.py --max-positions 10          # 最大持仓数
"""
import argparse
import sys
from datetime import datetime

from database.pg_manager import get_db
from signals.multi_strategy_signals import MultiStrategySignalGenerator
from signals.signal_reporter import SignalReporter


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='多策略交易信号分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                              # 运行所有策略
  %(prog)s --date 20251225             # 指定分析日期
  %(prog)s --output report.txt         # 输出到文件
  %(prog)s --max-positions 10          # 设置最大持仓数
        '''
    )

    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='分析日期 (YYYYMMDD), 默认为最新可用日期'
    )

    parser.add_argument(
        '--max-positions',
        type=int,
        default=5,
        help='最大持仓数 (默认: 5)'
    )

    parser.add_argument(
        '--initial-capital',
        type=float,
        default=5000,
        help='初始资金 (默认: 5000)'
    )

    parser.add_argument(
        '--strategies',
        type=str,
        nargs='+',
        default=None,
        help='指定要运行的策略名称 (默认: 运行所有策略)'
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
            quantity=quantity
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
            price=price
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
    print("多策略交易信号分析系统")
    print("=" * 100)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.date:
        print(f"分析日期: {args.date}")
    else:
        print(f"分析日期: 最新可用日期")
    print(f"最大持仓数: {args.max_positions}")
    print(f"初始资金: {args.initial_capital:.0f}元")
    print("=" * 100)

    try:
        # 初始化数据库 (禁用详细日志)
        from loguru import logger

        logger.disable("database.db_manager")
        logger.disable("datafeed.csv_dataloader")

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
        print("\n[3/5] 初始化信号生成器...")
        generator = MultiStrategySignalGenerator()
        print("      ✓ 信号生成器初始化完成")

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
            max_positions=args.max_positions,
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
