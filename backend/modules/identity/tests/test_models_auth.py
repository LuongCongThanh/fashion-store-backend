"""Persistence cho vòng đời refresh token (03 mục 2.4-2.5)."""

from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.identity.models import RefreshReplay
from modules.identity.tests.factories import RefreshTokenFactory

pytestmark = pytest.mark.django_db


def test_refresh_token_accepts_family_root() -> None:
    token = RefreshTokenFactory.create()

    actual = (token.used_at, token.successor, token.revoked_at)
    assert actual == (None, None, None)


def test_refresh_token_rejects_successor_without_used_at() -> None:
    successor = RefreshTokenFactory.create()
    parent = RefreshTokenFactory.build(
        account=successor.account, family_id=successor.family_id, successor=successor
    )

    with pytest.raises(IntegrityError, match="identity_refresh_successor_requires_used"):
        parent.save()


def test_refresh_token_successor_is_unique() -> None:
    successor = RefreshTokenFactory.create()
    RefreshTokenFactory.create(
        account=successor.account,
        family_id=successor.family_id,
        used_at=timezone.now(),
        successor=successor,
    )
    second_parent = RefreshTokenFactory.build(
        account=successor.account,
        family_id=successor.family_id,
        used_at=timezone.now(),
        successor=successor,
    )

    with pytest.raises(IntegrityError, match="successor_jti"):
        second_parent.save()


def test_refresh_replay_is_unique_per_parent() -> None:
    parent = RefreshTokenFactory.create()
    values = {
        "parent": parent,
        "encryption_key_id": "key-1",
        "nonce": b"0" * 12,
        "response_ciphertext": b"ciphertext",
        "expires_at": timezone.now() + timedelta(seconds=10),
    }
    RefreshReplay.objects.create(**values)
    duplicate = RefreshReplay(**values)

    with pytest.raises(IntegrityError, match="parent_jti"):
        duplicate.save()
