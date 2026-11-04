"""Fixture riêng của test identity: failure ledger trên Redis thật và ledger giả."""

import ipaddress
import uuid
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import pytest
from redis import Redis

from modules.identity.api.backoffice import views
from modules.identity.auth.login_attempts import LoginReservation

# DB Redis riêng cho test ledger, không lẫn key với cache/broker của máy dev
LEDGER_TEST_REDIS_DB = 15


class AllowLedger:
    """Ledger giả luôn cho thử mật khẩu; dùng khi test không kiểm hạn mức (05 mục 5)."""

    def reserve(self, *, email: str, client_ip: str) -> LoginReservation:
        return LoginReservation(
            attempt_id="allow", email_key="allow", ip_key="allow", enforced=False
        )

    def complete_failure(self, reservation: LoginReservation) -> None:
        pass

    def complete_success(self, reservation: LoginReservation) -> None:
        pass

    def release(self, reservation: LoginReservation) -> None:
        pass


@pytest.fixture
def allow_login_ledger(monkeypatch: pytest.MonkeyPatch) -> AllowLedger:
    """View đăng nhập dùng `AllowLedger` thay Redis."""
    ledger = AllowLedger()
    monkeypatch.setattr(views, "get_login_ledger", lambda: ledger)
    return ledger


@pytest.fixture
def ledger_redis(settings: Any) -> Redis:
    """Redis thật cho failure ledger (12 mục 2.2); `settings.REDIS_URL` trỏ vào DB riêng.

    Không flush DB: test chạy song song qua pytest-xdist, mỗi test dùng email/IP ngẫu nhiên nên
    key không trùng; key tự hết hạn sau cửa sổ 15 phút.
    """
    parts = urlsplit(settings.REDIS_URL)
    settings.REDIS_URL = urlunsplit(parts._replace(path=f"/{LEDGER_TEST_REDIS_DB}"))
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def random_email() -> str:
    return f"login-{uuid.uuid4().hex}@example.com"


def random_ip() -> str:
    # 10.0.0.0/8: dải private, không trùng IP thật
    return str(ipaddress.IPv4Address(0x0A000000 | (uuid.uuid4().int & 0xFFFFFF)))


@pytest.fixture
def bff_headers(settings: Any) -> dict[str, str]:
    """Header BFF hợp lệ kèm IP ngẫu nhiên để hạn mức theo IP không dính giữa các test."""
    return {
        "HTTP_X_BFF_SECRET": settings.BFF_SHARED_SECRETS[0],
        "HTTP_X_CLIENT_IP": random_ip(),
    }
