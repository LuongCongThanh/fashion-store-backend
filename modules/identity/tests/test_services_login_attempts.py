"""Failure ledger đăng nhập trên Redis thật (05 mục 5, 9)."""

import socket
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import redis.exceptions
import time_machine
from redis import Redis
from structlog.testing import capture_logs

from modules.identity.auth.login_attempts import (
    LoginAttemptLedger,
    LoginRateLimited,
    LoginReservation,
    get_login_ledger,
)
from modules.identity.tests.conftest import random_email, random_ip

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


@pytest.fixture
def ledger(ledger_redis: Redis) -> LoginAttemptLedger:
    return LoginAttemptLedger(ledger_redis)


def _fail(ledger: LoginAttemptLedger, *, email: str, client_ip: str, times: int = 1) -> None:
    for _ in range(times):
        ledger.complete_failure(ledger.reserve(email=email, client_ip=client_ip))


def _retry_after(ledger: LoginAttemptLedger, *, email: str, client_ip: str) -> int:
    with pytest.raises(LoginRateLimited) as exc_info:
        ledger.reserve(email=email, client_ip=client_ip)
    return exc_info.value.retry_after


def test_email_limit_allows_fifth_attempt_and_blocks_sixth(ledger: LoginAttemptLedger) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False):
        _fail(ledger, email=email, client_ip=client_ip, times=4)
        fifth = ledger.reserve(email=email, client_ip=client_ip)
        ledger.complete_failure(fifth)
        retry_after = _retry_after(ledger, email=email, client_ip=client_ip)

    assert fifth.enforced is True
    assert retry_after == 900


def test_ip_limit_counts_failures_across_emails(ledger: LoginAttemptLedger) -> None:
    client_ip = random_ip()

    with time_machine.travel(NOW, tick=False):
        for _ in range(19):
            _fail(ledger, email=random_email(), client_ip=client_ip)
        twentieth = ledger.reserve(email=random_email(), client_ip=client_ip)
        ledger.complete_failure(twentieth)
        retry_after = _retry_after(ledger, email=random_email(), client_ip=client_ip)

    assert twentieth.enforced is True
    assert retry_after == 900


def test_sliding_window_frees_attempt_when_oldest_failure_expires(
    ledger: LoginAttemptLedger,
) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        _fail(ledger, email=email, client_ip=client_ip, times=5)
        traveller.shift(timedelta(minutes=15) - timedelta(seconds=1))
        retry_after = _retry_after(ledger, email=email, client_ip=client_ip)
        traveller.shift(timedelta(seconds=1))
        reservation = ledger.reserve(email=email, client_ip=client_ip)

    assert retry_after == 1
    assert reservation.enforced is True


def test_email_differing_in_case_and_spaces_shares_counter(ledger: LoginAttemptLedger) -> None:
    email = random_email()

    with time_machine.travel(NOW, tick=False):
        _fail(ledger, email=f"  {email.upper()} ", client_ip=random_ip(), times=5)
        retry_after = _retry_after(ledger, email=email, client_ip=random_ip())

    assert retry_after == 900


def test_success_clears_email_failures_and_keeps_ip_failures(
    ledger: LoginAttemptLedger, ledger_redis: Redis
) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        _fail(ledger, email=email, client_ip=client_ip, times=4)
        traveller.shift(timedelta(seconds=1))
        reservation = ledger.reserve(email=email, client_ip=client_ip)
        ledger.complete_success(reservation)

    email_failures, _, ip_failures, _ = reservation.keys
    actual = (ledger_redis.zcard(email_failures), ledger_redis.zcard(ip_failures))
    assert actual == (0, 4)


def test_success_keeps_email_failure_recorded_after_success_time(
    ledger: LoginAttemptLedger, ledger_redis: Redis
) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        succeeding = ledger.reserve(email=email, client_ip=client_ip)
        failing = ledger.reserve(email=email, client_ip=client_ip)
        # Worker khác có đồng hồ chạy trước 5 giây ghi failure trước khi lần đúng hoàn tất
        traveller.shift(timedelta(seconds=5))
        ledger.complete_failure(failing)
        traveller.shift(timedelta(seconds=-5))
        ledger.complete_success(succeeding)

    email_failures = succeeding.keys[0]
    assert ledger_redis.zcard(email_failures) == 1


def test_pending_reservations_hold_slots_until_lease_expires(
    ledger: LoginAttemptLedger,
) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        for _ in range(5):
            ledger.reserve(email=email, client_ip=client_ip)
        retry_after = _retry_after(ledger, email=email, client_ip=client_ip)
        traveller.shift(timedelta(seconds=30))
        reservation = ledger.reserve(email=email, client_ip=client_ip)

    assert retry_after == 30
    assert reservation.enforced is True


