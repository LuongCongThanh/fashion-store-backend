from collections.abc import Iterator
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient
from structlog.testing import capture_logs

from shared.api.throttling import AnonThrottle
from shared.privacy import pii_hmac
from shared.tests._helpers import BFF_IP, BFF_SECRET, CLIENT_IP, OLD_BFF_SECRET

pytestmark = pytest.mark.urls("shared.tests.api_urls")


@pytest.fixture(autouse=True)
def _bff_secrets() -> Iterator[None]:
    with override_settings(BFF_SHARED_SECRETS=(BFF_SECRET, OLD_BFF_SECRET)):
        yield


def throttle_view(**headers: Any) -> dict[str, str]:
    response = APIClient().get("/throttle-key", REMOTE_ADDR=BFF_IP, **headers)
    assert response.status_code == 200
    body: dict[str, str] = response.json()
    return body


def throttle_key(**headers: Any) -> str:
    return throttle_view(**headers)["key"]


def anon_key(ip: str) -> str:
    return f"throttle_anon_{pii_hmac(ip)}"


def test_missing_secret_uses_remote_addr() -> None:
    assert throttle_key(HTTP_X_CLIENT_IP=CLIENT_IP) == anon_key(BFF_IP)


def test_wrong_secret_uses_remote_addr() -> None:
    key = throttle_key(HTTP_X_BFF_SECRET="secret-wrong", HTTP_X_CLIENT_IP=CLIENT_IP)

    assert key == anon_key(BFF_IP)


def test_valid_secret_uses_x_client_ip() -> None:
    body = throttle_view(HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_CLIENT_IP=CLIENT_IP)

    assert body["client_ip"] == CLIENT_IP
    assert body["key"] == anon_key(CLIENT_IP)
    assert CLIENT_IP not in body["key"]


def test_second_secret_accepted() -> None:
    key = throttle_key(HTTP_X_BFF_SECRET=OLD_BFF_SECRET, HTTP_X_CLIENT_IP="2001:db8::1")

    assert key == anon_key("2001:db8::1")


def test_malformed_client_ip_uses_remote_addr_and_logs_without_value() -> None:
    with capture_logs() as logs:
        key = throttle_key(HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_CLIENT_IP="1.2.3.4, 5.6.7.8")

    assert key == anon_key(BFF_IP)
    warnings = [log for log in logs if log["event"] == "client_ip_invalid"]
    assert len(warnings) == 1
    assert "1.2.3.4" not in repr(logs)
    assert BFF_SECRET not in repr(logs)


def test_anon_quota_is_per_verified_client_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(AnonThrottle, "THROTTLE_RATES", {"anon": "2/min"})
    client = APIClient()

    def get(ip: str) -> int:
        response = client.get(
            "/paged", REMOTE_ADDR=BFF_IP, HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_CLIENT_IP=ip
        )
        return response.status_code

    assert [get(CLIENT_IP) for _ in range(3)] == [200, 200, 429]
    assert get("198.51.100.9") == 200
