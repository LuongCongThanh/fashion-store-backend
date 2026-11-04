"""Failure ledger giữ hạn mức khi nhiều request đăng nhập chạy đồng thời (05 mục 5, 12 mục 2.2)."""

import threading

import pytest
from redis import Redis

from modules.identity.auth.login_attempts import (
    EMAIL_LIMIT,
    LoginAttemptLedger,
    LoginRateLimited,
)
from modules.identity.tests.conftest import random_email, random_ip

THREADS = 20


@pytest.mark.concurrency
def test_parallel_reservations_never_exceed_email_limit(ledger_redis: Redis) -> None:
    ledger = LoginAttemptLedger(ledger_redis)
    email = random_email()
    barrier = threading.Barrier(THREADS)
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        client_ip = random_ip()
        barrier.wait()
        try:
            reservation = ledger.reserve(email=email, client_ip=client_ip)
            outcome = "reserved" if reservation.enforced else "fail-open"
        except LoginRateLimited:
            outcome = "limited"
        with lock:
            outcomes.append(outcome)

    workers = [threading.Thread(target=attempt) for _ in range(THREADS)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    actual = (outcomes.count("reserved"), outcomes.count("limited"))
    assert actual == (EMAIL_LIMIT, THREADS - EMAIL_LIMIT)