def test_release_frees_slot_without_recording_failure(
    ledger: LoginAttemptLedger, ledger_redis: Redis
) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False):
        for _ in range(5):
            ledger.release(ledger.reserve(email=email, client_ip=client_ip))
        reservation = ledger.reserve(email=email, client_ip=client_ip)

    assert reservation.enforced is True
    assert ledger_redis.zcard(reservation.keys[0]) == 0


def test_retry_after_ignores_dimension_that_is_not_blocked(ledger: LoginAttemptLedger) -> None:
    victim, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        # IP có một failure sắp hết cửa sổ, nhưng chỉ email chạm hạn mức
        _fail(ledger, email=random_email(), client_ip=client_ip)
        traveller.shift(timedelta(minutes=14))
        _fail(ledger, email=victim, client_ip=client_ip, times=5)
        retry_after = _retry_after(ledger, email=victim, client_ip=client_ip)

    assert retry_after == 900


def test_retry_after_waits_until_count_drops_below_limit(ledger: LoginAttemptLedger) -> None:
    email, client_ip = random_email(), random_ip()

    with time_machine.travel(NOW, tick=False) as traveller:
        first_batch = [ledger.reserve(email=email, client_ip=client_ip) for _ in range(5)]
        # Lease hết hạn trước khi worker ghi kết quả: lô sau vẫn được giữ suất
        traveller.shift(timedelta(seconds=31))
        second_batch = [ledger.reserve(email=email, client_ip=client_ip) for _ in range(5)]
        for reservation in first_batch:
            ledger.complete_failure(reservation)
        traveller.shift(timedelta(seconds=60))
        for reservation in second_batch:
            ledger.complete_failure(reservation)
        # 10 failure > hạn mức 5: phải chờ failure thứ 6 (lô sau) hết cửa sổ
        retry_after = _retry_after(ledger, email=email, client_ip=client_ip)

    assert retry_after == 900


def test_redis_keys_hold_no_raw_email_or_ip(
    ledger: LoginAttemptLedger, ledger_redis: Redis
) -> None:
    email, client_ip = random_email(), random_ip()

    reservation = ledger.reserve(email=email, client_ip=client_ip)
    ledger.complete_failure(reservation)

    stored_keys = [key for key in reservation.keys if ledger_redis.exists(key)]
    assert stored_keys
    for key in stored_keys:
        assert email not in key
        assert client_ip not in key
        members = ledger_redis.zrange(key, 0, -1)
        assert all(email not in member and client_ip not in member for member in members)


class BrokenRedis:
    """Client Redis giả khi Redis tắt hoặc treo: mọi lệnh ném lỗi của redis-py."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def register_script(self, script: str) -> Any:
        def run(*, keys: list[str], args: list[object]) -> object:
            raise self._error

        return run


@pytest.mark.parametrize(
    "error",
    [redis.exceptions.ConnectionError("down"), redis.exceptions.TimeoutError("slow")],
    ids=["connection", "timeout"],
)
def test_ledger_fails_open_with_metric_event_without_identifier(error: Exception) -> None:
    ledger = LoginAttemptLedger(BrokenRedis(error))
    email, client_ip = "Staff@Example.com", "203.0.113.8"

    with capture_logs() as logs:
        reservation = ledger.reserve(email=email, client_ip=client_ip)
        pending = LoginReservation(attempt_id="a", email_key="e", ip_key="i", enforced=True)
        ledger.complete_failure(pending)
        ledger.complete_success(pending)
        ledger.release(pending)

    assert reservation.enforced is False
    events = [log["event"] for log in logs]
    assert events == ["login_failure_ledger_unavailable"] * 4
    assert all(log["log_level"] == "warning" for log in logs)
    logged = repr(logs).lower()
    assert email.lower() not in logged
    assert client_ip not in logged


@pytest.fixture
def unresponsive_redis_url(settings: Any) -> Iterator[None]:
    """Server TCP nhận kết nối nhưng không bao giờ trả lời, như Redis bị treo."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    connections: list[socket.socket] = []

    def accept_forever() -> None:
        while True:
            try:
                connections.append(server.accept()[0])
            except OSError:
                return

    threading.Thread(target=accept_forever, daemon=True).start()
    settings.REDIS_URL = f"redis://127.0.0.1:{server.getsockname()[1]}/0"
    yield
    server.close()
    for connection in connections:
        connection.close()


@pytest.mark.usefixtures("unresponsive_redis_url")
def test_ledger_fails_open_when_redis_hangs() -> None:
    results: list[LoginReservation] = []
    worker = threading.Thread(
        target=lambda: results.append(
            get_login_ledger().reserve(email=random_email(), client_ip=random_ip())
        ),
        daemon=True,
    )

    worker.start()
    worker.join(timeout=3)

    assert not worker.is_alive()
    assert [reservation.enforced for reservation in results] == [False]
