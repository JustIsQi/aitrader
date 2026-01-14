"""
系统监控模块

实时监控系统资源使用情况，提供告警和性能数据。
适用于8GB RAM系统的持续监控。

使用场景:
- 后台监控线程
- 性能分析
- 问题诊断

作者: AITrader
日期: 2026-01-13
"""

import psutil
import time
import threading
from loguru import logger
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SystemMetrics:
    """系统指标数据类"""
    timestamp: datetime
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_available_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    load_average_1m: float
    load_average_5m: float
    load_average_15m: float


class SystemMonitor:
    """
    系统监控器

    功能:
    - 实时监控CPU、内存、磁盘使用率
    - 负载均衡监控
    - 告警阈值检查
    - 后台监控线程
    """

    # 告警阈值
    WARNING_CPU_PERCENT = 90
    CRITICAL_CPU_PERCENT = 95
    WARNING_MEMORY_PERCENT = 85
    CRITICAL_MEMORY_PERCENT = 95
    WARNING_DISK_PERCENT = 90
    CRITICAL_DISK_PERCENT = 95

    def __init__(self):
        """初始化监控器"""
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.callbacks = []  # 告警回调函数列表

    def get_current_metrics(self) -> SystemMetrics:
        """
        获取当前系统指标

        Returns:
            SystemMetrics: 系统指标对象
        """
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)

        # 内存信息
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024**3)
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        memory_percent = memory.percent

        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_total_gb = disk.total / (1024**3)
        disk_used_gb = disk.used / (1024**3)
        disk_percent = disk.percent

        # 负载平均值 (Linux/Unix)
        try:
            load1, load5, load15 = psutil.getloadavg()
        except (AttributeError, OSError):
            # Windows或其他系统不支持getloadavg
            load1 = load5 = load15 = 0.0

        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_total_gb=memory_total_gb,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            memory_percent=memory_percent,
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_percent=disk_percent,
            load_average_1m=load1,
            load_average_5m=load5,
            load_average_15m=load15
        )

    def log_metrics(self, metrics: Optional[SystemMetrics] = None):
        """
        记录系统指标到日志

        Args:
            metrics: 系统指标对象，None则获取当前指标
        """
        if metrics is None:
            metrics = self.get_current_metrics()

        logger.info(
            f"系统状态: "
            f"CPU={metrics.cpu_percent}%, "
            f"RAM={metrics.memory_percent:.1f}% "
            f"({metrics.memory_available_gb:.2f}GB可用), "
            f"Disk={metrics.disk_percent:.1f}%, "
            f"Load={metrics.load_average_1m:.2f}"
        )

        # 检查告警条件
        self._check_alerts(metrics)

    def _check_alerts(self, metrics: SystemMetrics):
        """
        检查告警条件并触发告警

        Args:
            metrics: 系统指标
        """
        alerts = []

        # CPU告警
        if metrics.cpu_percent > self.CRITICAL_CPU_PERCENT:
            alerts.append(f"严重: CPU使用率 {metrics.cpu_percent}%")
        elif metrics.cpu_percent > self.WARNING_CPU_PERCENT:
            alerts.append(f"警告: CPU使用率 {metrics.cpu_percent}%")

        # 内存告警
        if metrics.memory_percent > self.CRITICAL_MEMORY_PERCENT:
            alerts.append(f"严重: 内存使用率 {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent > self.WARNING_MEMORY_PERCENT:
            alerts.append(f"警告: 内存使用率 {metrics.memory_percent:.1f}%")

        # 磁盘告警
        if metrics.disk_percent > self.CRITICAL_DISK_PERCENT:
            alerts.append(f"严重: 磁盘使用率 {metrics.disk_percent:.1f}%")
        elif metrics.disk_percent > self.WARNING_DISK_PERCENT:
            alerts.append(f"警告: 磁盘使用率 {metrics.disk_percent:.1f}%")

        # 触发告警
        for alert in alerts:
            logger.warning(f"⚠️ {alert}")
            # 调用回调函数
            for callback in self.callbacks:
                try:
                    callback(alert, metrics)
                except Exception as e:
                    logger.error(f"告警回调失败: {e}")

    def add_alert_callback(self, callback: Callable[[str, SystemMetrics], None]):
        """
        添加告警回调函数

        Args:
            callback: 回调函数，签名为 (alert_message: str, metrics: SystemMetrics) -> None
        """
        self.callbacks.append(callback)

    def start_background_monitoring(self, interval_seconds: int = 300):
        """
        启动后台监控线程

        Args:
            interval_seconds: 监控间隔(秒)，默认5分钟
        """
        if self.monitoring:
            logger.warning("监控已在运行")
            return

        self.monitoring = True

        def monitor_loop():
            logger.info(f"启动后台监控，间隔 {interval_seconds} 秒")
            while self.monitoring:
                try:
                    metrics = self.get_current_metrics()
                    self.log_metrics(metrics)
                except Exception as e:
                    logger.error(f"监控失败: {e}")

                time.sleep(interval_seconds)

            logger.info("后台监控已停止")

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_background_monitoring(self):
        """停止后台监控"""
        if not self.monitoring:
            return

        logger.info("停止后台监控...")
        self.monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.monitor_thread = None

    def check_postgres_connections(self) -> Optional[dict]:
        """
        检查PostgreSQL连接状态

        Returns:
            Optional[dict]: 连接状态，失败返回None
        """
        try:
            from database.pg_manager import get_db
            from sqlalchemy import text

            db = get_db()

            with db.get_session() as session:
                # 活跃连接数
                result = session.execute(text(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                ))
                active = result.scalar()

                # 总连接数
                result = session.execute(text(
                    "SELECT count(*) FROM pg_stat_activity"
                ))
                total = result.scalar()

                # 最大连接数
                result = session.execute(text(
                    "SELECT setting::int FROM pg_settings WHERE name = 'max_connections'"
                ))
                max_conn = result.scalar()

                status = {
                    'active_connections': active,
                    'total_connections': total,
                    'max_connections': max_conn,
                    'usage_percent': (total / max_conn) * 100
                }

                logger.debug(
                    f"PostgreSQL: {active}/{total} 活跃, "
                    f"{total}/{max_conn} 总计 ({status['usage_percent']:.1f}%)"
                )

                # 告警
                if status['usage_percent'] > 90:
                    logger.warning(
                        f"⚠️ PostgreSQL连接数过高: {total}/{max_conn} "
                        f"({status['usage_percent']:.1f}%)"
                    )

                return status

        except Exception as e:
            logger.error(f"检查PostgreSQL连接失败: {e}")
            return None


# 全局单例
_monitor_instance = None

def get_monitor() -> SystemMonitor:
    """获取监控器单例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = SystemMonitor()
    return _monitor_instance


# 便捷函数
def log_system_status():
    """记录系统状态到日志"""
    monitor = get_monitor()
    monitor.log_metrics()


def check_postgres():
    """检查PostgreSQL连接状态"""
    monitor = get_monitor()
    return monitor.check_postgres_connections()


def start_monitoring(interval_seconds: int = 300):
    """启动后台监控"""
    monitor = get_monitor()
    monitor.start_background_monitoring(interval_seconds)


def stop_monitoring():
    """停止后台监控"""
    monitor = get_monitor()
    monitor.stop_background_monitoring()


# 使用示例
if __name__ == '__main__':
    # 获取当前指标
    monitor = SystemMonitor()
    metrics = monitor.get_current_metrics()

    print(f"CPU: {metrics.cpu_percent}%")
    print(f"内存: {metrics.memory_percent:.1f}% ({metrics.memory_available_gb:.2f}GB可用)")
    print(f"磁盘: {metrics.disk_percent:.1f}%")
    print(f"负载: {metrics.load_average_1m:.2f} (1min)")

    # 检查PostgreSQL
    pg_status = monitor.check_postgres_connections()
    if pg_status:
        print(f"PostgreSQL: {pg_status['total_connections']}/{pg_status['max_connections']} 连接")
