"""
短线A股选股信号生成 CLI 入口

用法:
    python -m aitrader.app.cli.short_term_signals [DATE] [--fetch-only]
                                                  [--signals-only] [--force-refresh]
                                                  [-v]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from aitrader.infrastructure.config.logging import setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='短线A股选股信号生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m aitrader.app.cli.short_term_signals                   # 今天日期，自动模式
  python -m aitrader.app.cli.short_term_signals 20260415          # 指定日期
  python -m aitrader.app.cli.short_term_signals --fetch-only      # 仅获取板块数据
  python -m aitrader.app.cli.short_term_signals --signals-only    # 仅生成信号
  python -m aitrader.app.cli.short_term_signals --force-refresh   # 强制刷新板块数据
        """,
    )
    parser.add_argument('date', nargs='?', help='日期 (YYYYMMDD), 默认为今天')
    parser.add_argument('--fetch-only', action='store_true',
                        help='仅获取板块数据，不生成信号')
    parser.add_argument('--signals-only', action='store_true',
                        help='仅生成信号，跳过板块数据获取')
    parser.add_argument('--force-refresh', action='store_true',
                        help='强制刷新板块数据（即使数据已存在）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出（DEBUG 级别）')
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging('short_term_pipeline.log')
    args = build_parser().parse_args(argv)

    # 日期校验
    if args.date:
        try:
            datetime.strptime(args.date, '%Y%m%d')
            date = args.date
        except ValueError:
            print("日期格式错误，请使用 YYYYMMDD 格式，如: 20260415", file=sys.stderr)
            return 1
    else:
        date = datetime.now().strftime('%Y%m%d')

    if args.fetch_only:
        fetch_mode = 'fetch-only'
    elif args.signals_only:
        fetch_mode = 'signals-only'
    else:
        fetch_mode = 'auto'

    from aitrader.app.use_cases.short_term_signals import generate_daily_signals

    try:
        generate_daily_signals(date=date, fetch_mode=fetch_mode, force_refresh=args.force_refresh)
        print("\n✓✓✓ 全部完成!")
        return 0
    except Exception as e:
        print(f"\n✗✗✗ 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
