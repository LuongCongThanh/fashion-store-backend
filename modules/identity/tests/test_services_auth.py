"""Service `login_backoffice` (05 mục 3, 5; 03 mục 2.4)."""

import hashlib

import jwt
import pytest
from django.contrib.auth.hashers import MD5PasswordHasher
from structlog.testing import capture_logs

from modules.identity.exceptions import InvalidCredentials
from modules.identity.models import RefreshToken
from modules.identity.services.auth import login_backoffice
from modules.identity.tests.conftest import AllowLedger
from modules.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("jwt_keyring")]

CLIENT_IP = "198.51.100.7"


def test_login_stores_refresh_hash_and_family_without_logging_tokens() -> None:
    account = AccountFactory.create()

    with capture_logs() as logs:
        pair = login_backoffice(
            email=account.email,
            password=DEFAULT_PASSWORD,
            client_ip=CLIENT_IP,
            ledger=AllowLedger(),
        )

    stored = RefreshToken.objects.get(account=account)
    refresh_claims = jwt.decode(pair.refresh_token, options={"verify_signature": False})
    assert stored.token_hash == hashlib.sha256(pair.refresh_token.encode()).hexdigest()
    assert stored.jti == pair.refresh_jti
    assert str(stored.family_id) == refresh_claims["fam"]
    assert stored.expires_at == pair.refresh_expires_at
    logged = repr(logs)
    assert pair.refresh_token not in logged
    assert pair.access_token not in logged


def test_missing_email_runs_same_password_hashing_work_as_existing_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Settings test chỉ dùng MD5PasswordHasher: đếm số lần băm thay cho đo thời gian thật
    account = AccountFactory.create()
    encode_calls: list[str] = []
    original_encode = MD5PasswordHasher.encode

    def counting_encode(self: MD5PasswordHasher, password: str, salt: str) -> str:
        encode_calls.append(password)
        return original_encode(self, password, salt)

    monkeypatch.setattr(MD5PasswordHasher, "encode", counting_encode)
    ledger = AllowLedger()

    with pytest.raises(InvalidCredentials):
        login_backoffice(
            email="missing@example.com", password="Guess-2026", client_ip=CLIENT_IP, ledger=ledger
        )
    missing_calls = len(encode_calls)
    encode_calls.clear()
    with pytest.raises(InvalidCredentials):
        login_backoffice(
            email=account.email, password="Guess-2026", client_ip=CLIENT_IP, ledger=ledger
        )

    existing_calls = len(encode_calls)
    assert missing_calls == existing_calls
