"""
A股策略信号生成 CLI 入口

用法:
    python -m aitrader.app.cli.ashare_signals [--signal] [--weekly] [--monthly]
                                              [--force-backtest] [--workers N]
                                              [--filter-preset balanced]
                                              [--filter-target 1000] [--no-filter]
"""

from __future__ import annotations

import argparse
import sys

from aitrader.infrastructure.config.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='A股策略信号生成管道',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m aitrader.app.cli.ashare_signals --signal        仅生成信号(周频)
  python -m aitrader.app.cli.ashare_signals --weekly        周频策略: 回测+信号
  python -m aitrader.app.cli.ashare_signals --monthly       月频策略: 回测+信号
  python -m aitrader.app.cli.ashare_signals                 所有策略: 回测+信号
  python -m aitrader.app.cli.ashare_signals --signal --no-filter   禁用智能筛选
        """,
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--signal', action='store_true',
                            help='信号生成模式: 仅生成周频策略信号（每日推荐）')
    mode_group.add_argument('--all-signal', action='store_true',
                            help='全量信号模式: 生成所有策略信号（周频+月频）')
    mode_group.add_argument('--weekly', action='store_true',
                            help='周频策略模式: 运行周频策略回测并生成信号')
    mode_group.add_argument('--monthly', action='store_true',
                            help='月频策略模式: 运行月频策略回测并生成信号')

    parser.add_argument('--force-backtest', action='store_true',
                        help='强制重新运行回测')
    parser.add_argument('--workers', type=int, default=None,
                        help='并发回测线程数（默认2，最多3）')
    parser.add_argument('--filter-preset', type=str,
                        choices=['conservative', 'balanced', 'aggressive'],
                        default='balanced',
                        help='智能选股预设配置 (默认: balanced)')
    parser.add_argument('--filter-target', type=int, default=1000,
                        help='筛选目标股票数量 (默认: 1000)')
    parser.add_argument('--no-filter', action='store_true',
                        help='禁用智能筛选，使用完整股票池')

    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging('ashare_pipeline.log')
    args = build_parser().parse_args(argv)

    if args.signal:
        mode = 'signal-weekly'
    elif args.all_signal:
        mode = 'signal-all'
    elif args.weekly:
        mode = 'weekly'
    elif args.monthly:
        mode = 'monthly'
    else:
        mode = 'all'

    # 构建智能筛选配置（延迟导入，避免循环依赖）
    if args.no_filter:
        filter_config = None
        enable_filter = False
    else:
        from aitrader.domain.market.smart_filter import FilterPresets
        enable_filter = True
        preset_map = {
            'conservative': FilterPresets.conservative(),
            'balanced': FilterPresets.balanced(),
            'aggressive': FilterPresets.aggressive(),
        }
        filter_config = preset_map[args.filter_preset]
        filter_config.target_count = args.filter_target

    from aitrader.app.use_cases.ashare_signals import AShareSignalPipeline

    pipeline = AShareSignalPipeline(
        mode=mode,
        force_backtest=args.force_backtest,
        max_workers=args.workers,
        enable_smart_filter=enable_filter,
        filter_config=filter_config,
    )
    pipeline.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
