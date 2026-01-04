"""
失败重试装饰器
用于增强网络请求的容错能力，支持指数退避策略
"""
import time
from functools import wraps
from typing import Callable, Any
from loguru import logger


def retry_on_failure(max_retries: int = 5, delay: float = 1.0):
    """
    失败重试装饰器

    Args:
        max_retries: 最大重试次数（默认 5 次）
        delay: 基础重试延迟（秒），实际延迟会使用指数退避策略递增

    Returns:
        装饰后的函数

    示例:
        @retry_on_failure(max_retries=3, delay=1.0)
        def fetch_data():
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries - 1:
                        # 指数退避：每次重试延迟时间递增
                        current_delay = delay * (attempt + 1)
                        logger.warning(
                            f'{func.__name__} 失败，第 {attempt + 1} 次重试... '
                            f'错误: {e}，将在 {current_delay:.1f} 秒后重试'
                        )
                        time.sleep(current_delay)
                    else:
                        # 最后一次尝试失败
                        logger.error(
                            f'{func.__name__} 失败，已重试 {max_retries} 次，放弃'
                        )

            # 所有重试都失败，抛出最后一次的异常
            raise last_exception

        return wrapper
    return decorator
