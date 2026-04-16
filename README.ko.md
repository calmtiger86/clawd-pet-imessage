# clawd-pet-imessage 🦀

**[English](README.md)** | **한국어**

Claude Code가 작업할 때 픽셀아트 GIF 펫 반응을 iPhone으로 보내주는 iMessage 봇입니다. [clawd-on-desk](https://github.com/rullerzhou-afk/clawd-on-desk)에서 영감을 받았습니다.

---

## 작동 방식

Claude Code가 동작할 때마다 hook이 로컬 HTTP 서버에 이벤트를 전송합니다. 서버의 상태머신이 적절한 GIF를 선택하고 AppleScript + Messages.app을 통해 iPhone으로 보냅니다.

```
Claude Code hooks
    │  (PreToolUse, Stop, SubagentStart, …)
    │  HTTP POST → localhost:23456/state
    ▼
펫 상태머신
    │  디바운스 + 쿨다운 + 일일 제한
    │
    ├─► GIF 선택  (assets/gif/<state>.gif)
    │
    └─► AppleScript → Messages.app → iMessage ──► iPhone
```

**폴링 루프** (별도 스레드)가 2초마다 `~/Library/Messages/chat.db`를 읽어 iPhone에서 보낸 명령어를 처리합니다.

---

## 펫 상태

| 상태 | 트리거 | 자동 복귀 |
|---|---|---|
| `idle` | `SessionStart` | 10분 후 `sleeping` |
| `thinking` | `UserPromptSubmit` | 30초 후 `idle` |
| `working` | `PreToolUse` / `PostToolUse` | 60초 후 `idle` |
| `juggling` | `SubagentStart` | 120초 후 `working` |
| `sweeping` | `PreCompact` | 30초 후 `idle` |
| `happy` | `Stop` (성공) | 10초 후 `idle` |
| `error` | `PostToolUseFailure` / `StopFailure` | 10초 후 `idle` |
| `sleeping` | `SessionEnd` / idle 타임아웃 | — |

상태 전환은 우선순위를 따릅니다 (`error` > `happy` > `sweeping` > `juggling` > `working` > `thinking` > `idle` > `sleeping`). 5초 디바운스 윈도우로 빠른 연속 전환을 하나로 합칩니다.

---

## 명령어

iPhone에서 다음 명령어를 보내 봇을 제어할 수 있습니다:

| 명령어 | 기능 |
|---|---|
| `/pet` | 현재 상태 + GIF 확인 |
| `/status` | 상태, 오늘 발송 수, 음소거 여부 |
| `/feed` | `happy` 상태 전환 + GIF |
| `/sleep` | 알림 음소거 |
| `/wake` | 알림 재개 |
| `/help` | 전체 명령어 목록 |

---

## Permission Request (도구 승인)

활성화하면, Claude Code가 위험한 Bash 명령어를 실행하기 전에 iMessage로 승인 요청을 보냅니다.

**승인 요청이 발생하는 위험 패턴:**
`rm`, `rmdir`, `git push`, `git reset`, `git checkout .`, `drop`, `delete`, `truncate`, `kill`, `pkill`, `chmod`, `chown`, `sudo`, `dd if=`

**답장:** `y` / `yes` / `ㅇ` / `허용` → 허용 — `n` / `no` / `ㄴ` / `거부` → 거부

세 가지 모드 (`setup.sh`에서 설정):

| 모드 | 동작 |
|---|---|
| OFF | Permission 요청 없음, 상태 알림만 |
| 타임아웃 | N초 대기 후 자동 허용 또는 자동 거부 |
| 무제한 | 답장할 때까지 Claude Code 일시 정지 |

---

## 일일 제한 및 조용한 시간

- **일일 한도:** 100건 (24시간 롤링 윈도우)
- **조용한 시간:** 자정~오전 8시 메시지 미발송 (설정 가능)
- **디바운스:** 5초 내 연속 상태 전환은 하나로 합침
- **상태별 쿨다운:** 같은 상태 GIF 재발송 방지 (예: `working` → 30초, `sleeping` → 120초)
- **수동 음소거:** `/sleep`, `/wake` 명령어

---

## 에코 방지 (같은 번호 모드)

자기 번호로 메시지를 보내면 `chat.db`에 송수신이 모두 기록되어 봇이 자기 메시지를 다시 처리하는 무한 루프가 발생합니다. 3중 방어:

1. **해시 캐시** — 발송 메시지를 MD5 해시로 60초간 저장, 수신 메시지와 대조
2. **시스템 패턴** — 봇 이모지/프리픽스로 시작하는 메시지 무시
3. **SQL 필터** — 별도 번호 모드에서는 `is_from_me = 0` 필터 적용

---

## 요구 사항

- macOS (Messages.app 필요)
- Python 3.9+
- 터미널에 **전체 디스크 접근 권한** (시스템 설정 → 개인정보 보호 및 보안 → 전체 디스크 접근 권한)
- Mac에 iMessage 계정 로그인

---

## 설치

```bash
git clone https://github.com/calmtiger86/clawd-pet-imessage
cd clawd-pet-imessage
./setup.sh
```

`setup.sh`가 안내하는 항목:

1. Python 의존성 설치 (`Pillow`, `python-dotenv`, `schedule`)
2. 메시징 모드 — **별도 번호** (추천) 또는 **같은 번호** (에코 방지 자동 활성화)
3. 전화번호 입력 (`+국가코드번호` 형식 검증)
4. DRY_RUN 모드 (첫 실행 시 추천 — 실제 발송 없이 로그만)
5. Permission Request 설정 (끄기 / 타임아웃 / 무제한)
6. GIF 에셋 생성 (`assets/generate_gifs.py`)
7. Claude Code hook 등록 (`hooks/install.py`)
8. macOS 권한 안내

설정 완료 후 실행:

```bash
./start.sh
```

`.env`가 없으면 `start.sh`가 자동으로 setup을 실행합니다.

---

## 설정

모든 설정은 `.env`에 저장됩니다 (`setup.sh`가 자동 생성). 수동으로 수정 가능:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `RECIPIENT_PHONE` | — | `+821012345678` 형식의 전화번호 |
| `MESSAGING_MODE` | `separate` | `separate` 또는 `same` |
| `SERVER_PORT` | `23456` | Hook HTTP 서버 포트 |
| `DRY_RUN` | `false` | true면 실제 발송 없이 로그만 |
| `DAILY_MESSAGE_LIMIT` | `100` | 24시간 최대 메시지 수 |
| `QUIET_HOURS_START` | `0` | 조용한 시간 시작 (0–23) |
| `QUIET_HOURS_END` | `8` | 조용한 시간 종료 (0–23) |
| `POLLING_INTERVAL` | `2` | chat.db 폴링 간격 (초) |
| `PERMISSION_ENABLED` | `false` | Permission Request 활성화 |
| `PERMISSION_TIMEOUT` | `45` | 답장 대기 시간 (초). `0` = 무제한 |
| `PERMISSION_DEFAULT` | `allow` | 타임아웃 시 기본 동작 |

---

## 프로젝트 구조

```
clawd-pet-imessage/
├── main.py               # 진입점: HTTP 서버 + 폴링 루프
├── config.py             # .env에서 설정 로드
├── setup.sh              # 인터랙티브 설치 스크립트
├── start.sh              # 실행 (.env 없으면 setup 자동 실행)
├── requirements.txt      # python-dotenv, Pillow, schedule
│
├── hooks/
│   ├── pet-hook.sh       # Bash hook: curl POST (비동기, 최대 1초)
│   └── install.py        # Claude Code settings.json에 hook 등록
│
├── pet/
│   ├── state_machine.py  # 디바운스 + 쿨다운 + 자동 복귀 + idle 타이머
│   ├── hook_server.py    # localhost:23456 HTTP 서버 (/state, /permission)
│   ├── permission_handler.py  # 위험 명령어 감지 + 답장 폴링
│   └── personality.py    # 상태별 메시지 + 명령어 응답
│
├── messaging/
│   ├── sender.py         # AppleScript send_gif() / send_text()
│   ├── chat_db.py        # ~/Library/Messages/chat.db SQLite 리더
│   ├── echo_guard.py     # 3중 에코 방지
│   └── rate_limiter.py   # 일일 한도 + 조용한 시간 + 음소거
│
├── assets/
│   └── gif/              # idle.gif, thinking.gif, working.gif, …
│
└── utils/
    ├── logger.py
    ├── retry.py
    ├── safe_runner.py
    └── state_store.py
```

---

## DRY_RUN 모드

`.env`에서 `DRY_RUN=true`로 설정하면 실제 iMessage를 보내지 않고 로그만 출력합니다. 언제든 전환 가능:

```bash
# .env
DRY_RUN=false
```

---

## macOS 권한 (최초 1회)

| 권한 | 위치 | 이유 |
|---|---|---|
| 전체 디스크 접근 권한 | 시스템 설정 → 개인정보 보호 → 전체 디스크 접근 권한 → 터미널 추가 | `chat.db` 읽기 |
| 자동화 | 첫 발송 시 팝업 표시 | AppleScript로 Messages.app 제어 |

---

## 기술 스택

- **Python 3** — stdlib threads, `http.server`, `sqlite3`, `subprocess`
- **Pillow** — 픽셀아트 GIF 생성
- **python-dotenv** — `.env` 설정 로드
- **AppleScript** — `osascript`를 통한 Messages.app 자동화
- **SQLite** — `chat.db` 읽기 전용 접근

---

## 라이선스

MIT
