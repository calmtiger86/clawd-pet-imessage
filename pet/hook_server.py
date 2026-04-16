# pet/hook_server.py
# -----------------------------------------------------------------
# HTTP 서버 — Claude Code hook에서 POST /state를 수신한다.
# clawd-on-desk의 server.js 패턴을 최소한으로 포팅.
# -----------------------------------------------------------------

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Callable, TYPE_CHECKING
from utils.logger import logger

if TYPE_CHECKING:
    from pet.state_machine import PetStateMachine


class _HookHandler(BaseHTTPRequestHandler):
    """Hook POST 요청을 처리하는 핸들러."""

    state_machine: Optional['PetStateMachine'] = None
    _permission_callback: Optional[Callable[[dict], dict]] = None

    def do_GET(self):
        """헬스체크: GET /state → 200"""
        if self.path == '/state':
            self._respond(200, {'status': 'ok', 'state': self._get_state()})
        else:
            self._respond(404, {'error': 'not found'})

    def do_POST(self):
        if self.path == '/state':
            self._handle_state()
        elif self.path == '/permission':
            self._handle_permission()
        else:
            self._respond(404, {'error': 'not found'})

    def _handle_state(self):
        """상태 이벤트 수신: POST /state"""
        try:
            data = self._read_json()
            if data is None:
                return

            event = data.get('event', '')
            session_id = ''
            payload = data.get('payload', {})
            if isinstance(payload, dict):
                session_id = payload.get('session_id', '')

            if not event:
                self._respond(400, {'error': 'missing event'})
                return

            logger.debug(f"Hook 수신: event={event}, session={session_id}")

            if self.state_machine is not None:
                self.state_machine.handle_event(event, session_id)

            self._respond(200, {'status': 'ok'})

        except Exception as e:
            logger.error(f"Hook 처리 실패: {e}")
            self._respond(500, {'error': str(e)})

    def _handle_permission(self):
        """
        Permission 요청 처리: POST /permission

        이 요청은 사용자가 iMessage로 답할 때까지 블로킹된다.
        Claude Code의 HTTP hook 타임아웃 내에 반드시 응답한다.
        """
        try:
            data = self._read_json()
            if data is None:
                return

            cb = _HookHandler._permission_callback
            if cb is None:
                self._respond(200, self._permission_response('allow'))
                return

            result = cb(data)
            self._respond(200, result)

        except Exception as e:
            logger.error(f"Permission 처리 실패: {e}")
            # 에러 시 allow (Claude Code 차단 방지)
            self._respond(200, self._permission_response('allow'))

    def _read_json(self) -> Optional[dict]:
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 8192:
            self._respond(413, {'error': 'payload too large'})
            return None
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._respond(400, {'error': 'invalid json'})
            return None

    def _get_state(self) -> str:
        if self.state_machine is not None:
            return self.state_machine.state
        return 'unknown'

    @staticmethod
    def _permission_response(decision: str) -> dict:
        """Claude Code가 기대하는 permission 응답 형식."""
        return {
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': decision,
            }
        }

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode('utf-8'))

    def log_message(self, format, *args):
        """기본 stderr 로깅 억제 — 우리 logger 사용."""
        pass


def create_server(
    host: str,
    port: int,
    state_machine: 'PetStateMachine',
    permission_callback: Optional[Callable[[dict], dict]] = None,
) -> HTTPServer:
    """Hook HTTP 서버를 생성한다."""
    _HookHandler.state_machine = state_machine
    _HookHandler._permission_callback = permission_callback
    server = HTTPServer((host, port), _HookHandler)
    logger.info(f"Hook 서버 시작: http://{host}:{port}")
    return server
