# config.py
# -----------------------------------------------------------------
# iMessage Pet Bot 설정
# -----------------------------------------------------------------

import os
from dotenv import load_dotenv

load_dotenv()

# --- 수신자 ---
RECIPIENT_PHONE = os.getenv('RECIPIENT_PHONE', '')

# --- 서버 ---
SERVER_HOST = '127.0.0.1'
SERVER_PORT = int(os.getenv('SERVER_PORT', '23456'))

# --- 경로 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets', 'gif')
STATE_FILE = os.path.join(BASE_DIR, 'state.json')
CHAT_DB_PATH = os.path.expanduser('~/Library/Messages/chat.db')

# --- 로깅 ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.getenv('LOG_DIR', os.path.join(BASE_DIR, 'logs'))

# --- Rate Limiting ---
DAILY_MESSAGE_LIMIT = int(os.getenv('DAILY_MESSAGE_LIMIT', '100'))
QUIET_HOURS_START = int(os.getenv('QUIET_HOURS_START', '0'))
QUIET_HOURS_END = int(os.getenv('QUIET_HOURS_END', '8'))

# --- 폴링 ---
POLLING_INTERVAL = float(os.getenv('POLLING_INTERVAL', '2'))

# --- 디바운스 (초) ---
DEBOUNCE_WINDOW = 5        # 연속 전환 무시 윈도우
STATE_COOLDOWNS = {
    'idle': 60,
    'thinking': 20,
    'working': 30,
    'juggling': 60,
    'sweeping': 30,
    'happy': 10,
    'error': 10,
    'sleeping': 120,
}

# --- 자동 복귀 (초) ---
AUTO_RETURN = {
    'thinking': ('idle', 30),
    'working': ('idle', 60),
    'juggling': ('working', 120),
    'sweeping': ('idle', 30),
    'happy': ('idle', 10),
    'error': ('idle', 10),
}

# --- idle → sleep 전환 (초) ---
IDLE_TO_SLEEP_SECONDS = 600  # 10분

# --- 테스트 모드 ---
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'

# --- 메시징 모드 ---
# separate: 별도 번호/이메일 사용 (에코 문제 없음)
# same: 같은 번호 사용 (에코 방지 활성화)
MESSAGING_MODE = os.getenv('MESSAGING_MODE', 'separate')

# --- Permission Request ---
PERMISSION_ENABLED = os.getenv('PERMISSION_ENABLED', 'false').lower() == 'true'
PERMISSION_TIMEOUT = int(os.getenv('PERMISSION_TIMEOUT', '45'))  # 0 = 무제한
PERMISSION_DEFAULT = os.getenv('PERMISSION_DEFAULT', 'allow')    # allow 또는 deny
PERMISSION_POLL_INTERVAL = 1.5  # chat.db 폴링 간격 (초)
