"""Failure ledger Redis atomic cho đăng nhập (05 mục 5)."""

import math
import uuid
from dataclasses import dataclass
from functools import cache
from typing import Protocol, cast

import structlog
from django.conf import settings
from django.utils import timezone
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from shared.privacy import pii_hmac

logger = structlog.get_logger(__name__)

WINDOW_MS = 15 * 60 * 1000
LEASE_MS = 30 * 1000
EMAIL_LIMIT = 5
IP_LIMIT = 20
# Redis treo không được giữ request đăng nhập: hết hạn thì fail-open như Redis tắt
REDIS_TIMEOUT_SECONDS = 0.5

# KEYS: email failures, email reservations, ip failures, ip reservations.
# Mỗi chiều bị chặn khi failures + suất còn chờ >= hạn mức; Retry-After là lúc chiều đó còn dưới
# hạn mức: phần tử thứ (count - limit + 1) theo thời điểm hết hạn. Nhiều chiều bị chặn thì lấy
# thời gian chờ dài nhất.
RESERVE_SCRIPT = """
local now = tonumber(ARGV[2])
local window = tonumber(ARGV[3])
local lease = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now - lease)
redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', now - window)
redis.call('ZREMRANGEBYSCORE', KEYS[4], '-inf', now - lease)
local function wait_ms(failures_key, reservations_key, limit)
  local failures = redis.call('ZRANGE', failures_key, 0, -1, 'WITHSCORES')
  local reservations = redis.call('ZRANGE', reservations_key, 0, -1, 'WITHSCORES')
  local count = (#failures + #reservations) / 2
  if count < limit then return 0 end
  local expiries = {}
  for i = 2, #failures, 2 do table.insert(expiries, tonumber(failures[i]) + window) end
  for i = 2, #reservations, 2 do table.insert(expiries, tonumber(reservations[i]) + lease) end
  table.sort(expiries)
  return expiries[count - limit + 1] - now
end
local retry = math.max(wait_ms(KEYS[1], KEYS[2], tonumber(ARGV[5])),
                       wait_ms(KEYS[3], KEYS[4], tonumber(ARGV[6])))
if retry > 0 then
  return {0, math.max(1, math.ceil(retry / 1000))}
end
redis.call('ZADD', KEYS[2], now, ARGV[1])
redis.call('ZADD', KEYS[4], now, ARGV[1])
for i = 1, 4 do redis.call('PEXPIRE', KEYS[i], window + lease) end
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

# Chỉ xoá failure email có thời điểm không sau lần thành công; lịch sử IP giữ nguyên
SUCCESS_SCRIPT = """
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('ZREM', KEYS[4], ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[2])
return 1
"""

RELEASE_SCRIPT = """
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('ZREM', KEYS[4], ARGV[1])
return 1
"""


class Script(Protocol):
    def __call__(self, *, keys: list[str], args: list[str | int]) -> object: ...


class RedisClient(Protocol):
    def register_script(self, script: str) -> Script: ...


class LoginRateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Login rate limited")


@dataclass(frozen=True)
class LoginReservation:
    """Suất thử mật khẩu; `enforced=False` khi Redis lỗi và ledger fail-open."""

    attempt_id: str
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


def _now_ms() -> int:
    return math.floor(timezone.now().timestamp() * 1000)


def _log_ledger_unavailable(operation: str) -> None:
    # Log event là nguồn metric cảnh báo; không kèm email, IP hay key (05 mục 5)
    logger.warning("login_failure_ledger_unavailable", operation=operation)


def _run_script(
    operation: str, script: Script, reservation: LoginReservation, args: list[str | int]
) -> None:
    if not reservation.enforced:
        return
    try:
        script(keys=reservation.keys, args=args)
    except RedisError, OSError:
        _log_ledger_unavailable(operation)


class LoginAttemptLedger:
    def __init__(self, client: RedisClient) -> None:
        self._reserve = client.register_script(RESERVE_SCRIPT)
        self._failure = client.register_script(FAILURE_SCRIPT)
        self._success = client.register_script(SUCCESS_SCRIPT)
        self._release = client.register_script(RELEASE_SCRIPT)

    def reserve(self, *, email: str, client_ip: str) -> LoginReservation:
        """Giữ suất thử mật khẩu cho email/IP; Redis lỗi thì trả suất không enforced.

        Raises:
            LoginRateLimited: Email hoặc IP đã chạm hạn mức trong cửa sổ trượt.
        """
        # attempt_id sinh mới mỗi lần thử: id do client gửi có thể trùng và gộp nhiều lần thử
        reservation = LoginReservation(
            attempt_id=uuid.uuid4().hex,
            email_key=f"login:{{email:{pii_hmac(email.strip().lower())}}}",
            ip_key=f"login:{{ip:{pii_hmac(client_ip)}}}",
            enforced=True,
        )
        args: list[str | int] = [
            reservation.attempt_id,
            _now_ms(),
            WINDOW_MS,
            LEASE_MS,
            EMAIL_LIMIT,
            IP_LIMIT,
        ]
        try:
            result = self._reserve(keys=reservation.keys, args=args)
        except RedisError, OSError:
            _log_ledger_unavailable("reserve")
            return LoginReservation(
                attempt_id=reservation.attempt_id,
                email_key=reservation.email_key,
                ip_key=reservation.ip_key,
                enforced=False,
            )
        # Lua trả {1, 0} khi giữ được suất, {0, retry_after_seconds} khi bị chặn
        is_reserved, retry_after = cast("list[int]", result)
        if not is_reserved:
            raise LoginRateLimited(retry_after)
        return reservation

    def complete_failure(self, reservation: LoginReservation) -> None:
        """Chuyển suất thành một failure của cả email và IP."""
        args: list[str | int] = [reservation.attempt_id, _now_ms(), WINDOW_MS]
        _run_script("complete_failure", self._failure, reservation, args)

    def complete_success(self, reservation: LoginReservation) -> None:
        """Trả suất và xoá failure email đã ghi tới thời điểm thành công."""
        args: list[str | int] = [reservation.attempt_id, _now_ms()]
        _run_script("complete_success", self._success, reservation, args)

    def release(self, reservation: LoginReservation) -> None:
        """Trả suất mà không ghi failure: lần thử dừng vì lỗi hạ tầng, không phải sai mật khẩu."""
        _run_script("release", self._release, reservation, [reservation.attempt_id])


@cache
def _redis_client(url: str) -> Redis:
    # Một client (connection pool) cho mỗi URL, không tạo pool mới mỗi request
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        retry=Retry(NoBackoff(), 0),
    )


def get_login_ledger() -> LoginAttemptLedger:
    return LoginAttemptLedger(_redis_client(settings.REDIS_URL))
