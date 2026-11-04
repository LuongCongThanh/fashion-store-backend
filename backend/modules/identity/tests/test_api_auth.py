from typing import Any
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import override_settings
from rest_framework.test import APIClient

from modules.identity.constants import AccountKind
from modules.identity.models import RefreshReplay, RefreshToken
from modules.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory

pytestmark = pytest.mark.django_db


class AllowLedger:
    def reserve(self, **kwargs: object) -> object:
        return object()

    def complete_failure(self, reservation: object) -> None:
        pass

    def complete_success(self, reservation: object) -> None:
        pass


def _keyring() -> dict[str, dict[str, str]]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return {"current": {"private_key": private_pem, "public_key": public_pem}}


@pytest.fixture(autouse=True)
def auth_settings(settings: Any) -> None:
    settings.JWT_SIGNING_KEYS = _keyring()


@override_settings(ROOT_URLCONF="config.urls")
@pytest.mark.parametrize("kind", [AccountKind.STAFF, AccountKind.ADMIN])
def test_backoffice_login_returns_token_pair(kind: str) -> None:
    account = AccountFactory.create(kind=kind)

    with patch(
        "modules.identity.api.backoffice.views.get_login_ledger", return_value=AllowLedger()
    ):
        response = APIClient().post(
            "/api/v1/backoffice/auth/login",
            {"email": account.email, "password": DEFAULT_PASSWORD},
            format="json",
        )

    assert response.status_code == 200
    assert set(response.data) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert response.data["token_type"] == "Bearer"
    refresh = RefreshToken.objects.get(account=account)
    assert refresh.token_hash not in {response.data["refresh_token"], ""}
    assert RefreshReplay.objects.count() == 0


@override_settings(ROOT_URLCONF="config.urls")
@pytest.mark.parametrize("case", ["customer", "inactive", "wrong", "missing"])
def test_backoffice_login_rejects_with_same_error(case: str) -> None:
    account = AccountFactory.create(
        kind=AccountKind.CUSTOMER if case == "customer" else AccountKind.STAFF,
        is_active=case != "inactive",
    )
    email = "missing@example.com" if case == "missing" else account.email
    password = "Wrong-Password-2026" if case == "wrong" else DEFAULT_PASSWORD

    with patch(
        "modules.identity.api.backoffice.views.get_login_ledger", return_value=AllowLedger()
    ):
        response = APIClient().post(
            "/api/v1/backoffice/auth/login",
            {"email": email, "password": password},
            format="json",
        )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_CREDENTIALS"
    assert RefreshToken.objects.count() == 0
