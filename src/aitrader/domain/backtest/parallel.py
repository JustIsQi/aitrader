"""
并行回测框架 (动态按CPU/内存扩展)

使用多进程并行执行回测任务，充分利用多核CPU资源。
每个回测在独立进程中运行，避免GIL限制，实现真正的并行计算。

使用场景:
- 批量运行多个策略回测
- 参数扫描/优化
- 大规模策略评估

作者: AITrader
日期: 2026-01-13
"""

import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, List, Dict, Any, Optional

import pandas as pd

from aitrader.infrastructure.config.logging import logger
import time
import sys
from pathlib import Path


def _fork_context():
    try:
        return multiprocessing.get_context('fork')
    except ValueError:
        return None


def _job_display_name(strategy_job: Any) -> str:
    if isinstance(strategy_job, tuple) and len(strategy_job) == 2:
        display_name, payload = strategy_job
        if display_name:
            return str(display_name)
        return _job_display_name(payload)

    if callable(strategy_job):
        return getattr(strategy_job, '__name__', 'unknown')

    return getattr(strategy_job, 'name', 'unknown')


def _resolve_strategy_job(strategy_job: Any):
    if isinstance(strategy_job, tuple) and len(strategy_job) == 2:
        display_name, payload = strategy_job
        if callable(payload) and not hasattr(payload, 'symbols'):
            task = payload()
            return (display_name or getattr(payload, '__name__', 'unknown')), task
        return (display_name or getattr(payload, 'name', 'unknown')), payload

    if callable(strategy_job):
        task = strategy_job()
        return getattr(strategy_job, '__name__', getattr(task, 'name', 'unknown')), task

    return getattr(strategy_job, 'name', 'unknown'), strategy_job


