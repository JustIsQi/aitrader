"""
A股策略回测 CLI 入口

用法:
    python -m aitrader.app.cli.stock_backtests [--all] [--multi-factor-all]
                                               [--momentum-all]
                                               [--strategy multi_factor|momentum]
                                               [--period weekly|monthly|...]
                                               [--plot]
"""

from __future__ import annotations

import argparse
import sys

from aitrader.infrastructure.config.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='A股策略回测',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m aitrader.app.cli.stock_backtests --all                  运行所有策略
  python -m aitrader.app.cli.stock_backtests --multi-factor-all     运行所有多因子策略
  python -m aitrader.app.cli.stock_backtests --momentum-all         运行所有动量策略
  python -m aitrader.app.cli.stock_backtests --strategy multi_factor --period weekly
  python -m aitrader.app.cli.stock_backtests --all --plot            带图表
        """,
    )
    parser.add_argument('--all', action='store_true', help='运行所有策略')
    parser.add_argument('--multi-factor-all', action='store_true',
                        help='运行所有多因子策略')
    parser.add_argument('--momentum-all', action='store_true',
                        help='运行所有动量策略')
    parser.add_argument('--strategy', type=str,
                        choices=['multi_factor', 'momentum'],
                        help='策略类型')
    parser.add_argument('--period', type=str,
                        choices=['weekly', 'monthly', 'conservative', 'aggressive'],
                        help='调仓周期')
    parser.add_argument('--plot', action='store_true', help='显示图表')
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging('stock_backtests.log')
    args = build_parser().parse_args(argv)

    from aitrader.app.use_cases.stock_backtests import (
        run_all_strategies,
        run_multi_factor_strategies,
        run_momentum_strategies,
        run_single_strategy,
    )

    if args.all:
        run_all_strategies(plot=args.plot)
        return 0

    if args.multi_factor_all:
        run_multi_factor_strategies(plot=args.plot)
        return 0

    if args.momentum_all:
        run_momentum_strategies(plot=args.plot)
        return 0

    if args.strategy and args.period:
        if args.strategy == 'multi_factor':
            from aitrader.domain.strategy.multi_factor import (
                multi_factor_strategy_weekly,
                multi_factor_strategy_monthly,
                multi_factor_strategy_conservative,
            )
            strategy_map = {
                'weekly': multi_factor_strategy_weekly,
                'monthly': multi_factor_strategy_monthly,
                'conservative': multi_factor_strategy_conservative,
            }
        else:
            from aitrader.domain.strategy.momentum import (
                momentum_strategy_weekly,
                momentum_strategy_monthly,
                momentum_strategy_aggressive,
            )
            strategy_map = {
                'weekly': momentum_strategy_weekly,
                'monthly': momentum_strategy_monthly,
                'aggressive': momentum_strategy_aggressive,
            }

        func = strategy_map.get(args.period)
        if func:
            run_single_strategy(func, f"{args.strategy}-{args.period}", args.plot)
        else:
            print(f"错误: 策略 {args.strategy} 不支持周期 {args.period}", file=sys.stderr)
            return 1
        return 0

    # 默认: 运行周频多因子策略
    print("未指定策略，运行默认策略: 多因子周频")
    from aitrader.domain.strategy.multi_factor import multi_factor_strategy_weekly
    run_single_strategy(multi_factor_strategy_weekly, '多因子-周频', args.plot)
    return 0


if __name__ == '__main__':
    sys.exit(main())
