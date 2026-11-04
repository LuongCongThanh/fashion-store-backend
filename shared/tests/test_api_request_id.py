import json
import logging.config
from collections.abc import Iterator
from typing import Any

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from shared.tests._helpers import BFF_IP, BFF_SECRET, error_of

pytestmark = pytest.mark.urls("shared.tests.api_urls")

UPSTREAM_REQUEST_ID = "01JB8Z3K4M5N6P7Q8R9S0T1V2W"
MALFORMED_REQUEST_IDS = [("a" * 65, "too_long"), ("id with space", "invalid_chars")]


@pytest.fixture(autouse=True)
def _bff_secrets() -> Iterator[None]:
    with override_settings(BFF_SHARED_SECRETS=(BFF_SECRET,)):
        yield


@pytest.fixture
def get_domain_error(json_logging: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> Any:
    """Gọi route ném lỗi nghiệp vụ; trả `error`, các dòng log JSON và output thô.

    Log đọc qua chuỗi processor thật (`json_logging`, 12 mục 4): `request_id` do
    `merge_contextvars` gắn nên `capture_logs` (thay cả chuỗi processor) không thấy.
    """

    def call(**headers: Any) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
        # Cấu hình trong pha call: handler giữ stderr do capsys thay ở pha này
        logging.config.dictConfig(json_logging)
        response = APIClient().get("/domain-error", REMOTE_ADDR=BFF_IP, **headers)
        output = capsys.readouterr().err
        lines = [json.loads(line) for line in output.splitlines()]
        return error_of(response), lines, output

    return call


def request_ids_in(lines: list[dict[str, Any]]) -> set[str]:
    return {line["request_id"] for line in lines if "request_id" in line}


def invalid_warnings_in(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [line for line in lines if line["event"] == "request_id_invalid"]


@pytest.mark.parametrize("claimed", [UPSTREAM_REQUEST_ID, "a" * 64])
def test_trusted_request_id_is_used_in_error_and_logs(get_domain_error: Any, claimed: str) -> None:
    error, lines, _ = get_domain_error(HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_REQUEST_ID=claimed)

    assert error["request_id"] == claimed
    assert request_ids_in(lines) == {claimed}
    assert "request_started" in [line["event"] for line in lines]


@pytest.mark.parametrize(("claimed", "reason"), MALFORMED_REQUEST_IDS)
def test_malformed_request_id_is_replaced_and_logged_with_reason(
    get_domain_error: Any, claimed: str, reason: str
) -> None:
    error, lines, _ = get_domain_error(HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_REQUEST_ID=claimed)

    assert error["request_id"] != claimed
    assert request_ids_in(lines) == {error["request_id"]}
    warnings = invalid_warnings_in(lines)
    assert len(warnings) == 1
    assert warnings[0]["reason"] == reason


@pytest.mark.parametrize(("claimed", "reason"), MALFORMED_REQUEST_IDS)
def test_malformed_request_id_value_and_secret_are_not_logged(
    get_domain_error: Any, claimed: str, reason: str
) -> None:
    _, _, output = get_domain_error(HTTP_X_BFF_SECRET=BFF_SECRET, HTTP_X_REQUEST_ID=claimed)

    assert claimed not in output
    assert BFF_SECRET not in output


@pytest.mark.parametrize("headers", [{}, {"HTTP_X_REQUEST_ID": ""}])
def test_missing_or_empty_request_id_keeps_generated_id_without_warning(
    get_domain_error: Any, headers: dict[str, str]
) -> None:
    error, lines, _ = get_domain_error(HTTP_X_BFF_SECRET=BFF_SECRET, **headers)

    assert request_ids_in(lines) == {error["request_id"]}
    assert invalid_warnings_in(lines) == []


def test_request_id_header_ignored_when_bff_secret_missing(get_domain_error: Any) -> None:
    error, lines, _ = get_domain_error(HTTP_X_REQUEST_ID=UPSTREAM_REQUEST_ID)

    assert error["request_id"] != UPSTREAM_REQUEST_ID
    assert request_ids_in(lines) == {error["request_id"]}


@pytest.mark.parametrize("claimed", [UPSTREAM_REQUEST_ID, "id with space"])
def test_request_id_header_ignored_when_bff_secret_wrong(
    get_domain_error: Any, claimed: str
) -> None:
    error, lines, _ = get_domain_error(HTTP_X_BFF_SECRET="secret-wrong", HTTP_X_REQUEST_ID=claimed)

    assert error["request_id"] != claimed
    assert request_ids_in(lines) == {error["request_id"]}
    assert invalid_warnings_in(lines) == []
