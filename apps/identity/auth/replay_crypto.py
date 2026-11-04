"""Mã hoá response refresh cho RefreshReplay bằng AESGCM (05 mục 2.1; ADR 0014).

Khoá 32 byte độc lập khoá ký JWT (`settings.REFRESH_REPLAY_KEY`). Associated data gắn
`parent_jti|family_id|aud` để ciphertext của token này không giải mã được cho token khác.
Không log payload, nonce hay ciphertext.
"""

import os
import uuid
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

NONCE_BYTES = 12


class ReplayUnavailable(Exception):
    """Không mã hoá/giải mã được replay: thiếu khoá, sai `key_id` hoặc ciphertext hỏng."""


@dataclass(frozen=True)
class SealedReplay:
    key_id: str
    nonce: bytes
    ciphertext: bytes


def _current_key() -> tuple[str, AESGCM]:
    key_id: str = settings.REFRESH_REPLAY_KEY_ID
    key: bytes = settings.REFRESH_REPLAY_KEY
    if not key_id or not key:
        raise ReplayUnavailable("Refresh replay key is not configured")
    return key_id, AESGCM(key)


def _associated_data(*, parent_jti: uuid.UUID, family_id: uuid.UUID, audience: str) -> bytes:
    return f"{parent_jti}|{family_id}|{audience}".encode()


def encrypt_replay(
    payload: bytes, *, parent_jti: uuid.UUID, family_id: uuid.UUID, audience: str
) -> SealedReplay:
    """Mã hoá `payload` bằng khoá hiện hành với nonce ngẫu nhiên mới.

    Raises:
        ReplayUnavailable: Chưa cấu hình khoá replay.
    """
    key_id, aesgcm = _current_key()
    nonce = os.urandom(NONCE_BYTES)
    aad = _associated_data(parent_jti=parent_jti, family_id=family_id, audience=audience)
    return SealedReplay(key_id=key_id, nonce=nonce, ciphertext=aesgcm.encrypt(nonce, payload, aad))


def decrypt_replay(
    sealed: SealedReplay, *, parent_jti: uuid.UUID, family_id: uuid.UUID, audience: str
) -> bytes:
    """Giải mã replay đã lưu; khoá đã xoay thì replay cũ không dùng được nữa.

    Raises:
        ReplayUnavailable: Thiếu khoá, `key_id` khác khoá hiện hành, AAD sai hoặc ciphertext
            bị sửa.
    """
    key_id, aesgcm = _current_key()
    if sealed.key_id != key_id:
        raise ReplayUnavailable("Refresh replay was sealed with another key")
    aad = _associated_data(parent_jti=parent_jti, family_id=family_id, audience=audience)
    try:
        return aesgcm.decrypt(sealed.nonce, sealed.ciphertext, aad)
    except InvalidTag, ValueError:
        # from None: không nối exception gốc của cryptography vào traceback/log
        raise ReplayUnavailable("Refresh replay cannot be decrypted") from None
