# utils/retry.py
# -----------------------------------------------------------------
# 지수 백오프 재시도
# -----------------------------------------------------------------

import time
from typing import TypeVar, Callable, Tuple, Type
from utils.logger import logger

T = TypeVar('T')


def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> T:
    last_exception = None
    func_name = getattr(func, '__name__', str(func))

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(f"{func_name} 최종 실패 ({attempt + 1}/{max_retries}): {e}")
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"{func_name} 실패 ({attempt + 1}/{max_retries}), {delay:.1f}초 후 재시도: {e}")
            time.sleep(delay)

    raise last_exception
