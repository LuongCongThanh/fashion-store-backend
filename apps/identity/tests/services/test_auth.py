"""Service `login_backoffice` (05 mục 3, 5; 03 mục 2.4)."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
import time_machine
from django.contrib.auth.hashers import MD5PasswordHasher
from structlog.testing import capture_logs

from apps.identity.auth.tokens import IssuedTokenPair, TokenPairDTO
from apps.identity.constants import AccountKind
from apps.identity.exceptions import (
    InvalidCredentials,
    RefreshExpired,
    RefreshRejected,
    RefreshReplayUnavailable,
    RefreshSuperseded,
)
from apps.identity.models import Account, RefreshReplay, RefreshToken
from apps.identity.services.auth import login_backoffice, logout_session, refresh_session
from apps.identity.tests.conftest import AllowLedger
from apps.identity.tests.factories import DEFAULT_PASSWORD, AccountFactory, stored_refresh_session

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
    assert str(stored.jti) == refresh_claims["jti"]
    assert str(stored.family_id) == refresh_claims["fam"]
    assert int(stored.expires_at.timestamp()) == refresh_claims["exp"]
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


AUDIENCE = "backoffice"


LOGIN_AT = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


FIRST_REFRESH_AT = LOGIN_AT + timedelta(minutes=9)


REPLAY_WINDOW = timedelta(seconds=10)


@pytest.fixture(autouse=True)
def replay_key(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = "test-replay-1"
    settings.REFRESH_REPLAY_KEY = os.urandom(32)


@pytest.fixture
def account() -> Account:
    return AccountFactory.create()


@pytest.fixture
def login(account: Account) -> IssuedTokenPair:
    return stored_refresh_session(account=account, now=LOGIN_AT)


def _refresh(refresh_token: str, *, at: datetime) -> TokenPairDTO:
    with time_machine.travel(at, tick=False):
        return refresh_session(refresh_token=refresh_token, audience=AUDIENCE, now=at)


def _jti(token: str) -> str:
    return str(jwt.decode(token, options={"verify_signature": False})["jti"])


def test_first_refresh_issues_successor_and_marks_parent(login: IssuedTokenPair) -> None:
    with capture_logs() as logs:
        pair = _refresh(login.refresh_token, at=FIRST_REFRESH_AT)

    parent = RefreshToken.objects.get(jti=login.refresh_jti)
    successor = RefreshToken.objects.get(jti=_jti(pair.refresh_token))
    assert parent.used_at == FIRST_REFRESH_AT
    assert parent.successor_id == successor.jti
    assert successor.family_id == login.family_id
    assert successor.token_hash == hashlib.sha256(pair.refresh_token.encode()).hexdigest()
    assert (successor.used_at, successor.revoked_at) == (None, None)
    replay = RefreshReplay.objects.get(parent=parent)
    assert replay.expires_at == FIRST_REFRESH_AT + REPLAY_WINDOW
    assert replay.encryption_key_id == "test-replay-1"
    assert pair.refresh_token.encode() not in bytes(replay.response_ciphertext)
    logged = repr(logs)
    assert pair.refresh_token not in logged
    assert login.refresh_token not in logged


def test_retry_inside_window_returns_same_pair_without_extending(login: IssuedTokenPair) -> None:
    first = _refresh(login.refresh_token, at=FIRST_REFRESH_AT)

    retried = _refresh(login.refresh_token, at=FIRST_REFRESH_AT + timedelta(seconds=5))
    retried_again = _refresh(login.refresh_token, at=FIRST_REFRESH_AT + timedelta(seconds=9))

    assert retried == first
    assert retried_again == first
    assert RefreshToken.objects.filter(family_id=login.family_id).count() == 2
    replay = RefreshReplay.objects.get(parent__jti=login.refresh_jti)
    assert replay.expires_at == FIRST_REFRESH_AT + REPLAY_WINDOW


def test_retry_after_successor_used_raises_superseded(login: IssuedTokenPair) -> None:
    second = _refresh(login.refresh_token, at=FIRST_REFRESH_AT)
    _refresh(second.refresh_token, at=FIRST_REFRESH_AT + timedelta(seconds=1))

    with pytest.raises(RefreshSuperseded):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT + timedelta(seconds=2))

    revoked = RefreshToken.objects.filter(family_id=login.family_id, revoked_at__isnull=False)
    assert revoked.count() == 0


def test_reuse_outside_window_revokes_family(account: Account, login: IssuedTokenPair) -> None:
    other_family = stored_refresh_session(account=account, now=LOGIN_AT)
    _refresh(login.refresh_token, at=FIRST_REFRESH_AT)
    reused_at = FIRST_REFRESH_AT + REPLAY_WINDOW

    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=reused_at)

    family = RefreshToken.objects.filter(family_id=login.family_id)
    assert {token.revoked_at for token in family} == {reused_at}
    assert not RefreshReplay.objects.filter(parent__family_id=login.family_id).exists()
    other = RefreshToken.objects.get(jti=other_family.refresh_jti)
    assert other.revoked_at is None


def test_revoked_family_is_rejected(login: IssuedTokenPair) -> None:
    RefreshToken.revoke_family(login.family_id, now=LOGIN_AT)

    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT)

    assert RefreshToken.objects.filter(family_id=login.family_id).count() == 1


def _deactivate(account: Account) -> None:
    account.is_active = False


def _bump_token_version(account: Account) -> None:
    account.token_version += 1


def _promote(account: Account) -> None:
    account.kind = AccountKind.ADMIN


@pytest.mark.parametrize("change", [_deactivate, _bump_token_version, _promote])
def test_inactive_account_or_stale_token_version_is_rejected(
    account: Account, login: IssuedTokenPair, change: Any
) -> None:
    change(account)
    account.save()

    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT)

    parent = RefreshToken.objects.get(jti=login.refresh_jti)
    assert (parent.used_at, parent.successor_id) == (None, None)


def test_tampered_hash_is_rejected(login: IssuedTokenPair) -> None:
    RefreshToken.objects.filter(jti=login.refresh_jti).update(token_hash="0" * 64)

    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT)


def test_expired_token_raises_expired(login: IssuedTokenPair) -> None:
    with pytest.raises(RefreshExpired):
        _refresh(login.refresh_token, at=LOGIN_AT + timedelta(hours=13))


def test_unknown_jti_is_rejected(login: IssuedTokenPair) -> None:
    RefreshToken.objects.filter(jti=login.refresh_jti).delete()

    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT)


def _delete_replay(settings: Any) -> None:
    RefreshReplay.objects.all().delete()


def _tamper_replay(settings: Any) -> None:
    replay = RefreshReplay.objects.get()
    replay.response_ciphertext = b"\x00" + bytes(replay.response_ciphertext)[1:]
    replay.save()


def _rotate_key(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = "test-replay-2"
    settings.REFRESH_REPLAY_KEY = os.urandom(32)


def _drop_key(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = ""
    settings.REFRESH_REPLAY_KEY = b""


@pytest.mark.parametrize("damage", [_delete_replay, _tamper_replay, _rotate_key, _drop_key])
def test_missing_replay_inside_window_raises_unavailable(
    settings: Any, login: IssuedTokenPair, damage: Any
) -> None:
    _refresh(login.refresh_token, at=FIRST_REFRESH_AT)
    damage(settings)

    with pytest.raises(RefreshReplayUnavailable):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT + timedelta(seconds=5))

    family = RefreshToken.objects.filter(family_id=login.family_id)
    assert family.count() == 2
    assert not family.filter(revoked_at__isnull=False).exists()


def test_missing_key_on_first_refresh_issues_nothing(settings: Any, login: IssuedTokenPair) -> None:
    _drop_key(settings)

    with pytest.raises(RefreshReplayUnavailable):
        _refresh(login.refresh_token, at=FIRST_REFRESH_AT)

    parent = RefreshToken.objects.get(jti=login.refresh_jti)
    assert (parent.used_at, parent.successor_id) == (None, None)
    assert RefreshToken.objects.filter(family_id=login.family_id).count() == 1
    assert not RefreshReplay.objects.exists()


def _logout(refresh_token: str, *, at: datetime) -> None:
    with time_machine.travel(at, tick=False):
        logout_session(refresh_token=refresh_token, audience=AUDIENCE, now=at)


def test_logout_revokes_family_and_deletes_replay(account: Account, login: IssuedTokenPair) -> None:
    other_family = stored_refresh_session(account=account, now=LOGIN_AT)
    second = _refresh(login.refresh_token, at=FIRST_REFRESH_AT)
    logout_at = FIRST_REFRESH_AT + timedelta(seconds=3)

    _logout(second.refresh_token, at=logout_at)

    family = RefreshToken.objects.filter(family_id=login.family_id)
    assert {token.revoked_at for token in family} == {logout_at}
    assert not RefreshReplay.objects.filter(parent__family_id=login.family_id).exists()
    assert RefreshToken.objects.get(jti=other_family.refresh_jti).revoked_at is None
    account.refresh_from_db()
    assert account.token_version == 0
    with pytest.raises(RefreshRejected):
        _refresh(login.refresh_token, at=logout_at + timedelta(seconds=1))


def test_logout_is_idempotent_and_accepts_expired_token(login: IssuedTokenPair) -> None:
    expired_at = LOGIN_AT + timedelta(hours=13)

    _logout(login.refresh_token, at=expired_at)
    _logout(login.refresh_token, at=expired_at + timedelta(minutes=1))

    parent = RefreshToken.objects.get(jti=login.refresh_jti)
    assert parent.revoked_at == expired_at
    RefreshToken.objects.all().delete()
    _logout(login.refresh_token, at=expired_at + timedelta(minutes=2))


def test_logout_rejects_access_token(login: IssuedTokenPair) -> None:
    with pytest.raises(RefreshRejected):
        _logout(login.access_token, at=FIRST_REFRESH_AT)

    assert RefreshToken.objects.get(jti=login.refresh_jti).revoked_at is None
