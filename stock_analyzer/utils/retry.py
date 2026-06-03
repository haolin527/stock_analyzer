"""重试装饰器 - 指数退避"""

import time
from functools import wraps

from stock_analyzer.utils.logger import get_logger

logger = get_logger("utils.retry")


def retry(max_attempts: int = 3, base_delay: float = 2.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    """带指数退避的重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        delay = base_delay * (backoff ** attempt)
                        logger.warning(
                            "%s 第%d次尝试失败: %s，%0.1f秒后重试...",
                            func.__name__, attempt + 1, str(e)[:80], delay
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s 所有%d次尝试均失败: %s",
                            func.__name__, max_attempts, str(e)[:200]
                        )
            raise last_exc  # type: ignore
        return wrapper
    return decorator
