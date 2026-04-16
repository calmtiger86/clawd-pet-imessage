#!/usr/bin/env python3
# hooks/install.py
# -----------------------------------------------------------------
# ~/.claude/settings.json에 pet-hook.sh를 자동 등록한다.
# 기존 hook 배열에 추가하며, 이미 등록된 경우 건너뛴다.
# -----------------------------------------------------------------

import json
import os
import sys

SETTINGS_PATH = os.path.expanduser('~/.claude/settings.json')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK_SCRIPT = os.path.join(BASE_DIR, 'pet-hook.sh')

# 상태 알림용 이벤트
STATE_EVENTS = [
    'PreToolUse',
    'PostToolUse',
    'Stop',
]

HOOK_MARKER = 'imessage-pet'
PERMISSION_MARKER = 'imessage-pet/permission'


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def make_state_hook_entry(event: str) -> dict:
    """상태 알림용 command hook (비동기, 빠름)."""
    return {
        'matcher': '',
        'hooks': [{
            'type': 'command',
            'command': f'{HOOK_SCRIPT} {event}',
            'timeout': 2000,
        }]
    }


def make_permission_hook_entry(port: int, timeout: int) -> dict:
    """Permission 요청용 HTTP hook (동기, 블로킹)."""
    # timeout 0 → 매우 긴 값으로 변환 (사실상 무제한)
    hook_timeout = timeout if timeout > 0 else 3600
    return {
        'matcher': '',
        'hooks': [{
            'type': 'http',
            'url': f'http://127.0.0.1:{port}/permission',
            'timeout': hook_timeout * 1000,  # ms 단위
        }]
    }


def _has_marker(hooks_list: list, marker: str) -> bool:
    """특정 마커가 이미 등록되어 있는지 확인."""
    for entry in hooks_list:
        for hook in entry.get('hooks', []):
            cmd = hook.get('command', '')
            url = hook.get('url', '')
            if marker in cmd or marker in url:
                return True
    return False


def _remove_marker(hooks_list: list, marker: str) -> tuple:
    """마커에 해당하는 hook을 제거하고 (새 리스트, 제거 수)를 반환."""
    original = len(hooks_list)
    filtered = [
        entry for entry in hooks_list
        if not any(
            marker in h.get('command', '') or marker in h.get('url', '')
            for h in entry.get('hooks', [])
        )
    ]
    return filtered, original - len(filtered)


def install(permission_enabled: bool = False, port: int = 23456, timeout: int = 45):
    settings = load_settings()

    if 'hooks' not in settings:
        settings['hooks'] = {}

    hooks = settings['hooks']
    added = 0

    # 1. 상태 알림 hooks
    for event in STATE_EVENTS:
        if event not in hooks:
            hooks[event] = []

        if _has_marker(hooks[event], HOOK_MARKER):
            print(f"  ✓ {event} (상태 알림): 이미 등록됨")
            continue

        hooks[event].append(make_state_hook_entry(event))
        added += 1
        print(f"  + {event} (상태 알림): hook 추가")

    # 2. Permission hook (PreToolUse에 HTTP hook 추가)
    if permission_enabled:
        event = 'PreToolUse'
        if _has_marker(hooks.get(event, []), PERMISSION_MARKER):
            print(f"  ✓ {event} (permission): 이미 등록됨")
        else:
            hooks[event].append(make_permission_hook_entry(port, timeout))
            added += 1
            timeout_str = f"{timeout}초" if timeout > 0 else "무제한"
            print(f"  + {event} (permission): HTTP hook 추가 (timeout={timeout_str})")
    else:
        # permission 비활성 → 기존 permission hook 제거
        event = 'PreToolUse'
        if event in hooks:
            hooks[event], removed = _remove_marker(hooks[event], PERMISSION_MARKER)
            if removed > 0:
                print(f"  - {event} (permission): 기존 hook 제거")

    if added > 0:
        save_settings(settings)
        print(f"\n✅ {added}개 hook 등록 완료")
    else:
        print("\n✅ 모든 hook이 이미 등록되어 있습니다")


def uninstall():
    settings = load_settings()
    hooks = settings.get('hooks', {})
    removed_total = 0

    all_events = set(STATE_EVENTS + ['PreToolUse'])
    for event in all_events:
        if event not in hooks:
            continue

        hooks[event], r1 = _remove_marker(hooks[event], HOOK_MARKER)
        hooks[event], r2 = _remove_marker(hooks[event], PERMISSION_MARKER)
        removed = r1 + r2
        if removed > 0:
            removed_total += removed
            print(f"  - {event}: {removed}개 hook 제거")

    if removed_total > 0:
        save_settings(settings)
        print(f"\n✅ {removed_total}개 hook 제거 완료")
    else:
        print("\n✅ 제거할 hook이 없습니다")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--uninstall':
        uninstall()
    else:
        # .env에서 설정 읽기
        perm_enabled = False
        port = 23456
        timeout = 45

        try:
            sys.path.insert(0, os.path.join(BASE_DIR, '..'))
            from config import PERMISSION_ENABLED, SERVER_PORT, PERMISSION_TIMEOUT
            perm_enabled = PERMISSION_ENABLED
            port = SERVER_PORT
            timeout = PERMISSION_TIMEOUT
        except (ImportError, Exception):
            pass

        print(f"🦀 iMessage Pet Hook 설치")
        print(f"   스크립트: {HOOK_SCRIPT}")
        print(f"   설정 파일: {SETTINGS_PATH}")
        print(f"   Permission: {'ON' if perm_enabled else 'OFF'}\n")
        install(permission_enabled=perm_enabled, port=port, timeout=timeout)
