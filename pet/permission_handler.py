# pet/permission_handler.py
# -----------------------------------------------------------------
# Permission Request — iMessage를 통한 도구 사용 승인/거부
#
# 흐름:
# 1. Claude Code PreToolUse → HTTP POST /permission
# 2. iMessage로 승인 요청 발송
# 3. chat.db 폴링으로 사용자 답장 대기
# 4. 답장 또는 타임아웃 → allow/deny 반환
# -----------------------------------------------------------------

import time
import sqlite3
from typing import Optional
from utils.logger import logger

# 위험 도구 패턴 (이 도구들만 permission 요청)
DANGEROUS_TOOLS = {
    'Bash',
    'Write',
    'Edit',
}

# 항상 허용하는 안전 도구
SAFE_TOOLS = {
    'Read',
    'Glob',
    'Grep',
    'TodoWrite',
    'WebSearch',
    'WebFetch',
}


def is_permission_required(tool_name: str, tool_input: dict) -> bool:
    """이 도구가 permission 요청이 필요한지 판단한다."""
    if tool_name in SAFE_TOOLS:
        return False

    if tool_name in DANGEROUS_TOOLS:
        # Bash: 위험 명령어 필터링
        if tool_name == 'Bash':
            cmd = tool_input.get('command', '')
            dangerous_patterns = [
                'rm ', 'rm\t', 'rmdir',
                'git push', 'git reset', 'git checkout .',
                'drop ', 'delete ', 'truncate ',
                'kill ', 'pkill',
                'chmod', 'chown',
                'sudo',
                '> /dev/', 'dd if=',
            ]
            return any(p in cmd.lower() for p in dangerous_patterns)

        # Write/Edit: 항상 허용 (코드 작성은 자유롭게)
        return False

    # 알 수 없는 도구 → 설정에 따라
    return True


def format_permission_message(tool_name: str, tool_input: dict) -> str:
    """승인 요청 iMessage 텍스트를 생성한다."""
    if tool_name == 'Bash':
        cmd = tool_input.get('command', '(empty)')
        # 긴 명령어는 잘라서 표시
        if len(cmd) > 200:
            cmd = cmd[:200] + '...'
        return (
            f"⚠️ 도구 승인 요청\n\n"
            f"🔧 Bash 명령어:\n"
            f"$ {cmd}\n\n"
            f"✅ 허용: y 또는 yes\n"
            f"❌ 거부: n 또는 no"
        )

    # 기타 도구
    desc = str(tool_input)[:200]
    return (
        f"⚠️ 도구 승인 요청\n\n"
        f"🔧 {tool_name}\n"
        f"📋 {desc}\n\n"
        f"✅ 허용: y 또는 yes\n"
        f"❌ 거부: n 또는 no"
    )


def wait_for_reply(
    phone: str,
    chat_db_path: str,
    timeout: int,
    poll_interval: float = 1.5
) -> Optional[bool]:
    """
    chat.db에서 사용자 답장을 대기한다.

    Args:
        phone: 수신자 전화번호
        chat_db_path: chat.db 경로
        timeout: 대기 시간 (초). 0이면 무제한.
        poll_interval: 폴링 간격 (초)

    Returns:
        True (허용), False (거부), None (타임아웃)
    """
    # 현재 최신 rowid 기록 (이후 메시지만 검사)
    start_rowid = _get_latest_rowid(chat_db_path)
    start_time = time.time()

    logger.info(f"Permission 답장 대기 중 (timeout={timeout}s, from rowid={start_rowid})")

    while True:
        elapsed = time.time() - start_time

        # 타임아웃 체크 (0이면 무제한)
        if timeout > 0 and elapsed >= timeout:
            logger.info(f"Permission 타임아웃 ({timeout}s)")
            return None

        # chat.db 폴링
        reply = _check_for_reply(chat_db_path, phone, start_rowid)
        if reply is not None:
            return reply

        time.sleep(poll_interval)


def _get_latest_rowid(db_path: str) -> int:
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(rowid) FROM message")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0
    except Exception:
        return 0


def _check_for_reply(db_path: str, phone: str, after_rowid: int) -> Optional[bool]:
    """after_rowid 이후의 메시지에서 y/n 답장을 찾는다."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.text
            FROM message m
            JOIN handle h ON m.handle_id = h.rowid
            WHERE m.rowid > ?
              AND m.is_from_me = 0
              AND m.text IS NOT NULL
            ORDER BY m.rowid ASC
            LIMIT 10
        """, (after_rowid,))

        rows = cursor.fetchall()
        conn.close()

        for (text,) in rows:
            text = text.strip().lower()
            if text in ('y', 'yes', 'ㅇ', 'ㅇㅇ', '허용', 'allow', 'ok', '확인'):
                logger.info(f"Permission 허용: '{text}'")
                return True
            if text in ('n', 'no', 'ㄴ', 'ㄴㄴ', '거부', 'deny', '취소'):
                logger.info(f"Permission 거부: '{text}'")
                return False

        return None

    except Exception as e:
        logger.warning(f"Permission 폴링 실패: {e}")
        return None
