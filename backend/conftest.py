"""Fixture cần Tài khoản (12 mục 4): `shared` không được import `modules.identity`."""

from typing import Any

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from modules.identity.auth.tokens import issue_token_pair
from modules.identity.models import Account
from modules.identity.tests.factories import AccountFactory, jwt_test_keyring

pytest_plugins = ["shared.testing.fixtures"]


@pytest.fixture
def jwt_keyring(settings: Any) -> dict[str, dict[str, str]]:
    """Keyring JWT riêng của test; mọi token trong test ký và xác minh bằng keyring này."""
    keyring = jwt_test_keyring()
    settings.JWT_SIGNING_KEYS = keyring
    return keyring


def _backoffice_client(account: Account) -> APIClient:
    # Access token thật qua JWTAuthentication, không force_authenticate (05 mục 9)
    pair = issue_token_pair(
        account=account, audience=settings.JWT_AUDIENCE_BACKOFFICE, now=timezone.now()
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {pair.access_token}")
    return client


@pytest.fixture
def staff_client(db: None, jwt_keyring: dict[str, dict[str, str]]) -> APIClient:
    """Client của một Staff."""
    return _backoffice_client(AccountFactory.create())


@pytest.fixture
def admin_client(db: None, jwt_keyring: dict[str, dict[str, str]]) -> APIClient:
    """Client của một Admin."""
    return _backoffice_client(AccountFactory.create(admin=True))
