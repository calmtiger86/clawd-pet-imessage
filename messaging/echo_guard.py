# messaging/echo_guard.py
# -----------------------------------------------------------------
# 에코 방지 시스템 (iWanted router.py 패턴 포팅)
#
# 자기 번호로 보내면 chat.db에 송수신이 모두 기록되어
# 봇이 자신의 메시지를 다시 처리하는 무한 루프가 발생한다.
#
# 3중 방어:
# 1. 발송 메시지 해시 캐시 (60초 TTL)
# 2. 시스템 메시지 패턴 매칭
# 3. is_from_me=0 SQL 필터 (chat_db.py에서 처리)
# -----------------------------------------------------------------

import hashlib
import threading
from datetime import datetime, timedelta
from typing import List, Dict
from utils.logger import logger

# 캐시 TTL
CACHE_TTL_SECONDS = 60

# 발송 메시지 해시 캐시
_cache: List[Dict] = []
_lock = threading.Lock()

# 시스템 메시지 패턴 (봇이 보내는 메시지의 시작 부분)
SYSTEM_PREFIXES = [
    # 상태 알림
    '🦀', '🤔', '⚡', '🔨', '💻', '🤹', '🎪', '🔄',
    '🧹', '🗑️', '🎉', '✅', '🥳', '💥', '🔥', '⚠️',
    '😴', '🌙', '💤',
    # 명령어 응답
    '🦀 iMessage Pet 명령어',
    '🦀 펫 상태:', '📊 오늘 발송:',
    '🍕', '😋', '🔇', '🔔',
    # Permission
    '⚠️ 도구 승인 요청',
    '✅ 허용됨', '❌ 거부됨', '⏰ 타임아웃',
]


def record_sent(text: str) -> None:
    """발송한 메시지를 캐시에 기록한다."""
    with _lock:
        _cleanup()
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        _cache.append({
            'hash': text_hash,
            'time': datetime.now(),
        })


def is_echo(text: str) -> bool:
    """
    이 메시지가 봇이 보낸 에코인지 판단한다.

    Returns:
        True면 에코 → 무시해야 함
    """
    # 1. 해시 캐시 확인
    with _lock:
        _cleanup()
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        for item in _cache:
            if item['hash'] == text_hash:
                logger.debug(f"에코 감지 (해시 캐시): {text[:30]}...")
                return True

    # 2. 시스템 메시지 패턴 확인
    for prefix in SYSTEM_PREFIXES:
        if text.startswith(prefix):
            logger.debug(f"에코 감지 (시스템 패턴): {text[:30]}...")
            return True

    return False


def _cleanup() -> None:
    """TTL 초과 캐시 제거."""
    global _cache
    cutoff = datetime.now() - timedelta(seconds=CACHE_TTL_SECONDS)
    _cache = [item for item in _cache if item['time'] > cutoff]
