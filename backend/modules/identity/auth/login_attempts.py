"""Failure ledger Redis atomic cho đăng nhập (05 mục 5)."""

import math
import time
from dataclasses import dataclass
from typing import Any, Protocol

import structlog
from redis.exceptions import RedisError

from shared.privacy import pii_hmac

logger = structlog.get_logger(__name__)

WINDOW_MS = 15 * 60 * 1000
LEASE_MS = 30 * 1000
EMAIL_LIMIT = 5
IP_LIMIT = 20

RESERVE_SCRIPT = """
local now = tonumber(ARGV[2])
local window_start = now - tonumber(ARGV[3])
local lease_start = now - tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', window_start)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', lease_start)
redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', window_start)
redis.call('ZREMRANGEBYSCORE', KEYS[4], '-inf', lease_start)
local email_count = redis.call('ZCARD', KEYS[1]) + redis.call('ZCARD', KEYS[2])
local ip_count = redis.call('ZCARD', KEYS[3]) + redis.call('ZCARD', KEYS[4])
if email_count >= tonumber(ARGV[5]) or ip_count >= tonumber(ARGV[6]) then
  local earliest = now
  local values = {redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES'),
                  redis.call('ZRANGE', KEYS[2], 0, 0, 'WITHSCORES'),
                  redis.call('ZRANGE', KEYS[3], 0, 0, 'WITHSCORES'),
                  redis.call('ZRANGE', KEYS[4], 0, 0, 'WITHSCORES')}
  local retry = tonumber(ARGV[3])
  for i, value in ipairs(values) do
    if #value > 0 then
      local duration = (i == 2 or i == 4) and tonumber(ARGV[4]) or tonumber(ARGV[3])
      local ttl = tonumber(value[2]) + duration - now
      if ttl < retry then retry = ttl end
    end
  end
  return {0, math.max(1, math.ceil(retry / 1000))}
end
redis.call('ZADD', KEYS[2], now, ARGV[1])
redis.call('ZADD', KEYS[4], now, ARGV[1])
for i = 1, 4 do redis.call('PEXPIRE', KEYS[i], tonumber(ARGV[3]) + tonumber(ARGV[4])) end
return {1, 0}
"""

FAILURE_SCRIPT = """
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('ZREM', KEYS[4], ARGV[1])
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[1])
redis.call('ZADD', KEYS[3], ARGV[2], ARGV[1])
for i = 1, 4 do redis.call('PEXPIRE', KEYS[i], ARGV[3]) end
return 1
"""

SUCCESS_SCRIPT = """
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('ZREM', KEYS[4], ARGV[1])
redis.call('DEL', KEYS[1])
return 1
"""


class Script(Protocol):
    def __call__(self, *, keys: list[str], args: list[object]) -> object: ...


class RedisClient(Protocol):
    def register_script(self, script: str) -> Script: ...


class LoginRateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Login rate limited")


@dataclass(frozen=True)
class LoginReservation:
    request_id: str
    email_key: str
    ip_key: str
    enforced: bool

    @property
    def keys(self) -> list[str]:
        return [
            f"{self.email_key}:failures",
            f"{self.email_key}:reservations",
            f"{self.ip_key}:failures",
            f"{self.ip_key}:reservations",
        ]


class LoginAttemptLedger:
    reserve_script = RESERVE_SCRIPT

    def __init__(self, client: RedisClient) -> None:
        self._reserve = client.register_script(RESERVE_SCRIPT)
        self._failure = client.register_script(FAILURE_SCRIPT)
        self._success = client.register_script(SUCCESS_SCRIPT)

    def reserve(self, *, email: str, client_ip: str, request_id: str) -> LoginReservation:
        email_key = f"login:{{email:{pii_hmac(email.strip().lower())}}}"
        ip_key = f"login:{{ip:{pii_hmac(client_ip)}}}"
        reservation = LoginReservation(request_id, email_key, ip_key, True)
        now_ms = math.floor(time.time() * 1000)
        try:
            result: Any = self._reserve(
                keys=reservation.keys,
                args=[request_id, now_ms, WINDOW_MS, LEASE_MS, EMAIL_LIMIT, IP_LIMIT],
            )
            if int(result[0]) == 0:
                raise LoginRateLimited(int(result[1]))
            return reservation
        except LoginRateLimited:
            raise
        except RedisError, ConnectionError, OSError, TimeoutError:
            logger.warning("login_failure_ledger_unavailable", metric=1)
            return LoginReservation(request_id, email_key, ip_key, False)

    def complete_failure(self, reservation: LoginReservation) -> None:
        if not reservation.enforced:
            return
        try:
            self._failure(
                keys=reservation.keys,
                args=[reservation.request_id, math.floor(time.time() * 1000), WINDOW_MS],
            )
        except RedisError, ConnectionError, OSError, TimeoutError:
            logger.warning("login_failure_ledger_unavailable", metric=1)

    def complete_success(self, reservation: LoginReservation) -> None:
        if not reservation.enforced:
            return
        try:
            self._success(keys=reservation.keys, args=[reservation.request_id])
        except RedisError, ConnectionError, OSError, TimeoutError:
            logger.warning("login_failure_ledger_unavailable", metric=1)
