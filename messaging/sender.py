# messaging/sender.py
# -----------------------------------------------------------------
# iMessage 발송 (텍스트 + GIF 첨부)
# iWanted senders/imessage.py:97-177 패턴 확장
# -----------------------------------------------------------------

import subprocess
import os
import re
from typing import Optional
from utils.logger import logger
from messaging.echo_guard import record_sent

# 전화번호 검증 패턴
_PHONE_PATTERN = re.compile(r'^\+\d{10,15}$')


def _validate_phone(phone: str) -> bool:
    return bool(_PHONE_PATTERN.match(phone))


def _escape_for_applescript(text: str) -> str:
    return text.replace('\\', '\\\\').replace('"', '\\"')


def _mask_phone(phone: str) -> str:
    if len(phone) > 7:
        return phone[:4] + '****' + phone[-3:]
    return '***'


def _ensure_messages_running() -> None:
    """Messages.app이 실행 중인지 확인하고 실행한다."""
    try:
        subprocess.run(
            ['open', '-a', 'Messages'],
            capture_output=True,
            timeout=5
        )
    except Exception as e:
        logger.warning(f"Messages 앱 실행 실패: {e}")


def send_gif(phone: str, gif_path: str, text: Optional[str] = None, dry_run: bool = False) -> bool:
    """
    GIF 이미지 + 선택적 텍스트를 iMessage로 발송한다.

    Args:
        phone: 수신자 전화번호 (+821012345678 형태)
        gif_path: GIF 파일 절대 경로
        text: 함께 보낼 텍스트 (Optional)
        dry_run: True면 실제 발송 없이 로그만

    Returns:
        발송 성공 여부
    """
    if not _validate_phone(phone):
        logger.error(f"유효하지 않은 전화번호: {_mask_phone(phone)}")
        return False

    if not os.path.isfile(gif_path):
        logger.error(f"GIF 파일 없음: {gif_path}")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] GIF 발송: {_mask_phone(phone)} ← {os.path.basename(gif_path)}")
        if text:
            logger.info(f"[DRY RUN] 텍스트: {text}")
        return True

    _ensure_messages_running()

    safe_phone = _escape_for_applescript(phone)
    abs_gif_path = os.path.abspath(gif_path)

    # GIF 파일 발송
    gif_script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_phone}" of targetService
        send POSIX file "{abs_gif_path}" to targetBuddy
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', gif_script],
            capture_output=True,
            timeout=15
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"GIF 발송 실패 ({_mask_phone(phone)}): {error_msg}")
            return False

        logger.info(f"GIF 발송 성공: {_mask_phone(phone)} ← {os.path.basename(gif_path)}")

    except subprocess.TimeoutExpired:
        logger.error(f"GIF 발송 타임아웃 ({_mask_phone(phone)})")
        return False
    except Exception as e:
        logger.error(f"GIF 발송 실패 ({_mask_phone(phone)}): {e}")
        return False

    # 텍스트 발송 (GIF 성공 후)
    if text:
        return send_text(phone, text)

    # GIF만 보낸 경우 파일명을 에코 캐시에 기록
    record_sent(os.path.basename(gif_path))
    return True


def send_text(phone: str, text: str, dry_run: bool = False) -> bool:
    """텍스트만 iMessage로 발송한다."""
    if not _validate_phone(phone):
        logger.error(f"유효하지 않은 전화번호: {_mask_phone(phone)}")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] 텍스트 발송: {_mask_phone(phone)} ← {text[:50]}")
        return True

    _ensure_messages_running()

    safe_phone = _escape_for_applescript(phone)
    safe_text = _escape_for_applescript(text)

    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{safe_phone}" of targetService
        send "{safe_text}" to targetBuddy
    end tell
    '''

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            logger.info(f"텍스트 발송 성공: {_mask_phone(phone)} ({len(text)}자)")
            record_sent(text)
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"텍스트 발송 실패 ({_mask_phone(phone)}): {error_msg}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"텍스트 발송 타임아웃 ({_mask_phone(phone)})")
        return False
    except Exception as e:
        logger.error(f"텍스트 발송 실패 ({_mask_phone(phone)}): {e}")
        return False
