#!/usr/bin/env python3
# main.py
# -----------------------------------------------------------------
# iMessage Pet Bot 진입점
#
# 두 개의 스레드:
# 1. Hook HTTP 서버 (Claude Code 상태 수신)
# 2. 메시지 폴링 루프 (사용자 명령어 처리)
#
# 상태 변경 → GIF + 텍스트 iMessage 발송
# -----------------------------------------------------------------

import os
import sys
import time
import signal
import threading

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    RECIPIENT_PHONE, SERVER_HOST, SERVER_PORT, ASSETS_DIR,
    POLLING_INTERVAL, DAILY_MESSAGE_LIMIT, QUIET_HOURS_START,
    QUIET_HOURS_END, DRY_RUN, CHAT_DB_PATH,
    PERMISSION_ENABLED, PERMISSION_TIMEOUT, PERMISSION_DEFAULT,
    PERMISSION_POLL_INTERVAL, MESSAGING_MODE,
)
from utils.logger import logger
from utils.safe_runner import safe_run
from pet.state_machine import PetStateMachine
from pet.hook_server import create_server, _HookHandler
from pet.personality import get_state_message, get_command_response
from pet.permission_handler import (
    is_permission_required, format_permission_message, wait_for_reply,
)
from messaging.sender import send_gif, send_text
from messaging.rate_limiter import RateLimiter
from messaging import chat_db

# --- 전역 상태 ---
_shutdown = threading.Event()
_rate_limiter = RateLimiter(
    daily_limit=DAILY_MESSAGE_LIMIT,
    quiet_start=QUIET_HOURS_START,
    quiet_end=QUIET_HOURS_END,
)


def _handle_permission(data: dict) -> dict:
    """
    Permission 요청을 처리한다 (블로킹).

    Claude Code HTTP hook → 이 함수 → iMessage 발송 → 답장 대기 → 결정 반환
    """
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})

    # 안전한 도구는 즉시 허용
    if not is_permission_required(tool_name, tool_input):
        return _HookHandler._permission_response('allow')

    if not RECIPIENT_PHONE:
        return _HookHandler._permission_response(PERMISSION_DEFAULT)

    # iMessage로 승인 요청 발송
    message = format_permission_message(tool_name, tool_input)
    timeout_info = f" ({PERMISSION_TIMEOUT}초 내 답장)" if PERMISSION_TIMEOUT > 0 else ""
    default_info = f"\n⏰ 미응답 시: {'자동 허용' if PERMISSION_DEFAULT == 'allow' else '자동 거부'}{timeout_info}"
    full_message = message + default_info

    send_text(RECIPIENT_PHONE, full_message, dry_run=DRY_RUN)

    if DRY_RUN:
        logger.info(f"[DRY RUN] Permission → {PERMISSION_DEFAULT}")
        return _HookHandler._permission_response(PERMISSION_DEFAULT)

    # chat.db 폴링으로 답장 대기
    reply = wait_for_reply(
        phone=RECIPIENT_PHONE,
        chat_db_path=CHAT_DB_PATH,
        timeout=PERMISSION_TIMEOUT,
        poll_interval=PERMISSION_POLL_INTERVAL,
    )

    if reply is True:
        decision = 'allow'
        send_text(RECIPIENT_PHONE, "✅ 허용됨", dry_run=DRY_RUN)
    elif reply is False:
        decision = 'deny'
        send_text(RECIPIENT_PHONE, "❌ 거부됨", dry_run=DRY_RUN)
    else:
        # 타임아웃 → 설정된 기본값
        decision = PERMISSION_DEFAULT
        emoji = "✅" if decision == "allow" else "❌"
        send_text(RECIPIENT_PHONE, f"⏰ 타임아웃 → {emoji} 자동 {decision}", dry_run=DRY_RUN)

    logger.info(f"Permission 결정: {tool_name} → {decision}")
    return _HookHandler._permission_response(decision)


def _on_state_change(new_state: str, prev_state: str) -> None:
    """상태 변경 시 iMessage GIF + 텍스트를 발송한다."""
    if not RECIPIENT_PHONE:
        logger.warning("RECIPIENT_PHONE이 설정되지 않음, 메시지 미발송")
        return

    if not _rate_limiter.can_send():
        logger.info(f"Rate limit 또는 음소거: {new_state} 메시지 생략")
        return

    gif_path = os.path.join(ASSETS_DIR, f'{new_state}.gif')
    text = get_state_message(new_state)

    if not os.path.isfile(gif_path):
        logger.warning(f"GIF 없음: {gif_path}, 텍스트만 발송")
        success = send_text(RECIPIENT_PHONE, text, dry_run=DRY_RUN)
    else:
        success = send_gif(RECIPIENT_PHONE, gif_path, text=text, dry_run=DRY_RUN)

    if success:
        _rate_limiter.record_send()


