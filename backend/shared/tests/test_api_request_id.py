import logging
from collections.abc import Iterator
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from shared.tests._helpers import BFF_IP, BFF_SECRET, error_of

pytestmark = pytest.mark.urls("shared.tests.api_urls")

UPSTREAM_REQUEST_ID = "01JB8Z3K4M5N6P7Q8R9S0T1V2W"


@pytest.fixture(autouse=True)
def _bff_secrets() -> Iterator[None]:
    with override_settings(BFF_SHARED_SECRETS=(BFF_SECRET,)):
        yield


def get_domain_error(
    caplog: pytest.LogCaptureFixture, **headers: Any
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Gọi route ném lỗi nghiệp vụ; trả `error` và event dict của mọi log structlog.

    Đọc qua `caplog` thay vì `capture_logs`: logger của structlog được cache ở lần dùng đầu
    (`cache_logger_on_first_use`), nên logger mà test khác cùng worker đã dùng sẽ không vào
    `capture_logs`. `record.msg` là event dict đã gộp contextvars, có `request_id`.
    """
    caplog.set_level(logging.INFO)
    response = APIClient().get("/domain-error", REMOTE_ADDR=BFF_IP, **headers)
    logs = [record.msg for record in caplog.records if isinstance(record.msg, dict)]
    return error_of(response), logs


def request_ids_in(logs: list[dict[str, Any]]) -> set[str]:
    return {log["request_id"] for log in logs if "request_id" in log}


def test_trusted_request_id_is_used_in_error_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    error, logs = get_domain_error(
        caplog, HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_REQUEST_ID=UPSTREAM_REQUEST_ID
    )

    assert error["request_id"] == UPSTREAM_REQUEST_ID
    assert request_ids_in(logs) == {UPSTREAM_REQUEST_ID}
    assert "request_started" in [log["event"] for log in logs]


@pytest.mark.parametrize("claimed", ["a" * 65, "id with space", "id;drop"])
def test_malformed_request_id_is_replaced_and_logged_without_value(
    caplog: pytest.LogCaptureFixture, claimed: str
) -> None:
    error, logs = get_domain_error(caplog, HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_REQUEST_ID=claimed)

    assert error["request_id"] != claimed
    assert request_ids_in(logs) == {error["request_id"]}
    warnings = [log for log in logs if log["event"] == "request_id_invalid"]
    assert len(warnings) == 1
    assert claimed not in repr(warnings)
    assert BFF_SECRET not in repr(logs)


def test_request_id_header_ignored_when_bff_secret_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error, logs = get_domain_error(caplog, HTTP_X_REQUEST_ID=UPSTREAM_REQUEST_ID)

    assert error["request_id"] != UPSTREAM_REQUEST_ID
    assert request_ids_in(logs) == {error["request_id"]}


def test_request_id_header_ignored_when_bff_secret_wrong(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error, logs = get_domain_error(
        caplog, HTTP_X_BFF_SECRET="secret-wrong", HTTP_X_REQUEST_ID=UPSTREAM_REQUEST_ID
    )

    assert error["request_id"] != UPSTREAM_REQUEST_ID
    assert request_ids_in(logs) == {error["request_id"]}
