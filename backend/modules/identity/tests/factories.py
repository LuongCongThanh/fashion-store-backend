"""Factory của identity (13 mục 9, 12 mục 4)."""

import factory
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from factory.django import DjangoModelFactory

from modules.identity.constants import AccountKind
from modules.identity.models import Account

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