def _handle_command(command: str, args: str, state_machine: PetStateMachine) -> None:
    """사용자 명령어를 처리하고 응답한다."""
    if not RECIPIENT_PHONE:
        return

    if command == 'help':
        response = get_command_response('help')
    elif command == 'pet':
        state = state_machine.state
        gif_path = os.path.join(ASSETS_DIR, f'{state}.gif')
        response = get_command_response('pet_status', state=state)
        if os.path.isfile(gif_path):
            send_gif(RECIPIENT_PHONE, gif_path, text=response, dry_run=DRY_RUN)
            _rate_limiter.record_send()
            return
    elif command == 'status':
        state = state_machine.state
        remaining = _rate_limiter.remaining_today
        sent = _rate_limiter.sent_today
        response = (
            f"🦀 펫 상태: {state}\n"
            f"📊 오늘 발송: {sent}건 (잔여: {remaining}건)\n"
            f"🔇 음소거: {'ON' if _rate_limiter.muted else 'OFF'}"
        )
    elif command == 'feed':
        response = get_command_response('feed')
        state_machine.force_state('happy')
        gif_path = os.path.join(ASSETS_DIR, 'happy.gif')
        if os.path.isfile(gif_path):
            send_gif(RECIPIENT_PHONE, gif_path, text=response, dry_run=DRY_RUN)
            _rate_limiter.record_send()
            return
    elif command == 'sleep':
        _rate_limiter.mute()
        response = "🔇 알림 음소거됨. /wake로 재개해"
    elif command == 'wake':
        _rate_limiter.unmute()
        response = "🔔 알림 재개! 다시 소식 전해줄게~"
    else:
        response = get_command_response('unknown')

    send_text(RECIPIENT_PHONE, response, dry_run=DRY_RUN)
    _rate_limiter.record_send()


def _polling_loop(state_machine: PetStateMachine) -> None:
    """chat.db를 폴링하여 사용자 명령어를 처리한다."""
    from messaging.echo_guard import is_echo

    same_number_mode = (MESSAGING_MODE == 'same')
    chat_db.init(CHAT_DB_PATH)
    last_rowid = chat_db.get_latest_rowid()
    logger.info(f"메시지 폴링 시작 (last_rowid={last_rowid}, mode={MESSAGING_MODE})")

    while not _shutdown.is_set():
        # same 모드: is_from_me도 포함해서 읽어야 함 (자기에게 보낸 답장)
        if same_number_mode:
            messages = safe_run(
                chat_db.get_new_messages_safe,
                last_rowid,
                fallback=[],
                include_from_me=True,
            )
        else:
            messages = safe_run(
                chat_db.get_new_messages_safe,
                last_rowid,
                fallback=[]
            )

        for rowid, phone, text in (messages or []):
            last_rowid = rowid

            # 발신자 필터: same/separate 모드 공통 — RECIPIENT_PHONE만 처리
            # (iWanted 등 다른 서비스의 메시지와 분리)
            if RECIPIENT_PHONE and phone != RECIPIENT_PHONE:
                continue

            # same 모드: 에코 필터링 (봇이 보낸 메시지 제외)
            if same_number_mode and is_echo(text):
                continue

            command, args = chat_db.parse_command(text)
            if command:
                logger.info(f"명령어 수신: /{command} (from {phone[:7]}...)")
                safe_run(
                    _handle_command,
                    command, args, state_machine,
                    error_msg="명령어 처리 실패"
                )

        _shutdown.wait(timeout=POLLING_INTERVAL)


def _signal_handler(signum, frame):
    logger.info(f"종료 신호 수신 (signal {signum})")
    _shutdown.set()


def main():
    # 설정 검증
    if not RECIPIENT_PHONE:
        logger.warning("⚠️  RECIPIENT_PHONE이 설정되지 않았습니다. .env 파일을 확인하세요.")
        logger.warning("   메시지 발송 없이 hook 서버만 실행합니다.")

    logger.info("=" * 50)
    logger.info("🦀 iMessage Pet Bot 시작")
    logger.info(f"   수신자: {RECIPIENT_PHONE[:7] + '...' if RECIPIENT_PHONE else '미설정'}")
    logger.info(f"   서버: {SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"   DRY_RUN: {DRY_RUN}")
    logger.info(f"   일일 한도: {DAILY_MESSAGE_LIMIT}건")
    logger.info("=" * 50)

    # 상태머신 생성
    state_machine = PetStateMachine(on_state_change=_on_state_change)

    # Permission 콜백
    perm_callback = None
    if PERMISSION_ENABLED:
        perm_callback = _handle_permission
        logger.info(f"   Permission: ON (timeout={PERMISSION_TIMEOUT}s, default={PERMISSION_DEFAULT})")
    else:
        logger.info("   Permission: OFF")

    # Hook HTTP 서버 시작 (데몬 스레드)
    server = create_server(SERVER_HOST, SERVER_PORT, state_machine, perm_callback)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    # 시그널 핸들러
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # 메시지 폴링 루프 (메인 스레드)
    try:
        _polling_loop(state_machine)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("종료 중...")
        state_machine.shutdown()
        server.shutdown()
        logger.info("🦀 iMessage Pet Bot 종료")


if __name__ == '__main__':
    main()
