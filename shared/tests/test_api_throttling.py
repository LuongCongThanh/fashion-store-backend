import json
import logging.config
from types import SimpleNamespace
from typing import Any

import pytest
import redis.exceptions
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView
from structlog.testing import capture_logs

from shared.api.throttling import AccountThrottle, AnonThrottle
from shared.privacy import pii_hmac
from shared.tests._helpers import BFF_IP, BFF_SECRET, CLIENT_IP, drf_request


def test_account_throttle_keys_authenticated_user_by_pk() -> None:
    request = drf_request(SimpleNamespace(pk=42, is_authenticated=True))

    assert AccountThrottle().get_cache_key(request, APIView()) == "throttle_account_42"
    assert AnonThrottle().get_cache_key(request, APIView()) is None


def test_account_throttle_ignores_anonymous() -> None:
    assert AccountThrottle().get_cache_key(drf_request(), APIView()) is None


class DownCache:
    """Cache giả như RedisCache khi Redis tắt: mọi thao tác ném lỗi kết nối."""

    def get(self, *args: Any, **kwargs: Any) -> Any:
        raise redis.exceptions.ConnectionError("Error 111 connecting to redis:6379")

    set = get


@pytest.fixture
def cache_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SimpleRateThrottle, "cache", DownCache())


@pytest.mark.urls("shared.tests.api_urls")
@pytest.mark.usefixtures("cache_down")
def test_cache_down_allows_request_and_logs_without_ip() -> None:
    with override_settings(BFF_SHARED_SECRETS=(BFF_SECRET,)), capture_logs() as logs:
        response = APIClient().get(
            "/paged", REMOTE_ADDR=BFF_IP, HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_CLIENT_IP=CLIENT_IP
        )

    assert response.status_code == 200
    warnings = [log for log in logs if log["event"] == "throttle_backend_unavailable"]
    assert warnings == [
        {"event": "throttle_backend_unavailable", "scope": "anon", "log_level": "warning"}
    ]
    for raw in (CLIENT_IP, BFF_IP, pii_hmac(CLIENT_IP), "throttle_anon"):
        assert raw not in repr(logs)


@pytest.mark.urls("shared.tests.api_urls")
@pytest.mark.usefixtures("cache_down")
def test_cache_down_allows_authenticated_request() -> None:
    client = APIClient()
    user: Any = SimpleNamespace(pk=42, is_authenticated=True)
    client.force_authenticate(user=user)

    with capture_logs() as logs:
        response = client.get("/paged")

    assert response.status_code == 200
    warnings = [log for log in logs if log["event"] == "throttle_backend_unavailable"]
    assert warnings == [
        {"event": "throttle_backend_unavailable", "scope": "account", "log_level": "warning"}
    ]
    assert "throttle_account_42" not in repr(logs)


@pytest.mark.urls("shared.tests.api_urls")
@pytest.mark.usefixtures("cache_down")
def test_cache_down_json_log_has_no_raw_ip(
    json_logging: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    # Chạy qua chuỗi processor thật (có merge_contextvars), không thay bằng capture_logs:
    # middleware của django-structlog gắn contextvars mà dòng log nào cũng mang theo
    logging.config.dictConfig(json_logging)

    with override_settings(BFF_SHARED_SECRETS=(BFF_SECRET,)):
        response = APIClient().get(
            "/paged", REMOTE_ADDR=BFF_IP, HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_CLIENT_IP=CLIENT_IP
        )

    assert response.status_code == 200
    output = capsys.readouterr().err
    lines = [json.loads(line) for line in output.splitlines()]
    warnings = [line for line in lines if line["event"] == "throttle_backend_unavailable"]
    assert len(warnings) == 1
    assert warnings[0]["scope"] == "anon"
    # Cả dòng cảnh báo lẫn log request_started/finished của request đều không có IP thô
    for raw in (CLIENT_IP, BFF_IP):
        assert raw not in output
