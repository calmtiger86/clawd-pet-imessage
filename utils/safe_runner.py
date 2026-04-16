# utils/safe_runner.py
# -----------------------------------------------------------------
# 에러 처리 래퍼 — 에러가 나도 서비스가 멈추지 않는다.
# -----------------------------------------------------------------

from typing import TypeVar, Callable, Optional
from utils.logger import logger

T = TypeVar('T')


def safe_run(
    func: Callable[..., T],
    *args,
    fallback: Optional[T] = None,
    error_msg: str = "",
    **kwargs
) -> Optional[T]:
    try:
        return func(*args, **kwargs)
    except Exception as e:
        func_name = getattr(func, '__name__', str(func))
        logger.error(f"{func_name} 실패: {e}")
        return fallback
