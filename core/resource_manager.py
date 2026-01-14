"""
资源管理器 (针对8GB RAM系统)

集中管理和监控系统资源，确保在有限内存下安全运行各种工作负载。
自动调整并发数和资源分配，避免OOM错误。

使用场景:
- 回测前检查是否有足够资源
- 动态调整worker数量
- 系统资源监控和告警

作者: AITrader
日期: 2026-01-13
"""

import psutil
from loguru import logger
from enum import Enum
from typing import Tuple, Optional


class WorkloadType(Enum):
    """工作负载类型"""
    API = "api"                    # Web API请求
    BACKTEST = "backtest"          # 回测计算
    SIGNAL_GEN = "signal_gen"      # 信号生成
    DATA_LOAD = "data_load"        # 数据加载


class ResourceManager:
    """
    8GB系统资源管理器

    系统配置:
    - 总内存: 8GB
    - 保留最小空闲: 1.5GB (系统+其他进程)
    - 可用内存: 6.5GB

    工作负载资源分配:
    - API: 1GB max, 2 workers
    - Signal Generation: 2GB max, 2 workers
    - Backtest: 4GB max, 2 workers
    - Data Load: 3GB max, 1 worker
    """

    # 系统配置
    TOTAL_RAM_GB = 8
    MIN_FREE_RAM_GB = 1.5  # 系统保留内存

    # 工作负载资源配置
    WORKLOAD_ALLOCATION = {
        WorkloadType.API: {
            "max_memory_gb": 1.0,      # API最大1GB
            "max_workers": 2,           # 2个worker
            "priority": 1               # 最高优先级
        },
        WorkloadType.SIGNAL_GEN: {
            "max_memory_gb": 2.0,      # 信号生成最大2GB
            "max_workers": 2,           # 2个worker
            "priority": 2
        },
        WorkloadType.BACKTEST: {
            "max_memory_gb": 4.0,      # 回测最大4GB (2个并发)
            "max_workers": 2,           # 2个worker (每个2GB)
            "priority": 3
        },
        WorkloadType.DATA_LOAD: {
            "max_memory_gb": 3.0,      # 数据加载最大3GB
            "max_workers": 1,           # 1个worker (I/O密集)
            "priority": 4
        },
    }

    # 告警阈值
    WARNING_MEMORY_PERCENT = 85  # 内存使用超过85%告警
    CRITICAL_MEMORY_PERCENT = 95  # 内存使用超过95%严重告警

    @classmethod
    def get_system_status(cls) -> dict:
        """
        获取当前系统状态

        Returns:
            dict: 系统资源状态
        """
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            'memory_total_gb': memory.total / (1024**3),
            'memory_used_gb': memory.used / (1024**3),
            'memory_available_gb': memory.available / (1024**3),
            'memory_percent': memory.percent,
            'cpu_percent': cpu_percent,
            'status': 'ok' if memory.percent < cls.WARNING_MEMORY_PERCENT else 'warning'
        }

    @classmethod
    def can_start_workload(cls, workload_type: WorkloadType) -> Tuple[bool, str]:
        """
        检查是否有足够资源启动工作负载

        Args:
            workload_type: 工作负载类型

        Returns:
            Tuple[bool, str]: (是否可以启动, 原因说明)
        """
        available_gb = psutil.virtual_memory().available / (1024**3)
        config = cls.WORKLOAD_ALLOCATION[workload_type]
        required_gb = config["max_memory_gb"]

        # 检查是否有足够内存
        needed_gb = cls.MIN_FREE_RAM_GB + required_gb
        if available_gb < needed_gb:
            return False, (
                f"内存不足: {available_gb:.2f}GB可用, "
                f"需要 {needed_gb:.2f}GB "
                f"(保留{cls.MIN_FREE_RAM_GB}GB + 任务{required_gb}GB)"
            )

        # 检查内存使用率
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > cls.CRITICAL_MEMORY_PERCENT:
            return False, (
                f"系统内存使用率过高: {memory_percent:.1f}% "
                f"(阈值: {cls.CRITICAL_MEMORY_PERCENT}%)"
            )

        return True, "OK"

    @classmethod
    def get_optimal_workers(cls, workload_type: WorkloadType) -> int:
        """
        根据可用内存获取最优worker数量

        Args:
            workload_type: 工作负载类型

        Returns:
            int: 推荐的worker数量
        """
        available_gb = psutil.virtual_memory().available / (1024**3)
        config = cls.WORKLOAD_ALLOCATION[workload_type]
        max_workers = config["max_workers"]

        # 动态调整worker数量
        if available_gb < 3.0:
            # 内存紧张，使用1个worker
            optimal = 1
            logger.debug(f"低内存 ({available_gb:.2f}GB), 使用1个worker")
        elif available_gb < 5.0:
            # 中等内存，使用max_workers-1
            optimal = max(1, max_workers - 1)
            logger.debug(f"中等内存 ({available_gb:.2f}GB), 使用{optimal}个worker")
        else:
            # 内存充足，使用配置的max_workers
            optimal = max_workers
            logger.debug(f"内存充足 ({available_gb:.2f}GB), 使用{optimal}个worker")

        return optimal

    @classmethod
    def log_system_status(cls):
        """记录当前系统状态到日志"""
        status = cls.get_system_status()

        logger.info(
            f"系统状态: "
            f"CPU={status['cpu_percent']}%, "
            f"RAM={status['memory_percent']:.1f}% "
            f"({status['memory_available_gb']:.2f}GB可用/{status['memory_total_gb']:.2f}GB), "
            f"状态={status['status']}"
        )

        # 内存告警
        if status['memory_percent'] > cls.CRITICAL_MEMORY_PERCENT:
            logger.error(
                f"⚠️ 严重告警: 内存使用率 {status['memory_percent']:.1f}% "
                f"> {cls.CRITICAL_MEMORY_PERCENT}%"
            )
        elif status['memory_percent'] > cls.WARNING_MEMORY_PERCENT:
            logger.warning(
                f"⚠️ 内存使用率 {status['memory_percent']:.1f}% "
                f"> {cls.WARNING_MEMORY_PERCENT}%"
            )

        return status

    @classmethod
    def check_postgres_connections(cls) -> Optional[dict]:
        """
        检查PostgreSQL连接数

        Returns:
            Optional[dict]: 连接状态，失败返回None
        """
        try:
            from database.pg_manager import get_db
            db = get_db()

            with db.get_session() as session:
                from sqlalchemy import text

                # 获取活跃连接数
                result = session.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                active = result.scalar()

                # 获取最大连接数
                result = session.execute(text(
                    "SELECT setting::int FROM pg_settings WHERE name = 'max_connections'"
                ))
                max_conn = result.scalar()

                status = {
                    'active_connections': active,
                    'max_connections': max_conn,
                    'usage_percent': (active / max_conn) * 100
                }

                logger.debug(f"PostgreSQL连接: {active}/{max_conn} ({status['usage_percent']:.1f}%)")

                # 连接数告警
                if status['usage_percent'] > 90:
                    logger.warning(
                        f"⚠️ PostgreSQL连接数过高: {active}/{max_conn} "
                        f"({status['usage_percent']:.1f}%)"
                    )

                return status

        except Exception as e:
            logger.error(f"检查PostgreSQL连接失败: {e}")
            return None

    @classmethod
    def get_safe_batch_size(cls, current_batch_size: int, workload_type: WorkloadType) -> int:
        """
        根据当前内存使用情况获取安全的批次大小

        Args:
            current_batch_size: 当前计划使用的批次大小
            workload_type: 工作负载类型

        Returns:
            int: 调整后的安全批次大小
        """
        available_gb = psutil.virtual_memory().available / (1024**3)

        # 内存严重不足时，降低批次大小
        if available_gb < 2.0:
            reduced_size = max(10, current_batch_size // 2)
            logger.warning(
                f"低内存 ({available_gb:.2f}GB), 批次大小从 {current_batch_size} "
                f"降至 {reduced_size}"
            )
            return reduced_size

        # 内存紧张时，适度降低
        elif available_gb < 3.0:
            reduced_size = max(50, int(current_batch_size * 0.7))
            logger.info(
                f"中等内存 ({available_gb:.2f}GB), 批次大小从 {current_batch_size} "
                f"降至 {reduced_size}"
            )
            return reduced_size

        # 内存充足，保持原批次大小
        return current_batch_size


# 便捷函数
def check_resources(workload_type: WorkloadType) -> bool:
    """
    快速检查是否有足够资源运行指定工作负载

    Args:
        workload_type: 工作负载类型

    Returns:
        bool: 是否有足够资源
    """
    can_run, reason = ResourceManager.can_start_workload(workload_type)
    if not can_run:
        logger.error(f"资源不足: {reason}")
    return can_run


def get_optimal_workers(workload_type: WorkloadType) -> int:
    """
    获取指定工作负载的最优worker数

    Args:
        workload_type: 工作负载类型

    Returns:
        int: 最优worker数量
    """
    return ResourceManager.get_optimal_workers(workload_type)


def log_system_status():
    """记录系统状态到日志"""
    return ResourceManager.log_system_status()


# 使用示例
if __name__ == '__main__':
    # 检查系统状态
    ResourceManager.log_system_status()
    ResourceManager.check_postgres_connections()

    # 检查是否可以运行回测
    can_run, reason = ResourceManager.can_start_workload(WorkloadType.BACKTEST)
    print(f"可以运行回测: {can_run}, 原因: {reason}")

    # 获取最优worker数
    workers = ResourceManager.get_optimal_workers(WorkloadType.BACKTEST)
    print(f"推荐worker数: {workers}")
