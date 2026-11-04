from typing import Any

from modules.identity.auth.login_attempts import LoginAttemptLedger


class BrokenRedis:
    def register_script(self, script: str) -> Any:
        def run(*, keys: list[str], args: list[object]) -> object:
            raise ConnectionError

        return run


def test_failure_ledger_fail_open_when_redis_is_unavailable() -> None:
    ledger = LoginAttemptLedger(BrokenRedis())

    reservation = ledger.reserve(
        email=" Staff@Example.COM ", client_ip="127.0.0.1", request_id="request-1"
    )
    ledger.complete_failure(reservation)
    ledger.complete_success(reservation)

    assert reservation.enforced is False
    assert "staff@example.com" not in reservation.email_key
    assert "127.0.0.1" not in reservation.ip_key


def test_failure_ledger_lua_never_contains_identifier() -> None:
    ledger = LoginAttemptLedger(BrokenRedis())

    reservation = ledger.reserve(
        email="staff@example.com", client_ip="203.0.113.8", request_id="request-2"
    )

    assert reservation.email_key.startswith("login:{")
    assert reservation.ip_key.startswith("login:{")
    assert "staff@example.com" not in ledger.reserve_script
    assert "203.0.113.8" not in ledger.reserve_script
