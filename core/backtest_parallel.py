"""
并行回测框架 (针对8GB RAM优化)

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
from loguru import logger
import time
import sys
from pathlib import Path


def run_backtest_process(strategy_func: Callable) -> Dict[str, Any]:
    """
    在独立进程中运行单个回测

    Args:
        strategy_func: 策略函数，返回Task对象

    Returns:
        Dict: 回测结果字典
    """
    try:
        # 每个进程需要独立导入模块和创建数据库连接
        from core.backtrader_engine import Engine
        from database.models.base import backtest_engine  # 使用回测专用连接池

        task = strategy_func()
        engine = Engine()
        result = engine.run(task)

        return {
            'strategy_name': task.name,
            'success': True,
            'result': result,
            'task': task
        }
    except Exception as e:
        logger.error(f"回测进程执行失败: {e}")
        import traceback
        return {
            'strategy_name': getattr(strategy_func, '__name__', 'unknown'),
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


class ParallelBacktestRunner:
    """
    并行回测运行器

    使用ProcessPoolExecutor实现真正的多进程并行回测，
    适用于CPU密集型回测任务。

    内存管理 (8GB系统):
    - 默认使用2个worker (每个回测约1.5-2GB)
    - 最大支持3个worker (需要至少6GB可用内存)
    - 自动检测可用内存并调整worker数
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
        cpu_count = multiprocessing.cpu_count()  # 4核

        if self.enable_memory_check:
            try:
                import psutil
                available_gb = psutil.virtual_memory().available / (1024**3)

                # 根据可用内存动态调整worker数
                if available_gb < 3.0:
                    # 内存不足，只使用1个worker
                    optimal = 1
                    logger.warning(f"⚠️ Low memory: {available_gb:.2f}GB, using 1 worker")
                elif available_gb < 5.0:
                    # 内存紧张，使用2个worker
                    optimal = 2
                    logger.info(f"Memory available: {available_gb:.2f}GB, using 2 workers")
                else:
                    # 内存充足，使用CPU核心数 (最多4个)
                    optimal = min(cpu_count, 4)
                    logger.info(f"Sufficient memory: {available_gb:.2f}GB, using {optimal} workers")

                return optimal
            except ImportError:
                logger.debug("psutil not available, using default worker count")
                return 2  # 8GB默认安全值
        else:
            # 不检查内存时，保守使用2个worker
            return 2

    def _get_max_safe_workers(self) -> int:
        """
        获取8GB系统的最大安全worker数

        Returns:
            int: 最大安全worker数
        """
        try:
            import psutil
            available_gb = psutil.virtual_memory().available / (1024**3)
            total_gb = psutil.virtual_memory().total / (1024**3)

            # 8GB系统最大支持3个worker
            if total_gb < 10:
                return 3
            else:
                # 更大内存的系统可以使用更多worker
                return int(total_gb / 3)  # 每3GB分配1个worker
        except ImportError:
            return 3  # 8GB默认最大值

    def run_strategies_parallel(
        self,
        strategy_funcs: List[Callable],
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        并行运行多个策略回测

        Args:
            strategy_funcs: 策略函数列表
            timeout: 单个回测的超时时间(秒)，None表示无限制

        Returns:
            List[Dict]: 回测结果列表
        """
        if not strategy_funcs:
            logger.warning("没有提供策略函数")
            return []

        logger.info(f"开始并行回测: {len(strategy_funcs)} 个策略, {self.max_workers} 个worker")
        start_time = time.time()

        results = []
        completed = 0
        failed = 0

        # 设置默认超时 (30分钟)
        if timeout is None:
            timeout = 1800

        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_strategy = {
                    executor.submit(run_backtest_process, func): func
                    for func in strategy_funcs
                }

                # 收集结果
                for future in as_completed(future_to_strategy, timeout=timeout * len(strategy_funcs)):
                    strategy_func = future_to_strategy[future]
                    strategy_name = getattr(strategy_func, '__name__', 'unknown')

                    try:
                        result = future.result(timeout=timeout)
                        results.append(result)

                        if result.get('success'):
                            completed += 1
                            logger.success(f"✓ [{strategy_name}] 回测完成 ({completed}/{len(strategy_funcs)})")
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
            f"耗时 {elapsed:.2f}秒, 平均 {elapsed/len(strategy_funcs):.2f}秒/策略"
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
        from core.backtrader_engine import Task
        return Task(
            name='示例策略',
            symbols=['510300.SH'],
            start_date='20230101',
            end_date='20231231'
        )

    # 并行运行
    runner = ParallelBacktestRunner(max_workers=2)
    results = runner.run_strategies_parallel([example_strategy] * 3)

    print(f"完成: {len(results)} 个回测")
    for r in results:
        print(f"  {r['strategy_name']}: {'成功' if r['success'] else '失败'}")
