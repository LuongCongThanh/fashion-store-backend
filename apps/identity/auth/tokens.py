"""Phát và xác minh JWT của identity (05 mục 2)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt
from django.conf import settings

from apps.identity.constants import AccountKind
from apps.identity.models import Account

ALGORITHM = "EdDSA"
PURPOSE_ACCESS = "access"
PURPOSE_REFRESH = "refresh"
AUTH_SCHEME = "Bearer"
ACCESS_CLAIMS = ("iss", "aud", "sub", "token_use", "kind", "tv", "jti", "iat", "exp")


class InvalidToken(ValueError):
    """Token không đạt contract chữ ký/header/claims."""


class ExpiredToken(InvalidToken):
    """Chữ ký hợp lệ nhưng token đã hết hạn quá leeway; API trả `TOKEN_EXPIRED`."""


@dataclass(frozen=True)
class TokenPairDTO:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    refresh_jti: uuid.UUID
    family_id: uuid.UUID
    refresh_expires_at: datetime


@dataclass(frozen=True)
class AccessClaimsDTO:
    subject: uuid.UUID
    kind: str
    token_version: int
    jti: uuid.UUID
    audience: str


def _current_key() -> tuple[str, dict[str, str]]:
    try:
        kid = next(iter(settings.JWT_SIGNING_KEYS))
        key: dict[str, str] = settings.JWT_SIGNING_KEYS[kid]
    except (AttributeError, KeyError, StopIteration, TypeError) as exc:
        raise InvalidToken("JWT signing keyring is not configured") from exc
    if not key.get("private_key") or not key.get("public_key"):
        raise InvalidToken("Current JWT key must include private and public material")
    return kid, key


def _base_claims(
    *, account: Account, audience: str, token_use: str, jti: uuid.UUID, now: datetime, exp: datetime
) -> dict[str, Any]:
    return {
        "iss": settings.JWT_ISSUER,
        "aud": audience,
        "sub": str(account.id),
        "token_use": token_use,
        "kind": account.kind,
        "tv": account.token_version,
        "jti": str(jti),
        "iat": now,
        "exp": exp,
    }


def issue_token_pair(*, account: Account, audience: str, now: datetime) -> TokenPairDTO:
    """Phát cặp token; caller chịu trách nhiệm lưu hash refresh token."""
    kid, key = _current_key()
    access_jti, refresh_jti, family_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    access_exp = now + timedelta(seconds=settings.JWT_ACCESS_TTL_SECONDS)
    refresh_exp = now + timedelta(seconds=settings.JWT_BACKOFFICE_REFRESH_TTL_SECONDS)
    headers = {"kid": kid}
    access = jwt.encode(
        _base_claims(
            account=account,
            audience=audience,
            token_use=PURPOSE_ACCESS,
            jti=access_jti,
            now=now,
            exp=access_exp,
        ),
        key["private_key"],
        algorithm=ALGORITHM,
        headers=headers,
    )
    refresh_claims = _base_claims(
        account=account,
        audience=audience,
        token_use=PURPOSE_REFRESH,
        jti=refresh_jti,
        now=now,
        exp=refresh_exp,
    )
    refresh_claims["fam"] = str(family_id)
    refresh = jwt.encode(refresh_claims, key["private_key"], algorithm=ALGORITHM, headers=headers)
    return TokenPairDTO(
        access_token=access,
        refresh_token=refresh,
        token_type=AUTH_SCHEME,
        expires_in=settings.JWT_ACCESS_TTL_SECONDS,
        refresh_jti=refresh_jti,
        family_id=family_id,
        refresh_expires_at=refresh_exp,
    )


def decode_access_token(
    token: str, *, expected_audience: str, now: datetime | None = None
) -> AccessClaimsDTO:
    """Xác minh access token bằng allow-list EdDSA và keyring nội bộ."""
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != ALGORITHM or not isinstance(header.get("kid"), str):
            raise InvalidToken("Invalid JWT header")
        key = settings.JWT_SIGNING_KEYS[header["kid"]]["public_key"]
        payload = jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=expected_audience,
            issuer=settings.JWT_ISSUER,
            leeway=settings.JWT_LEEWAY_SECONDS,
            options={"require": list(ACCESS_CLAIMS)},
        )
        if payload["token_use"] != PURPOSE_ACCESS:
            raise InvalidToken("Wrong token purpose")
        if payload["kind"] not in AccountKind.values:
            raise InvalidToken("Invalid account kind")
        if type(payload["tv"]) is not int or payload["tv"] < 0:
            raise InvalidToken("Invalid token version")
        if type(payload["iat"]) not in (int, float) or type(payload["exp"]) not in (int, float):
            raise InvalidToken("Invalid timestamp claims")
        if payload["iat"] > payload["exp"]:
            raise InvalidToken("Token issued after expiry")
        if now is not None and payload["iat"] > now.timestamp() + settings.JWT_LEEWAY_SECONDS:
            raise InvalidToken("Token issued in the future")
        return AccessClaimsDTO(
            subject=uuid.UUID(payload["sub"]),
            kind=payload["kind"],
            token_version=payload["tv"],
            jti=uuid.UUID(payload["jti"]),
            audience=payload["aud"],
        )
    except InvalidToken:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredToken("Access token expired") from exc
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidToken("Invalid access token") from exc
