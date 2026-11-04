"""`GET backoffice/auth/me` qua `JWTAuthentication` với JWT thật (05 mục 2, 2.2, 4, 9)."""

import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import jwt
import pytest
import yaml
from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError, connection
from django.utils import timezone
from rest_framework.test import APIClient

from modules.identity.auth.tokens import issue_token_pair
from modules.identity.constants import AccountKind
from modules.identity.models import Account
from modules.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("jwt_keyring")]

ME_PATH = "/api/v1/backoffice/auth/me"
LOGIN_PATH = "/api/v1/backoffice/auth/login"
ACCOUNT_DTO_KEYS = {
    "id",
    "created_at",
    "updated_at",
    "email",
    "kind",
    "full_name",
    "phone",
    "language",
    "is_active",
    "email_verified",
}
ERROR_DTO_REF = {"$ref": "#/components/schemas/ErrorDTO"}


def _access_token(account: Account, *, audience: str | None = None, minutes_ago: int = 0) -> str:
    now = timezone.now() - timedelta(minutes=minutes_ago)
    audience = audience or settings.JWT_AUDIENCE_BACKOFFICE
    return issue_token_pair(account=account, audience=audience, now=now).access_token


def _get_me(token: str | None = None, *, header: str | None = None) -> Any:
    client = APIClient()
    if header is not None:
        client.credentials(HTTP_AUTHORIZATION=header)
    elif token is not None:
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client.get(ME_PATH)


