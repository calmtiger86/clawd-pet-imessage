# pet/personality.py
# -----------------------------------------------------------------
# 상태별 텍스트 응답 — 랜덤 변형으로 단조로움 방지
# -----------------------------------------------------------------

import random
from typing import Dict, List

# 상태 전환 시 보내는 메시지
STATE_MESSAGES: Dict[str, List[str]] = {
    'idle': [
        "🦀 대기 중~ 뭐 할까?",
        "🦀 한가하다~ 심심해~",
        "🦀 준비 완료!",
    ],
    'thinking': [
        "🤔 음... 생각 중...",
        "🧠 분석하는 중이야...",
        "💭 잠깐만, 고민 중...",
    ],
    'working': [
        "⚡ 열심히 코딩 중!",
        "🔨 뚝딱뚝딱 만드는 중!",
        "💻 코드 작성 중~",
    ],
    'juggling': [
        "🤹 여러 에이전트 동시에 돌리는 중!",
        "🎪 서브에이전트들과 협업 중!",
        "🔄 병렬 작업 진행 중!",
    ],
    'sweeping': [
        "🧹 컨텍스트 정리하는 중~",
        "🗑️ 메모리 청소 중!",
    ],
    'happy': [
        "🎉 작업 완료! 잘했다~",
        "✅ 끝! 완벽해!",
        "🥳 미션 성공!",
    ],
    'error': [
        "💥 앗, 뭔가 잘못됐어...",
        "🔥 에러 발생! 걱정 마, 고칠 거야",
        "⚠️ 문제가 생겼어...",
    ],
    'sleeping': [
        "😴 Zzz... 잘 자~",
        "🌙 졸려... 잠 좀 잘게",
        "💤 쉬는 중...",
    ],
}

# 명령어 응답
COMMAND_RESPONSES: Dict[str, List[str]] = {
    'feed': [
        "🦀 냠냠! 맛있다~ 고마워!",
        "🍕 우와! 먹을 거다!",
        "😋 감사합니다~ 에너지 충전!",
    ],
    'pet_status': [
        "지금 나는 {state} 상태야!",
    ],
    'unknown': [
        "🦀 잘 모르겠어~ /help 로 명령어를 확인해봐!",
    ],
}

HELP_TEXT = """🦀 iMessage Pet 명령어:
/pet — 현재 상태 확인
/status — Claude Code 세션 정보
/feed — 펫에게 먹이 주기
/sleep — 알림 음소거
/wake — 알림 재개
/help — 이 도움말"""


def get_state_message(state: str) -> str:
    """상태에 해당하는 랜덤 메시지를 반환한다."""
    messages = STATE_MESSAGES.get(state, STATE_MESSAGES['idle'])
    return random.choice(messages)


def get_command_response(command: str, **kwargs) -> str:
    """명령어 응답을 반환한다."""
    if command == 'help':
        return HELP_TEXT

    responses = COMMAND_RESPONSES.get(command, COMMAND_RESPONSES['unknown'])
    template = random.choice(responses)
    return template.format(**kwargs) if kwargs else template
