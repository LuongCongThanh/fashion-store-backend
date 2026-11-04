import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.identity.models import RefreshReplay, RefreshToken
from modules.identity.tests.factories import AccountFactory

pytestmark = pytest.mark.django_db


def test_refresh_token_accepts_family_root() -> None:
    account = AccountFactory.create()
    token = RefreshToken.objects.create(
        jti=uuid.uuid4(),
        account=account,
        family_id=uuid.uuid4(),
        token_hash="a" * 64,
        expires_at=timezone.now() + timedelta(hours=12),
    )

    assert token.used_at is None
    assert token.successor is None
    assert token.revoked_at is None


def test_refresh_token_rejects_successor_without_used_at() -> None:
    account = AccountFactory.create()
    successor = RefreshToken.objects.create(
        jti=uuid.uuid4(),
        account=account,
        family_id=uuid.uuid4(),
        token_hash="b" * 64,
        expires_at=timezone.now() + timedelta(hours=12),
    )

    with pytest.raises(IntegrityError):
        RefreshToken.objects.create(
            jti=uuid.uuid4(),
            account=account,
            family_id=successor.family_id,
            token_hash="c" * 64,
            expires_at=successor.expires_at,
            successor=successor,
        )


def test_refresh_replay_is_unique_per_parent() -> None:
    account = AccountFactory.create()
    parent = RefreshToken.objects.create(
        jti=uuid.uuid4(),
        account=account,
        family_id=uuid.uuid4(),
        token_hash="d" * 64,
        expires_at=timezone.now() + timedelta(hours=12),
    )
    values = {
        "parent": parent,
        "encryption_key_id": "key-1",
        "nonce": b"0" * 12,
        "response_ciphertext": b"ciphertext",
        "expires_at": timezone.now() + timedelta(seconds=10),
    }
    RefreshReplay.objects.create(**values)

    with pytest.raises(IntegrityError):
        RefreshReplay.objects.create(**values)
