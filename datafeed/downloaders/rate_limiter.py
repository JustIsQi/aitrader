"""
令牌桶限流器
确保每秒不超过指定请求数，用于控制 API 请求频率
"""
import time
import threading
from loguru import logger


class RateLimiter:
    """令牌桶限流器 - 确保每秒不超过指定请求数"""

    def __init__(self, max_requests_per_second: int = 10):
        """
        初始化限流器

        Args:
            max_requests_per_second: 每秒最大请求数（默认 10 次/秒）
        """
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_time = 0.0
        self.lock = threading.Lock()

        logger.debug(f'限流器初始化: 最大 {max_requests_per_second} 次/秒')

    def acquire(self):
        """
        获取请求许可，自动限流

        如果距离上次请求时间不足 min_interval，则会休眠等待
        """
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_time

            if time_since_last < self.min_interval:
                # 需要等待
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
                # 更新最后请求时间为醒来后的时间
                self.last_time = self.last_time + self.min_interval
            else:
                # 无需等待，直接更新时间
                self.last_time = current_time
