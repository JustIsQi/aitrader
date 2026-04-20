# 策略中文名: A股最优策略对比 runner
"""
一键回测 + 横向对比 4 个候选策略 + 原版换手率因子 + 沪深 300 基准。

输出 markdown 表格形式的对比矩阵, 落到:
  papers/arxiv/processed/2603.14288v2/08_comparison_results.md

用法:
  /home/yy/anaconda3/bin/python papers/arxiv/processed/2603.14288v2/07_compare_runner.py

可选环境变量:
  AITRADER_FAST=1     仅跑 2023-2024 (快速冒烟)
  AITRADER_ONLY=microcap,reversal     仅跑指定策略
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# 把 06_optimal_strategies 中的策略和原版策略都加载进来
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from importlib import import_module

from aitrader.domain.backtest.engine import Engine
from aitrader.domain.strategy.agentic_turnover import agentic_turnover_strategy_weekly

opt = import_module('06_optimal_strategies')


# ── 注册要对比的策略 ─────────────────────────────────────────────────────────
ALL_STRATEGIES = {
    '原版换手率(失败基线)':  agentic_turnover_strategy_weekly,
    '微盘股周频':            opt.microcap_weekly,
    '微盘股月频':            opt.microcap_monthly,
    '20日反转':              opt.reversal_weekly,
    '修复版换手率':          opt.turnover_fixed_weekly,
    'PB低估值月频':          opt.pb_value_monthly,
}


def _maybe_filter(name: str) -> bool:
    only = os.getenv('AITRADER_ONLY', '').strip()
    if not only:
        return True
    keys = [k.strip() for k in only.split(',') if k.strip()]
    # 简单匹配: 名字包含任一关键字即跑
    return any(k in name or k in name.replace(' ', '') for k in keys)


def _patch_dates(task) -> None:
    """快速模式下把回测窗口压到 2023-2024, 2 年看看相对排名."""
    if os.getenv('AITRADER_FAST') == '1':
        task.start_date = '20230101'
        task.end_date = '20241231'


def _extract_metrics(stats_dict: dict) -> dict:
    """从 ffn calc_stats 输出里抽几个核心指标."""
    if not stats_dict:
        return {}
    s = stats_dict.get('策略', stats_dict)
    if isinstance(s, dict):
        return {
            'Total Return':   s.get('total_return'),
            'CAGR':           s.get('cagr'),
            'Sharpe':         s.get('daily_sharpe'),
            'Sortino':        s.get('daily_sortino'),
            'Max Drawdown':   s.get('max_drawdown'),
            'Calmar':         s.get('calmar'),
            'Vol (ann)':      s.get('daily_vol'),
            'Best Year':      s.get('best_year'),
            'Worst Year':     s.get('worst_year'),
            'Win Year %':     s.get('win_year_perc'),
        }
    return {}


def run_one(name: str, factory) -> dict:
    """跑单个策略, 返回核心指标字典. 失败时返回 error."""
    print(f'\n\n{"#" * 70}')
    print(f'# 跑策略: {name}')
    print(f'{"#" * 70}\n')

    t0 = time.time()
    try:
        task = factory()
        _patch_dates(task)
        result = Engine().run(task)
        elapsed = time.time() - t0

        metrics = _extract_metrics(result.statistics)
        metrics['Strategy'] = name
        metrics['Elapsed (s)'] = round(elapsed, 1)
        return metrics
    except Exception as e:
        traceback.print_exc()
        return {
            'Strategy': name,
            'Error': str(e)[:200],
            'Elapsed (s)': round(time.time() - t0, 1),
        }


def format_pct(x):
    if x is None:
        return 'NA'
    try:
        return f'{x * 100:+.2f}%'
    except Exception:
        return str(x)


def format_num(x, n=2):
    if x is None:
        return 'NA'
    try:
        return f'{x:.{n}f}'
    except Exception:
        return str(x)


def write_markdown(rows: list[dict], output_path: Path) -> None:
    cols = [
        'Strategy', 'Total Return', 'CAGR', 'Sharpe', 'Sortino',
        'Max Drawdown', 'Calmar', 'Vol (ann)', 'Best Year', 'Worst Year',
        'Win Year %', 'Elapsed (s)',
    ]

    lines = []
    lines.append('# A 股最优策略对比结果\n')
    lines.append(f'> 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
    fast = '✅ 是 (2023-2024)' if os.getenv('AITRADER_FAST') == '1' else '❌ 否 (2019-2024 全段)'
    lines.append(f'> 快速模式: {fast}\n')
    lines.append('')
    lines.append('| ' + ' | '.join(cols) + ' |')
    lines.append('|' + '|'.join(['---'] * len(cols)) + '|')

    for r in rows:
        if 'Error' in r:
            lines.append(f"| {r['Strategy']} | ❌ 失败: {r['Error']} | | | | | | | | | | {r['Elapsed (s)']} |")
            continue
        cells = []
        for c in cols:
            v = r.get(c)
            if c in ('Total Return', 'CAGR', 'Max Drawdown', 'Vol (ann)',
                     'Best Year', 'Worst Year', 'Win Year %'):
                cells.append(format_pct(v))
            elif c in ('Sharpe', 'Sortino', 'Calmar'):
                cells.append(format_num(v))
            else:
                cells.append(str(v) if v is not None else 'NA')
        lines.append('| ' + ' | '.join(cells) + ' |')

    lines.append('')
    lines.append('## 解读')
    lines.append('')
    lines.append('- **Sharpe 排序**最重要 (越高越好). A 股可接受的 Sharpe 至少 > 0.8.')
    lines.append('- **Max Drawdown** 看尾部风险, A 股策略一般 > -30% 就要警惕.')
    lines.append('- **Calmar** = CAGR / |MaxDD|, > 1.0 代表好策略.')
    lines.append('- **Win Year %** = 正收益年占比, 应 > 60%.')

    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n\n✓ 对比结果已写入: {output_path}')


def _run_one_worker(strategy_name: str) -> dict:
    """ProcessPoolExecutor worker — fork 继承 ALL_STRATEGIES, 只传名字."""
    factory = ALL_STRATEGIES[strategy_name]
    return run_one(strategy_name, factory)


def main() -> None:
    strategies_to_run = [n for n in ALL_STRATEGIES if _maybe_filter(n)]
    skipped = [n for n in ALL_STRATEGIES if not _maybe_filter(n)]
    for name in skipped:
        print(f'  [跳过] {name}')

    if not strategies_to_run:
        print('没有要跑的策略')
        return

    max_workers = min(len(strategies_to_run), os.cpu_count() or 4, 6)
    print(f'\n🚀 并行回测: {len(strategies_to_run)} 个策略, {max_workers} 个 worker\n')

    t_wall = time.time()
    rows: list[dict] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_run_one_worker, name): name
            for name in strategies_to_run
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                result = future.result(timeout=7200)
                rows.append(result)
                elapsed_s = result.get('Elapsed (s)', '?')
                if 'Error' in result:
                    print(f'  ✗ [{name}] 失败 ({elapsed_s}s): {result["Error"][:80]}')
                else:
                    print(f'  ✓ [{name}] 完成 ({elapsed_s}s)')
            except Exception as e:
                rows.append({
                    'Strategy': name,
                    'Error': str(e)[:200],
                    'Elapsed (s)': -1,
                })
                print(f'  ✗ [{name}] 进程异常: {e}')

    wall_elapsed = time.time() - t_wall
    serial_sum = sum(r.get('Elapsed (s)', 0) for r in rows if r.get('Elapsed (s)', 0) > 0)

    name_order = {n: i for i, n in enumerate(ALL_STRATEGIES)}
    rows.sort(key=lambda r: name_order.get(r.get('Strategy', ''), 999))

    output = HERE / '08_comparison_results.md'
    write_markdown(rows, output)

    print('\n\n' + '=' * 90)
    print('A 股最优策略对比 (终端摘要)')
    print('=' * 90)
    fmt = '{:<24} {:>12} {:>10} {:>8} {:>14}'
    print(fmt.format('Strategy', 'TotalReturn', 'CAGR', 'Sharpe', 'MaxDrawdown'))
    print('-' * 90)
    for r in rows:
        if 'Error' in r:
            print(fmt.format(r['Strategy'][:24], '❌ FAIL', '-', '-', r['Error'][:14]))
            continue
        print(fmt.format(
            r['Strategy'][:24],
            format_pct(r.get('Total Return')),
            format_pct(r.get('CAGR')),
            format_num(r.get('Sharpe')),
            format_pct(r.get('Max Drawdown')),
        ))
    print('=' * 90)
    print(f'\n⏱  总墙钟耗时: {wall_elapsed:.1f}s | 各策略耗时之和: {serial_sum:.1f}s | 并行加速比: {serial_sum/wall_elapsed:.1f}x')


if __name__ == '__main__':
    main()
