# messaging/rate_limiter.py
# -----------------------------------------------------------------
# iMessage 발송 제한 — 일일 ~100건 + 조용한 시간대
# -----------------------------------------------------------------

import time
from datetime import datetime
from collections import deque
from typing import Deque
from utils.logger import logger


class RateLimiter:
    """일일 메시지 발송 제한."""

    def __init__(self, daily_limit: int = 100, quiet_start: int = 0, quiet_end: int = 8):
        self._daily_limit = daily_limit
        self._quiet_start = quiet_start
        self._quiet_end = quiet_end
        self._timestamps: Deque[float] = deque()
        self._muted = False

    @property
    def muted(self) -> bool:
        return self._muted

    def mute(self) -> None:
        self._muted = True
        logger.info("알림 음소거됨")

    def unmute(self) -> None:
        self._muted = False
        logger.info("알림 재개됨")

    def can_send(self) -> bool:
        """메시지 발송 가능 여부를 확인한다."""
        if self._muted:
            return False

        now = datetime.now()
        hour = now.hour

        # 조용한 시간대 (자정~8시)
        if self._quiet_start <= hour < self._quiet_end:
            logger.debug(f"조용한 시간대 ({self._quiet_start}:00-{self._quiet_end}:00)")
            return False

        # 24시간 이전 기록 제거
        cutoff = time.time() - 86400
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        # 일일 한도 확인
        if len(self._timestamps) >= self._daily_limit:
            logger.warning(f"일일 발송 한도 도달 ({self._daily_limit}건)")
            return False

        return True

    def record_send(self) -> None:
        """발송 기록을 추가한다."""
        self._timestamps.append(time.time())

    @property
    def remaining_today(self) -> int:
        cutoff = time.time() - 86400
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return max(0, self._daily_limit - len(self._timestamps))

    @property
    def sent_today(self) -> int:
        cutoff = time.time() - 86400
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        return len(self._timestamps)
