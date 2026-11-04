"""Phát và xác minh JWT theo OWASP JWT Cheat Sheet (05 mục 2, 9; 12 mục 2.5)."""

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
import time_machine

from modules.identity.auth.tokens import (
    ACCESS_CLAIMS,
    InvalidToken,
    decode_access_token,
    issue_token_pair,
)
from modules.identity.constants import AccountKind
from modules.identity.models import Account
from modules.identity.tests.factories import AccountFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("jwt_keyring")]

ISSUER = "fashion-store-test"
AUDIENCE = "backoffice"
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def jwt_settings(settings: Any) -> Iterator[None]:
    settings.JWT_ISSUER = ISSUER
    settings.JWT_ACCESS_TTL_SECONDS = 600
    settings.JWT_BACKOFFICE_REFRESH_TTL_SECONDS = 43_200
    settings.JWT_LEEWAY_SECONDS = 30
    # PyJWT kiểm `exp` theo đồng hồ hệ thống: cố định ở NOW để token phát tại NOW còn hạn
    with time_machine.travel(NOW, tick=False):
        yield


def _claims(token: str) -> dict[str, Any]:
    claims: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    return claims


def test_access_token_carries_required_claims_and_header() -> None:
    account = AccountFactory.create(kind=AccountKind.ADMIN)

    pair = issue_token_pair(account=account, audience=AUDIENCE, now=NOW)

    claims = _claims(pair.access_token)
    uuid.UUID(claims.pop("jti"))
    assert claims == {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": str(account.id),
        "token_use": "access",
        "kind": AccountKind.ADMIN,
        "tv": 0,
        "iat": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(minutes=10)).timestamp()),
    }
    header = jwt.get_unverified_header(pair.access_token)
    assert header == {"alg": "EdDSA", "kid": "current", "typ": "JWT"}
    assert pair.token_type == "Bearer"
    assert pair.expires_in == 600


def test_refresh_token_carries_family_and_twelve_hour_expiry() -> None:
    account = AccountFactory.create()

    pair = issue_token_pair(account=account, audience=AUDIENCE, now=NOW)

    claims = _claims(pair.refresh_token)
    refresh_exp = NOW + timedelta(hours=12)
    assert claims["token_use"] == "refresh"
    assert claims["aud"] == AUDIENCE
    assert claims["iss"] == ISSUER
    assert claims["fam"] == str(pair.family_id)
    assert claims["jti"] == str(pair.refresh_jti)
    assert claims["exp"] == int(refresh_exp.timestamp())
    assert pair.refresh_expires_at == refresh_exp
    assert jwt.get_unverified_header(pair.refresh_token)["kid"] == "current"


def test_decode_access_token_returns_verified_claims() -> None:
    account = AccountFactory.create()
    pair = issue_token_pair(account=account, audience=AUDIENCE, now=NOW)

    claims = decode_access_token(pair.access_token, expected_audience=AUDIENCE, now=NOW)

    assert claims.subject == account.id
    assert claims.kind == AccountKind.STAFF
    assert claims.token_version == 0
    assert claims.audience == AUDIENCE


def _valid_claims(account: Account) -> dict[str, Any]:
    return {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": str(account.id),
        "token_use": "access",
        "kind": AccountKind.STAFF,
        "tv": 0,
        "jti": str(uuid.uuid4()),
        "iat": NOW,
        "exp": NOW + timedelta(minutes=10),
    }


def _sign(claims: dict[str, Any], keyring: dict[str, dict[str, str]], kid: str = "current") -> str:
    return jwt.encode(
        claims, keyring["current"]["private_key"], algorithm="EdDSA", headers={"kid": kid}
    )


def _refresh_token(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return issue_token_pair(account=account, audience=AUDIENCE, now=NOW).refresh_token


def _store_audience(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return issue_token_pair(account=account, audience="store", now=NOW).access_token


def _future_iat(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    claims = _valid_claims(account)
    claims["iat"] = NOW + timedelta(minutes=2)
    return _sign(claims, keyring)


def _wrong_issuer(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return _sign({**_valid_claims(account), "iss": "attacker"}, keyring)


def _unknown_kid(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return _sign(_valid_claims(account), keyring, kid="retired")


def _hs256(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return jwt.encode(
        _valid_claims(account), "x" * 32, algorithm="HS256", headers={"kid": "current"}
    )


def _alg_none(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return jwt.encode(_valid_claims(account), "", algorithm="none", headers={"kid": "current"})


def _negative_tv(account: Account, keyring: dict[str, dict[str, str]]) -> str:
    return _sign({**_valid_claims(account), "tv": -1}, keyring)


REJECTED_TOKENS: dict[str, Callable[[Account, dict[str, dict[str, str]]], str]] = {
    "refresh-as-access": _refresh_token,
    "store-audience": _store_audience,
    "future-iat": _future_iat,
    "wrong-issuer": _wrong_issuer,
    "unknown-kid": _unknown_kid,
    "hs256": _hs256,
    "alg-none": _alg_none,
    "negative-tv": _negative_tv,
}


@pytest.mark.parametrize("case", list(REJECTED_TOKENS))
def test_decode_access_token_rejects_invalid_token(
    case: str, jwt_keyring: dict[str, dict[str, str]]
) -> None:
    token = REJECTED_TOKENS[case](AccountFactory.create(), jwt_keyring)

    with pytest.raises(InvalidToken):
        decode_access_token(token, expected_audience=AUDIENCE, now=NOW)


@pytest.mark.parametrize("claim", ACCESS_CLAIMS)
def test_decode_access_token_rejects_missing_claim(
    claim: str, jwt_keyring: dict[str, dict[str, str]]
) -> None:
    claims = _valid_claims(AccountFactory.create())
    del claims[claim]
    token = _sign(claims, jwt_keyring)

    with pytest.raises(InvalidToken):
        decode_access_token(token, expected_audience=AUDIENCE, now=NOW)
