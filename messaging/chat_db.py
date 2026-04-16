# messaging/chat_db.py
# -----------------------------------------------------------------
# chat.db 폴링 + 명령어 파싱
# iWanted senders/imessage.py:20-78 패턴 재사용
# -----------------------------------------------------------------

import sqlite3
import re
from typing import List, Tuple, Optional
from utils.logger import logger
from utils.retry import retry_with_backoff

CHAT_DB_PATH = ''  # config에서 설정


def init(db_path: str) -> None:
    global CHAT_DB_PATH
    CHAT_DB_PATH = db_path


def _normalize_phone(phone: str) -> Optional[str]:
    """전화번호를 +국가코드 형식으로 정규화."""
    clean = re.sub(r'[^\d+]', '', phone)
    if clean.startswith('+'):
        return clean
    if clean.startswith('010'):
        return '+82' + clean[1:]
    return clean if clean else None


def get_new_messages(last_rowid: int, include_from_me: bool = False) -> List[Tuple[int, str, str]]:
    """last_rowid 이후의 새 메시지를 반환한다."""
    try:
        conn = sqlite3.connect(
            f"file:{CHAT_DB_PATH}?mode=ro",
            uri=True,
            timeout=5
        )
        cursor = conn.cursor()

        # same 모드: is_from_me 필터 제거 (자기에게 보낸 답장도 읽어야 함)
        from_me_filter = "" if include_from_me else "AND m.is_from_me = 0"

        cursor.execute(f"""
            SELECT m.rowid, COALESCE(h.id, 'self'), m.text
            FROM message m
            LEFT JOIN handle h ON m.handle_id = h.rowid
            WHERE m.rowid > ?
              {from_me_filter}
              AND m.text IS NOT NULL
              AND m.text != ''
            ORDER BY m.rowid ASC
            LIMIT 50
        """, (last_rowid,))

        messages = cursor.fetchall()
        conn.close()

        result = []
        for rowid, phone, text in messages:
            normalized = _normalize_phone(phone)
            if normalized:
                result.append((rowid, normalized, text.strip()))
        return result

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            logger.warning("chat.db 잠김, 재시도 예정")
            raise
        logger.error(f"chat.db 읽기 실패: {e}")
        return []
    except Exception as e:
        logger.error(f"chat.db 읽기 실패: {e}")
        return []


def get_new_messages_safe(last_rowid: int, include_from_me: bool = False) -> List[Tuple[int, str, str]]:
    """재시도 로직이 포함된 안전한 메시지 조회."""
    try:
        return retry_with_backoff(
            get_new_messages,
            last_rowid,
            include_from_me,
            max_retries=3,
            base_delay=0.5,
            exceptions=(sqlite3.OperationalError,)
        )
    except Exception:
        return []


def get_latest_rowid() -> int:
    """현재 chat.db의 최신 rowid를 반환한다."""
    try:
        conn = sqlite3.connect(
            f"file:{CHAT_DB_PATH}?mode=ro",
            uri=True,
            timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(rowid) FROM message")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0
    except Exception as e:
        logger.error(f"최신 rowid 조회 실패: {e}")
        return 0


def parse_command(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    텍스트에서 명령어를 파싱한다.

    Returns:
        (command, args) 또는 (None, None)
    """
    text = text.strip()
    if not text.startswith('/'):
        return None, None

    parts = text.split(maxsplit=1)
    command = parts[0].lower().lstrip('/')
    args = parts[1] if len(parts) > 1 else None

    valid_commands = {'pet', 'status', 'feed', 'sleep', 'wake', 'help'}
    if command in valid_commands:
        return command, args

    return None, None
