"""
A股策略回测 Use Case

支持批量运行多个策略，生成对比报告。
"""

from __future__ import annotations

import traceback
from typing import Callable, Dict, List, Optional

from aitrader.domain.backtest.engine import Engine
from aitrader.domain.backtest.parallel import ParallelBacktestRunner


def run_single_strategy(strategy_func: Callable, strategy_name: str, plot: bool = False):
    """
    运行单个策略

    Args:
        strategy_func: 返回 Task 对象的策略工厂函数
        strategy_name: 策略名称（用于显示）
        plot: 是否显示图表

    Returns:
        BacktestResult 对象，失败返回 None
    """
    print(f"\n{'='*60}")
    print(f"运行策略: {strategy_name}")
    print(f"{'='*60}")

    try:
        task = strategy_func()
        _print_task_summary(task)

        print(f"\n开始回测...")
        engine = Engine()
        result = engine.run(task)

        print("\n" + "=" * 60)
        print("回测结果")
        print("=" * 60)
        result.stats()

        if plot:
            try:
                result.plot()
            except Exception as e:
                print(f"绘图失败: {e}")

        return result

    except Exception as e:
        print(f"\n策略 {strategy_name} 运行失败: {e}")
        traceback.print_exc()
        return None


def _print_task_summary(task):
    print(f"\n策略配置:")
    print(f"  名称: {task.name}")
    print(f"  股票池: {len(task.symbols)} 只")
    print(f"  买入条件: {len(task.select_buy)} 个")
    print(f"  卖出条件: {len(task.select_sell)} 个")
    print(f"  调仓周期: {task.period}")
    print(f"  持仓数量: {task.order_by_topK}")
    print(f"  A股模式: {'是' if task.ashare_mode else '否'}")


def _print_summary(strategies: List, results: Dict, successful: int, failed: int):
    print("\n\n" + "=" * 60)
    print("策略对比报告")
    print("=" * 60)
    print(f"\n{'策略名称':<20} {'状态':<10}")
    print("-" * 30)
    for name, _ in strategies:
        status = "✅ 成功" if name in results else "❌ 失败"
        print(f"{name:<20} {status}")
    print("\n" + "=" * 60)
    print(f"总策略数: {len(strategies)}  成功: {successful}  失败: {failed}  "
          f"成功率: {successful/len(strategies)*100:.1f}%")


def _run_strategy_batch(strategies, plot: bool, parallel: bool):
    use_parallel = parallel and not plot and len(strategies) > 1

    if use_parallel:
        print("\n" + "#" * 60)
        print("# 批量运行所有A股策略 (并行)")
        print("#" * 60)

        jobs = []
        for name, func in strategies:
            task = func()
            print("\n" + "=" * 60)
            print(f"准备策略: {name}")
            print("=" * 60)
            _print_task_summary(task)
            jobs.append((name, task))

        runner = ParallelBacktestRunner()
        parallel_results = runner.run_strategies_parallel(jobs)
        result_map = {item['strategy_name']: item for item in parallel_results if item.get('success')}

        results: Dict = {}
        success_count = 0
        for name, _ in strategies:
            item = result_map.get(name)
            if item is not None:
                results[name] = item['result']
                success_count += 1

        _print_summary(strategies, results, success_count, len(strategies) - success_count)
        return results

    results: Dict = {}
    success_count = 0
    for name, func in strategies:
        result = run_single_strategy(func, name, plot)
        if result is not None:
            results[name] = result
            success_count += 1

    _print_summary(strategies, results, success_count, len(strategies) - success_count)
    return results


def run_all_strategies(plot: bool = False, parallel: bool = True) -> Dict:
    """批量运行所有策略"""
    from aitrader.domain.strategy.multi_factor import (
        multi_factor_strategy_weekly,
        multi_factor_strategy_monthly,
        multi_factor_strategy_conservative,
    )
    from aitrader.domain.strategy.momentum import (
        momentum_strategy_weekly,
        momentum_strategy_monthly,
        momentum_strategy_aggressive,
    )

    strategies = [
        ('多因子-周频', multi_factor_strategy_weekly),
        ('多因子-月频', multi_factor_strategy_monthly),
        ('多因子-保守版', multi_factor_strategy_conservative),
        ('动量-周频', momentum_strategy_weekly),
        ('动量-月频', momentum_strategy_monthly),
        ('动量-激进版', momentum_strategy_aggressive),
    ]

    return _run_strategy_batch(strategies, plot=plot, parallel=parallel)


def run_multi_factor_strategies(plot: bool = False, parallel: bool = True) -> Dict:
    """运行所有多因子策略"""
    from aitrader.domain.strategy.multi_factor import (
        multi_factor_strategy_weekly,
        multi_factor_strategy_monthly,
        multi_factor_strategy_conservative,
    )

    strategies = [
        ('多因子-周频', multi_factor_strategy_weekly),
        ('多因子-月频', multi_factor_strategy_monthly),
        ('多因子-保守版', multi_factor_strategy_conservative),
    ]
    return _run_strategy_batch(strategies, plot=plot, parallel=parallel)


def run_momentum_strategies(plot: bool = False, parallel: bool = True) -> Dict:
    """运行所有动量策略"""
    from aitrader.domain.strategy.momentum import (
        momentum_strategy_weekly,
        momentum_strategy_monthly,
        momentum_strategy_aggressive,
    )

    strategies = [
        ('动量-周频', momentum_strategy_weekly),
        ('动量-月频', momentum_strategy_monthly),
        ('动量-激进版', momentum_strategy_aggressive),
    ]
    return _run_strategy_batch(strategies, plot=plot, parallel=parallel)
