"""
A股策略回测脚本

支持批量运行多个策略，生成对比报告

使用方式:
    # 运行所有策略
    python scripts/run_stock_backtests.py --all

    # 运行指定策略
    python scripts/run_stock_backtests.py --strategy multi_factor --period weekly

    # 显示图表
    python scripts/run_stock_backtests.py --strategy momentum --period monthly --plot

作者: AITrader
日期: 2026-01-06
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.backtrader_engine import Engine
import argparse


def run_single_strategy(strategy_func, strategy_name, plot=False):
    """
    运行单个策略

    Args:
        strategy_func: 策略函数
        strategy_name: 策略名称
        plot: 是否显示图表

    Returns:
        result: 回测结果对象
    """
    print(f"\n{'='*60}")
    print(f"运行策略: {strategy_name}")
    print(f"{'='*60}")

    try:
        task = strategy_func()

        # 显示策略配置
        print(f"\n策略配置:")
        print(f"  名称: {task.name}")
        print(f"  股票池: {len(task.symbols)} 只")
        print(f"  买入条件: {len(task.select_buy)} 个")
        print(f"  卖出条件: {len(task.select_sell)} 个")
        print(f"  调仓周期: {task.period}")
        print(f"  持仓数量: {task.order_by_topK}")
        print(f"  A股模式: {'是' if task.ashare_mode else '否'}")

        # 运行回测
        print(f"\n开始回测...")
        engine = Engine()
        result = engine.run(task)

        # 显示结果
        print("\n" + "="*60)
        print("回测结果")
        print("="*60)

        # 调用stats方法显示统计信息
        result.stats()

        # 可选: 绘制图表
        if plot:
            print("\n生成图表...")
            try:
                result.plot()
            except Exception as e:
                print(f"绘图失败: {e}")

        return result

    except Exception as e:
        print(f"\n策略 {strategy_name} 运行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_strategies(plot=False):
    """
    批量运行所有策略

    Args:
        plot: 是否显示图表

    Returns:
        dict: 策略名称到结果的映射
    """
    # 导入所有策略
    from strategies.stocks_多因子智能选股策略 import (
        multi_factor_strategy_weekly,
        multi_factor_strategy_monthly,
        multi_factor_strategy_conservative
    )
    from strategies.stocks_动量轮动选股策略 import (
        momentum_strategy_weekly,
        momentum_strategy_monthly,
        momentum_strategy_aggressive
    )

    # 定义策略列表
    strategies = [
        ('多因子-周频', multi_factor_strategy_weekly),
        ('多因子-月频', multi_factor_strategy_monthly),
        ('多因子-保守版', multi_factor_strategy_conservative),
        ('动量-周频', momentum_strategy_weekly),
        ('动量-月频', momentum_strategy_monthly),
        ('动量-激进版', momentum_strategy_aggressive),
    ]

    results = {}
    successful_count = 0
    failed_count = 0

    print("\n" + "#"*60)
    print("# 批量运行所有A股策略")
    print("#"*60)

    for name, strategy_func in strategies:
        print(f"\n\n{'#'*60}")
        print(f"# 策略: {name}")
        print(f"{'#'*60}")

        result = run_single_strategy(strategy_func, name, plot)

        if result is not None:
            results[name] = result
            successful_count += 1
        else:
            failed_count += 1

    # 生成对比报告
    if results:
        print("\n\n" + "="*60)
        print("策略对比报告")
        print("="*60)

        # 尝试提取关键指标
        print(f"\n{'策略名称':<20} {'状态':<10} {'备注':<30}")
        print("-"*60)

        for name, result in results.items():
            try:
                # 这里只是简单标记成功，实际指标需要根据result对象结构调整
                print(f"{name:<20} {'✅ 成功':<10}")
            except Exception as e:
                print(f"{name:<20} {'⚠️ 部分成功':<10} {str(e)[:28]}")

        # 显示运行统计
        print("\n" + "="*60)
        print("运行统计")
        print("="*60)
        print(f"总策略数: {len(strategies)}")
        print(f"成功: {successful_count}")
        print(f"失败: {failed_count}")
        print(f"成功率: {successful_count/len(strategies)*100:.1f}%")

    return results


def run_multi_factor_strategies(plot=False):
    """运行所有多因子策略"""
    from strategies.stocks_多因子智能选股策略 import (
        multi_factor_strategy_weekly,
        multi_factor_strategy_monthly,
        multi_factor_strategy_conservative
    )

    strategies = [
        ('多因子-周频', multi_factor_strategy_weekly),
        ('多因子-月频', multi_factor_strategy_monthly),
        ('多因子-保守版', multi_factor_strategy_conservative),
    ]

    results = {}
    for name, strategy_func in strategies:
        result = run_single_strategy(strategy_func, name, plot)
        if result:
            results[name] = result

    return results


def run_momentum_strategies(plot=False):
    """运行所有动量策略"""
    from strategies.stocks_动量轮动选股策略 import (
        momentum_strategy_weekly,
        momentum_strategy_monthly,
        momentum_strategy_aggressive
    )

    strategies = [
        ('动量-周频', momentum_strategy_weekly),
        ('动量-月频', momentum_strategy_monthly),
        ('动量-激进版', momentum_strategy_aggressive),
    ]

    results = {}
    for name, strategy_func in strategies:
        result = run_single_strategy(strategy_func, name, plot)
        if result:
            results[name] = result

    return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='A股策略回测脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行所有策略
  python scripts/run_stock_backtests.py --all

  # 运行多因子策略
  python scripts/run_stock_backtests.py --strategy multi_factor --period weekly

  # 运行动量策略
  python scripts/run_stock_backtests.py --strategy momentum --period monthly

  # 显示图表
  python scripts/run_stock_backtests.py --all --plot

  # 运行所有多因子策略
  python scripts/run_stock_backtests.py --multi-factor-all

  # 运行所有动量策略
  python scripts/run_stock_backtests.py --momentum-all
        """
    )

    parser.add_argument('--all', action='store_true',
                        help='运行所有策略')
    parser.add_argument('--multi-factor-all', action='store_true',
                        help='运行所有多因子策略')
    parser.add_argument('--momentum-all', action='store_true',
                        help='运行所有动量策略')
    parser.add_argument('--strategy', type=str,
                        choices=['multi_factor', 'momentum'],
                        help='策略类型 (multi_factor|momentum)')
    parser.add_argument('--period', type=str,
                        choices=['weekly', 'monthly', 'conservative', 'aggressive'],
                        help='调仓周期 (weekly|monthly|conservative|aggressive)')
    parser.add_argument('--plot', action='store_true',
                        help='显示图表')

    args = parser.parse_args()

    # 默认运行周频多因子策略
    if not any([args.all, args.multi_factor_all, args.momentum_all,
                args.strategy, args.period]):
        print("未指定策略，运行默认策略: 多因子周频")
        from strategies.stocks_多因子智能选股策略 import multi_factor_strategy_weekly
        run_single_strategy(multi_factor_strategy_weekly, '多因子-周频', args.plot)
        return

    # 运行所有策略
    if args.all:
        run_all_strategies(plot=args.plot)
        return

    # 运行所有多因子策略
    if args.multi_factor_all:
        run_multi_factor_strategies(plot=args.plot)
        return

    # 运行所有动量策略
    if args.momentum_all:
        run_momentum_strategies(plot=args.plot)
        return

    # 运行指定策略
    if args.strategy and args.period:
        # 导入对应策略
        if args.strategy == 'multi_factor':
            from strategies.stocks_多因子智能选股策略 import (
                multi_factor_strategy_weekly,
                multi_factor_strategy_monthly,
                multi_factor_strategy_conservative
            )
            strategy_map = {
                'weekly': multi_factor_strategy_weekly,
                'monthly': multi_factor_strategy_monthly,
                'conservative': multi_factor_strategy_conservative
            }
        else:  # momentum
            from strategies.stocks_动量轮动选股策略 import (
                momentum_strategy_weekly,
                momentum_strategy_monthly,
                momentum_strategy_aggressive
            )
            strategy_map = {
                'weekly': momentum_strategy_weekly,
                'monthly': momentum_strategy_monthly,
                'aggressive': momentum_strategy_aggressive
            }

        strategy_func = strategy_map.get(args.period)
        if strategy_func:
            strategy_name = f"{args.strategy}-{args.period}"
            run_single_strategy(strategy_func, strategy_name, args.plot)
        else:
            print(f"错误: 策略类型 {args.strategy} 不支持周期 {args.period}")


if __name__ == '__main__':
    main()
