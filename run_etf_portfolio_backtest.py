#!/usr/bin/env python3
"""
ETF组合回测主程序

使用组合回测引擎对ETF策略进行完整的历史回测

使用方法:
    python run_etf_portfolio_backtest.py                                    # 回测所有ETF策略
    python run_etf_portfolio_backtest.py --strategy "基于ETF历史评分的轮动策略"  # 指定策略
    python run_etf_portfolio_backtest.py --start 20200101 --end 20251215     # 指定日期范围
    python run_etf_portfolio_backtest.py --capital 1000000                  # 指定初始资金
"""
import argparse
import sys
from datetime import datetime
from loguru import logger

from core.portfolio_bt_engine import PortfolioBacktestEngine, PortfolioTask
from signals.strategy_parser import StrategyParser
from core.smart_etf_filter import SmartETFFilter, EtfFilterPresets


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='ETF组合回测系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                                              # 回测所有ETF策略
  %(prog)s --strategy "基于ETF历史评分的轮动策略"       # 指定策略
  %(prog)s --start 20200101 --end 20251215            # 指定日期范围
  %(prog)s --capital 1000000                          # 指定初始资金
  %(prog)s --filter-preset balanced                   # 使用平衡型筛选
        '''
    )

    parser.add_argument(
        '--strategy',
        type=str,
        default=None,
        help='策略名称 (默认: 运行所有ETF策略)'
    )

    parser.add_argument(
        '--start',
        type=str,
        default='20200101',
        help='回测开始日期 (YYYYMMDD, 默认: 20200101)'
    )

    parser.add_argument(
        '--end',
        type=str,
        default=None,
        help='回测结束日期 (YYYYMMDD, 默认: 最新日期)'
    )

    parser.add_argument(
        '--capital',
        type=float,
        default=1000000,
        help='初始资金 (默认: 1000000)'
    )

    parser.add_argument(
        '--commission',
        type=float,
        default=0.0003,
        help='手续费率 (默认: 0.0003, 即万三)'
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
        help='ETF筛选预设 (默认: balanced)'
    )

    return parser.parse_args()


def run_single_strategy_backtest(strategy, start_date, end_date, initial_capital, commission_rate):
    """
    运行单个策略的组合回测

    Args:
        strategy: ParsedStrategy对象
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        commission_rate: 手续费率

    Returns:
        回测结果字典
    """
    task = strategy.task

    # 创建组合回测任务
    portfolio_task = PortfolioTask(
        name=task.name,
        symbols=task.symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        commission_rate=commission_rate,

        # 买入条件
        select_buy=task.select_buy,
        buy_at_least_count=task.buy_at_least_count if task.buy_at_least_count > 0 else len(task.select_buy),

        # 卖出条件
        select_sell=task.select_sell,
        sell_at_least_count=task.sell_at_least_count if task.sell_at_least_count > 0 else 1,

        # 组合配置
        weight_type='equal',
        rebalance_on_signal_change=True
    )

    # 运行回测
    engine = PortfolioBacktestEngine(portfolio_task)
    result = engine.run()

    return result


def print_backtest_result(result):
    """打印回测结果"""
    print("\n" + "="*80)
    print(f"策略名称: {result['strategy_name']}")
    print(f"回测期间: {result['start_date']} ~ {result['end_date']}")
    print(f"初始资金: {result['initial_capital']:,.0f} 元")
    print(f"最终资金: {result['final_value']:,.0f} 元")
    print("="*80)
    print(f"总收益: {result['total_return']*100:.2f}%")
    print(f"年化收益: {result['annual_return']*100:.2f}%")
    print(f"夏普比率: {result['sharpe_ratio']:.2f}")
    print(f"Sortino比率: {result['sortino_ratio']:.2f}")
    print(f"Calmar比率: {result['calmar_ratio']:.2f}")
    print(f"最大回撤: {result['max_drawdown']*100:.2f}%")
    print(f"95% VaR: {result['var_95']*100:.2f}%")
    print(f"95% CVaR: {result['cvar_95']*100:.2f}%")
    print("="*80)
    print(f"平均换手率: {result['avg_turnover_rate']*100:.2f}%")
    print(f"总交易次数: {result['total_trades']}")
    print(f"日胜率: {result['win_rates']['daily']:.2f}%")
    print(f"周胜率: {result['win_rates']['weekly']:.2f}%")
    print(f"月胜率: {result['win_rates']['monthly']:.2f}%")
    print("="*80)

    # 打印月度收益（前6个月和后6个月）
    if result['monthly_returns']:
        print("\n月度收益 (部分):")
        monthly_items = list(result['monthly_returns'].items())
        for month, ret in monthly_items[:6]:
            print(f"  {month}: {ret*100:+.2f}%")
        if len(monthly_items) > 6:
            print("  ...")
            for month, ret in monthly_items[-6:]:
                print(f"  {month}: {ret*100:+.2f}%")

    # 打印最后持仓
    if result['final_holdings']:
        print("\n最后持仓:")
        for holding in result['final_holdings']:
            print(f"  {holding['symbol']}: {holding['shares']:,}股, "
                  f"市值 {holding['market_value']:,.0f}元, "
                  f"权重 {holding['weight']*100:.2f}%")


def main():
    """主函数"""
    args = parse_arguments()

    # 设置结束日期
    if args.end is None:
        end_date = datetime.now().strftime('%Y%m%d')
    else:
        end_date = args.end

    print("\n" + "=" * 100)
    print("ETF组合回测系统")
    print("=" * 100)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"回测期间: {args.start} ~ {end_date}")
    print(f"初始资金: {args.capital:,.0f} 元")
    print(f"手续费率: {args.commission*10000:.0f} 万分之")
    if args.enable_smart_filter:
        print(f"智能筛选: 启用 ({args.filter_preset}模式)")
    else:
        print(f"智能筛选: 禁用")
    print("=" * 100)

    try:
        # 禁用详细日志
        logger.disable("database.db_manager")
        logger.disable("datafeed.db_dataloader")

        print("\n[1/4] 初始化数据库连接...")
        from database.pg_manager import get_db
        db = get_db()
        print("      ✓ 数据库连接成功")

        print("\n[2/4] 解析ETF策略...")
        parser = StrategyParser(strategy_dir="strategies")
        all_strategies = parser.parse_all_strategies()

        # 过滤ETF策略
        etf_strategies = [s for s in all_strategies if not s.filename.startswith('stocks_')]

        if args.strategy:
            # 指定策略
            etf_strategies = [s for s in etf_strategies if s.task and s.task.name == args.strategy]
            if not etf_strategies:
                print(f"  ❌ 未找到策略: {args.strategy}")
                sys.exit(1)

        print(f"      ✓ 发现 {len(etf_strategies)} 个ETF策略")

        # 应用ETF智能筛选
        if args.enable_smart_filter:
            print("\n[3/4] 应用ETF智能筛选...")
            filter_config = EtfFilterPresets.balanced()
            if args.filter_preset == 'conservative':
                filter_config = EtfFilterPresets.conservative()
            elif args.filter_preset == 'aggressive':
                filter_config = EtfFilterPresets.aggressive()

            smart_filter = SmartETFFilter(filter_config)
            filtered_symbols = smart_filter.filter_etfs(initial_symbols=None)

            # 更新所有策略的ETF池
            for strategy in etf_strategies:
                if strategy.task:
                    strategy.task.symbols = filtered_symbols

            print(f"      ✓ 筛选后ETF池: {len(filtered_symbols)} 只")
        else:
            print("\n[3/4] 跳过ETF智能筛选")

        print("\n[4/4] 运行组合回测...")

        # 运行回测
        results = []
        for i, strategy in enumerate(etf_strategies, 1):
            if strategy.task is None:
                continue

            print(f"\n  [{i}/{len(etf_strategies)}] 回测策略: {strategy.task.name}")

            try:
                result = run_single_strategy_backtest(
                    strategy=strategy,
                    start_date=args.start,
                    end_date=end_date,
                    initial_capital=args.capital,
                    commission_rate=args.commission
                )
                results.append(result)
            except Exception as e:
                logger.error(f"策略 {strategy.task.name} 回测失败: {e}")
                print(f"  ❌ 回测失败: {e}")

        # 打印所有结果
        if results:
            print("\n\n" + "=" * 100)
            print("回测结果汇总")
            print("=" * 100)

            for result in results:
                print_backtest_result(result)

            # 对比表格
            if len(results) > 1:
                print("\n" + "=" * 100)
                print("策略对比")
                print("=" * 100)
                print(f"{'策略名称':<30} {'总收益':>10} {'年化收益':>10} {'夏普':>8} {'最大回撤':>10} {'换手率':>10}")
                print("-" * 100)
                for result in results:
                    print(f"{result['strategy_name']:<30} "
                          f"{result['total_return']*100:>9.2f}% "
                          f"{result['annual_return']*100:>9.2f}% "
                          f"{result['sharpe_ratio']:>8.2f} "
                          f"{result['max_drawdown']*100:>9.2f}% "
                          f"{result['avg_turnover_rate']*100:>9.2f}%")

        print(f"\n\n回测完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        sys.exit(1)
    except Exception as e:
        logger.exception("执行过程中发生错误")
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
