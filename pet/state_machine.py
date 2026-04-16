# pet/state_machine.py
# -----------------------------------------------------------------
# 펫 상태머신 — clawd-on-desk state.js를 Python으로 포팅
#
# 핵심 차이: iMessage는 메시지당 비용(일일 ~100건 제한)이므로
# 공격적 디바운스로 불필요한 메시지 발송을 억제한다.
# -----------------------------------------------------------------

import time
import threading
from typing import Optional, Callable, Dict, Tuple
from utils.logger import logger

# 상태 우선순위 (높을수록 우선)
STATE_PRIORITY: Dict[str, int] = {
    'sleeping': 0,
    'idle': 1,
    'thinking': 2,
    'working': 3,
    'juggling': 4,
    'sweeping': 6,
    'happy': 7,
    'error': 8,
}

# 이벤트 → 상태 매핑 (clawd-on-desk hooks/clawd-hook.js 동일)
EVENT_TO_STATE: Dict[str, str] = {
    'SessionStart': 'idle',
    'SessionEnd': 'sleeping',
    'UserPromptSubmit': 'thinking',
    'PreToolUse': 'working',
    'PostToolUse': 'working',
    'PostToolUseFailure': 'error',
    'Stop': 'happy',
    'StopFailure': 'error',
    'SubagentStart': 'juggling',
    'SubagentStop': 'working',
    'PreCompact': 'sweeping',
}

# 자동 복귀 설정: state → (target_state, delay_seconds)
AUTO_RETURN: Dict[str, Tuple[str, int]] = {
    'thinking': ('idle', 30),
    'working': ('idle', 60),
    'juggling': ('working', 120),
    'sweeping': ('idle', 30),
    'happy': ('idle', 10),
    'error': ('idle', 10),
}

# 상태별 최소 쿨다운 (같은 상태 GIF 재발송 방지)
STATE_COOLDOWNS: Dict[str, int] = {
    'idle': 60,
    'thinking': 20,
    'working': 30,
    'juggling': 60,
    'sweeping': 30,
    'happy': 10,
    'error': 10,
    'sleeping': 120,
}

# 디바운스 윈도우 (초) — 이 시간 내 연속 전환은 마지막만 발송
DEBOUNCE_WINDOW = 5.0


class PetStateMachine:
    """
    펫 상태머신.

    상태 변경 시 on_state_change 콜백을 호출한다.
    디바운스 + 쿨다운으로 iMessage 발송을 최소화한다.
    """

    def __init__(self, on_state_change: Optional[Callable[[str, str], None]] = None):
        self._state = 'sleeping'
        self._previous_state = 'sleeping'
        self._on_state_change = on_state_change
        self._lock = threading.Lock()

        # 디바운스
        self._pending_state: Optional[str] = None
        self._debounce_timer: Optional[threading.Timer] = None

        # 쿨다운 추적: state → last_sent_time
        self._last_sent: Dict[str, float] = {}

        # 자동 복귀 타이머
        self._auto_return_timer: Optional[threading.Timer] = None

        # idle → sleep 타이머
        self._idle_timer: Optional[threading.Timer] = None

        # 마지막 활동 시각
        self._last_activity = time.time()

    @property
    def state(self) -> str:
        return self._state

    def handle_event(self, event: str, session_id: str = '') -> None:
        """Claude Code hook 이벤트를 처리한다."""
        new_state = EVENT_TO_STATE.get(event)
        if new_state is None:
            logger.debug(f"알 수 없는 이벤트 무시: {event}")
            return

        self._last_activity = time.time()
        self._request_transition(new_state)

    def _request_transition(self, target: str) -> None:
        """디바운스를 거쳐 상태 전환을 요청한다."""
        with self._lock:
            current_priority = STATE_PRIORITY.get(self._state, 0)
            target_priority = STATE_PRIORITY.get(target, 0)

            # 우선순위가 낮으면 무시 (현재 상태가 더 중요)
            if target_priority < current_priority and target != 'sleeping':
                return

            # 같은 상태면 타이머만 갱신
            if target == self._state:
                self._refresh_auto_return()
                return

            # 디바운스: 기존 타이머 취소하고 새로 설정
            self._pending_state = target
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()

            self._debounce_timer = threading.Timer(
                DEBOUNCE_WINDOW, self._commit_transition
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _commit_transition(self) -> None:
        """디바운스 윈도우 후 실제 상태 전환을 실행한다."""
        with self._lock:
            target = self._pending_state
            if target is None:
                return
            self._pending_state = None

            # 쿨다운 체크
            now = time.time()
            cooldown = STATE_COOLDOWNS.get(target, 10)
            last_sent = self._last_sent.get(target, 0)

            should_notify = (now - last_sent) >= cooldown

            # 내부 상태는 항상 업데이트
            self._previous_state = self._state
            self._state = target

            # 자동 복귀 타이머 설정
            self._setup_auto_return(target)

            # idle → sleep 타이머 관리
            if target == 'idle':
                self._start_idle_timer()
            else:
                self._cancel_idle_timer()

            logger.info(f"상태 전환: {self._previous_state} → {target}"
                        f"{' (알림 발송)' if should_notify else ' (쿨다운 중)'}")

            # 콜백 호출 (쿨다운 통과 시만)
            if should_notify and self._on_state_change is not None:
                self._last_sent[target] = now
                # lock 밖에서 콜백 호출
                callback = self._on_state_change
                prev = self._previous_state

        if should_notify and self._on_state_change is not None:
            try:
                callback(target, prev)
            except Exception as e:
                logger.error(f"상태 변경 콜백 실패: {e}")

    def _setup_auto_return(self, state: str) -> None:
        """자동 복귀 타이머를 설정한다."""
        if self._auto_return_timer is not None:
            self._auto_return_timer.cancel()
            self._auto_return_timer = None

        ret = AUTO_RETURN.get(state)
        if ret is None:
            return

        target_state, delay = ret
        self._auto_return_timer = threading.Timer(
            delay, self._request_transition, args=[target_state]
        )
        self._auto_return_timer.daemon = True
        self._auto_return_timer.start()

    def _refresh_auto_return(self) -> None:
        """같은 상태의 자동 복귀 타이머를 리셋한다."""
        self._setup_auto_return(self._state)

    def _start_idle_timer(self) -> None:
        """idle 상태에서 10분 후 sleeping으로 전환."""
        self._cancel_idle_timer()
        from config import IDLE_TO_SLEEP_SECONDS
        self._idle_timer = threading.Timer(
            IDLE_TO_SLEEP_SECONDS, self._request_transition, args=['sleeping']
        )
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _cancel_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None

    def force_state(self, state: str) -> None:
        """명령어로 강제 상태 전환 (디바운스 무시)."""
        with self._lock:
            self._previous_state = self._state
            self._state = state
            self._last_sent[state] = time.time()

            if state == 'idle':
                self._start_idle_timer()
            else:
                self._cancel_idle_timer()

            self._setup_auto_return(state)

        if self._on_state_change is not None:
            try:
                self._on_state_change(state, self._previous_state)
            except Exception as e:
                logger.error(f"강제 상태 변경 콜백 실패: {e}")

    def shutdown(self) -> None:
        """모든 타이머를 정리한다."""
        if self._debounce_timer:
            self._debounce_timer.cancel()
        if self._auto_return_timer:
            self._auto_return_timer.cancel()
        self._cancel_idle_timer()