def run_backtest_process(strategy_job: Any) -> Dict[str, Any]:
    """
    在独立进程中运行单个回测

    Args:
        strategy_func: 策略函数，返回Task对象

    Returns:
        Dict: 回测结果字典
    """
    try:
        # 每个进程需要独立导入模块和创建数据库连接
        from aitrader.domain.backtest.engine import Engine
        from aitrader.infrastructure.db.models.base import backtest_engine  # 使用回测专用连接池

        strategy_name, task = _resolve_strategy_job(strategy_job)
        engine = Engine()
        result = engine.run(task)

        return {
            'strategy_name': strategy_name,
            'success': True,
            'result': result,
            'task': task,
        }
    except Exception as e:
        logger.error(f"回测进程执行失败: {e}")
        import traceback
        return {
            'strategy_name': _job_display_name(strategy_job),
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


class ParallelBacktestRunner:
    """
    并行回测运行器

    使用ProcessPoolExecutor实现真正的多进程并行回测，
    适用于CPU密集型回测任务。

    内存管理:
    - 根据可用内存和CPU数自动调整worker数
    - 默认按单个回测约2GB内存估算
    - 可通过max_workers手动覆盖
    """

    def __init__(self, max_workers: Optional[int] = None, enable_memory_check: bool = True):
        """
        初始化并行回测运行器

        Args:
            max_workers: 最大worker数，None则自动计算
            enable_memory_check: 是否启用内存检查 (需要psutil)
        """
        self.enable_memory_check = enable_memory_check

        if max_workers is None:
            # 自动计算最优worker数
            self.max_workers = self._calculate_optimal_workers()
        else:
            # 用户指定时，进行安全限制
            cpu_count = multiprocessing.cpu_count()
            if enable_memory_check:
                max_safe_workers = self._get_max_safe_workers()
                self.max_workers = min(max_workers, max_safe_workers, cpu_count)
            else:
                self.max_workers = min(max_workers, cpu_count)

        logger.info(f"并行回测运行器初始化: max_workers={self.max_workers}")

    def _calculate_optimal_workers(self) -> int:
        """
        计算8GB系统的最优worker数

        Returns:
            int: 推荐的worker数量
        """
        cpu_count = multiprocessing.cpu_count()

        if self.enable_memory_check:
            try:
                import psutil
                available_gb = psutil.virtual_memory().available / (1024**3)

                # 根据可用内存动态调整worker数。每个回测通常会吃掉约 2GB RAM。
                if available_gb < 3.0:
                    optimal = 1
                    logger.warning(f"⚠️ Low memory: {available_gb:.2f}GB, using 1 worker")
                elif available_gb < 6.0:
                    optimal = min(cpu_count, 2)
                    logger.info(f"Memory available: {available_gb:.2f}GB, using {optimal} workers")
                else:
                    memory_limited = max(1, int(available_gb // 2.0))
                    optimal = min(cpu_count, memory_limited)
                    logger.info(f"Sufficient memory: {available_gb:.2f}GB, using {optimal} workers")

                return optimal
            except ImportError:
                logger.debug("psutil not available, using default worker count")
                return min(cpu_count, 2)
        else:
            # 不检查内存时，保守使用2个worker
            return min(cpu_count, 2)

    def _get_max_safe_workers(self) -> int:
        """
        获取8GB系统的最大安全worker数

        Returns:
            int: 最大安全worker数
        """
        try:
            import psutil
            available_gb = psutil.virtual_memory().available / (1024**3)
            cpu_count = multiprocessing.cpu_count()
            memory_limited = max(1, int(available_gb // 2.0))
            return min(cpu_count, memory_limited)
        except ImportError:
            return 2

    def run_strategies_parallel(
        self,
        strategy_jobs: List[Any],
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        并行运行多个策略回测

        Args:
            strategy_jobs: 策略任务/函数/ (显示名, 任务) 列表
            timeout: 单个回测的超时时间(秒)，None表示无限制

        Returns:
            List[Dict]: 回测结果列表
        """
        if not strategy_jobs:
            logger.warning("没有提供策略任务")
            return []

        logger.info(f"开始并行回测: {len(strategy_jobs)} 个策略, {self.max_workers} 个worker")
        start_time = time.time()

        results = []
        completed = 0
        failed = 0

        resolved_jobs = []
        preload_requests = {}
        benchmark_requests = {}

        for job in strategy_jobs:
            try:
                strategy_name, task = _resolve_strategy_job(job)
            except Exception as exc:
                logger.warning(f"策略任务解析失败，跳过预热: {_job_display_name(job)} ({exc})")
                resolved_jobs.append(job)
                continue

            resolved_jobs.append((strategy_name, task))

            symbols = sorted({symbol for symbol in getattr(task, 'symbols', []) if symbol})
            if not symbols:
                continue

            start_date = _normalize_cache_bound(getattr(task, 'start_date', '20100101'))
            end_date = _normalize_cache_bound(getattr(task, 'end_date', start_date))
            preload_requests[(tuple(symbols), start_date, end_date)] = symbols

            benchmark = getattr(task, 'benchmark', None)
            if benchmark:
                benchmark_requests[(benchmark, start_date, end_date)] = benchmark

        if preload_requests or benchmark_requests:
            from aitrader.domain.backtest import engine as engine_module
            from aitrader.infrastructure.market_data.loaders import DbDataLoader

            loader = DbDataLoader(auto_download=False, adjust_type='qfq')

            for (_, start_date, end_date), symbols in preload_requests.items():
                try:
                    loader.read_dfs(symbols=symbols, start_date=start_date, end_date=end_date, copy_result=False)
                except Exception as exc:
                    logger.warning(f"预热行情缓存失败 ({start_date} ~ {end_date}, {len(symbols)} 只): {exc}")

            for (benchmark, start_date, end_date), _ in benchmark_requests.items():
                try:
                    bench_dfs = loader.read_dfs(
                        symbols=[benchmark],
                        start_date=start_date,
                        end_date=end_date,
                        copy_result=False,
                    )
                    bench_df = bench_dfs.get(benchmark)
                    if bench_df is None or bench_df.empty:
                        continue

                    bench_data = bench_df.copy()
                    if 'date' in bench_data.columns:
                        bench_data['date'] = pd.to_datetime(bench_data['date'])
                        bench_data.set_index('date', inplace=True)
                    bench_data.sort_index(inplace=True)
                    benchmark_curve = bench_data.pivot_table(values='close', index=bench_data.index, columns='symbol')
                    benchmark_curve.columns = ['benchmark']
                    engine_module._BENCHMARK_CACHE[(benchmark, start_date, end_date)] = benchmark_curve
                except Exception as exc:
                    logger.warning(f"预热基准缓存失败 ({benchmark} {start_date} ~ {end_date}): {exc}")

        # 设置默认超时 (30分钟)
        if timeout is None:
            timeout = 1800

        try:
            executor_kwargs = {'max_workers': self.max_workers}
            mp_context = _fork_context()
            if mp_context is not None:
                executor_kwargs['mp_context'] = mp_context

            with ProcessPoolExecutor(**executor_kwargs) as executor:
                future_to_strategy = {
                    executor.submit(run_backtest_process, job): job
                    for job in resolved_jobs
                }

                for future in as_completed(future_to_strategy, timeout=timeout * len(resolved_jobs)):
                    strategy_job = future_to_strategy[future]
                    strategy_name = _job_display_name(strategy_job)

                    try:
                        result = future.result(timeout=timeout)
                        results.append(result)

                        if result.get('success'):
                            completed += 1
                            logger.success(f"✓ [{strategy_name}] 回测完成 ({completed}/{len(resolved_jobs)})")
                        else:
                            failed += 1
                            logger.error(f"✗ [{strategy_name}] 回测失败: {result.get('error', 'Unknown error')}")

                    except Exception as e:
                        failed += 1
                        logger.error(f"✗ [{strategy_name}] 回测异常: {e}")
                        results.append({
                            'strategy_name': strategy_name,
                            'success': False,
                            'error': str(e)
                        })

        except Exception as e:
            logger.error(f"并行回测执行失败: {e}")
            raise

        elapsed = time.time() - start_time

        logger.info(
            f"并行回测完成: {completed} 成功, {failed} 失败, "
            f"耗时 {elapsed:.2f}秒, 平均 {elapsed/len(resolved_jobs):.2f}秒/策略"
        )

        return results

    def run_strategy_with_params(
        self,
        strategy_func: Callable,
        param_grid: Dict[str, List[Any]],
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        使用不同参数组合运行同一策略 (参数扫描)

        Args:
            strategy_func: 基础策略函数
            param_grid: 参数网格 {param_name: [values]}
            timeout: 单个回测的超时时间(秒)

        Returns:
            List[Dict]: 所有参数组合的回测结果
        """
        from itertools import product

        # 生成所有参数组合
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(product(*param_values))

        logger.info(f"参数扫描: {len(param_combinations)} 组参数组合")

        # 为每个参数组合创建策略函数
        strategy_funcs = []
        for combination in param_combinations:
            # 创建带参数的策略函数
            def make_strategy(params):
                def wrapper():
                    task = strategy_func()
                    # 应用参数到task
                    for key, value in params.items():
                        if hasattr(task, key):
                            setattr(task, key, value)
                    return task
                wrapper.__name__ = f"{strategy_func.__name__}_{params}"
                return wrapper

            params = dict(zip(param_names, combination))
            strategy_funcs.append(make_strategy(params))

        # 并行运行所有组合
        return self.run_strategies_parallel(strategy_funcs, timeout=timeout)


# 使用示例
if __name__ == '__main__':
    # 示例策略函数
    def example_strategy():
        from aitrader.domain.backtest.engine import Task
        return Task(
            name='示例策略',
            symbols=['000001.SZ'],
            start_date='20230101',
            end_date='20231231'
        )

    # 并行运行
    runner = ParallelBacktestRunner(max_workers=2)
    results = runner.run_strategies_parallel([example_strategy] * 3)

    print(f"完成: {len(results)} 个回测")
    for r in results:
        print(f"  {r['strategy_name']}: {'成功' if r['success'] else '失败'}")
