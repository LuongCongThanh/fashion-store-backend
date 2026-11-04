"""Factory của identity (13 mục 9, 12 mục 4)."""

import hashlib
import uuid
from datetime import datetime, timedelta

import factory
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.identity.auth.tokens import IssuedTokenPair, issue_token_pair
from apps.identity.constants import AccountKind
from apps.identity.models import Account, RefreshToken

DEFAULT_PASSWORD = "Fashion-Store-2026"


class AccountFactory(DjangoModelFactory[Account]):
    """Tài khoản Staff đang hoạt động; trait `admin` cho Admin."""

    class Meta:
        model = Account

    email = factory.Sequence(lambda n: f"staff{n}@example.com")
    kind = AccountKind.STAFF
    password = factory.django.Password(DEFAULT_PASSWORD)

    class Params:
        admin = factory.Trait(kind=AccountKind.ADMIN)


class RefreshTokenFactory(DjangoModelFactory[RefreshToken]):
    """Refresh token gốc của một family, chưa dùng và còn hạn 12 giờ."""

    class Meta:
        model = RefreshToken

    jti = factory.LazyFunction(uuid.uuid4)
    account = factory.SubFactory(AccountFactory)
    family_id = factory.LazyFunction(uuid.uuid4)
    token_hash = factory.LazyFunction(lambda: hashlib.sha256(uuid.uuid4().bytes).hexdigest())
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=12))


def stored_refresh_session(*, account: Account, now: datetime) -> IssuedTokenPair:
    """Cặp token back-office phát tại `now` kèm RefreshToken gốc đã lưu hash, như sau đăng nhập."""
    issued = issue_token_pair(account=account, audience=settings.JWT_AUDIENCE_BACKOFFICE, now=now)
    RefreshTokenFactory.create(
        jti=issued.refresh_jti,
        account=account,
        family_id=issued.family_id,
        token_hash=hashlib.sha256(issued.refresh_token.encode()).hexdigest(),
        expires_at=issued.refresh_expires_at,
    )
    return issued


def jwt_test_keyring() -> dict[str, dict[str, str]]:
    """Keyring Ed25519 sinh mới cho test, cùng dạng `settings.JWT_SIGNING_KEYS`."""
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
