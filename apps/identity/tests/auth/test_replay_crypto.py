"""Mã hoá response refresh trong RefreshReplay (05 mục 2.1, 9; ADR 0014)."""

import os
import uuid
from dataclasses import replace
from typing import Any

import pytest

from apps.identity.auth.replay_crypto import (
    ReplayUnavailable,
    SealedReplay,
    decrypt_replay,
    encrypt_replay,
)

KEY_ID = "test-replay-1"
PAYLOAD = b'{"access_token": "a", "refresh_token": "r", "token_type": "Bearer", "expires_in": 600}'
PARENT_JTI = uuid.uuid4()
FAMILY_ID = uuid.uuid4()
AUDIENCE = "backoffice"


@pytest.fixture(autouse=True)
def replay_key(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = KEY_ID
    settings.REFRESH_REPLAY_KEY = os.urandom(32)


def _seal() -> SealedReplay:
    return encrypt_replay(PAYLOAD, parent_jti=PARENT_JTI, family_id=FAMILY_ID, audience=AUDIENCE)


def test_encrypt_then_decrypt_round_trips_with_fresh_nonce() -> None:
    first, second = _seal(), _seal()

    actual = decrypt_replay(first, parent_jti=PARENT_JTI, family_id=FAMILY_ID, audience=AUDIENCE)

    assert actual == PAYLOAD
    assert first.key_id == KEY_ID
    assert len(first.nonce) == 12
    assert first.nonce != second.nonce
    assert PAYLOAD not in first.ciphertext


@pytest.mark.parametrize("binding", ["parent_jti", "family_id", "audience"])
def test_decrypt_rejects_wrong_aad(binding: str) -> None:
    sealed = _seal()
    aad: dict[str, Any] = {"parent_jti": PARENT_JTI, "family_id": FAMILY_ID, "audience": AUDIENCE}
    aad[binding] = "store" if binding == "audience" else uuid.uuid4()

    with pytest.raises(ReplayUnavailable):
        decrypt_replay(sealed, **aad)


def test_decrypt_rejects_tampered_ciphertext() -> None:
    sealed = _seal()
    flipped = bytes([sealed.ciphertext[0] ^ 1]) + sealed.ciphertext[1:]
    tampered = replace(sealed, ciphertext=flipped)

    with pytest.raises(ReplayUnavailable):
        decrypt_replay(tampered, parent_jti=PARENT_JTI, family_id=FAMILY_ID, audience=AUDIENCE)


def test_decrypt_rejects_other_key_id(settings: Any) -> None:
    sealed = _seal()
    settings.REFRESH_REPLAY_KEY_ID = "test-replay-2"
    settings.REFRESH_REPLAY_KEY = os.urandom(32)

    with pytest.raises(ReplayUnavailable):
        decrypt_replay(sealed, parent_jti=PARENT_JTI, family_id=FAMILY_ID, audience=AUDIENCE)


def test_encrypt_without_key_raises_unavailable(settings: Any) -> None:
    settings.REFRESH_REPLAY_KEY_ID = ""
    settings.REFRESH_REPLAY_KEY = b""

    with pytest.raises(ReplayUnavailable):
        _seal()
