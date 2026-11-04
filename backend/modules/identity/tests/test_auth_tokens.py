import uuid
from datetime import timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import override_settings
from django.utils import timezone

from modules.identity.auth.tokens import InvalidToken, decode_access_token, issue_token_pair
from modules.identity.constants import AccountKind
from modules.identity.tests.factories import AccountFactory


def _keyring() -> dict[str, dict[str, str]]:
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


@pytest.mark.django_db
@override_settings(
    JWT_ISSUER="fashion-store-test",
    JWT_AUDIENCE_BACKOFFICE="backoffice",
    JWT_ACCESS_TTL_SECONDS=600,
    JWT_BACKOFFICE_REFRESH_TTL_SECONDS=43200,
    JWT_LEEWAY_SECONDS=30,
)
def test_issue_and_decode_backoffice_token_pair(settings: Any) -> None:
    settings.JWT_SIGNING_KEYS = _keyring()
    account = AccountFactory.create(kind=AccountKind.STAFF)
    now = timezone.now().replace(microsecond=0)

    pair = issue_token_pair(account=account, audience="backoffice", now=now)
    claims = decode_access_token(pair.access_token, expected_audience="backoffice", now=now)

    assert pair.token_type == "Bearer"
    assert pair.expires_in == 600
    assert claims.subject == account.id
    assert claims.kind == AccountKind.STAFF
    assert claims.token_version == 0
    assert jwt.get_unverified_header(pair.access_token) == {
        "alg": "EdDSA",
        "kid": "current",
        "typ": "JWT",
    }


@pytest.mark.django_db
@override_settings(
    JWT_ISSUER="fashion-store-test",
    JWT_AUDIENCE_BACKOFFICE="backoffice",
    JWT_ACCESS_TTL_SECONDS=600,
    JWT_BACKOFFICE_REFRESH_TTL_SECONDS=43200,
    JWT_LEEWAY_SECONDS=30,
)
def test_access_decoder_rejects_refresh_and_wrong_audience(settings: Any) -> None:
    settings.JWT_SIGNING_KEYS = _keyring()
    account = AccountFactory.create()
    now = timezone.now().replace(microsecond=0)
    pair = issue_token_pair(account=account, audience="backoffice", now=now)

    with pytest.raises(InvalidToken):
        decode_access_token(pair.refresh_token, expected_audience="backoffice", now=now)
    with pytest.raises(InvalidToken):
        decode_access_token(pair.access_token, expected_audience="store", now=now)


@pytest.mark.django_db
@override_settings(
    JWT_ISSUER="fashion-store-test",
    JWT_AUDIENCE_BACKOFFICE="backoffice",
    JWT_ACCESS_TTL_SECONDS=600,
    JWT_BACKOFFICE_REFRESH_TTL_SECONDS=43200,
    JWT_LEEWAY_SECONDS=30,
)
def test_access_decoder_rejects_future_iat_and_wrong_algorithm(settings: Any) -> None:
    settings.JWT_SIGNING_KEYS = _keyring()
    account = AccountFactory.create()
    now = timezone.now().replace(microsecond=0)
    key = settings.JWT_SIGNING_KEYS["current"]["private_key"]
    base = {
        "iss": "fashion-store-test",
        "aud": "backoffice",
        "sub": str(account.id),
        "token_use": "access",
        "kind": AccountKind.STAFF,
        "tv": 0,
        "jti": str(uuid.uuid4()),
        "iat": now + timedelta(minutes=2),
        "exp": now + timedelta(minutes=12),
    }
    future = jwt.encode(base, key, algorithm="EdDSA", headers={"kid": "current"})
    wrong_algorithm = jwt.encode(
        base, "not-a-real-secret", algorithm="HS256", headers={"kid": "current"}
    )

    with pytest.raises(InvalidToken):
        decode_access_token(future, expected_audience="backoffice", now=now)
    with pytest.raises(InvalidToken):
        decode_access_token(wrong_algorithm, expected_audience="backoffice", now=now)
