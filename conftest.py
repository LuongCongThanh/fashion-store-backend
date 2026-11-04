"""Fixture pytest dùng chung (12 mục 4): fixture không cần nghiệp vụ và fixture cần Tài khoản.

Đặt ở gốc repo vì `common` không được import `apps.identity`.
"""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
import structlog
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.identity.auth.tokens import issue_token_pair
from apps.identity.models import Account
from apps.identity.tests.factories import AccountFactory, jwt_test_keyring
from common.observability.logging import configure_logging


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    # Bộ đếm throttle nằm trong cache: không để hạn mức của test này ảnh hưởng test khác
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def json_logging() -> Iterator[dict[str, Any]]:
    """Cấu hình structlog như production (log JSON); trả dict `LOGGING` để test `dictConfig`."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield configure_logging(json=True)
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()


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
