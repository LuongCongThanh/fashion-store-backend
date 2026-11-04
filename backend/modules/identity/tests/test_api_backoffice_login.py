"""`POST backoffice/auth/login` (04 mục 4.2, 05 mục 3, 5)."""

import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
import pytest
import time_machine
from django.db import OperationalError, connection
from rest_framework.test import APIClient

from modules.identity.constants import AccountKind
from modules.identity.models import RefreshReplay, RefreshToken
from modules.identity.tests.conftest import random_email
from modules.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("jwt_keyring")]

LOGIN_PATH = "/api/v1/backoffice/auth/login"
WRONG_PASSWORD = "Wrong-Password-2026"
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


def _login(email: str, password: str, **headers: str) -> Any:
    client = APIClient()
    client.credentials(**headers)
    return client.post(LOGIN_PATH, {"email": email, "password": password}, format="json")


@pytest.mark.usefixtures("allow_login_ledger")
@pytest.mark.parametrize("kind", [AccountKind.STAFF, AccountKind.ADMIN])
def test_backoffice_login_returns_token_pair(kind: str) -> None:
    account = AccountFactory.create(kind=kind)

    response = _login(account.email, DEFAULT_PASSWORD)

    assert response.status_code == 200
    assert set(response.data) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert response.data["token_type"] == "Bearer"
    assert response.data["expires_in"] == 600
    assert RefreshToken.objects.filter(account=account).count() == 1
    assert RefreshReplay.objects.count() == 0


def _rejected_login(case: str) -> Any:
    account = AccountFactory.create(
        kind=AccountKind.CUSTOMER if case == "customer" else AccountKind.STAFF,
        is_active=case != "inactive",
    )
    email = "missing@example.com" if case == "missing" else account.email
    password = WRONG_PASSWORD if case == "wrong" else DEFAULT_PASSWORD
    return _login(email, password)


@pytest.mark.usefixtures("allow_login_ledger")
def test_backoffice_login_rejects_every_case_with_same_body() -> None:
    cases = ["customer", "inactive", "wrong", "missing"]

    responses = [_rejected_login(case) for case in cases]

    statuses = [response.status_code for response in responses]
    assert statuses == [401, 401, 401, 401]
    # request_id khác nhau theo request; phần còn lại của body phải giống hệt nhau
    bodies = [{**response.data["error"], "request_id": None} for response in responses]
    assert bodies == [bodies[0]] * len(cases)
    assert bodies[0]["code"] == "INVALID_CREDENTIALS"
    assert RefreshToken.objects.count() == 0


@pytest.mark.usefixtures("ledger_redis")
def test_login_rate_limited_after_five_failures_with_retry_after(
    bff_headers: dict[str, str],
) -> None:
    account = AccountFactory.create(email=random_email())
    # BFF gửi lại cùng X-Request-ID: ledger vẫn phải đếm từng lần thử riêng
    headers = {**bff_headers, "HTTP_X_REQUEST_ID": str(uuid.uuid4())}

    with time_machine.travel(NOW, tick=False):
        failures = [_login(account.email, WRONG_PASSWORD, **headers) for _ in range(5)]
        response = _login(account.email, DEFAULT_PASSWORD, **headers)

    assert [failure.status_code for failure in failures] == [401] * 5
    assert response.status_code == 429
    assert response["Retry-After"] == "900"
    assert response.data["error"]["code"] == "THROTTLED"


@pytest.mark.usefixtures("ledger_redis")
@pytest.mark.parametrize("case", ["customer", "missing"])
def test_login_counts_customer_and_missing_email_as_failure(
    case: str, bff_headers: dict[str, str]
) -> None:
    kind = AccountKind.CUSTOMER if case == "customer" else AccountKind.STAFF
    account = AccountFactory.create(email=random_email(), kind=kind)
    email = random_email() if case == "missing" else account.email

    with time_machine.travel(NOW, tick=False):
        failures = [_login(email, DEFAULT_PASSWORD, **bff_headers) for _ in range(5)]
        response = _login(email, DEFAULT_PASSWORD, **bff_headers)

    assert [failure.status_code for failure in failures] == [401] * 5
    assert response.status_code == 429


@pytest.mark.usefixtures("ledger_redis")
def test_login_issues_token_for_configured_backoffice_audience(
    settings: Any, bff_headers: dict[str, str]
) -> None:
    settings.JWT_AUDIENCE_BACKOFFICE = "backoffice-test"
    account = AccountFactory.create(email=random_email())

    response = _login(account.email, DEFAULT_PASSWORD, **bff_headers)

    claims = jwt.decode(response.data["access_token"], options={"verify_signature": False})
    assert claims["aud"] == "backoffice-test"


@pytest.mark.usefixtures("ledger_redis")
def test_login_server_error_does_not_hold_reservation(bff_headers: dict[str, str]) -> None:
    account = AccountFactory.create(email=random_email())

    def fail_refresh_insert(execute: Any, sql: str, params: Any, many: bool, ctx: Any) -> Any:
        if sql.startswith("INSERT") and "identity_refresh_token" in sql:
            raise OperationalError("database unavailable")
        return execute(sql, params, many, ctx)

    # Lỗi 500 liên tiếp (DB lỗi khi lưu refresh token) không được khoá email
    with connection.execute_wrapper(fail_refresh_insert):
        for _ in range(5):
            with pytest.raises(OperationalError):
                _login(account.email, DEFAULT_PASSWORD, **bff_headers)
    response = _login(account.email, DEFAULT_PASSWORD, **bff_headers)

    assert response.status_code == 200