def _b64(data: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _claims(token: str) -> dict[str, Any]:
    claims: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    return claims


@pytest.mark.usefixtures("allow_login_ledger")
@pytest.mark.parametrize("kind", [AccountKind.STAFF, AccountKind.ADMIN])
def test_login_access_token_reads_me(kind: str) -> None:
    account = AccountFactory.create(kind=kind, full_name="Nhân viên")
    login = APIClient().post(
        LOGIN_PATH, {"email": account.email, "password": DEFAULT_PASSWORD}, format="json"
    )

    response = _get_me(login.data["access_token"])

    assert response.status_code == 200
    assert set(response.data) == ACCOUNT_DTO_KEYS
    assert response.data["id"] == str(account.id)
    assert response.data["kind"] == kind
    assert response.data["email"] == account.email


@pytest.mark.parametrize(
    ("kind", "expected_status"),
    [
        (AccountKind.CUSTOMER, 403),
        (AccountKind.STAFF, 200),
        (AccountKind.ADMIN, 200),
    ],
)
def test_me_permission_by_kind(kind: str, expected_status: int) -> None:
    account = AccountFactory.create(kind=kind)

    response = _get_me(_access_token(account))

    assert response.status_code == expected_status


def test_me_rejects_anonymous() -> None:
    response = _get_me()

    assert response.status_code == 401
    assert response.data["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_rejects_store_audience_token() -> None:
    account = AccountFactory.create()

    response = _get_me(_access_token(account, audience="store"))

    assert response.status_code == 401
    assert response.data["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_rejects_refresh_token_as_bearer() -> None:
    account = AccountFactory.create()
    pair = issue_token_pair(
        account=account, audience=settings.JWT_AUDIENCE_BACKOFFICE, now=timezone.now()
    )

    response = _get_me(pair.refresh_token)

    assert response.status_code == 401
    assert response.data["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_rejects_hs256_token_signed_with_public_key(jwt_keyring: dict[str, Any]) -> None:
    account = AccountFactory.create()
    claims = _claims(_access_token(account))
    public_key = jwt_keyring["current"]["public_key"].encode()
    header = _b64({"alg": "HS256", "kid": "current", "typ": "JWT"})
    payload = _b64(claims)
    signing_input = f"{header}.{payload}".encode()
    signature = base64.urlsafe_b64encode(
        hmac.new(public_key, signing_input, hashlib.sha256).digest()
    ).rstrip(b"=")
    forged = f"{header}.{payload}.{signature.decode()}"

    response = _get_me(forged)

    assert response.status_code == 401


def test_me_rejects_alg_none_token() -> None:
    account = AccountFactory.create()
    claims = _claims(_access_token(account))
    forged = f"{_b64({'alg': 'none', 'kid': 'current'})}.{_b64(claims)}."

    response = _get_me(forged)

    assert response.status_code == 401


def test_me_rejects_unknown_kid() -> None:
    account = AccountFactory.create()
    token = _access_token(account)
    _header, payload, signature = token.split(".")
    forged = f"{_b64({'alg': 'EdDSA', 'kid': 'retired', 'typ': 'JWT'})}.{payload}.{signature}"

    response = _get_me(forged)

    assert response.status_code == 401


def test_me_rejects_expired_token_with_token_expired() -> None:
    account = AccountFactory.create()

    response = _get_me(_access_token(account, minutes_ago=60))

    assert response.status_code == 401
    assert response.data["error"]["code"] == "TOKEN_EXPIRED"


@pytest.mark.parametrize("header", ["Bearer", "Bearer a b", "Bearer not-a-jwt"])
def test_me_rejects_malformed_bearer_header(header: str) -> None:
    response = _get_me(header=header)

    assert response.status_code == 401
    assert response.data["error"]["code"] == "NOT_AUTHENTICATED"


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda a: setattr(a, "token_version", a.token_version + 1), id="tv"),
        pytest.param(lambda a: setattr(a, "is_active", False), id="inactive"),
        pytest.param(lambda a: setattr(a, "kind", AccountKind.ADMIN), id="kind"),
    ],
)
def test_me_reads_auth_state_from_db_each_request(change: Callable[[Account], None]) -> None:
    account = AccountFactory.create()
    token = _access_token(account)
    assert _get_me(token).status_code == 200
    change(account)
    account.save()

    response = _get_me(token)

    assert response.status_code == 401
    assert response.data["error"]["code"] == "NOT_AUTHENTICATED"


def test_me_rejects_token_of_deleted_account() -> None:
    account = AccountFactory.create()
    token = _access_token(account)
    account.delete()

    response = _get_me(token)

    assert response.status_code == 401


def test_me_returns_503_when_auth_state_unavailable() -> None:
    account = AccountFactory.create()
    token = _access_token(account)

    def fail_account_reads(execute: Any, sql: str, params: Any, many: bool, context: Any) -> Any:
        if "identity_account" in sql:
            raise OperationalError("database unavailable")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(fail_account_reads):
        response = _get_me(token)

    assert response.status_code == 503
    assert response.data["error"]["code"] == "AUTH_STATE_UNAVAILABLE"


@pytest.mark.usefixtures("allow_login_ledger")
def test_login_ignores_bearer_header() -> None:
    account = AccountFactory.create()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer not-a-jwt")

    response = client.post(
        LOGIN_PATH, {"email": account.email, "password": DEFAULT_PASSWORD}, format="json"
    )

    assert response.status_code == 200


@pytest.fixture(scope="module")
def openapi(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    file = tmp_path_factory.mktemp("openapi") / "openapi.yaml"
    call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(file))
    loaded: dict[str, Any] = yaml.safe_load(file.read_text(encoding="utf-8"))
    return loaded


def test_openapi_declares_me_auth_errors(openapi: dict[str, Any]) -> None:
    operation = openapi["paths"][ME_PATH]["get"]
    responses = operation["responses"]
    codes = list(responses)

    assert codes == ["200", "400", "401", "403", "429", "500", "503"]
    for code in ("401", "403", "503"):
        assert responses[code]["content"]["application/json"]["schema"] == ERROR_DTO_REF
    assert operation["security"] == [{"BackofficeBearer": []}]


def test_openapi_declares_login_errors(openapi: dict[str, Any]) -> None:
    responses = openapi["paths"][LOGIN_PATH]["post"]["responses"]
    codes = list(responses)

    assert codes == ["200", "400", "401", "429", "500"]
    assert responses["401"]["content"]["application/json"]["schema"] == ERROR_DTO_REF
