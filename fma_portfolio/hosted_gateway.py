"""Loopback-only owner-operated forecast gateway, for controlled P8.1C pilot.

Not an Internet-facing HTTP service. Put behind independently authenticated,
HTTPS, request-limited infrastructure only after the cloud readiness gates.
"""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import threading
import time
from typing import Callable

from .p7.forecast_contract import validate_request, InvalidForecastInput
from .eligibility import classify_fixture
from .p7.owner_local import _clean_projection

MAX_REQUEST_BYTES = 4096
MAX_RESPONSE_BYTES = 4096
REQUEST_FIELDS = frozenset((
    'league', 'home', 'away', 'fixture_date', 'ah_line',
    'ah_home_odds', 'ah_away_odds', 'asian_line',
    'asian_over_odds', 'asian_under_odds',
    'fixed_over_odds', 'fixed_under_odds',
))


class GatewayState:
    def __init__(self, *, token: str, executor: Callable[[dict], dict],
                 max_per_hour: int = 4, cooldown_seconds: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        if not isinstance(token,str) or len(token) < 32 or any(c in token for c in '\r\n'):
            raise ValueError('Gateway requires a strong secret token (at least 32 characters)')
        if not 1 <= max_per_hour <= 30 or not 0 <= cooldown_seconds <= 3600:
            raise ValueError('Invalid gateway quota')
        self.token = token
        self.executor = executor
        self.max_per_hour = max_per_hour
        self.cooldown_seconds = cooldown_seconds
        self.clock = clock
        self._admissions = deque()
        self._lock = threading.Lock()
        self._worker = threading.BoundedSemaphore(1)

    def admit(self) -> str:
        """Reserve a global inference slot, or return a safe refusal reason."""
        if not self._worker.acquire(blocking=False):
            return 'busy'
        with self._lock:
            now = self.clock()
            while self._admissions and now - self._admissions[0] >= 3600:
                self._admissions.popleft()
            if len(self._admissions) >= self.max_per_hour:
                self._worker.release()
                return 'quota'
            if self._admissions and now - self._admissions[-1] < self.cooldown_seconds:
                self._worker.release()
                return 'cooldown'
            self._admissions.append(now)
        return 'accepted'

    def release(self) -> None:
        self._worker.release()


class GatewayHandler(BaseHTTPRequestHandler):
    server_version = 'FMA-Gateway/0.1'
    sys_version = ''

    def log_message(self, format: str, *args: object) -> None:
        # Never log visitor inputs, Authorization headers or bookmaker odds.
        return

    def _reply(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, allow_nan=False, separators=(',', ':')).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == '/healthz':
            self._reply(200, {'status':'ready'})
        else:
            self._reply(404, {'error':'not_found'})

    def do_POST(self) -> None:
        if self.path != '/v1/forecast':
            self._reply(404, {'error':'not_found'})
            return
        state: GatewayState = self.server.gateway_state
        bearer = self.headers.get('Authorization','')
        if not bearer.startswith('Bearer ') or not hmac.compare_digest(bearer[7:], state.token):
            self._reply(401, {'error':'unauthorized'})
            return
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0].lower().strip() != 'application/json':
            self._reply(415, {'error':'invalid_content_type'})
            return
        try:
            size = int(self.headers.get('Content-Length',''))
            if not 1 <= size <= MAX_REQUEST_BYTES:
                raise ValueError
        except ValueError:
            self._reply(413, {'error':'invalid_request_size'})
            return
        try:
            raw = self.rfile.read(size)
            obj = json.loads(raw.decode('utf-8'))
            if (not isinstance(obj,dict) or set(obj) != {'request'}
                    or not isinstance(obj['request'],dict)
                    or set(obj['request']) != REQUEST_FIELDS):
                raise ValueError
            validated = validate_request(obj['request'])
            if any(ord(c) < 32 or ord(c) == 127 for key in ('home','away') for c in validated[key]):
                raise ValueError('Unsafe team text')
        except (ValueError, InvalidForecastInput, UnicodeError, TypeError, OverflowError):
            self._reply(400, {'error':'invalid_forecast_input'})
            return
        coverage = classify_fixture(validated['league'], validated['home'], validated['away'], validated['fixture_date'])
        if coverage.status != 'ELIGIBLE':
            # Public explanation only: never leak paths, model logs or user markets.
            self._reply(422, {'error': 'fixture_ineligible' if coverage.status == 'INELIGIBLE'
                              else 'eligibility_unverified', 'reason': coverage.reason})
            return
        admission = state.admit()
        if admission != 'accepted':
            self._reply(429 if admission != 'busy' else 503, {'error':admission})
            return
        try:
            projection = _clean_projection(state.executor(validated))
            response = {'ok':True,'result':projection}
            encoded = json.dumps(response,allow_nan=False).encode('utf-8')
            if len(encoded) > MAX_RESPONSE_BYTES:
                raise ValueError('Oversize projection')
        except Exception:  # fail closed: never return model logs, paths or exception details
            self._reply(503, {'error':'model_unavailable'})
        else:
            self._reply(200, response)
        finally:
            state.release()

    def do_PUT(self) -> None:
        self._reply(405, {'error':'method_not_allowed'})

    def do_DELETE(self) -> None:
        self._reply(405, {'error':'method_not_allowed'})


class LoopbackGateway(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port: int, state: GatewayState):
        if not 0 <= port <= 65535:
            raise ValueError('Invalid TCP port')
        super().__init__(('127.0.0.1',port), GatewayHandler)
        self.gateway_state = state
